"""V3: PDF formation topology, monotone individual charge and causal archery."""
from pathlib import Path
import json, math, csv, sys
import numpy as np
from motion_v22 import Crowd
from archers_v22 import Archers
from combat_response_v22 import CombatResponseV22
import time
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];variant=sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('--') else 'A';O=P/'variants'/variant;O.mkdir(exist_ok=True)
C=json.loads((O/'params.json').read_text())
requestedDuration=float(C['duration']);terminationEvidence=None
if C.get('openingBurst'):
 from archers_burst_v22r import Archers
if C.get('safeFrontEngagement'):
 from motion_volley_v22r import Crowd
if '--motion' in sys.argv:C['disableCombat']=True;O=O/'motion-data';O.mkdir(exist_ok=True)
rng=np.random.default_rng(C['seed']);dt=1/C['simulationFps'];N=round(C['duration']/dt)+1
blue=[];red=[];side=C['groupSide']
for g in range(C['blueGroups']):
 theta=g*math.pi/(C['blueGroups']-1);center=np.array([C['uHalfWidth']*math.cos(theta),C['uArmsStartZ']+C['uDepth']*math.sin(theta)])
 for row in range(side):
  for col in range(side):
   p=center+[(col-(side-1)/2)*C['blueSpacing'],(row-(side-1)/2)*C['blueSpacing']]
   blue.append(dict(id=f'B{len(blue):04}',team='blue',model='archer',group=g,start=p.tolist(),delay=float(rng.uniform(0,C['blueStartSpread'])),phase=float(rng.random()),cycle=float(C['archerCycle']*rng.uniform(.88,1.12))))
# PDF7 macro order: rear red flail, middle orange sword, front yellow samurai.
# Each homogeneous army is 3x3 platoons, with 6/8/4 rows and six columns.
# Preserve V5 initial placement exactly; production changes movement/state only.
baseline=json.loads((P/'baseline/V5-simulation.json').read_text())
blue=[dict(u) for u in baseline['units'][:baseline['blueCount']]]
red=[dict(u) for u in baseline['units'][baseline['blueCount']:]]
if 'blueArmyTranslation' in C:
 for u in blue:u['start']=(np.asarray(u['start'])+C['blueArmyTranslation']).tolist()
if 'redArmyTranslations' in C:
 for u in red:u['start']=(np.asarray(u['start'])+C['redArmyTranslations'].get(u['color'],[0.,0.])).tolist()
archers=Archers(blue,C)
if C.get('openingBurst'):archers.redUnits=red
# V22-R opt-in opening experiment. Only start delays change; original V22
# params take the untouched path. Keep slots, targets, speed and action ABI.
if 'openingBlueStartWindow' in C:
 longest=max(u['delay'] for u in blue)
 for u in blue:
  old=u['delay'];u['delay']=old*C['openingBlueStartWindow']/longest
  u['arrival']+=u['delay']-old;u['readyAt']+=u['delay']-old

for u in red:
 u['deathTime']=None
 u['delay']=float(.035+.125*u['phase']+.018*u['squadRow']+.006*u['row'])
 u['accelerationSeconds']=.25
if 'openingRedStartWindow' in C:
 for j,u in enumerate(red):
  u['delay']=C['openingRedStartWindow']*(((j+1)*.61803398875)%1)
motion=Crowd(red,C)
if C.get('safeFrontEngagement'):motion.blueDefensePositions=archers.defenseSlots+archers.slotOffsets
redChargeStart=float(C.get('redChargeStart',0.))
blueResponse=CombatResponseV22(blue,config=C)
responseTargets=[]

squadBounds={}
for u in red:
 pts=[v['start'][0] for v in red if v['platoon']==u['platoon']]
 squadBounds[u['platoon']]=(min(pts)-.55,max(pts)+.55)
