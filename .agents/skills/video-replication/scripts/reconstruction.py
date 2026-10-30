"""Engine-neutral layout math adapted from audited local fitting methods."""
import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment
from scipy.spatial.distance import cdist

def stable_mask_layout(mask, previous):
    """Deterministic farthest points in support; Hungarian maps old IDs to points."""
    yy,xx=np.where(mask>0); candidates=np.c_[xx,yy].astype(float)
    old=np.asarray(previous,float)
    if not len(old) or len(candidates)<len(old):raise ValueError('Insufficient support or no members')
    chosen=[int(np.argmin(np.linalg.norm(candidates-candidates.mean(0),axis=1)))]
    distance=np.linalg.norm(candidates-candidates[chosen[0]],axis=1)
    for _ in range(len(old)-1):
        j=int(np.argmax(distance)); chosen.append(j)
        distance=np.minimum(distance,np.linalg.norm(candidates-candidates[j],axis=1))
    target=candidates[chosen]; rows,cols=linear_sum_assignment(cdist(old,target))
    result=np.empty_like(old); result[rows]=target[cols]
    return result

def occupation_quantiles(mask,uv):
    """Area-CDF x and conditional y-CDF; handles disjoint occupied runs."""
    occupied=np.asarray(mask)>0
    xs=np.flatnonzero(occupied.sum(0))
    if not len(xs):raise ValueError('Empty support')
    uv=np.asarray(uv,float)
    if uv.ndim!=2 or uv.shape[1]!=2 or np.any((uv<0)|(uv>=1)):raise ValueError('UV must lie in [0,1)')
    weights=occupied[:,xs].sum(0); cdf=np.cumsum(weights)/weights.sum(); result=[]
    for u,v in uv:
        x=xs[min(len(xs)-1,int(np.searchsorted(cdf,u,side='right')))]; ys=np.flatnonzero(occupied[:,x])
        result.append([float(x),float(ys[min(len(ys)-1,int(v*len(ys)))])])
    return np.array(result)

def fit_path(times, positions, observed_times, observed_positions, smooth_weight, bound):
    """Bounded least squares of member positions, not a tactical path generator.
    All data must share coordinates. Caller supplies held-out observations separately.
    """
    ts=np.asarray(times,float); base=np.asarray(positions,float); ot=np.asarray(observed_times,float); obs=np.asarray(observed_positions,float)
    if len(ts)<2 or np.any(np.diff(ts)<=0) or base.shape!=(len(ts),2):raise ValueError('Invalid path')
    if len(ot)==0 or np.any(ot<ts[0]) or np.any(ot>ts[-1]) or obs.shape!=(len(ot),2):raise ValueError('Invalid observations')
    def residual(flat):
        p=base+flat.reshape(base.shape)
        predicted=np.c_[np.interp(ot,ts,p[:,0]),np.interp(ot,ts,p[:,1])]
        vel=np.diff(p,axis=0)/np.diff(ts)[:,None]
        return np.r_[(predicted-obs).ravel(), (smooth_weight*np.diff(vel,axis=0)).ravel(),(.01*flat)]
    sol=least_squares(residual,np.zeros(base.size),bounds=(-bound,bound),loss='soft_l1')
    return dict(positions=(base+sol.x.reshape(base.shape)).tolist(),cost=float(sol.cost),success=bool(sol.success),validation='REQUIRES_HELDOUT_AND_VISUAL_REVIEW')

def continuous_min_distance(a0,a1,b0,b1):
    r=np.asarray(a0)-np.asarray(b0); v=np.asarray(a1)-np.asarray(b1)-r
    t=float(np.clip(-np.dot(r,v)/np.dot(v,v),0,1)) if np.dot(v,v)>0 else 0.
    return float(np.linalg.norm(r+t*v))

def resolve(layers, t):
    """Return highest-priority available absolute position and writer; no silent sum."""
    valid=[x for x in layers if x['start']<=t<=x['end']]
    if not valid:return None
    priorities=[x['priority'] for x in valid]
    if len(priorities)!=len(set(priorities)):raise ValueError('Ambiguous active writer priorities')
    chosen=max(valid,key=lambda x:x['priority'])
    return dict(position=chosen['position'],writer=chosen['id'],inputs_hash=chosen['inputs_hash'])
