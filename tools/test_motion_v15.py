"""A-D/F repeatable 5-second tests use the exact production Crowd implementation."""
from pathlib import Path
import json,copy,hashlib,time,csv
import numpy as np
from motion_v15 import Crowd,DT,SpatialHash
P=Path(__file__).resolve().parents[1];O=P/'output';B=P.parent/'PveMontageShot01V14';C=json.loads((P/'variants/FINAL/params.json').read_text());S=json.loads((B/'variants/FINAL/simulation.json').read_text())
red=[copy.deepcopy(u) for u in S['units'][S['blueCount']:] if u['army']==1][:50]
for u in red:u['deathTime']=None
assert len(red)==50 and len({u['platoon'] for u in red[:20]})==1

def run(units,obstacles=False):
 m=Crowd(copy.deepcopy(units),C);pos=[m.position.copy()];vel=[m.velocity.copy()];ctrl=[m.control()];cycle=[m.cycles.copy()];routes=[m.route.copy()];causes=[m.neighbor.copy()];reasons=[m.reason.copy()];hit=[m.hitTime.copy()];dead=[m.dead.copy()];sides=[m.routeSide.copy()];timers=[m.timer.copy()];events=[]
 for f in range(1,301):
  t=f*DT
  if obstacles and f in [90,108]:
   target=0 if f==90 else 6;damage=3 if f==90 else 2;m.apply_hit(target,damage,t)
   if m.dead[target]:m.units[target]['deathTime']=t
   events.append(dict(frame=f,time=t,member=m.units[target]['id'],kind='STATIC_CORPSE' if m.dead[target] else 'INJURED',source='AUTHORIZED_DIAGNOSTIC_FIXTURE_NOT_BATTLE_ARROW'))
  m.step(t);pos.append(m.position.copy());vel.append(m.velocity.copy());ctrl.append(m.control());cycle.append(m.cycles.copy());routes.append(m.route.copy());causes.append(m.neighbor.copy());reasons.append(m.reason.copy());hit.append(m.hitTime.copy());dead.append(m.dead.copy());sides.append(m.routeSide.copy());timers.append(m.timer.copy())
 return m,dict(pos=np.array(pos),vel=np.array(vel),ctrl=np.array(ctrl),cycles=np.array(cycle),routes=np.array(routes),causes=np.array(causes),reasons=np.array(reasons),hit=np.array(hit),dead=np.array(dead),sides=np.array(sides),timers=np.array(timers)),events

m,A,_=run(red);m2,A2,_=run(red);ob,D,events=run(red,True)
for k in A:assert np.array_equal(A[k],A2[k]),k
speeds=A['vel'][:,:,1];healthy=speeds[36:, :20];std=healthy.std(axis=0)
assert np.min(std)>.12,('A constant speeds',std)
copies=sum(np.allclose(healthy[:,i],healthy[:,j],atol=.001) for i in range(20) for j in range(i));assert copies==0
phase=(A['cycles']+m.phase[None,:])%1
distances=[np.std(phase[f,:20]) for f in range(36,301)];assert min(distances)>.10
relative=np.ptp(A['pos'][36:,:20,1]-A['pos'][36:,:20,1].mean(axis=1,keepdims=True),axis=0);assert np.median(relative)>.12
minsep=100.
for ps in [A['pos'],D['pos']]:
 for p in ps:
  tree=SpatialHash(p);pairs=tree.pairs(.7)
  if len(pairs):minsep=min(minsep,float(np.linalg.norm(p[pairs[:,0]]-p[pairs[:,1]],axis=1).min()))
assert minsep>=.58,minsep
# Obstacle must persist, and an actual follower must slow, move around it, then
# accelerate. No test accepts a bare 'avoiding' label as sufficient evidence.
yieldExamples=[]
for i in range(1,50):
 for f in range(91,265):
  if D['dead'][f,i] or D['hit'][f,i]>0:continue
  route=D['routes'][f,i];cause=D['causes'][f,i]
  if route not in [0,6] and cause not in [0,6]:continue
  if D['vel'][f,i,1]>ob.preferred[i]*.92:continue
  end=f+1+int(np.argmax(D['vel'][f+1:min(f+61,301),i,1]));shift=abs(D['pos'][end,i,0]-D['pos'][f,i,0])
  if D['vel'][end,i,1]>D['vel'][f,i,1]+1 and shift>.12:
   yieldExamples.append(dict(id=ob.units[i]['id'],slowTime=f/60,speed=float(D['vel'][f,i,1]),recoverTime=end/60,recoverSpeed=float(D['vel'][end,i,1]),sideMovement=float(shift),obstacle=ob.units[int(route if route in [0,6] else cause)]['id']));break
