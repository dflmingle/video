"""V3: PDF formation topology, monotone individual charge and causal archery."""
from pathlib import Path
import json, math, csv, sys
import numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];variant=sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('--') else 'A';O=P/'variants'/variant;O.mkdir(exist_ok=True)
C=json.loads((O/'params.json').read_text())
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
for j,u in enumerate(blue):
 # Stable ID-derived individual parameters, never per-frame random noise.
 row=(j%36)//6;col=j%6
 q=((j+1)*.61803398875)%1; r=((col+1)*.41421356237+u['group']*.19)%1
 # Front members leave first and never travel behind followers in their lane.
 # Individual phase and per-column timing differ without compressing body gaps.
 u['delay']=.035+.032*(u['group']%4)+.021*row+.035*r
 u['moveSeconds']=C['blueMoveSeconds']*(.92+.017*row+.050*r)
 u['arrival']=u['delay']+u['moveSeconds']
 u['drawSeconds']=.25+.10*q;u['aimSeconds']=.055+.045*r
 u['recoverSeconds']=.19+.09*(1-q);u['turnSeconds']=.07+.07*r
 u['cycle']=max(.04+u['drawSeconds']+u['aimSeconds']+u['recoverSeconds']+u['turnSeconds'],C['archerCycle']*(.85+.35*r))
 u['readyAt']=u['arrival']+u['turnSeconds']+u['drawSeconds']+u['aimSeconds']+.16*q
 u['shootYaw']=math.pi

