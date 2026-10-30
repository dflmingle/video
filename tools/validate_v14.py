from pathlib import Path
import json,csv,hashlib,numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V13/variants/FINAL'
S=json.loads((D/'simulation.json').read_text());Q=json.loads((B/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];nr=S['redCount'];A=np.load(D/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*60;K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');A0=np.load(B/'trajectories.npy');V0=np.diff(A0,axis=0,prepend=A0[:1])*60;E=S['events'];I=[e for e in E if e['resolution']=='IMPACT_IN_SHOT'];first={};first0={}
assert np.array_equal(A[0],A0[0]);assert [u['id'] for u in U]==[u['id'] for u in Q['units']];assert nr==972 and nb==252
for e in I:first.setdefault(e['target'],e['impact'])
for e in Q['events']:
 if e['resolution']=='IMPACT_IN_SHOT':first0.setdefault(e['target'],e['impact'])
assert np.min(np.diff(A[:,nb:,1],axis=0))>=-1e-5
assert np.allclose(K[:,:,1],V[:,nb:,1],atol=.001)
assert np.min(np.diff(Y,axis=0))>=-1e-6
# Blue world deployment must remain byte-equivalent at each common timestamp.
assert np.array_equal(A[:len(A0),:nb],A0[:,:nb])
minLive=100.;minCorpse=100.;faction=[];neighbor=[]
for k,a in enumerate(A):
 t=k/60;live=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>t]);dead=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is not None and 0<=t-U[i]['deathTime']<.9],dtype=int)
 nn=cKDTree(a[live]).query(a[live],k=2)[0][:,1];minLive=min(minLive,float(nn.min()));faction.append(float(cKDTree(a[:nb]).query(a[nb:])[0].min()))
 if len(dead):minCorpse=min(minCorpse,float(cKDTree(a[dead]).query(a[live])[0].min()))
 if k%15==0:neighbor.append(dict(time=t,p10p50p90=np.percentile(nn,[10,50,90]).tolist()))
assert minLive>=.58-1e-4,(minLive,'live overlap');assert minCorpse>=.58-1e-4,(minCorpse,'corpse penetration')
steps=np.linalg.norm(np.diff(A,axis=0),axis=2);bound=np.minimum(faction[:-1],faction[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))-6.2
assert bound.min()>=C['minimumEnemyClearance']
for i in range(nb,len(U)):
 if U[i]['deathTime'] is not None:
  k=round(U[i]['deathTime']*60);assert np.allclose(A[k:,i],A[k,i]);assert any(e['target']==i and e['killed'] for e in I)
for e in E:
 rf=e['releaseFrame'];j=e['shooter'];i=e['target'];u=U[j]
 assert np.linalg.norm(A[rf,i]-A[rf,j])<=C['archerRange']+1e-4
 assert e['drawStart']-u['turnSeconds']>=u['arrival']-1e-5
 if e['resolution']=='IMPACT_IN_SHOT':assert np.allclose(A[e['impactFrame'],i],np.array(e['destination'])[[0,2]],atol=1e-5)
