from pathlib import Path
import json,copy,hashlib,csv,time
import numpy as np
from scipy.spatial import cKDTree
from motion_v17 import Crowd
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V16'
S=json.loads((D/'simulation.json').read_text(encoding='utf-8'));C=S['config'];U=S['units'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');BC=np.load(D/'blue-control.npy');pressure=np.load(D/'formation-pressure.npy');oldA=np.load(B/'variants/FAST125/trajectories.npy')
assert np.array_equal(A[0],oldA[0]);assert len(U)==1224 and nb==252 and C['redSpeed']==21.75
assert np.diff(A[:,nb:,1],axis=0).min()>=-1e-6
schedule={}
for e in S['events']:
 if e['resolution']=='IMPACT_IN_SHOT':schedule.setdefault(e['impactFrame'],[]).append(e)
m=Crowd(copy.deepcopy(U[nb:]),C);pos=[m.position.copy()];cy=[m.cycles.copy()]
for f in range(1,len(A)):
 for e in schedule.get(f,[]):m.apply_hit(e['target']-nb,e['plannedDamage'],f/60)
 m.bluePositions=A[f,:nb].astype(float);m.step(f/60);pos.append(m.position.copy());cy.append(m.cycles.copy())
# Float32 blue cache vs original double path must be numerically equivalent,
# pressure may differ at floating precision; movement tolerance is 1e-4 unit.
assert np.allclose(np.array(pos),A[:,nb:],atol=1e-4,rtol=0)
assert np.allclose(np.array(cy),Y[:,nb:],atol=1e-5,rtol=0)
dist=[];minsep=99.;minblue=99.
for f,p in enumerate(A):
 dist.append(float(cKDTree(p[:nb]).query(p[nb:])[0].min()));minsep=min(minsep,float(cKDTree(p[nb:]).query(p[nb:],k=2)[0][:,1].min()));minblue=min(minblue,float(cKDTree(p[:nb]).query(p[:nb],k=2)[0][:,1].min()))
step=np.linalg.norm(np.diff(A,axis=0),axis=2);bounds=np.minimum(dist[:-1],dist[1:])-.5*(step[:,:nb].max(axis=1)+step[:,nb:].max(axis=1))-6.2
assert bounds.min()>=4 and minsep>=.58 and minblue>=.58,(bounds.min(),minsep,minblue)
for i,u in enumerate(U[nb:],nb):
 if u['deathTime'] is not None:
  f=round(u['deathTime']*60);assert np.all(A[f:,i]==A[f,i]);assert any(e['target']==i and e.get('killed') for e in S['events'])
es=S['events'];hit=[e for e in es if e['impactFrame']<round(C['duration']*60)]
for e in es:
 j=e['shooter'];target=e['target'];f=e['releaseFrame'];assert BC[f,j,0]==5
 assert np.linalg.norm(A[f,target]-A[f,j])<=C['archerRange']+1e-4
 assert e['drawStart']>=U[j]['readyAt']-1e-6
 assert e['release']-e['drawStart']>=U[j]['drawSeconds']-1e-6
 assert e['release']<e['impact']
 if e['resolution']=='IMPACT_IN_SHOT':assert np.allclose(A[e['impactFrame'],target],np.array(e['destination'])[[0,2]],atol=1e-4)
for path,h in json.loads((O/'protected-v16.json').read_text()).items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h
blue=U[:nb];arrivals=[u['arrival'] for u in blue];uniqueStates=[len(np.unique(BC[f,:36,0])) for f in range(len(A))]
assert max(uniqueStates)>=3 and np.ptp([u['delay'] for u in blue[:36]])>.10
assert np.ptp(arrivals)>.7
healthy=np.array([i for i in range(20) if all(e['target']!=nb+i for e in hit)]);v=K[:,healthy,1];assert np.std(v[60:],axis=1).mean()>.1
assert min(np.std(((Y[f,nb:nb+20]+np.array([u['phase'] for u in U[nb:nb+20]]))%1)) for f in range(1,len(A)))>.1
assert pressure[-1].mean()>pressure[1].mean()+.1 and np.diff(pressure,axis=0).max()<.15
first=min(hit,key=lambda e:e['impact']);f=first['impactFrame'];rf=first['releaseFrame'];releases=sorted(e['release'] for e in es);paths=np.linalg.norm(np.diff(A[:,:nb],axis=0),axis=2).sum(axis=0)
result=dict(status='PASS',initialExactV16=True,red972Blue252=True,realSpeedUnchanged21_75=True,replayPositionAndGait=True,noReverseSteps=True,minRedSeparation=minsep,minBlueSeparation=minblue,minimumContinuousFactionEnvelope=float(bounds.min()),corpsePositionsFixed=True,independentBlueFSM=True,blueFirstSquadMaxSimultaneousStates=max(uniqueStates),releaseBoundToFSMAndRange=True,pressureStartEnd=[float(pressure[1].mean()),float(pressure[-1].mean())],healthyFinalSpeedP10P50P90=np.percentile(K[-2,:,1],[10,50,90]).tolist(),gaitCadenceFinalP10P50P90=np.percentile(K[-2,:,4],[10,50,90]).tolist(),bluePathLengthMinMax=[float(paths.min()),float(paths.max())],blueArrivalRange=[min(arrivals),max(arrivals)],blueMaxActualSpeed=float(np.linalg.norm(np.diff(A[:,:nb],axis=0)*60,axis=2).max()),timeline=dict(t0=min(u['delay'] for u in U[nb:]),tDeploy=min(u['delay'] for u in blue),tReady=min(u['readyAt'] for u in blue),tRelease=min(releases),tHit=first['impact'],tEnd=C['duration'],engagementWindow=C['duration']-first['impact'],firstHitPairDistance=float(np.linalg.norm(A[f,first['target']]-A[f,first['shooter']])),firstReleasePairDistance=first['releaseDistance'],range=34.,maxGapBetweenReleases=float(np.diff(releases).max()),visibleHits=len(hit)),V16Protected=True,stepMsP50P95=np.percentile([a['stepMs'] for a in m.metrics],[50,95]).tolist())
(O/'V17-algorithm-tests.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
with (O/'V17-archer-states.csv').open('w',newline='',encoding='utf-8-sig') as fp:
 w=csv.writer(fp);w.writerow(['time','id','state','stateTimer','target','x','z'])
 for f in range(len(A)):
  for j in range(36):w.writerow([f/60,U[j]['id'],*BC[f,j,:3],*A[f,j]])
