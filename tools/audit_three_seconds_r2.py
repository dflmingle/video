"""Read-only budget from unchanged overlap trajectories. No modified battle run."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
R=Path(__file__).resolve().parents[1];D=R/'docs/scene-requirements-r2';v=R/'variants/V22R-overlap'
s=json.loads((v/'simulation.json').read_text());c=json.loads((v/'params.json').read_text());p=np.load(v/'trajectories.npy');bc=np.load(v/'blue-control.npy');nb=s['blueCount'];fps=c['simulationFps'];end=(len(p)-1)/fps
nearest=np.array([cKDTree(q[nb:]).query(q[:nb])[0] for q in p]);inside=nearest<=c['archerRange'];rangeRecords=[]
for j,u in enumerate(s['units'][:nb]):
 ids=np.flatnonzero(inside[:,j]);fi=int(ids[0]) if len(ids) else None
 if fi is None:continue
 state=int(round(bc[fi,j,0]));drawFrames=math.ceil(u['drawSeconds']*fps-1e-9);releaseFrame=fi+drawFrames
 if releaseFrame>=len(p):continue
 # Optimistic PREPARATION bound only: full aim already completed, valid range,
 # original draw duration and intercept flight. Does not implement movement+bow blending.
 q=p[releaseFrame];dist,idx=cKDTree(q[nb:]).query(q[j]);target=int(idx);rel=q[nb+target]-q[j]
 vel=(p[releaseFrame,nb+target]-p[max(0,releaseFrame-1),nb+target])*fps
 qa=float(vel@vel-c['arrowSpeed']**2);qb=2*float(rel@vel);qc=float(rel@rel);disc=qb*qb-4*qa*qc
 roots=[] if disc<0 else [(-qb+math.sqrt(disc))/(2*qa),(-qb-math.sqrt(disc))/(2*qa)]
 valid=[x for x in roots if x>0];flight=max(.18,min(valid)) if valid else None
 impactFrame=None if flight is None else releaseFrame+max(1,round(flight*fps))
 rangeRecords.append(dict(id=u['id'],index=j,group=u['group'],firstRangeTime=fi/fps,stateAtRange=state,rangeDistance=float(nearest[fi,j]),drawSeconds=u['drawSeconds'],optimisticRelease=releaseFrame/fps,optimisticImpact=None if impactFrame is None else impactFrame/fps,canHitBeforeObservedCut=impactFrame is not None and impactFrame/fps<=end))
states=[dict(state=name,firstTime=next((f/fps for f in range(len(p)) if np.any(np.round(bc[f,:,0])==k)),None)) for k,name in [(2,'ARRIVING'),(7,'TURNING'),(3,'AIMING'),(4,'DRAWING'),(5,'RELEASING')]]
red=p[-1,nb:];blue=p[-1,:nb];velocity=(p[-1,nb:]-p[-7,nb:])/(6/fps)
forecasts=[]
for duration in [2.8,3.,3.2]:
 dt=duration-end;forecast=red+velocity*dt
 # Proposal-only rigid longitudinal separation: never written into params/paths.
 def gap(offset):return float(cKDTree(blue).query(forecast-[0,offset])[0].min()-2*c['weaponEnvelopeRadius'])
 lo=0.;hi=60.
 for _ in range(45):
  mid=(lo+hi)/2
  if gap(mid)>=4.1:hi=mid
  else:lo=mid
 forecasts.append(dict(targetDuration=duration,extraSeconds=dt,frozenBlueLinearRedPredictedGap=gap(0.),proposalAdditionalStartSeparation=hi,proposedGapWithMargin=gap(hi),assumptions='No new damage/collisions simulated; last 0.1 s red velocities extrapolated, blue endpoints held. Estimate for discussion only, not a validated or applied start-position change.'))
first=min(rangeRecords,key=lambda x:x['optimisticImpact'] if x['optimisticImpact'] is not None else 1e9)
result=dict(targetDuration=[2.8,3.2],existingSafeEnd=end,firstObservedRelease=min(e['release'] for e in s['events']),firstObservedHit=None,states=states,earliestRange=min(x['firstRangeTime'] for x in rangeRecords),optimisticPreparedShot=first,eligibleArchersWithOptimisticHitBeforeCut=sum(x['canHitBeforeObservedCut'] for x in rangeRecords),rangeAndPreparationRecords=rangeRecords,separationForecasts=forecasts,protectedParameters=dict(redSpeed=c['redSpeed'],arrowSpeed=c['arrowSpeed'],archerRange=c['archerRange'],blueAdvance=c['blueAdvance'],minimumEnemyClearance=c['minimumEnemyClearance']),sourceHashes={name:hashlib.sha256((v/name).read_bytes()).hexdigest() for name in ['params.json','simulation.json','trajectories.npy']},scope='Preliminary numerical audit only; no early-prep code, no speed changes, no position changes, no production scene edit or full video render. Need approved scene before further battle production.')
(D/'three-second-feasibility.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(dict(existingSafeEnd=end,earliestRange=result['earliestRange'],optimisticPreparedShot=first,separationForecasts=forecasts),indent=2))
