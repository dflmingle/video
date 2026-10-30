"""V3: PDF formation topology, monotone individual charge and causal archery."""
from pathlib import Path
import json, math, csv, sys
import numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];variant=sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].startswith('--') else 'A';O=P/'variants'/variant;O.mkdir(exist_ok=True)
C=json.loads((O/'params.json').read_text());C['disableCombat']=True
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
for u in blue:u['cycle']=C['archerCycle']*(u['cycle']/baseline['config']['archerCycle'])
for u in red:
 u['deathTime']=None;u['speed']*=C['redSpeed']/baseline['config']['redSpeed'];u['accelerationSeconds']*=C['accelerationSeconds']/baseline['config']['accelerationSeconds']
 # Continuous, repeatable personal/squad pace. Starts remain exactly unchanged.
 squad=.055*math.sin(u['platoon']*2.399)+.022*math.cos(u['platoon']*1.17)
 column=.018*math.sin(u['column']*1.63+u['platoon']*.4)
 front=.018*(1-u['row']/max(1,C['armyMemberRows'][u['army']]-1))
 u['speed']*=(1+squad+column+front)*(1+.035*(1-u['squadRow']))*(1+.045*math.sin(int(u['id'][1:])*2.399))
 u['delay']=float(np.clip(u['delay']+.045*math.sin(u['platoon']*1.9)+.012*u['row'],0,.23))
 u['laneDrift']=.13*math.sin(u['platoon']*1.7+u['column']*.7)
 u['gaitStride']=C['runStride']
 u['headingBias']=.045*math.sin(int(u['id'][1:])*1.731)

squadBounds={}
for u in red:
 pts=[v['start'][0] for v in red if v['platoon']==u['platoon']]
 squadBounds[u['platoon']]=(min(pts)-.55,max(pts)+.55)
