"""Duration-only replay comparison. Never generate or approve unsafe frames."""
import csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

R=Path(__file__).resolve().parents[1];A=R/'variants/V22R-overlap';B=R/'variants/V22R-duration-only';D=R/'docs/v22r-duration-only';D.mkdir(exist_ok=True)
load=lambda p:json.loads(p.read_text(encoding='utf8'))
a=load(A/'simulation.json');b=load(B/'simulation.json');term=load(B/'termination-evidence.json');proposal=load(D/'proposal.json')
arrays={}
for name in ['trajectories.npy','blue-control.npy','red-control.npy','gait-distance.npy','gait-cycles.npy','hit-times.npy','member-states.npy','movement-reasons.npy','avoidance-causes.npy','response-targets.npy']:
 x=np.load(A/name);y=np.load(B/name);assert x.shape==y.shape
 arrays[name]=dict(shape=list(x.shape),bitIdentical=bool(np.array_equal(x,y)),maxAbsoluteDifference=float(np.max(np.abs(x.astype(float)-y.astype(float)))))
assert all(v['bitIdentical'] for v in arrays.values()) and a==b
original=load(R/'output/V22R-final/render-audit.json');hashes={n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in original['sourceHashes']}
assert hashes==original['sourceHashes']==proposal['baselineHashes']
p=np.load(B/'trajectories.npy');nb=b['blueCount'];gap=[float(cKDTree(q[:nb]).query(q[nb:])[0].min()-6.2) for q in p];steps=np.linalg.norm(np.diff(p,axis=0),axis=2);lower=np.minimum(gap[:-1],gap[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))
fps=60;rows=[]
for k,q in enumerate(p):
 t=k/fps;sp=np.zeros(len(q)) if not k else np.linalg.norm(q-p[k-1],axis=1)*fps
 rows.append(dict(frame=k,time=t,redWorldExact=True,blueWorldExact=True,controlExact=True,eventsExact=True,minimumSurfaceGap=gap[k],redMoving=int((sp[nb:]>.02).sum()),blueMoving=int((sp[:nb]>.02).sum()),releases=sum(t<=e['release']<(k+1)/fps for e in b['events']),arrowsInFlight=sum(e['release']<=t<e['impact'] for e in b['events']),hits=sum(e['resolution']=='IMPACT_IN_SHOT' and t<=e['impact']<(k+1)/fps for e in b['events'])))
with (D/'common-every-frame.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (D/'events-every-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:
 keys=['time','redMoving','blueMoving','releases','arrowsInFlight','hits','minimumSurfaceGap'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for k in range(0,len(rows),6):
  row={key:rows[k][key] for key in keys};row['releases']=sum(r['releases'] for r in rows[k:k+6]);row['hits']=sum(r['hits'] for r in rows[k:k+6]);w.writerow(row)
lastVelocity=np.diff(p[-2:],axis=0)[0]*fps;relativeClosing=(gap[-2]-gap[-1])*fps
result=dict(status='BLOCKED_BY_UNCHANGED_SAFETY_CONSTRAINT',baselineSourceMatchesOriginalVideo=True,onlyRequestedParameterChange='duration 2.2 -> 3.5',newBattleLogicUsed=False,arrayComparisons=arrays,fullSimulationJSONIdentical=a==b,allShooterEventsIdentical=a['events']==b['events'],arrowsIdenticalBecauseAllTrajectoryInputsAndRendererUnchanged=True,commonSimulationFrames=len(p),commonVideoFrames=132,firstRelease=min(e['release'] for e in b['events']),firstScheduledImpact=min(e['impact'] for e in b['events']),scheduledImpactIsNotActualHit=True,actualHitsBeforeCut=0,firstMotion=dict(red=next(r['time'] for r in rows if r['redMoving']),blue=next(r['time'] for r in rows if r['blueMoving'])),lastAcceptedStateTime=term['lastAcceptedTime'],termination=term,minimumAcceptedSampleGap=min(gap),minimumAcceptedConservativeGap=float(min(lower)),requestedExtension=dict(start=2.2,end=3.5,generated=False,renderableAdditionalFrames=0,realReleases=None,realHits=None,minimumSurfaceGap=None,reason='No accepted state exists after 2.2; do not count nonexistent events or extrapolated impacts as actual results'),localBudgetEstimate=dict(lastMeasuredGapClosingSpeed=relativeClosing,method='Linear extrapolation of the last measured nearest-gap change; NOT a new simulation or approved adjustment',additionalGapAt3Seconds=(3.-2.2)*relativeClosing,additionalGapAt3Point5Seconds=(3.5-2.2)*relativeClosing,additionalGapAt4Seconds=(4.-2.2)*relativeClosing,warning='Moving initial positions would alter range entry and usually shooting times; no placement change authorized or applied'),redFormationVerdict='Identical to original in all accepted frames; cannot evaluate an ungenerated extension')
(D/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');shutil.copyfile(B/'termination-evidence.json',D/'termination-evidence.json');shutil.copyfile(B/'params.json',D/'accepted-params.json')
print(json.dumps({k:v for k,v in result.items() if k!='arrayComparisons'},ensure_ascii=True,indent=2))
