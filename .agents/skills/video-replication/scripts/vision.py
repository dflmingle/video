"""Traditional CV primitives; outputs are candidates, never semantic truth."""
import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

def mask(im, spec):
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    m = np.zeros(im.shape[:2], np.uint8)
    for lo, hi in spec['hsv']:
        m |= cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
    for x0,y0,x1,y1 in spec.get('exclude', []):
        h,w = m.shape
        m[round(y0*h):round(y1*h), round(x0*w):round(x1*w)] = 0
    if 'roi' in spec:
        x0,y0,x1,y1 = spec['roi']; h,w = m.shape
        keep = np.zeros_like(m)
        keep[round(y0*h):round(y1*h), round(x0*w):round(x1*w)] = 255
        m &= keep
    k = int(spec.get('close_px', 1))
    if k > 1:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((k,k),np.uint8))
    return m

def components(m, minimum=10):
    n, lab, stats, centers = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1,n):
        x,y,w,h,area = map(int, stats[i])
        if area < minimum:
            continue
        local = np.uint8(lab[y:y+h,x:x+w] == i) * 255
        contours,_ = cv2.findContours(local, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea) + np.array([[[x,y]]])
        contour = cv2.approxPolyDP(contour, .7, True).reshape(-1,2)
        yy,xx = np.where(local)
        points = np.c_[xx+x, yy+y].astype(float)
        cov = np.cov(points.T) if len(points)>2 else np.eye(2)
        vals,vecs = np.linalg.eigh(cov); axis=vecs[:,-1]
        projected = (points-centers[i]) @ np.c_[axis,[-axis[1],axis[0]]]
        extent = np.percentile(projected,98,axis=0)-np.percentile(projected,2,axis=0)
        out.append(dict(center=centers[i].tolist(), contour=contour.tolist(),
                        bbox=[x,y,w,h], area_px=area, occupancy=area/max(1,w*h),
                        axis_radians=float(np.arctan2(axis[1],axis[0]) % np.pi),
                        axis_is_heading=False, extent_px=extent.tolist(),
                        anisotropy=float(vals[-1]/max(vals[0],1e-6))))
    return out

def associate(active, detections, t, gate, max_gap):
    """One-to-one gated association; split/merge/physical identity remain unknown."""
    ids = [k for k,v in active.items() if 0 < t-v[-1]['t'] <= max_gap]
    if not ids or not detections:
        return {}
    pred = []
    for k in ids:
        rows = active[k]; p = np.array(rows[-1]['center'])
        if len(rows)>1:
            dt = rows[-1]['t']-rows[-2]['t']
            p = p+(p-np.array(rows[-2]['center']))/dt*(t-rows[-1]['t'])
        pred.append(p)
    cost = np.linalg.norm(np.array(pred)[:,None,:]-np.array([d['center'] for d in detections])[None,:,:],axis=2)
    # Dummy columns allow rejecting a match rather than stealing another identity.
    augmented = np.hstack([np.where(cost<=gate,cost,gate*100), np.full((len(ids),len(ids)),gate+1)])
    rows,cols = linear_sum_assignment(augmented)
    return {int(c):ids[r] for r,c in zip(rows,cols) if c<len(detections) and cost[r,c]<=gate}

def binary_metrics(a,b):
    aa,bb=a>0,b>0
    if not aa.any() and not bb.any():
        return dict(iou=None, symmetric_chamfer_px=None, density_mae=0., status='BOTH_EMPTY')
    inter=(aa&bb).sum(); union=(aa|bb).sum()
    def dist(x,y):
        if not x.any() or not y.any(): return None
        d=cv2.distanceTransform(np.uint8(~y)*255,cv2.DIST_L2,3)
        return float(d[x].mean())
    d1,d2=dist(aa,bb),dist(bb,aa)
    ga=cv2.GaussianBlur(aa.astype(np.float32),(0,0),3)
    gb=cv2.GaussianBlur(bb.astype(np.float32),(0,0),3)
    return dict(iou=float(inter/max(1,union)), symmetric_chamfer_px=None if d1 is None or d2 is None else (d1+d2)/2,
                density_mae=float(np.abs(ga-gb).mean()), source_pixels=int(aa.sum()), candidate_pixels=int(bb.sum()),status='MEASURED')

def register(a,b,model='affine',max_error=3.):
    gray=lambda x:cv2.cvtColor(x,cv2.COLOR_BGR2GRAY)
    detector=cv2.SIFT_create()
    ka,da=detector.detectAndCompute(gray(a),None); kb,db=detector.detectAndCompute(gray(b),None)
    result=dict(status='UNKNOWN',model=model,matrix=None,reason='INSUFFICIENT_MATCHES')
    if da is None or db is None or len(db)<2:return result
    pairs=cv2.BFMatcher().knnMatch(da,db,k=2)
    good=[m for pair in pairs if len(pair)==2 for m,n in [pair] if m.distance<.75*n.distance]
    if len(good)<12:return result
    src=np.float32([ka[m.queryIdx].pt for m in good]); dst=np.float32([kb[m.trainIdx].pt for m in good])
    held=np.arange(len(good))%4==0
    if model=='homography':
        M,inliers=cv2.findHomography(src[~held],dst[~held],cv2.RANSAC,max_error)
    else:
        M,inliers=cv2.estimateAffinePartial2D(src[~held],dst[~held],method=cv2.RANSAC,ransacReprojThreshold=max_error)
        if M is not None:M=np.vstack([M,[0,0,1]])
    if M is None:return result
    p=cv2.perspectiveTransform(src[held,None,:],M)[:,0,:]
    errors=np.linalg.norm(p-dst[held],axis=1)
    # A good median can hide a large moving/ambiguous region. Do not promote that
    # transform as a reliable whole-frame registration without regional review.
    accepted=bool(np.median(errors)<=max_error and np.percentile(errors,95)<=3*max_error and inliers.mean()>=.5)
    result.update(status='PASS' if accepted else 'FAIL', matrix=M.tolist() if accepted else None,
                  reason='HELDOUT_GATE', matches=len(good), fit_inlier_ratio=float(inliers.mean()),
                  heldout_count=int(held.sum()),heldout_median_px=float(np.median(errors)),
                  heldout_p95_px=float(np.percentile(errors,95)),semantic_alignment='UNKNOWN')
    return result

def flow(a,b,max_error=1.):
    a=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY); b=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
    p=cv2.goodFeaturesToTrack(a,400,.01,6)
    if p is None:return dict(status='UNKNOWN',points=[],reason='NO_FEATURES')
    q,st,_=cv2.calcOpticalFlowPyrLK(a,b,p,None)
    if q is None:return dict(status='UNKNOWN',points=[],reason='LK_FAILED')
    back,st2,_=cv2.calcOpticalFlowPyrLK(b,a,q,None)
    if back is None:return dict(status='UNKNOWN',points=[],reason='BACKWARD_FAILED')
    error=np.linalg.norm((back-p)[:,0,:],axis=1)
    keep=(st[:,0]>0)&(st2[:,0]>0)&(error<=max_error)
    return dict(status='CANDIDATES',total=len(p),retained=int(keep.sum()),
                identity='UNKNOWN',points=[dict(a=x.tolist(),b=y.tolist(),fb_error=float(e)) for x,y,e in zip(p[keep,0],q[keep,0],error[keep])])