nb,nr=len(blue),len(red);units=blue+red;n=nb+nr
positions=np.zeros((N,n,2),np.float32);gait=np.zeros((N,n),np.float32);velocities=np.zeros((N,n,2),np.float32)
rp=np.array([u['start'] for u in red]);bs=np.array([u['start'] for u in blue]);death=np.full(nr,1e6);hp=np.full(nr,C['redHitPoints']);hit=np.full(nr,-10.);lastHit=np.full((N,nr),-10,np.float32)
responses=[];states=np.zeros((N,nr),np.uint8);avoidance=np.full((N,nr),-1,np.int32)
events=[];scheduled={};fired=[[] for _ in blue];arrival=max(u['delay']+C['blueMoveSeconds'] for u in blue);firstDraw=arrival+.14
nextAllowed=np.zeros(nr);routes=np.full(nr,-1,int);routeSide=np.zeros(nr);reason=np.zeros((N,nr),np.uint8);slowCause=np.full((N,nr),-1,np.int32)
nextFire=np.array([firstDraw+u['phase']*.70+.10*(u['group']%2)+C['drawSeconds'] for u in blue]);vx=np.zeros(nr);minimum=1e6;minf=0;distanceByFrame=[]
for f in range(N):
 t=f*dt
 for target,e in scheduled.pop(f,[]):
  assert death[target]>t-1e-6
  damage=int(e['plannedDamage']);hp[target]-=damage;hit[target]=t;e.update(damage=damage,remainingHP=int(hp[target]),killed=bool(hp[target]<=0))
  if hp[target]<=0:death[target]=t
  responses.append(dict(event=e['id'],memberID=red[target]['id'],time=t,kind='DEAD' if hp[target]<=0 else 'STAGGER',source='BOUND_ARROW_IMPACT'))
 for j,u in enumerate(blue):
  a=float(np.clip((t-u['delay'])/C['blueMoveSeconds'],0,1));k=a*a*(3-2*a);positions[f,j]=bs[j]+[0,-C['blueAdvance']*k]
 alive=death>t
 if f:
  previous=rp.copy();v=np.zeros_like(rp)
  for j,u in enumerate(red):
   if not alive[j] or t<u['delay']:continue
   a=min(1,(t-u['delay'])/u['accelerationSeconds']);acc=a*a*(3-2*a)
   age=t-hit[j];stagger=C['hitStaggerSeconds'];recover=C['hitRecoverySeconds'];damage=C['redHitPoints']-hp[j]
   woundFactor=1. if damage==0 else C['hitWoundSpeed'] if damage==1 else C['hitSeriousSpeed']
   if age<stagger:
    factor=.12 if damage==1 else .03;states[f,j]=1;reason[f,j]=1
   elif age<stagger+recover:
    a2=(age-stagger)/recover;factor=.12+(woundFactor-.12)*(a2*a2*(3-2*a2));states[f,j]=2;reason[f,j]=1
   else:
    factor=woundFactor;states[f,j]=0 if damage==0 else 4 if damage==1 else 5
    if damage:reason[f,j]=1
   v[j,1]=u['speed']*acc*factor
   # Wounded person alone loses balance, stepping slightly out of original lane.
   woundSide=1 if u['column']>=C['redMemberColumns']/2 else -1
   displacement=0 if damage==0 else woundSide*(.42 if damage==1 else .52)*(1-math.exp(-max(0,age)*8))
   # Independent heading/velocity, not a return spring to a fixed slot.
   lo,hi=squadBounds[u['platoon']]
   steer=u['headingBias']*acc
   if rp[j,0]<lo:steer+=min(.7,(lo-rp[j,0])*3)
   if rp[j,0]>hi:steer-=min(.7,(rp[j,0]-hi)*3)
   v[j,0]=steer
  states[f,~alive]=3
  # Predict relative motion for any slower live member. A persistent passing
  # target is selected from future occupancy, with no per-frame random offsets.
  crowd=cKDTree(rp)
  ahead=crowd.query_ball_point(rp+[0,2.2],3.5)
  for j,local in enumerate(ahead):
   if not alive[j] or t<red[j]['delay']:continue
   k=int(routes[j]);valid=k>=0 and alive[k] and rp[k,1]-rp[j,1]>-1.0 and rp[k,1]-rp[j,1]<5.5
   if not valid:
    choices=[]
    for q in local:
     if q==j or not alive[q]:continue
     dz=rp[q,1]-rp[j,1];dx=abs(rp[q,0]-rp[j,0]);dv=v[j,1]-v[q,1]
     if .05<dz<5.0 and dx<.68 and dv>.35 and (dz-.61)/dv<.85:choices.append(((dz-.61)/dv,q))
    if not choices:routes[j]=-1;continue
    _,k=min(choices);routes[j]=k
    tau=float(np.clip((rp[k,1]-rp[j,1])/max(.35,v[j,1]-v[k,1]),.22,.85))
    lo,hi=squadBounds[red[j]['platoon']];candidates=[]
    for side in [-1,1]:
     goal=float(np.clip(rp[k,0]+side*.76,lo,hi));pred=rp[j]+[goal-rp[j,0],v[j,1]*tau]
     others=[q for q in local if q!=j and alive[q]]
     pts=rp[others]+v[others]*tau
     clearance=float(np.linalg.norm(pts-pred,axis=1).min()) if len(pts) else 3
     candidates.append((min(clearance,1.2)-.12*abs(goal-rp[j,0]),goal))
    routeSide[j]=max(candidates)[1]
   v[j,0]=np.clip((routeSide[j]-rp[j,0])*3,-1.2,1.2);avoidance[f,j]=k;reason[f,j]=2
  ids=np.where(alive)[0]
  # Smooth preferred velocity, then solve relative velocity half-planes. No
  # position projection: every correction is a bounded actual velocity.
  vx+=np.clip(v[:,0]-vx,-dt*9,dt*9);vx=np.clip(vx,-1.8,1.8);vx[~alive]=0;v[:,0]=vx
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
     wi=.1 if hp[i]<C['redHitPoints'] else 1.;wk=.1 if hp[k]<C['redHitPoints'] else 1.;total=wi+wk
     v[i]+=normal*need*wi/total;v[k]-=normal*need*wk/total
     v[i,0]=np.clip(v[i,0],-1.8,1.8);v[k,0]=np.clip(v[k,0],-1.8,1.8)
     v[i,1]=np.clip(v[i,1],0,red[i]['speed']);v[k,1]=np.clip(v[k,1],0,red[k]['speed'])
     if hp[i]==C['redHitPoints']:slowCause[f,i]=k;reason[f,i]=3
     if hp[k]==C['redHitPoints']:slowCause[f,k]=i;reason[f,k]=3
  v[~alive]=0;rp+=v*dt;vx=v[:,0].copy()
  assert np.all(rp[:,1]>=previous[:,1]-1e-9)
 positions[f,nb:]=rp;lastHit[f]=hit
 if f:
  step=positions[f]-positions[f-1];velocities[f]=step/dt;gait[f]=gait[f-1]+np.linalg.norm(step,axis=1)
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
    sector=min(2,int(max(0,t-firstDraw)/.50))
    eligible=eligible[((rp[eligible,1]>rp[active,1].max()-12.)|(hp[eligible]<C['redHitPoints']))&np.array([red[k]['squadCol']==sector for k in eligible])]
   if not len(eligible):continue
   p=positions[f,j];ds=np.linalg.norm(rp[eligible]-p,axis=1);frontCount=C['targetFrontCount'];close=eligible[np.argsort(ds)[:frontCount]];wounded=eligible[hp[eligible]<C['redHitPoints']];pool=wounded if len(wounded) and u['phase']<.5 else close;target=int(rng.choice(pool));dist=float(np.linalg.norm(rp[target]-p))
   flight=float(max(.35,dist/C['arrowSpeed']));hf=f+round(flight/dt)
   if hf>=N-2:continue
   pending[target]+=1;nextAllowed[target]=hf*dt+C['minHitInterval'];e=dict(id=f'A{len(events):05}',shooter=j,shooterID=u['id'],target=nb+target,targetID=red[target]['id'],releaseFrame=f,release=t,drawStart=t-C['drawSeconds'],aimStart=t-C['aimSeconds'],impactFrame=hf,impact=hf*dt,arc=float(C['arrowArcHeight']*(.9+.2*u['phase'])),damage=None,plannedDamage=3 if u['phase']<.08 else 1)
   events.append(e);scheduled.setdefault(hf,[]).append((target,e));fired[j].append(len(events)-1);nextFire[j]=t+u['cycle']
 if f%120==0:print('SIM',round(t,2),'alive',int(alive.sum()),'arrows',len(events),flush=True)