for u in red:
 u['deathTime']=None;u['speed']*=C['redSpeed']/baseline['config']['redSpeed'];u['accelerationSeconds']*=C['accelerationSeconds']/baseline['config']['accelerationSeconds']
 # Continuous, repeatable personal/squad pace. Starts remain exactly unchanged.
 # Keep nominal organization: modest correlated squad pace and stable personal pace.
 # Natural pre-impact deformation is allowed. No slot spring or rectangle restoration.
 squad=.012*math.sin(u['platoon']*2.399)+.006*math.cos(u['platoon']*1.17)
 personal=.009*math.sin(int(u['id'][1:])*2.399)
 front=.008*(1-u['row']/max(1,C['armyMemberRows'][u['army']]-1))
 u['speed']=C['redSpeed']*(1+squad+personal+front)
 u['delay']=float(.035+.125*u['phase']+.018*u['squadRow']+.006*u['row'])
 u['accelerationSeconds']=float(.20+.10*u['phase']+.022*u['squadRow'])
 u['laneDrift']=.13*math.sin(u['platoon']*1.7+u['column']*.7)
 u['gaitScale']=.96+.08*((int(u['id'][1:])*.754877666)%1)
 u['gaitStride']=C['runStride']*u['gaitScale'];u['personalPosture']=.06*math.sin(int(u['id'][1:])*1.319)
 u['headingBias']=.018*math.sin(int(u['id'][1:])*1.731)
 pid=int(u['id'][1:]);q=(pid*.7548776662466927)%1;r=(pid*.5698402909980532)%1
 u['pacePeriod']=C['pacePeriodMin']+(C['pacePeriodMax']-C['pacePeriodMin'])*q
 u['paceOffset']=2*math.pi*r;u['paceAmplitude']=C['paceAmplitude']*(.80+.40*((pid*.438579)%1))
 u['speedResponseSeconds']=.12+.08*((pid*.41421356)%1)
 u['reacceleration']=5.5+3.5*q;u['controlledDeceleration']=8.+3.*r
 u['maxChargeSpeed']=u['speed']*(1+u['paceAmplitude']+.015)

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
control[0,:,3]=stride;control[0,:,5]=posture
events=[];scheduled={};fired=[[] for _ in blue];arrival=max(u['arrival'] for u in blue);firstDraw=min(u['arrival'] for u in blue)
nextAllowed=np.zeros(nr);routes=np.full(nr,-1,int);routeSide=np.zeros(nr);reason=np.zeros((N,nr),np.uint8);slowCause=np.full((N,nr),-1,np.int32)
nextFire=np.array([u['readyAt'] for u in blue]);vx=np.zeros(nr);minimum=1e6;minf=0;distanceByFrame=[]
for f in range(N):
 t=f*dt
 for target,e in scheduled.pop(f,[]):
  assert death[target]>t-1e-6
  damage=int(e['plannedDamage']);hp[target]-=damage;hit[target]=t;e.update(damage=damage,remainingHP=int(hp[target]),killed=bool(hp[target]<=0))
  if hp[target]<=0:death[target]=t
  responses.append(dict(event=e['id'],memberID=red[target]['id'],time=t,kind='DEAD' if hp[target]<=0 else 'STAGGER',source='BOUND_ARROW_IMPACT'))
 for j,u in enumerate(blue):
  a=float(np.clip((t-u['delay'])/u['moveSeconds'],0,1));k=a*a*(3-2*a);positions[f,j]=bs[j]+[0,-C['blueAdvance']*k]
 alive=death>t
 if f:
  previous=rp.copy();v=np.zeros_like(rp)
  targetSpeed=np.zeros(nr);effort=np.zeros(nr);ceiling=np.array([u['maxChargeSpeed'] for u in red])
  for j,u in enumerate(red):
   if not alive[j] or t<u['delay']:continue
   a=min(1,(t-u['delay'])/u['accelerationSeconds']);acc=a*a*(3-2*a)
   age=t-hit[j];stagger=C['hitStaggerSeconds'];recover=C['hitRecoverySeconds'];damage=C['redHitPoints']-hp[j]
   woundFactor=1. if damage==0 else C['hitWoundSpeed'] if damage==1 else C['hitSeriousSpeed']
   if age<stagger:
    factor=.55 if damage==1 else .35;states[f,j]=1;reason[f,j]=1
   elif age<stagger+recover:
    a2=(age-stagger)/recover;low=.55 if damage==1 else .35;factor=low+(woundFactor-low)*(a2*a2*(3-2*a2));states[f,j]=2;reason[f,j]=1
   else:
    factor=woundFactor;states[f,j]=0 if damage==0 else 4 if damage==1 else 5
    if damage:reason[f,j]=1
   # Individual push / release of exertion: deterministic personal oscillators,
   # not frame-wise noise. Actual response is bounded by current speed and accel.
   ageRun=max(0,t-u['delay']);osc=math.sin(2*math.pi*ageRun/u['pacePeriod']+u['paceOffset'])
   effort[j]=osc;targetSpeed[j]=u['speed']*(1+u['paceAmplitude']*osc)*acc*factor
   if ageRun<u['accelerationSeconds']:
    forward[j]=targetSpeed[j]
   else:
    wanted=float(np.clip((targetSpeed[j]-forward[j])/u['speedResponseSeconds'],-u['controlledDeceleration'],u['reacceleration']))
    paceAcceleration[j]+=float(np.clip(wanted-paceAcceleration[j],-65*dt,65*dt))
    forward[j]=float(np.clip(forward[j]+paceAcceleration[j]*dt,0,ceiling[j]))
   # Bound injury slowdown to this exact member at the bound impact tick.
   if 0<=age<dt*1.1:forward[j]=min(forward[j],targetSpeed[j])
   v[j,1]=forward[j]
   # Wounded person alone loses balance, stepping slightly out of original lane.
   woundSide=1 if u['column']>=C['redMemberColumns']/2 else -1
   displacement=0 if damage==0 else woundSide*(.24 if damage==1 else .34)*(1-math.exp(-max(0,age)*8))
   # Independent heading/velocity, not a return spring to a fixed slot.
   lo,hi=squadBounds[u['platoon']]
   steer=u['headingBias']*acc
   if damage and 0<=age<.55:steer+=woundSide*.45*math.sin(math.pi*age/.55)
   if rp[j,0]<lo:steer+=min(.7,(lo-rp[j,0])*3)
   if rp[j,0]>hi:steer-=min(.7,(rp[j,0]-hi)*3)
   v[j,0]=steer
  states[f,~alive]=3
  # Predict relative motion for any slower live member. A persistent passing
  # target is selected from future occupancy, with no per-frame random offsets.
  crowd=cKDTree(rp);obstacle=death>t-.65
  ahead=crowd.query_ball_point(rp+[0,3.2],4.7)
  for j,local in enumerate(ahead):
   if not alive[j] or t<red[j]['delay']:continue
   k=int(routes[j]);valid=k>=0 and obstacle[k] and rp[k,1]-rp[j,1]>-.65 and rp[k,1]-rp[j,1]<7.0 and abs(rp[k,0]-rp[j,0])<.9
   if not valid:
    choices=[]
    for q in local:
     if q==j or not obstacle[q]:continue
     dz=rp[q,1]-rp[j,1];dx=abs(rp[q,0]-rp[j,0]);dv=v[j,1]-v[q,1]
     if .05<dz<7.0 and dx<.68 and dv>.35 and (dz-.61)/dv<1.15:choices.append(((dz-.61)/dv,q))
    if not choices:routes[j]=-1;continue
    _,k=min(choices);routes[j]=k
    tau=float(np.clip((rp[k,1]-rp[j,1])/max(.35,v[j,1]-v[k,1]),.22,1.15))
    lo,hi=squadBounds[red[j]['platoon']];candidates=[]
    for side in [-1,1]:
     goal=float(np.clip(rp[k,0]+side*.76,lo,hi));pred=rp[j]+[goal-rp[j,0],v[j,1]*tau]
     others=[q for q in local if q!=j and obstacle[q]]
     pts=rp[others]+v[others]*tau
     clearance=float(np.linalg.norm(pts-pred,axis=1).min()) if len(pts) else 3
     candidates.append((min(clearance,1.2)-.12*abs(goal-rp[j,0]),goal))
    routeSide[j]=max(candidates)[1]
   v[j,0]=np.clip((routeSide[j]-rp[j,0])*3,-2.1,2.1);avoidance[f,j]=k;reason[f,j]=2
  # Recent corpses keep a stationary occupied disk; later prone bodies keep a
  # smaller footprint. Alive followers cannot use them as empty space.
  solid=alive | ((death<=t)&(t-death<.9));ids=np.where(solid)[0]
  # Smooth preferred velocity, then solve relative velocity half-planes. No
  # position projection: every correction is a bounded actual velocity.
  vx+=np.clip(v[:,0]-vx,-dt*9,dt*9);vx=np.clip(vx,-2.7,2.7);vx[~alive]=0;v[:,0]=vx
  pairs=cKDTree(rp[ids]).query_pairs(1.25,output_type='ndarray')
  if len(pairs):
   ia=ids[pairs[:,0]];ib=ids[pairs[:,1]];delta=rp[ia]-rp[ib];dist=np.linalg.norm(delta,axis=1);norm=delta/np.maximum(dist[:,None],1e-8);required=(.615-dist)/dt
   for iteration in range(150):
    rel=np.sum((v[ia]-v[ib])*norm,axis=1);viol=required-rel;bad=np.where(viol>1e-5)[0]
    if not len(bad):break
    for q in bad:
     i,k=ia[q],ib[q];normal=norm[q];need=required[q]-float(np.dot(v[i]-v[k],normal))
     if need<=1e-5:continue
     # Hurt soldiers keep their slowdown; following unhurt soldiers yield only
     # to the concrete occupied body, never to a group-wide density formula.
     wi=0. if not alive[i] else .1 if hp[i]<C['redHitPoints'] else 1.;wk=0. if not alive[k] else .1 if hp[k]<C['redHitPoints'] else 1.;total=wi+wk
     if total==0:continue
     v[i]+=normal*need*wi/total;v[k]-=normal*need*wk/total
     v[i,0]=np.clip(v[i,0],-2.7,2.7);v[k,0]=np.clip(v[k,0],-2.7,2.7)
     v[i,1]=np.clip(v[i,1],0,ceiling[i]);v[k,1]=np.clip(v[k,1],0,ceiling[k])
     if hp[i]==C['redHitPoints']:slowCause[f,i]=k;reason[f,i]=3
     if hp[k]==C['redHitPoints']:slowCause[f,k]=i;reason[f,k]=3
  v[~alive]=0;rp+=v*dt;vx=v[:,0].copy();forward=v[:,1].copy()
  # Derive pose intent from actual solved motion, not from desired speed alone.
  actualAcceleration=(v[:,1]-velocities[f-1,nb:,1])/dt
  strideGoal=np.array([u['gaitStride'] for u in red])*(1+C['dynamicStrideAmplitude']*effort+.018*np.tanh(actualAcceleration/5))
  stride+= (strideGoal-stride)*(1-math.exp(-dt/.12))
  postureGoal=np.array([u['personalPosture'] for u in red])+.055*effort+.035*np.tanh(actualAcceleration/6)
  posture+=(postureGoal-posture)*(1-math.exp(-dt/.10))
  armGoal=.5*effort+.35*np.tanh(actualAcceleration/6)-.45*(np.abs(v[:,0])>1.0)
  arm+=(armGoal-arm)*(1-math.exp(-dt/.12))
  turnGoal=np.arctan2(v[:,0],np.maximum(.1,v[:,1]));turn+=(turnGoal-turn)*(1-math.exp(-dt/.08))
  control[f,:,0]=targetSpeed;control[f,:,1]=v[:,1];control[f,:,2]=actualAcceleration;control[f,:,3]=stride;control[f,:,4]=np.linalg.norm(v,axis=1)/stride;control[f,:,5]=posture;control[f,:,6]=arm;control[f,:,7]=turn;control[f,:,8]=effort;control[f,:,9]=reason[f]
  assert np.all(rp[:,1]>=previous[:,1]-1e-9)
 positions[f,nb:]=rp;lastHit[f]=hit
 if f:
  step=positions[f]-positions[f-1];velocities[f]=step/dt;gait[f]=gait[f-1]+np.linalg.norm(step,axis=1)
  cycles[f,:nb]=cycles[f-1,:nb]+np.linalg.norm(step[:nb],axis=1)/C['blueStride']
  cycles[f,nb:]=cycles[f-1,nb:]+np.linalg.norm(step[nb:],axis=1)/np.maximum(.1,(control[f,:,3]+control[f-1,:,3])*.5)
 m=float(cKDTree(positions[f,:nb]).query(rp)[0].min());distanceByFrame.append(m)
 if m<minimum:minimum=m;minf=f
 if t>=firstDraw and not C.get('disableCombat',False):
  active=np.where(alive)[0];pending=np.zeros(nr,int)
  for batch in scheduled.values():
   for target,e in batch:pending[target]+=1
  for j,u in enumerate(blue):
   if t+dt*.1<nextFire[j]:continue
   eligible=active[((hp[active]-pending[active])>0)&(pending[active]==0)&(t>=nextAllowed[active])]
   if len(eligible):
    p=positions[f,j];ds=np.linalg.norm(rp[eligible]-p,axis=1)
    eligible=eligible[ds<=C['archerRange']]
   if len(eligible):
    sector=(u['group']+int(max(0,t-u['readyAt'])/u['cycle']))%3
    preferred=[k for k in eligible if red[k]['squadCol']==sector and ((int(red[k]['id'][1:])*.61803398875)%1)<.65]
    if preferred:eligible=np.array(preferred)
   if not len(eligible):continue
   p=positions[f,j];ds=np.linalg.norm(rp[eligible]-p,axis=1);close=eligible[np.argsort(ds)[:C['targetFrontCount']]]
   wounded=close[hp[close]<C['redHitPoints']];pool=wounded if len(wounded) and j%3==0 else close
   target=int(rng.choice(pool));dist=float(np.linalg.norm(rp[target]-p))
   flight=float(max(.35,dist/C['arrowSpeed']));hf=f+round(flight/dt)
   if t>C['duration']-1/C['fps']+1e-6:continue
   pending[target]+=1;nextAllowed[target]=hf*dt+C['minHitInterval'];e=dict(id=f'A{len(events):05}',shooter=j,shooterID=u['id'],target=nb+target,targetID=red[target]['id'],releaseFrame=f,release=t,drawStart=t-u['aimSeconds']-u['drawSeconds'],aimStart=t-u['aimSeconds'],impactFrame=hf,impact=hf*dt,arc=float(C['arrowArcHeight']*(.9+.2*u['phase'])),damage=None,plannedDamage=3 if j%13==0 else 1)
   events.append(e)
   if hf<N:e['resolution']='IMPACT_IN_SHOT';scheduled.setdefault(hf,[]).append((target,e))
   else:e.update(resolution='IN_FLIGHT_AT_CUT',remainingHP=None,killed=False,destinationEvidence='Extrapolated continuation beyond visible cut, no simulated damage')
   fired[j].append(len(events)-1);nextFire[j]=t+u['cycle']
 if f%120==0:print('SIM',round(t,2),'alive',int(alive.sum()),'arrows',len(events),flush=True)