nb,nr=len(blue),len(red);units=blue+red;n=nb+nr
positions=np.zeros((N,n,2),np.float32);gait=np.zeros((N,n),np.float32);velocities=np.zeros((N,n,2),np.float32)
rp=np.array([u['start'] for u in red]);bs=np.array([u['start'] for u in blue]);death=np.full(nr,1e6);hp=np.full(nr,C['redHitPoints']);hit=np.full(nr,-10.);lastHit=np.full((N,nr),-10,np.float32)
responses=[];states=np.zeros((N,nr),np.uint8);avoidance=np.full((N,nr),-1,np.int32)
# One authoritative integrated control state per member. No position slot target.
control=np.zeros((N,nr,10),np.float32);cycles=np.zeros((N,n),np.float32)
forward=np.zeros(nr);paceAcceleration=np.zeros(nr);stride=np.array([u['gaitStride'] for u in red]);posture=np.array([u['personalPosture'] for u in red]);arm=np.zeros(nr);turn=np.zeros(nr)
control[0]=motion.control();simulationStart=time.perf_counter()
events=[];scheduled={};fired=[[] for _ in blue];arrival=max(u['arrival'] for u in blue);firstDraw=min(u['arrival'] for u in blue)
nextAllowed=np.zeros(nr);routes=np.full(nr,-1,int);routeSide=np.zeros(nr);reason=np.zeros((N,nr),np.uint8);slowCause=np.full((N,nr),-1,np.int32)
nextFire=np.array([u['readyAt'] for u in blue]);vx=np.zeros(nr);minimum=1e6;minf=0;distanceByFrame=[]
blueControls=np.zeros((N,nb,12),np.float32);pressureHistory=np.zeros((N,nr),np.float32)
for f in range(N):
 t=f*dt
 for target,e in scheduled.pop(f,[]):
  assert death[target]>t-1e-6
  damage=int(e['plannedDamage']);motion.apply_hit(target,damage,max(0.,t-redChargeStart));hp[target]-=damage;hit[target]=t;e.update(damage=damage,remainingHP=int(hp[target]),killed=bool(hp[target]<=0))
  blueResponse.record_impact(e['shooter'],target,damage,bool(hp[target]<=0),t)
  if hp[target]<=0:death[target]=t
  responses.append(dict(event=e['id'],memberID=red[target]['id'],time=t,kind='DEAD' if hp[target]<=0 else 'STAGGER',source='BOUND_ARROW_IMPACT'))
 archers.redPositions=rp
 archers.responseOffsets=blueResponse.offsets(t,archers.position,dt,rp)
 responseTargets.append(archers.responseOffsets.copy())
 archers.move(t,dt);positions[f,:nb]=archers.position
 motion.bluePositions=archers.position
 alive=death>t
 if f:
  if t>=redChargeStart:motion.step(t-redChargeStart,dt)
  rp=motion.position.copy();control[f]=motion.control()
  pressureHistory[f]=motion.pressure;states[f]=motion.behavior;avoidance[f]=motion.route;reason[f]=motion.reason;slowCause[f]=motion.neighbor
 positions[f,nb:]=rp;lastHit[f]=hit
 if f:
  step=positions[f]-positions[f-1];velocities[f]=step/dt;gait[f]=gait[f-1]+np.linalg.norm(step,axis=1)
  cycles[f,:nb]=cycles[f-1,:nb]+np.linalg.norm(step[:nb],axis=1)/C['blueStride']
  cycles[f,nb:]=motion.cycles
 m=float(cKDTree(positions[f,:nb]).query(rp)[0].min());distanceByFrame.append(m)
 if f and C.get('autoCut'):
  prior=distanceByFrame[-2];maxStep=np.linalg.norm(positions[f]-positions[f-1],axis=1)
  lower=min(prior,m)-.5*(maxStep[:nb].max()+maxStep[nb:].max())-2*C['weaponEnvelopeRadius']
  if lower<C['minimumEnemyClearance']+.05:
   terminationEvidence=dict(reason='SAFETY_AUTOCUT',requestedDuration=requestedDuration,firstRejectedFrame=f,firstRejectedTime=t,lastAcceptedFrame=f-1,lastAcceptedTime=(f-1)*dt,priorCenterDistance=prior,rejectedCenterDistance=m,rejectedSurfaceClearance=m-2*C['weaponEnvelopeRadius'],conservativeSegmentClearance=float(lower),requiredSurfaceClearance=C['minimumEnemyClearance'],cutBuffer=.05,maximumBlueStep=float(maxStep[:nb].max()),maximumRedStep=float(maxStep[nb:].max()))
   N=f;cutFrame=f-1;C['duration']=cutFrame*dt
   pass # first unsafe state discarded; no contact frame is rendered
   break
 if m<minimum:minimum=m;minf=f
 if not C.get('disableCombat',False):
  pending=np.zeros(nr,int)
  pendingDamage=np.zeros(nr,int) if C.get('openingBurst') else None
  for batch in scheduled.values():
   for target,e in batch:
    pending[target]+=1
    if pendingDamage is not None:pendingDamage[target]+=e['plannedDamage']
  reserved=(pending>0)|(t<nextAllowed)|(hp<=0)
  if C.get('openingBurst'):archers.set_pending(pending,pendingDamage,hp)
  def spawn(j,target,t,drawStart):
   u=blue[j];relative=rp[target]-positions[f,j];targetVelocity=motion.velocity[target]
   qa=float(targetVelocity@targetVelocity-C['arrowSpeed']**2);qb=2*float(relative@targetVelocity);qc=float(relative@relative)
   disc=max(0.,qb*qb-4*qa*qc);roots=[(-qb+math.sqrt(disc))/(2*qa),(-qb-math.sqrt(disc))/(2*qa)]
   flight=max(.18,min(x for x in roots if x>0));hf=f+max(1,round(flight/dt));nextAllowed[target]=hf*dt+C['minHitInterval']
   e=dict(id=f'A{len(events):05}',shooter=j,shooterID=u['id'],target=nb+target,targetID=red[target]['id'],releaseFrame=f,release=t,drawStart=float(drawStart),aimStart=float(drawStart-u['aimSeconds']),impactFrame=hf,impact=hf*dt,releaseDistance=float(np.linalg.norm(relative)),arc=float(C['arrowArcHeight']*(.9+.2*u['phase'])),damage=None,plannedDamage=3 if j%17==0 else 1)
   events.append(e)
   if hf<N:e['resolution']='IMPACT_IN_SHOT';scheduled.setdefault(hf,[]).append((target,e))
   else:e.update(resolution='IN_FLIGHT_AT_CUT',remainingHP=None,killed=False)
   fired[j].append(len(events)-1);return e
  archers.update_fire(t,dt,rp,hp,reserved,spawn)
 blueControls[f]=archers.control()
 if C.get('checkpointFrame')==f:
  import pickle
  checkpoint=dict(frame=f,config=dict(C),motion=motion,archers=archers,blueResponse=blueResponse,red=red,blue=blue,hp=hp,death=death,hit=hit,events=events,scheduled=scheduled,nextAllowed=nextAllowed,responses=responses)
  with (O/'continuation-checkpoint.pkl').open('wb') as checkpointFile:pickle.dump(checkpoint,checkpointFile,protocol=5)
 if f%120==0:print('SIM',round(t,2),'alive',int(alive.sum()),'arrows',len(events),flush=True)