audit=json.loads((O/'asset-render-audit.json').read_text()) if (O/'asset-render-audit.json').exists() else None
for e in events:
 e['destination']=[float(positions[e['impactFrame'],e['target'],0]),.85,float(positions[e['impactFrame'],e['target'],1])]
 p=positions[e['releaseFrame'],e['shooter']];yaw=math.atan2(e['destination'][0]-p[0],e['destination'][2]-p[1]);local=audit['models']['archer']['bowReleaseLocal'] if audit else [0,C['arrowOriginHeight'],C['arrowOriginForward']]
 e['origin']=[float(p[0]+local[0]*math.cos(yaw)+local[2]*math.sin(yaw)),float(local[1]+.015),float(p[1]-local[0]*math.sin(yaw)+local[2]*math.cos(yaw))];e['originMapping']='sampled native left-hand at release phase 0.64, rotated toward target' if audit else 'provisional'
 e['resolution']='IMPACT_IN_SHOT'
 assert e['damage'] is not None
# Preserve arrows that are still in flight when the shot cuts. Their future
# aim points are predictions, never recorded as observed impacts or deaths.
if not C.get('disableCombat',False):
 lastVisible=C['duration']-1/C['fps'];survivors=np.where(death>lastVisible)[0]
 for j,u in enumerate(blue):
  release=float(nextFire[j])
  while release<=lastVisible:
   rf=round(release/dt);release=rf*dt;p=positions[rf,j]
   candidates=[k for k in survivors if death[k]>C['duration']]
   distances=np.linalg.norm(positions[rf,nb+np.array(candidates)]-p,axis=1)
   choices=np.where(release+distances/C['arrowSpeed']>C['duration']+.02)[0]
   if len(choices):
    k=int(choices[np.argmin(distances[choices])]);target=int(candidates[k]);flight=float(distances[k]/C['arrowSpeed']);impact=release+flight
    end=positions[-1,nb+target]+velocities[-1,nb+target]*(impact-C['duration'])
    destination=[float(end[0]),.85,float(end[1])];yaw=math.atan2(destination[0]-p[0],destination[2]-p[1]);local=audit['models']['archer']['bowReleaseLocal'] if audit else [0,C['arrowOriginHeight'],C['arrowOriginForward']]
    origin=[float(p[0]+local[0]*math.cos(yaw)+local[2]*math.sin(yaw)),float(local[1]+.015),float(p[1]-local[0]*math.sin(yaw)+local[2]*math.cos(yaw))]
    e=dict(id=f'A{len(events):05}',shooter=j,shooterID=u['id'],target=nb+target,targetID=red[target]['id'],releaseFrame=rf,release=release,drawStart=release-C['drawSeconds'],aimStart=release-C['aimSeconds'],impactFrame=round(impact/dt),impact=impact,arc=float(C['arrowArcHeight']*(.9+.2*u['phase'])),damage=None,remainingHP=None,killed=False,destination=destination,origin=origin,originMapping='sampled native left-hand at release phase 0.64, rotated toward target',resolution='IN_FLIGHT_AT_CUT',destinationEvidence='linear continuation aim estimate beyond visible shot; no impact or damage simulated')
    events.append(e);fired[j].append(len(events)-1)
   release+=u['cycle']
 for sequence in fired:sequence.sort(key=lambda k:events[k]['release'])
