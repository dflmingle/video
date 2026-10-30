"""Resume the trusted C1 F159 checkpoint, preserving every prefix array/event."""
from pathlib import Path
import sys,json,pickle,math,copy
import numpy as np
from melee_continuation_v22r import MeleeContinuation

P=Path(__file__).resolve().parents[1]
def serial(value):
 if isinstance(value,np.generic):return value.item()
 if isinstance(value,np.ndarray):return value.tolist()
 raise TypeError(type(value).__name__)
source=P/'variants'/(sys.argv[sys.argv.index('--source')+1] if '--source' in sys.argv else 'V22R-C1')
out=P/'variants'/(sys.argv[sys.argv.index('--out')+1] if '--out' in sys.argv else 'V22R-C1-melee');out.mkdir(exist_ok=True)
S=json.loads((source/'simulation.json').read_text(encoding='utf8'))
checkpoint=P/'variants'/(sys.argv[sys.argv.index('--checkpoint')+1] if '--checkpoint' in sys.argv else 'V22R-C1-checkpoint')/'continuation-checkpoint.pkl'
with checkpoint.open('rb') as f: ck=pickle.load(f)
C=copy.deepcopy(S['config']);C.update(meleeContinuation=True,autoCut=False)
m,a,response=ck['motion'],ck['archers'],ck['blueResponse']
nb,nr=a.n,m.n;n=nb+nr;dt=1/C['simulationFps'];cut=ck['frame'];cutTime=cut*dt
hp=ck['hp'].copy();death=ck['death'].copy();hit=ck['hit'].copy()
bhp=np.full(nb,3);bdeath=np.full(nb,1e6);bhit=np.full(nb,-10.)
engine=MeleeContinuation(m,a,bhp,bdeath)
prefix=copy.deepcopy(S['events']);events=copy.deepcopy(prefix)
scheduled={}
for e in events:
 if e['impactFrame']>cut:scheduled.setdefault(e['impactFrame'],[]).append(e)
nextAllowed=ck['nextAllowed'].copy();fired=copy.deepcopy(S['shooterEvents'])
responses=copy.deepcopy(ck['responses']);arrays={}
for name in ['trajectories','gait-distance','hit-times','red-control','gait-cycles','blue-control']:
 arrays[name]=list(np.load(source/(name+'.npy')))
arrays['velocities']=list(np.fromfile(source/'velocities.f32',np.float32).reshape(-1,n,2))
melee=[np.zeros((nr,4),np.float32) for _ in range(cut+1)]
blueHits=[np.full(nb,-10.,np.float32) for _ in range(cut+1)]
previous=arrays['trajectories'][-1].astype(float);gait=arrays['gait-distance'][-1].astype(float)
cycle=arrays['gait-cycles'][-1].astype(float)
winner=None;wonAt=None;last=30.
auditPath=source/'asset-render-audit.json'
releaseLocal=json.loads(auditPath.read_text(encoding='utf8'))['models']['archer']['bowReleaseLocal'] if auditPath.exists() else [0,C['arrowOriginHeight'],C['arrowOriginForward']]
resumePath=out/'progress-checkpoint.pkl'
startFrame=cut+1
if '--resume' in sys.argv:
 with resumePath.open('rb') as resumeFile:globals().update(pickle.load(resumeFile))
 startFrame=f+1
