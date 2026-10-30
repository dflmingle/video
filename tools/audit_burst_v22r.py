"""Causal, geometry and healthy-rear speed evidence for A/C1/C2."""
import collections,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parents[1];D=R/'docs/v22r-burst';proposal=json.loads((D/'proposal.json').read_text());fps=60
results=[]
for label,variant in [('A','V22R-fast-A'),('C1','V22R-C1'),('C2','V22R-C2')]:
 v=R/'variants'/variant;s=json.loads((v/'simulation.json').read_text(encoding='utf8'));c=s['config'];p=np.load(v/'trajectories.npy');bc=np.load(v/'blue-control.npy');nb=s['blueCount'];n=len(p);duration=round(c['duration']*fps)/fps;frames=round(duration*fps);events=[e for e in s['events'] if e['release']<duration];hits=[e for e in s['events'] if e['resolution']=='IMPACT_IN_SHOT' and e['impact']<duration];death=np.array([u.get('deathTime') if u.get('deathTime') is not None else 1e6 for u in s['units'][nb:]]);firstHit=np.full(s['redCount'],1e6)
 for e in hits:firstHit[e['target']-nb]=min(firstHit[e['target']-nb],e['impact'])
 vel=np.concatenate([np.zeros_like(p[:1]),np.diff(p,axis=0)*fps]);rear=np.array([u['color'] in ['red','orange'] for u in s['units'][nb:]]);groups=collections.defaultdict(list)
 for j,u in enumerate(s['units'][nb:]):groups[u['platoon']].append(j)
 front=np.zeros(s['redCount'],bool)
 for ids in groups.values():
  z=p[0,nb+np.array(ids),1];front[ids]=z>=z.max()-1.7
 gaps=[];spacing=[];deadError=[];rows=[]
 for k,q in enumerate(p):
  t=k/fps;gap=float(cKDTree(q[:nb]).query(q[nb:])[0].min()-2*c['weaponEnvelopeRadius']);gaps.append(gap);spacing.append(float(cKDTree(q[nb:]).query(q[nb:],k=2)[0][:,1].min()))
  if k:
   alreadyDead=death<(k-1)/fps-1e-8;deadError.append(float(np.linalg.norm(q[nb:][alreadyDead]-p[k-1,nb:][alreadyDead],axis=1).max()) if alreadyDead.any() else 0.)
  if k%6==0:
   healthy=firstHit>t;healthyRear=healthy&rear;speed=np.linalg.norm(vel[k,nb:],axis=1);movingBlue=np.linalg.norm(vel[k,:nb],axis=1)
   rows.append(dict(time=t,unhitCount=int(healthy.sum()),unhitMedianSpeed=float(np.median(speed[healthy])),unhitP10Speed=float(np.quantile(speed[healthy],.1)),unhitBelow10=int((speed[healthy]<10).sum()),unhitRearCount=int(healthyRear.sum()),unhitRearMedianSpeed=float(np.median(speed[healthyRear])),unhitRearP10Speed=float(np.quantile(speed[healthyRear],.1)),redLive=int((death>t).sum()),blueMoving=int((movingBlue>.02).sum()),blueAssembly=float((p[0,:nb,1]-q[:nb,1]).mean()),releases=sum(t<=e['release']<min(t+.1,duration) for e in events),flying=sum(e['release']<=t<e['impact'] for e in events),hits=sum(t<=e['impact']<min(t+.1,duration) for e in hits),kills=sum(t<=e['impact']<min(t+.1,duration) and e.get('killed',False) for e in hits),surfaceGap=gap))
 steps=np.linalg.norm(np.diff(p,axis=0),axis=2);lower=np.minimum(gaps[:-1],gaps[1:])-.5*(steps[:,:nb].max(1)+steps[:,nb:].max(1));firstRelease=min(e['release'] for e in events);firstWave=[e for e in events if firstRelease<=e['release']<firstRelease+.5];shooterCounts=collections.Counter(e['shooter'] for e in events);releasePerFrame=collections.Counter(e['releaseFrame'] for e in events);impactCounts=collections.Counter(e['target'] for e in hits);hp=np.full(s['redCount'],c['redHitPoints']);pending=collections.defaultdict(list);causalErrors=[];capacityErrors=[];seenShooters=set();maxPending=0
 for k in range(n):
  for e in pending.pop(k,[]):
   j=e['target']-nb
   if hp[j]<=0:causalErrors.append(e['id']+' targeted already dead')
   hp[j]-=e['plannedDamage']
   if e['damage']!=e['plannedDamage'] or bool(e['killed'])!=bool(hp[j]<=0):causalErrors.append(e['id']+' wrong damage result')
  for e in [e for e in s['events'] if e['releaseFrame']==k]:
   j=e['target']-nb;outstanding=[x for es in pending.values() for x in es if x['target']==e['target']]
   if c.get('openingBurst') and e['shooter'] not in seenShooters:
    if e['plannedDamage']>hp[j]-sum(x['plannedDamage'] for x in outstanding):capacityErrors.append(e['id'])
    if len(outstanding)>=c['openingPendingArrowCap']:capacityErrors.append(e['id']+' cap')
   seenShooters.add(e['shooter'])
   pending[e['impactFrame']].append(e)
   maxPending=max(maxPending,len(outstanding)+1)
 firstShots=[s['events'][ids[0]] for ids in s['shooterEvents'] if ids and s['events'][ids[0]]['release']<duration]
 invalid=[e['id'] for e in s['events'] if e['releaseDistance']>c['archerRange']+1e-5 or round(bc[e['releaseFrame'],e['shooter'],0])!=5 or round(bc[e['releaseFrame'],e['shooter'],11])!=int(e['id'][1:])]
 widthRatios=[]
 for ids in groups.values():
  x=p[:,nb+np.array(ids),0];widthRatios.append(float(np.ptp(x,axis=1).max()/np.ptp(x[0])))
 finalK=frames-1;healthyEnd=firstHit>finalK/fps;sp=np.linalg.norm(vel[finalK,nb:],axis=1);rearMask=healthyEnd&rear;term=json.loads((v/'termination-evidence.json').read_text());frontHits={e['target']-nb for e in hits if front[e['target']-nb]};frontKills={e['target']-nb for e in hits if e.get('killed') and front[e['target']-nb]}
 result=dict(label=label,variant=variant,duration=duration,frames=frames,firstRelease=firstRelease,firstActualHit=min(e['impact'] for e in hits),releases=len(events),hits=len(hits),kills=sum(bool(e.get('killed')) for e in hits),firstWaveHalfSecondReleases=len(firstWave),firstWaveParticipatingShooters=len({e['shooter'] for e in firstWave}),firstWaveReleaseFrameCount=len({e['releaseFrame'] for e in firstWave}),firstWaveTargetPlatoons=len({s['units'][e['target']]['platoon'] for e in firstWave}),firstWaveTargets=len({e['target'] for e in firstWave}),firstShots=len(firstShots),shootersAtLeastTwoShots=sum(x>=2 for x in shooterCounts.values()),maximumReleasesInOneFrame=max(releasePerFrame.values()),maximumArrowsOutstandingPerTarget=maxPending,uniqueHitSoldiers=len(impactCounts),uniqueFrontRowHitSoldiers=len(frontHits),uniqueFrontRowKilledSoldiers=len(frontKills),frontDefinition='Initial leading 1.7 world units within each original small squad',flightCoverageSeconds=sum(any(e['release']<=k/fps<e['impact'] for e in events) for k in range(frames))/fps,minimumSampleGap=min(gaps),minimumConservativeGap=float(min(lower)),minimumRedSpacing=min(spacing),deadRootMaxMovement=max(deadError),maximumRootReverseStep=float(np.maximum(0,-np.diff(p[:,nb:,1],axis=0)).max()),maxSquadWidthRatio=max(widthRatios),medianSquadWidthRatio=float(np.median(widthRatios)),finalUnhitMedianSpeed=float(np.median(sp[healthyEnd])),finalUnhitRearMedianSpeed=float(np.median(sp[rearMask])),finalUnhitRearP10Speed=float(np.quantile(sp[rearMask],.1)),finalUnhitRearBelow10=int((sp[rearMask]<10).sum()),finalUnhitRearCount=int(rearMask.sum()),causalErrors=causalErrors,firstShotCapacityErrors=capacityErrors,invalidReleases=invalid,releasePhaseMaxError=max(abs(float(bc[e['releaseFrame'],e['shooter'],6])-.64) for e in s['events']),extraWorldHitImpulse=0,upperBodyPoseAmplitude=c.get('impactPoseScale',1),termination=term,movement=rows,visualAcceptance='PENDING: original wall crossing and cropping remain')
 result['commonWindowReleases1Point4To1Point9']=sum(1.4<=e['release']<1.9 for e in events)
 result['commonWindowReleases1Point5To2']=sum(1.5<=e['release']<2 for e in events)
 result['completeFallAnimationsByEnd']=int(sum(t+c['deathSeconds']<=duration for t in death if t<1e5))
 result['additionalFullSpeedPathBudget']={str(t):max(0.,t-duration)*c['redSpeed'] for t in [3.,3.5,4.]}
 base=json.loads((R/'variants/V22R-fast-A/simulation.json').read_text(encoding='utf8'))
 keys=['aimSeconds','drawSeconds','recoverSeconds','cycle','walkSpeed','walkAccel','walkBrake']
 result['originalPersonalActionParametersUnchanged']=all(u[key]==v[key] for u,v in zip(s['units'][:nb],base['units'][:nb]) for key in keys)
 result['originalPerArrowDamageUnchanged']=all(e['plannedDamage']==(3 if e['shooter']%17==0 else 1) for e in s['events'])
 assert result['originalPersonalActionParametersUnchanged'] and result['originalPerArrowDamageUnchanged']
 assert not causalErrors and not capacityErrors and not invalid and result['minimumConservativeGap']>=4 and result['deadRootMaxMovement']==0 and result['minimumRedSpacing']>=2*c['bodyRadius']
 with (D/(label+'-every-0.1s.csv')).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (D/(label+'-audit.json')).write_text(json.dumps(result,indent=2),encoding='utf8');results.append(result)
 if label!='A':shutil.copyfile(v/'params.json',D/(label+'-accepted-params.json'))
hashChecks={name:hashlib.sha256((R/name).read_bytes()).hexdigest()==value for name,value in proposal['sourceHashes'].items()};assert all(hashChecks.values())
report=dict(candidates=[{k:v for k,v in x.items() if k not in ['movement','termination']} for x in results],sourceUnchanged=hashChecks,moreThanOneSecondGain=False,formalRender=False)
(D/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