for p,h in json.loads((O/'protected-v13.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
motion=[]
for army in range(3):
 ids=[i for i in range(nb,len(U)) if U[i]['army']==army and first.get(i,99)>2.2 and first0.get(i,99)>2.2];js=np.array(ids)-nb
 # Compare how each member varies over time, not variance between constant speeds.
 r=dict(army=army,members=len(ids),v13TemporalSpeedStdP10P50P90=np.percentile(np.std(V0[36:131,ids,1],axis=0),[10,50,90]).tolist(),v14TemporalSpeedStdP10P50P90=np.percentile(np.std(V[36:131,ids,1],axis=0),[10,50,90]).tolist(),v14MeanSpeedP10P50P90=np.percentile(np.mean(V[36:131,ids,1],axis=0),[10,50,90]).tolist(),v14TemporalCadenceStdMedian=float(np.median(np.std(K[36:131,js,4],axis=0))))
 assert r['v14TemporalSpeedStdP10P50P90'][1]>.25;assert r['v14TemporalCadenceStdMedian']>.05
 motion.append(r)
avoid=np.load(D/'avoidance-causes.npy');slow=np.load(D/'slow-causes.npy');reason=np.load(D/'movement-reasons.npy')
events=[]
for j in range(nr):
 i=nb+j
 for k in range(35,len(A)-15):
  cause=int(avoid[k,j]) if avoid[k,j]>=0 else int(slow[k,j]);
  if cause<0 or first.get(i,99)<=k/60:continue
  if V[k,i,1]<U[i]['speed']*.94 and np.max(V[k+1:k+16,i,1])>V[k,i,1]+.45:
   end=k+1+int(np.argmax(V[k+1:k+16,i,1]));events.append(dict(id=U[i]['id'],index=i,slowTime=k/60,slowSpeed=float(V[k,i,1]),recoverTime=end/60,recoverSpeed=float(V[end,i,1]),neighbor=U[nb+cause]['id'],neighborIndex=nb+cause,route=bool(avoid[k,j]>=0),xMove=float(A[end,i,0]-A[k,i,0])));break
assert events,'Need evidence of occupancy-related slow / reacceleration'
# Select a single 24-member yellow platoon with observed cause/recovery and hits.
scores=[]
for p in sorted({u['platoon'] for u in U[nb:] if u['army']==2}):
 ids=[i for i in range(nb,len(U)) if U[i]['platoon']==p];score=sum(U[e['index']]['platoon']==p for e in events)*3+sum(i in first for i in ids)
 scores.append((score,p))
_,platoon=max(scores);pool=[i for i in range(nb,len(U)) if U[i]['platoon']==platoon];ids=pool[:20]
chosen=[e for e in events if e['index'] in ids]
if not chosen:
 e=next(e for e in events if U[e['index']]['platoon']==platoon);ids=pool[:19]+[e['index']];ids=list(dict.fromkeys(ids));ids+= [i for i in pool if i not in ids][:20-len(ids)]
assert len(ids)==20 and len({U[i]['platoon'] for i in ids})==1
(O/'tracked-v14.json').write_text(json.dumps(dict(platoon=platoon,indices=ids,members=[U[i]['id'] for i in ids]),indent=2))
with (O/'V14-individual-controls.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['time','id','x','z','vx','vz','gaitCycles',*S['controlColumns'],'avoidID','slowCauseID','firstHit','death'];w=csv.writer(f);w.writerow(fields)
 for k in range(len(A)):
  for i in ids:
   j=i-nb;av=int(avoid[k,j]);sc=int(slow[k,j]);w.writerow([k/60,U[i]['id'],*A[k,i],*V[k,i],Y[k,i],*K[k,j],U[nb+av]['id'] if av>=0 else '',U[nb+sc]['id'] if sc>=0 else '',first.get(i),U[i]['deathTime']])
# Pairwise relative forward position must change continuously after startup.
relative=[]
for ai,i in enumerate(ids):
 for j in ids[ai+1:]:
  if abs(A[0,i,0]-A[0,j,0])<1.5 and abs(A[0,i,1]-A[0,j,1])<2:
   delta=A[36:132,i,1]-A[36:132,j,1];relative.append(float(np.ptp(delta)))
R=dict(engineeringStatus='PASS',visualStatus='PENDING_RENDER',framesChecked=len(A),initialExact=True,blueDeploymentUnchanged=True,redCount=nr,blueCount=nb,minimumLiveRedCenterDistance=minLive,minimumRecentCorpseCenterDistance=minCorpse,bodyDiameter=.58,minimumContinuousFactionEnvelopeClearance=float(bound.min()),required=4,reverseSteps=0,firstRelease=min(e['release'] for e in E),firstImpact=min(e['impact'] for e in I),arrows=len(E),impactsInVisibleFrames=sum(e['impactFrame']<len(A)-1 for e in I),deaths=sum(u['deathTime'] is not None and u['deathTime']<C['duration'] for u in U[nb:]),temporalMotion=motion,occupancyRecoveryExamples=events[:30],trackedRecoveryExamples=[e for e in events if e['index'] in ids],trackedNeighborRelativeZRangeMedian=float(np.median(relative)),trackedPlatoon=platoon,trackedCount=len(ids),neighbors=neighbor,protectedV13=True)
(O/'V14-engineering-validation.json').write_text(json.dumps(R,indent=2));print(json.dumps({k:v for k,v in R.items() if k not in ['neighbors','occupancyRecoveryExamples','trackedRecoveryExamples']},indent=2));print('Tracked recovery:',json.dumps(R['trackedRecoveryExamples'][:3],indent=2))