audit=json.loads((O/'asset-render-audit.json').read_text()) if (O/'asset-render-audit.json').exists() else None
for e in events:
 if e['resolution']=='IMPACT_IN_SHOT':end=positions[e['impactFrame'],e['target']]
 else:end=positions[-1,e['target']]+velocities[-1,e['target']]*(e['impact']-C['duration'])
 e['destination']=[float(end[0]),.85,float(end[1])]
 p=positions[e['releaseFrame'],e['shooter']];yaw=math.atan2(e['destination'][0]-p[0],e['destination'][2]-p[1]);local=audit['models']['archer']['bowReleaseLocal'] if audit else [0,C['arrowOriginHeight'],C['arrowOriginForward']]
 e['origin']=[float(p[0]+local[0]*math.cos(yaw)+local[2]*math.sin(yaw)),float(local[1]+.015),float(p[1]-local[0]*math.sin(yaw)+local[2]*math.cos(yaw))];e['originMapping']='sampled native left-hand at release phase 0.64, rotated toward target' if audit else 'provisional'
 if e['resolution']=='IMPACT_IN_SHOT':assert e['damage'] is not None
for j,u in enumerate(red):u['deathTime']=None if death[j]>1e5 else float(death[j])
positions.tofile(O/'trajectories.f32');np.save(O/'trajectories.npy',positions);gait.tofile(O/'gait-distance.f32');np.save(O/'gait-distance.npy',gait);lastHit.tofile(O/'hit-times.f32');np.save(O/'hit-times.npy',lastHit);velocities.tofile(O/'velocities.f32')
np.save(O/'movement-reasons.npy',reason);np.save(O/'slow-causes.npy',slowCause);np.save(O/'member-states.npy',states);np.save(O/'avoidance-causes.npy',avoidance);(O/'hit-responses.json').write_text(json.dumps(responses,indent=2))
control.tofile(O/'red-control.f32');np.save(O/'red-control.npy',control);cycles.tofile(O/'gait-cycles.f32');np.save(O/'gait-cycles.npy',cycles)
(O/'simulation.json').write_text(json.dumps(dict(version='V14',config=C,units=units,blueCount=nb,redCount=nr,frames=N,blueLastArrival=arrival,events=events,shooterEvents=fired,controlColumns=['targetSpeed','forwardSpeed','acceleration','stride','cadenceCyclesPerSecond','posture','armSwing','turn','effort','reason']),separators=(',',':')),encoding='utf8')
report=dict(status='PASS' if minimum-2*C['weaponEnvelopeRadius']>=C['minimumEnemyClearance'] else 'FAIL',framesChecked=N,minimumCenterDistance=minimum,minimumAtSeconds=minf*dt,envelopeRadiusPerUnit=C['weaponEnvelopeRadius'],minimumSurfaceClearance=minimum-2*C['weaponEnvelopeRadius'],requiredSurfaceClearance=C['minimumEnemyClearance'],blueCount=nb,redCounts={c:sum(u['color']==c for u in red) for c in ['red','orange','yellow']},arrows=len(events),causalKills=int((death<1e5).sum()),deadBodiesIncluded=True,noMeleeEvents=True,distanceByFrame=distanceByFrame)
(O/'safety-and-causality.json').write_text(json.dumps(report,indent=2),encoding='utf8')
with (O/'member-trajectories.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['frame60','seconds','id','team','model','x','z','worldSpeed','cumulativePath','life'])
 for k in range(0,N,6):
  for j,u in enumerate(units):w.writerow([k,round(k*dt,3),u['id'],u['team'],u['model'],*positions[k,j].round(5),round(float(np.linalg.norm(velocities[k,j])),4),round(float(gait[k,j]),4),'DEAD' if u.get('deathTime') is not None and k*dt>=u['deathTime'] else 'ALIVE'])
print({k:v for k,v in report.items() if k!='distanceByFrame'},flush=True)
assert report['status']=='PASS',report['minimumSurfaceClearance']