for j,u in enumerate(red):u['deathTime']=None if death[j]>1e5 else float(death[j])
positions.tofile(O/'trajectories.f32');np.save(O/'trajectories.npy',positions);gait.tofile(O/'gait-distance.f32');np.save(O/'gait-distance.npy',gait);lastHit.tofile(O/'hit-times.f32');np.save(O/'hit-times.npy',lastHit);velocities.tofile(O/'velocities.f32')
np.save(O/'movement-reasons.npy',reason);np.save(O/'slow-causes.npy',slowCause);np.save(O/'member-states.npy',states);np.save(O/'avoidance-causes.npy',avoidance);(O/'hit-responses.json').write_text(json.dumps(responses,indent=2))
(O/'simulation.json').write_text(json.dumps(dict(version='V10',config=C,units=units,blueCount=nb,redCount=nr,frames=N,blueLastArrival=arrival,events=events,shooterEvents=fired),separators=(',',':')),encoding='utf8')
report=dict(status='PASS' if minimum-2*C['weaponEnvelopeRadius']>=C['minimumEnemyClearance'] else 'FAIL',framesChecked=N,minimumCenterDistance=minimum,minimumAtSeconds=minf*dt,envelopeRadiusPerUnit=C['weaponEnvelopeRadius'],minimumSurfaceClearance=minimum-2*C['weaponEnvelopeRadius'],requiredSurfaceClearance=C['minimumEnemyClearance'],blueCount=nb,redCounts={c:sum(u['color']==c for u in red) for c in ['red','orange','yellow']},arrows=len(events),causalKills=int((death<1e5).sum()),deadBodiesIncluded=True,noMeleeEvents=True,distanceByFrame=distanceByFrame)
(O/'safety-and-causality.json').write_text(json.dumps(report,indent=2),encoding='utf8')
with (O/'member-trajectories.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['frame60','seconds','id','team','model','x','z','worldSpeed','cumulativePath','life'])
 for k in range(0,N,6):
  for j,u in enumerate(units):w.writerow([k,round(k*dt,3),u['id'],u['team'],u['model'],*positions[k,j].round(5),round(float(np.linalg.norm(velocities[k,j])),4),round(float(gait[k,j]),4),'DEAD' if u.get('deathTime') is not None and k*dt>=u['deathTime'] else 'ALIVE'])
print({k:v for k,v in report.items() if k!='distanceByFrame'},flush=True)
assert report['status']=='PASS',report['minimumSurfaceClearance']
