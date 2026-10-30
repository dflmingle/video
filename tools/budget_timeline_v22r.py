"""Measure actual V22 and opt-in V22-R trajectories, never animation time."""
import csv, hashlib, json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/v22r'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def measure(name):
    d=ROOT/'variants'/name;s=json.loads((d/'simulation.json').read_text());c=json.loads((d/'params.json').read_text());p=np.load(d/'trajectories.npy');fps=c['simulationFps'];nb=s['blueCount'];nr=s['redCount'];n=len(p)
    delta=np.diff(p,axis=0,prepend=p[:1]);velocity=delta*fps
    speed=np.linalg.norm(velocity,axis=-1);moving=speed>.02
    red_forward=velocity[:,nb:,1];blue_forward=-velocity[:,:nb,1]
    red_progress=(p[:,nb:,1]-p[0,nb:,1]).mean(axis=1)
    blue_progress=(p[0,:nb,1]-p[:,:nb,1]).mean(axis=1)
    blue=np.load(d/'blue-control.npy');states=blue[:,:,0].round().astype(int)
    events=s['events'];responses=json.loads((d/'hit-responses.json').read_text())
    if isinstance(responses,dict):responses=responses.get('events',[])
    gaps=np.array([cKDTree(q[:nb]).query(q[nb:])[0].min()-2*c['weaponEnvelopeRadius'] for q in p])
    step=np.linalg.norm(delta,axis=2)
    continuous_lower=np.minimum(gaps[1:],gaps[:-1])-.5*(step[1:,:nb].max(axis=1)+step[1:,nb:].max(axis=1))
    def onset(mask, count):
        ids=np.flatnonzero(mask.sum(axis=1)>=count)
        return float(ids[0]/fps) if len(ids) else None
    overlap=(moving[:,:nb].sum(axis=1)>0)&(moving[:,nb:].sum(axis=1)>0)
    intervals=[];start=None
    for f,v in enumerate(np.r_[overlap,False]):
        if v and start is None:start=f
        if not v and start is not None:intervals.append([start/fps,min(f/fps,(n-1)/fps)]);start=None
    blue_median_start=[]
    for group in range(c['blueGroups']):
        ids=[i for i,u in enumerate(s['units'][:nb]) if u['group']==group]
        blue_median_start.append(onset(moving[:,ids],len(ids)//2))
    arrivals=[u.get('arrival') for u in s['units'][:nb]]
    transitions=json.loads((d/'blue-transitions.json').read_text())
    observed_arrivals={e['id']:e['time'] for e in reversed(transitions) if e['state']=='TURNING' and e['time']<=(n-1)/fps+1e-9}
    stats=[]
    for a in np.arange(0,(n-1)/fps-1e-8,.1):
        b=min(a+.1,(n-1)/fps);f0=round(a*fps);f1=min(n-1,round(b*fps));sl=slice(f0+1,f1+1)
        releases=[e for e in events if a<=e['release']<b-1e-9]
        hits=[e for e in events if e.get('damage') is not None and a<=e['impact']<b-1e-9]
        center_speed=np.mean([(-velocity[sl,[i for i,u in enumerate(s['units'][:nb]) if u['group']==g],1]).mean() for g in range(c['blueGroups'])])
        stats.append(dict(start=round(float(a),6),end=round(float(b),6),redMeanForwardSpeed=float(red_forward[sl].mean()),redMeanProgress=float(red_progress[f1]),blueSquadCenterMeanForwardSpeed=float(center_speed),blueMeanAssemblyProgress=float(blue_progress[f1]),redMovingMean=float(moving[sl,nb:].sum(axis=1).mean()),blueMovingMean=float(moving[sl,:nb].sum(axis=1).mean()),bothMovingSeconds=float(overlap[sl].sum()/fps),simultaneousRedMovingMean=float((moving[sl,nb:].sum(axis=1)*overlap[sl]).mean()),simultaneousBlueMovingMean=float((moving[sl,:nb].sum(axis=1)*overlap[sl]).mean()),preparingShootersMean=float(np.isin(states[sl],[3,4,7]).sum(axis=1).mean()),releases=len(releases),inFlightAtEnd=sum(e['release']<=b<e['impact'] for e in events),hits=len(hits),deaths=sum(bool(e.get('killed')) for e in hits),hitOrFallStateMean=float((np.load(d/'member-states.npy',mmap_mode='r')[sl]>0).sum(axis=1).mean()),avoidingMean=float((np.load(d/'avoidance-causes.npy',mmap_mode='r')[sl]>=0).sum(axis=1).mean()),minimumSurfaceGap=float(gaps[f0:f1+1].min())))
    with (OUT/f'{name}-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(stats[0]));w.writeheader();w.writerows(stats)
    first=lambda key,valid=lambda e:True:min((e[key] for e in events if valid(e)),default=None)
    actual_hits=[e for e in events if e.get('damage') is not None]
    result=dict(name=name,frames=n,duration=(n-1)/fps,redGlobalHold=c.get('redChargeStart',0),redFirstMotion=onset(moving[:,nb:],1),redMajorityMotion=onset(moving[:,nb:],nr//2),redAllMotion=onset(moving[:,nb:],nr),blueFirstMotion=onset(moving[:,:nb],1),blueMajorityMotion=onset(moving[:,:nb],nb//2),blueGroupMajorityStart=blue_median_start,motionOverlapIntervals=intervals,motionOverlapDuration=sum(b-a for a,b in intervals),blueArrivals=[min(arrivals),max(arrivals)],firstAim=first('aimStart'),firstDraw=first('drawStart'),firstRelease=first('release'),firstActualHit=first('impact',lambda e:e.get('damage') is not None),arrows=len(events),actualHits=len(actual_hits),kills=sum(bool(e.get('killed')) for e in actual_hits),continuousShootingCoverage=None if not events else [(min(e['release'] for e in events)),min((n-1)/fps,max(e['impact'] for e in events))],redMeanForwardDistance=float(red_progress[-1]),redForwardDistanceRange=[float((p[-1,nb:,1]-p[0,nb:,1]).min()),float((p[-1,nb:,1]-p[0,nb:,1]).max())],redMeanPathLength=float(np.linalg.norm(delta[:,nb:],axis=2).sum(axis=0).mean()),blueMeanForwardDistance=float(blue_progress[-1]),minimumSurfaceGap=float(gaps.min()),betweenFrameConservativeGap=float(continuous_lower.min()),targetDurationReached=(n-1)/fps>=3.8,noIdleBuckets=all(x['redMovingMean']>0 or x['blueMovingMean']>0 or x['releases'] or x['inFlightAtEnd'] or x['hits'] for x in stats),sourceSHA256={f:sha(d/f) for f in ['params.json','simulation.json','trajectories.npy']})
    result['blueArrivalFieldCaveat']='Unit arrival may retain an estimate for not-yet-arrived members at the safe cut; use observed arrival transitions below.'
    result['blueObservedArrivals']=dict(count=len(observed_arrivals),first=min(observed_arrivals.values(),default=None),last=max(observed_arrivals.values(),default=None),notObservedBeforeCut=nb-len(observed_arrivals))
    fig,axs=plt.subplots(3,1,figsize=(9,8),sharex=True);t=np.arange(n)/fps
    axs[0].plot(t,red_progress,label='Red mean forward displacement');axs[0].plot(t,blue_progress,label='Blue mean assembly displacement');axs[0].set_ylabel('World units');axs[0].legend()
    axs[1].plot(t,moving[:,nb:].sum(axis=1),label='Red moving members');axs[1].plot(t,moving[:,:nb].sum(axis=1),label='Blue moving members');axs[1].set_ylabel('People');axs[1].legend()
    axs[2].plot(t,gaps,label='Weapon envelope surface gap');axs[2].axhline(4,color='r',ls='--',label='Minimum 4.0');axs[2].set_ylabel('World units');axs[2].set_xlabel('Seconds');axs[2].legend()
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle(name+' / measured world coordinates');fig.tight_layout();fig.savefig(OUT/f'{name}-curves.png',dpi=130);plt.close(fig)
    return result

def main():
    results=[measure(x) for x in ['V22-C','V22R-extended','V22R-immediate','V22R-overlap']]
    checks=dict(baselineExtendedTrajectoriesEqual=sha(ROOT/'variants/V22-C/trajectories.npy')==sha(ROOT/'variants/V22R-extended/trajectories.npy'),positionsAndSpeedUnchanged=True)
    orig=json.loads((ROOT/'variants/V22-C/simulation.json').read_text());new=json.loads((ROOT/'variants/V22R-overlap/simulation.json').read_text())
    checks['positionsAndSpeedUnchanged']=all(a['start']==b['start'] and a.get('speed')==b.get('speed') for a,b in zip(orig['units'],new['units']))
    overlap=results[-1]
    checks.update(redMajorityByFrame3=overlap['redMajorityMotion']<=3/60,blueGroupMajoritiesByFrame6=max(overlap['blueGroupMajorityStart'])<=6/60,continuousOverlapOver2Seconds=overlap['motionOverlapDuration']>2.,safeClearance=overlap['betweenFrameConservativeGap']>=4.,noIdleBuckets=overlap['noIdleBuckets'])
    (OUT/'timeline-budget.json').write_text(json.dumps(dict(scenarios=results,checks=checks,limitation='No 4-second production candidate exists: all simulations auto-cut at the original 4.0 clearance; no unsafe frame rendered. Counts and movement are data evidence, not visual approval.'),indent=2),encoding='utf8')
    print(json.dumps({'scenarios':[{k:x[k] for k in ['name','duration','redFirstMotion','redMajorityMotion','blueFirstMotion','blueGroupMajorityStart','motionOverlapDuration','firstRelease','firstActualHit','arrows','minimumSurfaceGap','betweenFrameConservativeGap','redMeanForwardDistance']} for x in results],'checks':checks},indent=2))
    assert all(checks.values())

if __name__=='__main__':main()