if terminationEvidence is None:
 terminationEvidence=dict(reason='REQUESTED_DURATION_REACHED',requestedDuration=requestedDuration,lastAcceptedFrame=N-1,lastAcceptedTime=(N-1)*dt)
(O/'termination-evidence.json').write_text(json.dumps(terminationEvidence,indent=2),encoding='utf8')
# Trim all authoritative arrays to the last safe state. Reclassify arrows
# beyond that state instead of claiming their damage happened on screen.
positions=positions[:N];velocities=velocities[:N];gait=gait[:N];lastHit=lastHit[:N];control=control[:N];cycles=cycles[:N];states=states[:N];avoidance=avoidance[:N];reason=reason[:N];slowCause=slowCause[:N]
distanceByFrame=distanceByFrame[:N];minimum=min(distanceByFrame);minf=int(np.argmin(distanceByFrame))
for j in range(nr):
 if death[j]>C['duration']:death[j]=1e6
for e in events:
 if e['impactFrame']>=N:
  e.update(resolution='IN_FLIGHT_AT_CUT',damage=None,remainingHP=None,killed=False,destinationEvidence='Extrapolated beyond safe cut; no visible impact claimed')
blueControls=blueControls[:N];pressureHistory=pressureHistory[:N]
np.save(O/'response-targets.npy',np.asarray(responseTargets)[:N])
(O/'blue-transitions.json').write_text(json.dumps(archers.transitions,indent=2))
blueControls.tofile(O/'blue-control.f32');np.save(O/'blue-control.npy',blueControls);np.save(O/'formation-pressure.npy',pressureHistory)
responses=[e for e in responses if e['time']<=C['duration']]
(O/'params.json').write_text(json.dumps(C,indent=2))
audit=json.loads((O/'asset-render-audit.json').read_text(encoding='utf8')) if (O/'asset-render-audit.json').exists() else None
for e in events:
 if e['resolution']=='IMPACT_IN_SHOT':end=positions[e['impactFrame'],e['target']]
 else:end=positions[-1,e['target']]+velocities[-1,e['target']]*(e['impact']-C['duration'])
 e['destination']=[float(end[0]),.85,float(end[1])]
 p=positions[e['releaseFrame'],e['shooter']];yaw=float(blueControls[e['releaseFrame'],e['shooter'],8]);e['releaseYaw']=yaw;local=audit['models']['archer']['bowReleaseLocal'] if audit else [0,C['arrowOriginHeight'],C['arrowOriginForward']]
 e['origin']=[float(p[0]+local[0]*math.cos(yaw)+local[2]*math.sin(yaw)),float(local[1]+.015),float(p[1]-local[0]*math.sin(yaw)+local[2]*math.cos(yaw))];e['originMapping']='sampled native left-hand at release phase 0.64, rotated by actual per-member facingYaw' if audit else 'provisional'
 if e['resolution']=='IMPACT_IN_SHOT':assert e['damage'] is not None