for f in range(startFrame,round(last/dt)+1):
 t=f*dt
 engine.prepare(t,dt)
 a.redPositions=m.position;a.responseOffsets=response.offsets(t,a.position,dt,m.position)
 a.move(t,dt);engine.integrate_red(t,dt)
 a.deadMask=bhp<=0
 for e in scheduled.pop(f,[]):
  j=e['target']-nb;endpoint=np.array(e['destination'])[::2]
  error=float(np.linalg.norm(endpoint-m.position[j]))
  # Resolve against the actual impact-frame root, after the one collision-
  # constrained integral. Never damage a merely predicted future position.
  valid=hp[j]>0 and error<=.68
  e.update(endpointError=error,resolution='IMPACT_IN_SHOT' if valid else 'MISS',damage=int(e['plannedDamage']) if valid else 0,remainingHP=int(hp[j]),killed=False)
  if valid:
   damage=e['plannedDamage'];m.apply_hit(j,damage,t);hp[j]-=damage;hit[j]=t
   e.update(remainingHP=int(hp[j]),killed=bool(hp[j]<=0))
   if hp[j]<=0:death[j]=t
   response.record_impact(e['shooter'],j,damage,bool(hp[j]<=0),t)
   responses.append(dict(event=e['id'],memberID=m.units[j]['id'],time=t,kind='DEAD' if hp[j]<=0 else 'STAGGER',source='BOUND_ARROW_IMPACT'))
 for event in engine.events:
  if abs(event['time']-t)<dt*.1 and event['damage']:bhit[event['target']]=t
 pending=np.zeros(nr,int);pendingDamage=np.zeros(nr,int)
 for batch in scheduled.values():
  for e in batch:
   j=e['target']-nb;pending[j]+=1;pendingDamage[j]+=e['plannedDamage']
 reserved=(pending>0)|(t<nextAllowed)|(hp<=0)
 a.set_pending(pending,pendingDamage,hp)
 def spawn(shooter,target,release,drawStart):
  relative=m.position[target]-a.position[shooter];velocity=m.velocity[target]
  qa=float(velocity@velocity-C['arrowSpeed']**2);qb=2*float(relative@velocity);qc=float(relative@relative)
  roots=np.roots([qa,qb,qc]);flight=max(.18,min(float(r.real) for r in roots if abs(r.imag)<1e-8 and r.real>0))
  hf=f+max(1,round(flight/dt));nextAllowed[target]=hf*dt+C['minHitInterval']
  end=m.position[target]+velocity*((hf-f)*dt);yaw=float(a.facingYaw[shooter]);local=releaseLocal;p=a.position[shooter]
  e=dict(id=f'A{len(events):05}',shooter=shooter,shooterID=a.units[shooter]['id'],target=nb+target,targetID=m.units[target]['id'],releaseFrame=f,release=t,drawStart=float(drawStart),aimStart=float(drawStart-a.units[shooter]['aimSeconds']),impactFrame=hf,impact=hf*dt,releaseDistance=float(np.linalg.norm(relative)),arc=float(C['arrowArcHeight']*(.9+.2*a.units[shooter]['phase'])),damage=None,plannedDamage=3 if shooter%17==0 else 1,resolution='IN_FLIGHT_AT_CUT',remainingHP=None,killed=False,destination=[float(end[0]),.85,float(end[1])],origin=[float(p[0]+local[0]*math.cos(yaw)+local[2]*math.sin(yaw)),float(local[1]+.015),float(p[1]-local[0]*math.sin(yaw)+local[2]*math.cos(yaw))],releaseYaw=yaw,ballisticPolicy='FIXED_AT_RELEASE_PREDICTION')
  events.append(e);fired[shooter].append(len(events)-1);scheduled.setdefault(hf,[]).append(e);return e
 a.update_fire(t,dt,m.position,hp,reserved,spawn)
 position=np.vstack([a.position,m.position]);step=position-previous;velocity=step/dt;gait+=np.linalg.norm(step,axis=1)
 cycle[:nb]+=np.linalg.norm(step[:nb],axis=1)/C['blueStride'];cycle[nb:]=m.cycles
 for name,data in [('trajectories',position),('velocities',velocity),('gait-distance',gait),('gait-cycles',cycle),('hit-times',hit),('red-control',m.control()),('blue-control',a.control())]:arrays[name].append(np.array(data,dtype=np.float32,copy=True))
 melee.append(engine.control().astype(np.float32));blueHits.append(bhit.astype(np.float32).copy());previous=position.copy()
 if not (hp>0).any() or not (bhp>0).any():
  if winner is None:winner='blue' if not (hp>0).any() else 'red';wonAt=t
  if t>=wonAt+.7:break
 if f%60==0:
  print('CONTINUE',round(t,3),'red',int((hp>0).sum()),'blue',int((bhp>0).sum()),'arrows',len(events),'melee',len(engine.events),flush=True)
  keys=['f','m','a','response','hp','death','hit','bhp','bdeath','bhit','engine','events','scheduled','nextAllowed','fired','responses','arrays','melee','blueHits','previous','gait','cycle','winner','wonAt']
  with resumePath.open('wb') as progressFile:pickle.dump({key:globals()[key] for key in keys},progressFile,protocol=5)

C['duration']=float((f+1)*dt);C['continuationPolicy']='C1_PREFIX_LOCKED_THEN_LOCAL_MELEE'
for name,data in arrays.items():
 arr=np.asarray(data,dtype=np.float32);np.save(out/(name+'.npy'),arr);arr.tofile(out/(name+'.f32'))
np.asarray(melee,np.float32).tofile(out/'melee-control.f32');np.asarray(blueHits,np.float32).tofile(out/'blue-hit-times.f32')
units=copy.deepcopy(S['units'])
for j,u in enumerate(units):
 d=bdeath[j] if j<nb else death[j-nb];u['deathTime']=None if d>1e5 else float(d)
simulation=dict(S,config=C,units=units,frames=f+1,events=events,shooterEvents=fired,prefixCutTime=cutTime,prefixEvents=prefix,prefixShooterEvents=S['shooterEvents'],meleeEvents=engine.events)
(out/'params.json').write_text(json.dumps(C,indent=2,default=serial),encoding='utf8')
(out/'simulation.json').write_text(json.dumps(simulation,separators=(',',':'),default=serial),encoding='utf8')
(out/'hit-responses.json').write_text(json.dumps(responses,default=serial),encoding='utf8')
prefixCheck={name:bool(np.array_equal(np.asarray(data[:cut+1]),np.load(source/(name+'.npy')))) for name,data in arrays.items() if (source/(name+'.npy')).exists()}
report=dict(prefixArraysEqual=prefixCheck,prefixEventsFrozen=True,winner=winner,wonAt=wonAt,duration=C['duration'],aliveRed=int((hp>0).sum()),aliveBlue=int((bhp>0).sum()),meleeAttempts=len(engine.events),meleeHits=sum(e['damage']>0 for e in engine.events),meleeKills=sum(e['killed'] for e in engine.events),arrowReleases=len(events),arrowHits=sum(bool(e.get('damage')) for e in events),arrowKills=sum(bool(e.get('killed')) for e in events),minimumBodyCenter=min(e['minimumCenter'] for e in engine.solverAudit),minimumSweptBodyCenter=min(e['sweptMinimum'] for e in engine.solverAudit),physicalBodyDiameter=.58,meleeRules=dict(blueHP=3,redDamage=1,attackDuration=engine.duration,impactPhase=engine.impactPhase,reach=engine.reach),termination='SIDE_ELIMINATED' if winner else 'TIME_LIMIT_UNRESOLVED')
(out/'continuation-audit.json').write_text(json.dumps(report,indent=2,default=serial),encoding='utf8')
(out/'body-projection.json').write_text(json.dumps(engine.solverAudit,default=serial),encoding='utf8')
print(json.dumps(report,indent=2,default=serial),flush=True)
assert all(prefixCheck.values())
