from pathlib import Path
import json,hashlib,numpy as np,copy,time
from scipy.spatial import cKDTree
from motion_v15 import Crowd,DT
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V14';S=json.loads((D/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');old=np.load(B/'variants/FINAL/trajectories.npy');first={}
assert np.array_equal(A[0],old[0]) and np.array_equal(A[:,:nb],old[:len(A),:nb]);assert len(U)==1224 and nb==252
assert np.min(np.diff(A[:,nb:,1],axis=0))>=-1e-5
steps=np.linalg.norm(np.diff(A,axis=0),axis=2);separation=[];minbody=100.;mincorpse=100.
for f,p in enumerate(A):
 t=f/60;live=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>t]);dead=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is not None and U[i]['deathTime']<=t],dtype=int)
 minbody=min(minbody,float(cKDTree(p[live]).query(p[live],k=2)[0][:,1].min()));separation.append(float(cKDTree(p[:nb]).query(p[nb:])[0].min()))
 if len(dead):mincorpse=min(mincorpse,float(cKDTree(p[dead]).query(p[live])[0].min()))
bound=np.minimum(separation[:-1],separation[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))-2*C['weaponEnvelopeRadius']
assert bound.min()>=4 and minbody>=.58 and mincorpse>=.58,(bound.min(),minbody,mincorpse)
for e in S['events']:
 assert np.linalg.norm(A[e['releaseFrame'],e['target']]-A[e['releaseFrame'],e['shooter']])<=C['archerRange']+1e-4
 if e['resolution']=='IMPACT_IN_SHOT':first.setdefault(e['target'],e['impact']);assert np.allclose(A[e['impactFrame'],e['target']],np.array(e['destination'])[[0,2]],atol=1e-4)
for i in range(nb,len(U)):
 if U[i]['deathTime'] is not None:
  f=round(U[i]['deathTime']*60);assert np.all(A[f:,i]==A[f,i]);assert any(e['target']==i and e.get('killed') for e in S['events'])
release=min(e['releaseFrame'] for e in S['events']);front=[];means=[]
for f in range(release,len(A)):
 live=[i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>f/60]
 front.append(float(A[f,live,1].max()));means.append(float(A[f,nb:,1].mean()))
assert np.min(np.diff(front))>=-1e-5 and np.min(np.diff(means))>0
# Run the WHOLE 972-member controller twice with exact bound arrow inputs.
def replay():
 units=copy.deepcopy(U[nb:]);m=Crowd(units,C);positions=[m.position.copy()];cycles=[m.cycles.copy()]
 scheduled={}
 for e in S['events']:
  if e['resolution']=='IMPACT_IN_SHOT':scheduled.setdefault(e['impactFrame'],[]).append(e)
 for f in range(1,len(A)):
  for e in scheduled.get(f,[]):m.apply_hit(e['target']-nb,e['plannedDamage'],f/60)
  m.step(f/60);positions.append(m.position.copy());cycles.append(m.cycles.copy())
 return m,np.array(positions).astype('float32'),np.array(cycles).astype('float32')
m,replayed,cyc=replay();assert np.array_equal(A[:,nb:],replayed) and np.array_equal(Y[:,nb:],cyc),'F full replay differs'
protected=json.loads((O/'protected-v14.json').read_text())
for p,h in protected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
forward=np.diff(A[:,nb:,1],axis=0)*60
healthy=[i for i in range(nb,len(U)) if first.get(i,99)>C['duration']]
performance=json.loads((D/'simulation-performance.json').read_text())
out=dict(status='PASS',E=dict(status='PASS',firstRelease=release/60,firstImpact=min(first.values()),frontAtFirstRelease=front[0],frontAtEnd=front[-1],frontAdvancement=front[-1]-front[0],meanAdvancementDuringArrows=means[-1]-means[0],reverseSteps=0,liveMinimumCenter=minbody,corpseMinimumCenter=mincorpse,continuousFactionEnvelopeLowerBound=float(bound.min()),arrows=len(S['events']),impacts=sum(e['impactFrame']<len(A)-1 for e in S['events']),deaths=sum(u.get('deathTime') is not None for u in U[nb:])),F=dict(status='PASS',wholeArmySameSeedReplayBitIdentical=True,red972StepMsP50P95=np.percentile([s['stepMs'] for s in m.metrics],[50,95]).tolist(),pipelineWallSeconds=performance['wallSeconds'],maxNeighborQuery=max(s['maxNeighbors'] for s in m.metrics),maxLocalContactPairs=max(s['contactPairs'] for s in m.metrics)),invariants=dict(initialExact=True,blueDeploymentExact=True,redCount=972,blueCount=252,V14Protected=True),healthyTemporalSpeedStdMedian=float(np.median(np.std(forward[36:130,np.array(healthy)-nb],axis=0))),duration=C['duration'])
(O/'V15-battle-tests.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