assert yieldExamples,'D: no true slow / bypass / recover evidence'
assert np.all(D['pos'][90:,0]==D['pos'][90,0]),'corpse moved'
for i in range(50):
 for f in range(1,301):
  if D['routes'][f,i]>=0 and D['routes'][f,i]==D['routes'][f-1,i] and D['timers'][f,i]>0:
   assert D['sides'][f,i]==D['sides'][f-1,i],'side flipped within one avoidance'
assert np.max(np.abs(D['vel'][:,:,0]))<=2.50001
assert np.min(np.diff(D['pos'][:,:,1],axis=0))>=-1e-8
report=dict(A=dict(status='PASS',seconds=5,sameSquadMembers=20,speedStdRange=[float(std.min()),float(std.max())],identicalPairs=copies),B=dict(status='PASS',minimumPhaseStd=float(min(distances))),C=dict(status='PASS',medianRelativeForwardRange=float(np.median(relative))),D=dict(status='PASS',minimumBodyCenterDistance=minsep,corpsePersistentToEnd=True,examples=yieldExamples),F=dict(status='PASS',sameSeedBitIdentical=True,fixedDt=DT,simulation50StepMsP50P95=np.percentile([a['stepMs'] for a in ob.metrics],[50,95]).tolist()),videoFixture=dict(count=50,seconds=5,originalStartingPositions=True,army='orange',firstSquad=red[0]['platoon'],fixtureEvents=events))
(O/'V15-algorithm-tests.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Export exact obstacle test for original-character browser rendering.
L=P/'variants/LOCAL';CC=dict(C,duration=5.,width=1280,height=1280,variant='LOCAL',previewOnly=False)
(L/'params.json').write_text(json.dumps(CC,indent=2));pos=D['pos'].astype('float32');ctrl=D['ctrl'].astype('float32');cycle=D['cycles'].astype('float32');dist=np.cumsum(np.linalg.norm(np.diff(pos,axis=0,prepend=pos[:1]),axis=2),axis=0).astype('float32')
for name,data in [('trajectories',pos),('red-control',ctrl),('gait-cycles',cycle),('gait-distance',dist),('hit-times',D['hit'].astype('float32')),('velocities',D['vel'].astype('float32'))]:np.save(L/f'{name}.npy',data);data.tofile(L/f'{name}.f32')
np.save(L/'avoidance-causes.npy',D['routes']);np.save(L/'slow-causes.npy',D['causes']);np.save(L/'movement-reasons.npy',D['reasons'])
(L/'simulation.json').write_text(json.dumps(dict(version='V15',config=CC,units=ob.units,blueCount=0,redCount=50,frames=301,events=[],shooterEvents=[],fixtureEvents=events,controlColumns=['targetSpeed','forwardSpeed','acceleration','stride','cadenceCyclesPerSecond','posture','armSwing','turn','effort','reason']),separators=(',',':')))
with (O/'V15-50-member-controls.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','id','x','z','vx','vz','phase','target','acceleration','cadence','route','cause'])
 for k in range(301):
  for i,u in enumerate(ob.units):w.writerow([k/60,u['id'],*D['pos'][k,i],*D['vel'][k,i],(cycle[k,i]+u['phase'])%1,ctrl[k,i,0],ctrl[k,i,2],ctrl[k,i,4],D['routes'][k,i],D['causes'][k,i]])
# Also export the healthy-only run: all 20 selected members stay unhit for the
# entire five seconds, so the video cannot rely on the fixture for differences.
H=P/'variants/HEALTHY';H.mkdir(exist_ok=True);HC=dict(CC,variant='HEALTHY')
(H/'params.json').write_text(json.dumps(HC,indent=2))
distance=np.cumsum(np.linalg.norm(np.diff(A['pos'],axis=0,prepend=A['pos'][:1]),axis=2),axis=0)
for name,data in [('trajectories',A['pos']),('red-control',A['ctrl']),('gait-cycles',A['cycles']),('gait-distance',distance),('hit-times',A['hit']),('velocities',A['vel'])]:data=data.astype('float32');np.save(H/f'{name}.npy',data);data.tofile(H/f'{name}.f32')
(H/'simulation.json').write_text(json.dumps(dict(version='V15',config=HC,units=m.units,blueCount=0,redCount=50,frames=301,events=[],shooterEvents=[],fixtureEvents=[],controlColumns=S.get('controlColumns',[])),separators=(',',':')))
