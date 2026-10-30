from pathlib import Path
import copy,json,numpy as np,hashlib
from motion_v16 import Crowd,SpatialHash,DT
P=Path(__file__).resolve().parents[1];O=P/'output';B=P.parent/'PveMontageShot01V15'
S=json.loads((P/'variants/FAST125/simulation.json').read_text());C=S['config'];units=S['units'];nb=S['blueCount'];red=copy.deepcopy(units[nb:]);A=np.load(P/'variants/FAST125/trajectories.npy');Y=np.load(P/'variants/FAST125/gait-cycles.npy')
m=Crowd(red,C);history=[m.position.copy()];cycles=[m.cycles.copy()];schedule={}
for e in S['events']:
 if e['resolution']=='IMPACT_IN_SHOT':schedule.setdefault(e['impactFrame'],[]).append(e)
for f in range(1,len(A)):
 for e in schedule.get(f,[]):m.apply_hit(e['target']-nb,e['plannedDamage'],f/60)
 m.step(f/60);history.append(m.position.copy());cycles.append(m.cycles.copy())
assert np.array_equal(np.array(history).astype('float32'),A[:,nb:])
assert np.array_equal(np.array(cycles).astype('float32'),Y[:,nb:])
pool=[copy.deepcopy(u) for u in red if u['army']==1][:50]
def run():
 q=Crowd(copy.deepcopy(pool),C);p=[];v=[];phase=[];routes=[];sides=[];timer=[]
 for f in range(301):
  if f in [90,108]:q.apply_hit(0 if f==90 else 6,3 if f==90 else 2,f/60)
  if f:q.step(f/60)
  p.append(q.position.copy());v.append(q.velocity.copy());phase.append(q.cycles+q.phase);routes.append(q.route.copy());sides.append(q.routeSide.copy());timer.append(q.timer.copy())
 return q,np.array(p),np.array(v),np.array(phase),np.array(routes),np.array(sides),np.array(timer)
q,p,v,phase,routes,sides,timer=run();q2,p2,v2,ph2,_,_,_=run();assert np.array_equal(p,p2) and np.array_equal(v,v2) and np.array_equal(phase,ph2)
healthy=[i for i in range(20) if i not in[0,6]];assert np.min(np.std(v[36:,healthy,1],axis=0))>.1
assert not any(np.allclose(v[36:,i,1],v[36:,j,1]) for a,i in enumerate(healthy) for j in healthy[:a])
assert np.min(np.std(phase[:,healthy]%1,axis=1))>.1
assert np.all(p[90:,0]==p[90,0]);assert np.min(np.diff(p[:,:,1],axis=0))>=-1e-8
minsep=100.
for ps in p:
 g=SpatialHash(ps);pairs=g.pairs(.7)
 if len(pairs):minsep=min(minsep,float(np.linalg.norm(ps[pairs[:,0]]-ps[pairs[:,1]],axis=1).min()))
assert minsep>=.58
for f in range(1,301):
 for i in range(50):
  if routes[f,i]>=0 and routes[f,i]==routes[f-1,i] and timer[f,i]>0:assert sides[f,i]==sides[f-1,i]
# Separate obstacle fixture with real free side space. The production-derived
# sample above is the LEFT boundary column: a corpse there may correctly queue
# followers because the adjacent lane is occupied. It cannot establish that
# passing is possible. Do not loosen the recovery criterion to hide that fact.
fixture=copy.deepcopy(pool)
for i,u in enumerate(fixture):u['start']=[(i%10-4.5)*1.8,-(i//10)*2.0];u['delay']=.03
ob=Crowd(fixture,C);op=[];ov=[];orr=[]
for f in range(361):
 if f==90:ob.apply_hit(4,3,f/60)
 if f:ob.step(f/60)
 op.append(ob.position.copy());ov.append(ob.velocity.copy());orr.append(ob.route.copy())
op=np.array(op);ov=np.array(ov);orr=np.array(orr);examples=[]
for i in range(50):
 if i==4:continue
 for f in range(91,301):
  if orr[f,i]!=4 or ov[f,i,1]>.9*ob.preferred[i]:continue
  end=f+1+int(np.argmax(ov[f+1:f+61,i,1]))
  if ov[end,i,1]>ov[f,i,1]+1 and abs(op[end,i,0]-op[f,i,0])>.12:examples.append(dict(id=fixture[i]['id'],time=f/60,recovery=end/60,slow=float(ov[f,i,1]),fast=float(ov[end,i,1])));break
assert examples
for e in S['events']:
 shooter=units[e['shooter']];assert e['drawStart']-shooter['turnSeconds']>=shooter['arrival']-1e-6
 assert np.linalg.norm(A[e['releaseFrame'],e['target']]-A[e['releaseFrame'],e['shooter']])<=C['archerRange']+1e-5
 if e['resolution']=='IMPACT_IN_SHOT':assert np.allclose(A[e['impactFrame'],e['target']],np.array(e['destination'])[[0,2]],atol=1e-4)
for path,h in json.loads((O/'protected-v15.json').read_text()).items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h
out=dict(status='PASS',fixedDt=DT,full972ReplayPositionAndGaitBitIdentical=True,local50FiveSecondsReplayBitIdentical=True,independentSpeedCurves=True,independentPhase=True,stableAvoidanceSide=True,corpsePermanent=True,minimumBodyCenter=minsep,avoidanceRecoveryExamples=examples[:5],archeryAfterIndividualArrival=True,rangeAndImpactBinding=True,V15Protected=True,wholeArmyStepMsP50P95=np.percentile([a['stepMs'] for a in m.metrics],[50,95]).tolist())
(O/'V16-algorithm-tests.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
