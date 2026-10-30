"""V21 deterministic acceptance audit.

Read-only: compares authored trajectories/control/event data and writes reports.
Usage: python tools/validate_v21.py --variant FINAL --old V20-B --new FINAL
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "V21-validation"
OUT.mkdir(parents=True, exist_ok=True)
STATE_NAMES = {0:"WAITING",1:"MOVING",2:"ARRIVING",3:"AIMING",4:"DRAWING",5:"RELEASING",6:"RECOVERING",7:"TURNING"}

def read_variant(name):
    d = ROOT / "variants" / name
    s = json.loads((d / "simulation.json").read_text(encoding="utf8"))
    cfg = s.get("config", {})
    frames, units = int(s["frames"]), s["units"]
    nb, nr = int(s["blueCount"]), int(s["redCount"])
    traj = np.fromfile(d / "trajectories.f32", np.float32).reshape(frames, nb + nr, 2)
    dt = 1.0 / float(cfg.get("simulationFps", cfg.get("fps", 60)))
    controls = None
    cp = d / "blue-control.f32"
    if cp.exists() and frames and nb:
        cols = len(s.get("controlColumns", [])) or int(np.fromfile(cp, np.float32).size // (frames * nb))
        controls = np.fromfile(cp, np.float32).reshape(frames, nb, cols)
    return dict(name=name, dir=d, sim=s, cfg=cfg, units=units, frames=frames, nb=nb, nr=nr, traj=traj, dt=dt, controls=controls)

def sha(path):
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def state_spread(v):
    c=v["controls"]; out={}
    if c is None: return out
    for st,name in STATE_NAMES.items():
        per=[]
        for j in range(v["nb"]):
            ix=np.where(np.rint(c[:,j,0]).astype(int)==st)[0]
            if len(ix): per.append(ix[0]*v["dt"])
        if per: out[name]={"count":len(per),"min":float(min(per)),"max":float(max(per)),"range":float(max(per)-min(per)),"std":float(np.std(per))}
    return out

def phase_dispersion(v):
    c=v["controls"]
    if c is None or c.shape[2] < 7: return {}
    out=[]
    # circular std and pairwise normalized spread, only active archers.
    for f in range(v["frames"]):
        active=np.isin(np.rint(c[f,:,0]).astype(int),[1,2,3,4,5,6,7])
        if active.sum()<2: continue
        phase=c[f,active,6].astype(float)%1.0
        ang=phase*2*np.pi; r=float(np.hypot(np.mean(np.cos(ang)),np.mean(np.sin(ang))))
        out.append((f*v["dt"],float(math.sqrt(max(0.0,-2.0*math.log(max(r,1e-8))))),float(np.std(phase))))
    if not out:return {}
    a=np.array(out)
    return {"frames":len(out),"circularStdP50":float(np.percentile(a[:,1],50)),"circularStdP90":float(np.percentile(a[:,1],90)),"linearStdP50":float(np.percentile(a[:,2],50)),"linearStdMax":float(a[:,2].max())}

def slot_metrics(v):
    cfg=v["cfg"]; blue=v["traj"][:,:v["nb"]]; units=v["units"][:v["nb"]]
    end=[]; offset_norm=[]; lateral=[]; depth=[]
    for j,u in enumerate(units):
        off=np.asarray(u.get("slotOffset",[0.0,0.0]),float)
        expected=np.asarray(u["start"],float)+np.array([off[0],-float(cfg.get("blueAdvance",7.5))+off[1]])
        delta=blue[-1,j]-expected; end.append(delta); offset_norm.append(float(np.linalg.norm(off))); lateral.append(float(delta[0])); depth.append(float(delta[1]))
    end=np.asarray(end); start=np.asarray([u["start"] for u in units],float)
    # Compare actual motion with each member's authored curved corridor.
    nominal_z=start[:,1]-float(cfg.get("blueAdvance",7.5))
    q=np.clip((blue[:,:,1]-start[:,1])/(nominal_z-start[:,1]),0,1)
    path_bend=np.asarray([float(u.get("pathBend",0.0)) for u in units])
    base_x=start[:,0][None,:]+path_bend[None,:]*np.sin(np.pi*q)
    soft_drift=blue[:,:,0]-base_x
    final_q=q[-1]; arrived=final_q>=0.999
    arr_err=np.linalg.norm(end[arrived],axis=1) if np.any(arrived) else np.zeros(0)
    return {"slotOffsetNormMax":float(max(offset_norm,default=0)),"slotOffsetNormP95":float(np.percentile(offset_norm,95)) if offset_norm else 0.0,"arrivedMemberCount":int(arrived.sum()),"endpointErrorArrivedMax":float(arr_err.max()) if len(arr_err) else None,"endpointErrorArrivedP95":float(np.percentile(arr_err,95)) if len(arr_err) else None,"endpointErrorArrivedMean":float(arr_err.mean()) if len(arr_err) else None,"softDriftFrameMax":float(np.max(np.abs(soft_drift))),"softDriftFrameP95":float(np.percentile(np.abs(soft_drift),95)),"endpointDeltaSamples":end.round(6).tolist()[:12]}

def local_motion(v):
    p=v["traj"][:,v["nb"]:,:]; dt=v["dt"]
    dz=np.diff(p[:,:,1],axis=0); dx=np.diff(p[:,:,0],axis=0); speed=np.linalg.norm(np.diff(p,axis=0),axis=2)/dt
    backward=np.argwhere(dz < -1e-4)
    fronts=np.max(p[:,:,1],axis=1); avg=np.mean(p[:,:,1],axis=1); med=np.median(p[:,:,1],axis=1)
    hit=[]
    for e in v["sim"].get("events",[]):
        if e.get("impact") is None or e.get("resolution")!="IMPACT_IN_SHOT": continue
        rid=int(e["target"])-v["nb"]; f=min(v["frames"]-1,max(1,round(float(e["impact"])/dt))); before=max(0,f-3); after=min(v["frames"]-1,f+6)
        local_before=float(np.mean(p[before, max(0,rid-2):min(v["nr"],rid+3),1]))
        target_before=float(p[before,rid,1]); target_after=float(p[after,rid,1]); target_delta=target_after-target_before
        squad=int(v["units"][v["nb"]+rid].get("platoon",-1))
        members=[k for k,u in enumerate(v["units"][v["nb"]:],0) if int(u.get("platoon",-2))==squad and k!=rid]
        healthy_delta=float(np.mean(p[after,members,1]-p[before,members,1])) if members else None
        hit.append({"id":e.get("id"),"time":float(e["impact"]),"target":e.get("targetID"),"targetForwardDelta":target_delta,"healthyNeighborForwardDelta":healthy_delta,"globalFrontDelta":float(fronts[after]-fronts[before]),"globalMeanDelta":float(avg[after]-avg[before])})
    return {"backwardStepCount":int(len(backward)),"backwardStepMin":float(dz.min()) if dz.size else 0.0,"globalFrontDelta":float(fronts[-1]-fronts[0]),"globalMeanDelta":float(avg[-1]-avg[0]),"frontMonotonicViolations":int(np.sum(np.diff(fronts)<-1e-4)),"meanMonotonicViolations":int(np.sum(np.diff(avg)<-1e-4)),"hitSamples":hit[:64],"hitCount":len(hit),"hitTargetForwardP50":float(np.median([x["targetForwardDelta"] for x in hit])) if hit else None,"hitHealthyNeighborForwardP50":float(np.median([x["healthyNeighborForwardDelta"] for x in hit if x["healthyNeighborForwardDelta"] is not None])) if hit else None}

def safety(v):
    from scipy.spatial import cKDTree
    p=v["traj"]; mins=[]; frames=[]
    for f in range(v["frames"]): mins.append(float(cKDTree(p[f,:v["nb"]]).query(p[f,v["nb"]:])[0].min()))
    mins=np.asarray(mins); env=float(v["sim"].get("config",{}).get("weaponEnvelopeRadius",3.1)); required=float(v["sim"].get("config",{}).get("minimumEnemyClearance",4)); surface=mins-2*env
    return {"centerDistanceMin":float(mins.min()),"surfaceClearanceMin":float(surface.min()),"requiredSurfaceClearance":required,"contactFrames":int(np.sum(surface<0)),"unsafeFrames":int(np.sum(surface<required)),"minimumAtSeconds":float(np.argmin(surface)*v["dt"]),"noContact":bool(np.all(surface>=0))}

def arrows(v):
    ev=v["sim"].get("events",[]); rel=sorted(float(e["release"]) for e in ev if e.get("release") is not None); imp=sorted(float(e["impact"]) for e in ev if e.get("impact") is not None and e.get("resolution")=="IMPACT_IN_SHOT")
    def gaps(a): return np.diff(a).tolist() if len(a)>1 else []
    bins=np.arange(0,v["sim"]["config"]["duration"]+0.2501,.25); hist,_=np.histogram(rel,bins=bins) if len(bins)>1 else ([],[])
    post=[x for x in gaps(rel) if x>=0]
    return {"releaseCount":len(rel),"impactCount":len(imp),"firstRelease":rel[0] if rel else None,"firstImpact":imp[0] if imp else None,"preFirstReleaseEmpty":not bool([x for x in imp if not rel or x<rel[0]]),"releaseGapMaxAfterFirst":float(max(post)) if post else None,"releaseGapP95":float(np.percentile(post,95)) if post else None,"releaseHistogram025":{f"{bins[i]:.2f}-{bins[i+1]:.2f}":int(hist[i]) for i in range(len(hist))},"impactFlightP50":float(np.median([e["impact"]-e["release"] for e in ev if e.get("impact") is not None and e.get("resolution")=="IMPACT_IN_SHOT"])) if imp else None}

def audit(v):
    files=["simulation.json","trajectories.f32","blue-control.f32","safety-and-causality.json"]
    hashes={x:sha(v["dir"]/x) for x in files if (v["dir"]/x).exists()}
    return {"variant":v["name"],"version":v["sim"].get("version"),"frames":v["frames"],"duration":float(v["frames"]-1)*v["dt"],"counts":{"blue":v["nb"],"red":v["nr"]},"fileSHA256":hashes,"slotOffsets":slot_metrics(v),"archerStateSpread":state_spread(v),"archerPhaseDispersion":phase_dispersion(v),"localMotion":local_motion(v),"safety":safety(v),"arrows":arrows(v)}

def compare(old,new):
    return {"old":old["name"],"new":new["name"],"sameFrames":old["frames"]==new["frames"],"sameCounts":(old["nb"],old["nr"])==(new["nb"],new["nr"]),"sameInitialTrajectories":bool(np.allclose(old["traj"][0],new["traj"][0],atol=1e-5)),"sameInitialRedBlue":bool(np.allclose(old["traj"][0,:,:],new["traj"][0,:,:],atol=1e-5)),"metrics":{"firstReleaseDelta":(arrows(new)["firstRelease"] or 0)-(arrows(old)["firstRelease"] or 0),"firstImpactDelta":(arrows(new)["firstImpact"] or 0)-(arrows(old)["firstImpact"] or 0),"surfaceClearanceDelta":safety(new)["surfaceClearanceMin"]-safety(old)["surfaceClearanceMin"],"releaseCountDelta":arrows(new)["releaseCount"]-arrows(old)["releaseCount"],"impactCountDelta":arrows(new)["impactCount"]-arrows(old)["impactCount"],"backwardStepDelta":local_motion(new)["backwardStepCount"]-local_motion(old)["backwardStepCount"]}}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='FINAL');ap.add_argument('--old',default='V20-B');ap.add_argument('--new',default=None);args=ap.parse_args(); v=read_variant(args.variant); report=audit(v); (OUT/f'{args.variant}-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    old=read_variant(args.old); new=read_variant(args.new or args.variant); cmp=compare(old,new); (OUT/f'{args.old}-vs-{args.new or args.variant}.json').write_text(json.dumps(cmp,indent=2),encoding='utf8')
    # Stable same-time CSV template for later encoded-video/screenshot joins.
    rows=[]
    for f in range(min(old["frames"],new["frames"])):
        def row(v):
            p=v["traj"][f]; d=np.linalg.norm(p[:v["nb"],None,:]-p[v["nb"]:,None,:],axis=2).min() if False else None
            return [float(f*v["dt"]),float(np.max(p[v["nb"]:,1])),float(np.mean(p[v["nb"]:,1]))]
        ro=row(old); rn=row(new); rows.append(ro+rn[1:])
    with (OUT/f'{args.old}-vs-{args.new or args.variant}-same-time.csv').open('w',newline='',encoding='utf8') as fp:
        w=csv.writer(fp);w.writerow(['seconds','old_front_z','old_mean_z','new_front_z','new_mean_z']);w.writerows(rows)
    print(json.dumps({'audit':str(OUT/f'{args.variant}-audit.json'),'comparison':str(OUT/f'{args.old}-vs-{args.new or args.variant}.json'),'sameTime':str(OUT/f'{args.old}-vs-{args.new or args.variant}-same-time.csv'),'status':'PASS_READ_ONLY'},ensure_ascii=False,indent=2))
if __name__=='__main__': main()