for j,u in enumerate(red):u['deathTime']=None if death[j]>1e5 else float(death[j])
positions.tofile(O/'trajectories.f32');np.save(O/'trajectories.npy',positions);gait.tofile(O/'gait-distance.f32');np.save(O/'gait-distance.npy',gait);lastHit.tofile(O/'hit-times.f32');np.save(O/'hit-times.npy',lastHit);velocities.tofile(O/'velocities.f32')
np.save(O/'movement-reasons.npy',reason);np.save(O/'slow-causes.npy',slowCause);np.save(O/'member-states.npy',states);np.save(O/'avoidance-causes.npy',avoidance);(O/'hit-responses.json').write_text(json.dumps(responses,indent=2))
control.tofile(O/'red-control.f32');np.save(O/'red-control.npy',control);cycles.tofile(O/'gait-cycles.f32');np.save(O/'gait-cycles.npy',cycles)
(O/'simulation.json').write_text(json.dumps(dict(version='V22-SPECIALIST-TEST',config=C,units=units,blueCount=nb,redCount=nr,frames=N,blueLastArrival=arrival,events=events,shooterEvents=fired,controlColumns=['state','timer','target','lastRelease','walkPhase','turnPhase','actionPhase','moveSpeed','facingYaw','targetYaw','stateProgress','releaseEventId']),separators=(',',':')),encoding='utf8')
report=dict(status='PASS' if minimum-2*C['weaponEnvelopeRadius']>=C['minimumEnemyClearance'] else 'FAIL',framesChecked=N,minimumCenterDistance=minimum,minimumAtSeconds=minf*dt,envelopeRadiusPerUnit=C['weaponEnvelopeRadius'],minimumSurfaceClearance=minimum-2*C['weaponEnvelopeRadius'],requiredSurfaceClearance=C['minimumEnemyClearance'],blueCount=nb,redCounts={c:sum(u['color']==c for u in red) for c in ['red','orange','yellow']},arrows=len(events),causalKills=int((death<1e5).sum()),deadBodiesIncluded=True,noMeleeEvents=True,distanceByFrame=distanceByFrame)
(O/'safety-and-causality.json').write_text(json.dumps(report,indent=2),encoding='utf8')
with (O/'member-trajectories.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['frame60','seconds','id','team','model','x','z','worldSpeed','cumulativePath','life'])
 for k in range(0,N,6):
  for j,u in enumerate(units):w.writerow([k,round(k*dt,3),u['id'],u['team'],u['model'],*positions[k,j].round(5),round(float(np.linalg.norm(velocities[k,j])),4),round(float(gait[k,j]),4),'DEAD' if u.get('deathTime') is not None and k*dt>=u['deathTime'] else 'ALIVE'])
(O/'simulation-performance.json').write_text(json.dumps(dict(wallSeconds=time.perf_counter()-simulationStart,steps=motion.metrics),indent=2));print({k:v for k,v in report.items() if k!='distanceByFrame'},flush=True)
if C.get('safeFrontEngagement'):
 (O/'front-projection.json').write_text(json.dumps(dict(frames=motion.frontConstraintFrames,solver=motion.projectionStats),indent=2))
assert report['status']=='PASS',report['minimumSurfaceClearance']




