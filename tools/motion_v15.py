"""Fixed-step, seeded individual charge. X lateral / Z forward, metres-like units.
Only Crowd.step writes authoritative root positions. No moving-slot overwrite.
"""
import math, time
from collections import defaultdict
import numpy as np

DT=1/60

class SpatialHash:
 def __init__(self, positions, cell=2.0):
  self.positions=positions;self.cell=cell;self.cells=defaultdict(list)
  for i,(x,z) in enumerate(positions):self.cells[(math.floor(x/cell),math.floor(z/cell))].append(i)
 def query(self, point, radius, exclude=-1, limit=48):
  x,z=point;c=self.cell;cx,cz=math.floor(x/c),math.floor(z/c);r=math.ceil(radius/c)
  ids=[j for dz in range(-r,r+1) for dx in range(-r,r+1) for j in self.cells.get((cx+dx,cz+dz),()) if j!=exclude]
  if not ids:return np.empty(0,dtype=int)
  a=np.asarray(ids,dtype=int);d=np.sum((self.positions[a]-point)**2,axis=1);order=np.argsort(d,kind='stable');a=a[order];d=d[order]
  return a[d<=radius*radius][:limit]
 def pairs(self,radius):
  # Hash visits each pair once. No all-army N x N distance matrix.
  out=[]
  for i,p in enumerate(self.positions):
   for j in self.query(p,radius,i,128):
    if j>i:out.append((i,int(j)))
  return np.asarray(out,dtype=int).reshape(-1,2)

class Crowd:
 def __init__(self, units, config):
  self.units=units;self.config=config;self.n=len(units);self.seed=config['seed'];self.time=0.;self.ticks=0
  self.position=np.array([u['start'] for u in units],dtype=float);self.initial=self.position.copy();self.velocity=np.zeros((self.n,2))
  self.phase=np.array([u['phase'] for u in units]);self.cycles=np.zeros(self.n);self.dead=np.zeros(self.n,dtype=bool)
  self.hp=np.full(self.n,config['redHitPoints']);self.hitTime=np.full(self.n,-1e6);self.deathPosition=self.position.copy()
  self.preferred=np.zeros(self.n);self.maxAcceleration=np.zeros(self.n);self.maxTurnRate=np.zeros(self.n);self.strideBase=np.zeros(self.n)
  self.rhythmA=np.zeros(self.n);self.rhythmB=np.zeros(self.n);self.phaseA=np.zeros(self.n);self.phaseB=np.zeros(self.n)
  self.stride=np.zeros(self.n);self.posture=np.zeros(self.n);self.arm=np.zeros(self.n);self.yaw=np.zeros(self.n)
  self.targetSpeed=np.zeros(self.n);self.acceleration=np.zeros(self.n);self.congestion=np.ones(self.n)
  self.behavior=np.zeros(self.n,dtype=np.uint8);self.timer=np.zeros(self.n);self.route=np.full(self.n,-1,int);self.routeSide=np.zeros(self.n);self.clearFrames=np.zeros(self.n,int)
  self.neighbor=np.full(self.n,-1,int);self.reason=np.zeros(self.n,int);self.effort=np.zeros(self.n)
  self.lower=np.zeros(self.n);self.upper=np.zeros(self.n);self.metrics=[]
  bounds={}
  for u in units:bounds.setdefault(u['platoon'],[]).append(u['start'][0])
  for i,u in enumerate(units):
   # Per-ID RNG streams: adding a different ID does not reshuffle existing people.
   rng=np.random.default_rng(np.random.SeedSequence([self.seed,int(u['id'][1:]),15]))
   self.preferred[i]=config['redSpeed']*rng.uniform(.94,1.06)
   self.maxAcceleration[i]=rng.uniform(75,103);self.maxTurnRate[i]=rng.uniform(1.3,2.0)
   self.rhythmA[i]=rng.uniform(3.4,5.5);self.rhythmB[i]=rng.uniform(6.7,9.2)
   self.phaseA[i],self.phaseB[i]=rng.uniform(0,2*math.pi,2);self.phase[i]=rng.random()
   self.strideBase[i]=config['runStride']*rng.uniform(.90,1.11);self.stride[i]=self.strideBase[i]
   self.posture[i]=rng.uniform(-.055,.065)
   self.lower[i]=min(bounds[u['platoon']])-.55;self.upper[i]=max(bounds[u['platoon']])+.55
   u.update(speed=float(self.preferred[i]),gaitStride=float(self.strideBase[i]),phase=float(self.phase[i]),maxAcceleration=float(self.maxAcceleration[i]),maxTurnRate=float(self.maxTurnRate[i]),rhythmA=float(self.rhythmA[i]),rhythmB=float(self.rhythmB[i]),phaseA=float(self.phaseA[i]),phaseB=float(self.phaseB[i]),gaitScale=float(self.strideBase[i]/config['runStride']),personalPosture=float(self.posture[i]))
  self.initialPosture=self.posture.copy()

 def apply_hit(self,i,damage,t):
  if self.dead[i]:raise AssertionError('Arrow targeted dead member')
  self.hp[i]-=damage;self.hitTime[i]=t
  if self.hp[i]<=0:self.dead[i]=True;self.velocity[i]=0;self.deathPosition[i]=self.position[i]

 def get_hit_speed_multiplier(self,i,t):
  damage=self.config['redHitPoints']-self.hp[i]
  if not damage:return 1.
  age=t-self.hitTime[i];stagger=self.config['hitStaggerSeconds'];recovery=self.config['hitRecoverySeconds']
  low=.55 if damage==1 else .35;end=self.config['hitWoundSpeed'] if damage==1 else self.config['hitSeriousSpeed']
  if age<stagger:return low
  s=min(1.,(age-stagger)/recovery);return low+(end-low)*s*s*(3-2*s)

 def compute_congestion(self,i,neighbors):
  """Time-to-contact speed bound against real ahead body, not squad average."""
  if not len(neighbors):return 1.,-1
  delta=self.position[neighbors]-self.position[i];ahead=(delta[:,1]>.05)&(delta[:,1]<5.8)&(np.abs(delta[:,0])<.64)
  a=neighbors[ahead]
  if not len(a):return 1.,-1
  dz=self.position[a,1]-self.position[i,1];gap=np.maximum(0,dz-.68)
  safe=np.sqrt(np.maximum(0,self.velocity[a,1])**2+2*27*gap)
  k=int(np.argmin(safe));return min(1.,float(safe[k]/max(.01,self.preferred[i]))),int(a[k])

 def compute_desired_speed(self,i,t,congestion):
  rhythm=.035*math.sin(t*self.rhythmA[i]+self.phaseA[i])+.020*math.sin(t*self.rhythmB[i]+self.phaseB[i])
  self.effort[i]=rhythm/.055
  return self.preferred[i]*(1+rhythm)*congestion*self.get_hit_speed_multiplier(i,t)

 def compute_soft_formation_correction(self,i):
  # Only outside the platoon's allowed lateral region, never a longitudinal slot.
  x=self.position[i,0];deadzone=.18
  if x<self.lower[i]-deadzone:return min(.8,(self.lower[i]-deadzone-x)*1.6)
  if x>self.upper[i]+deadzone:return -min(.8,(x-self.upper[i]-deadzone)*1.6)
  return 0.

 def compute_local_avoidance(self,i,neighbors,t):
  """Persistent side decision; min duration .24s, exit after 8 clear ticks."""
  target=int(self.route[i]);active=target>=0
  if active:
   delta=self.position[target]-self.position[i]
   clear=delta[1]<-.70 or abs(delta[0])>1.0
   self.clearFrames[i]=self.clearFrames[i]+1 if clear else 0
   self.timer[i]+=DT
   if self.timer[i]>=.24 and self.clearFrames[i]>=8:
    self.route[i]=-1;self.timer[i]=0;self.clearFrames[i]=0;active=False
  if not active:
   candidates=[]
   for q in neighbors:
    dz=self.position[q,1]-self.position[i,1];dx=abs(self.position[q,0]-self.position[i,0]);dv=self.preferred[i]-self.velocity[q,1]
    if .1<dz<5.8 and dx<.68 and dv>.65 and (dz-.62)/dv<.9:candidates.append(((dz-.62)/dv,int(q)))
   if candidates:
    _,target=min(candidates);p=self.position[i];options=[]
    for side in [-1,1]:
     goal=self.position[target,0]+side*.84
     if goal<self.lower[i]-.18 or goal>self.upper[i]+.18:continue
     dz=self.position[target,1]-p[1];tau=min(.7,max(.12,(dz-.3)/max(1,self.preferred[i]-self.velocity[target,1])))
     probe=np.array([goal,p[1]+self.preferred[i]*tau]);others=neighbors[neighbors!=target]
     clearance=float(np.min(np.linalg.norm(self.position[others]+self.velocity[others]*tau-probe,axis=1))) if len(others) else 2.
     if clearance>.66:options.append((min(clearance,1.5)-.1*abs(goal-p[0]),side))
    if options:
     _,side=max(options);self.route[i]=target;self.routeSide[i]=side;self.timer[i]=0.;self.clearFrames[i]=0;active=True
  if not active:return 0.
  target=int(self.route[i]);goal=self.position[target,0]+self.routeSide[i]*.84
  return float(np.clip((goal-self.position[i,0])*4,-2.0,2.0))

 def limit_steering_and_speed(self,i,desired,dt):
  # acceleration has world units/s^2; max turn is radians/s.
  old=self.velocity[i];speed=float(np.linalg.norm(old));target=float(np.linalg.norm(desired))
  heading=float(np.clip(math.atan2(desired[0],max(.001,desired[1])),-.48,.48));previous=math.atan2(old[0],max(.001,old[1]))
  heading=previous+float(np.clip(heading-previous,-self.maxTurnRate[i]*dt,self.maxTurnRate[i]*dt))
  accel=self.maxAcceleration[i] if target>speed else 42.
  new=speed+float(np.clip(target-speed,-accel*dt,accel*dt))
  return np.array([float(np.clip(math.sin(heading)*new,-2.0,2.0)),max(0.,math.cos(heading)*new)])

 def step(self,t,dt=DT):
  assert abs(dt-DT)<1e-12
  started=time.perf_counter();old=self.position.copy();oldv=self.velocity.copy();grid=SpatialHash(old)
  proposal=np.zeros_like(oldv);self.neighbor.fill(-1);self.reason.fill(0);self.targetSpeed.fill(0);self.congestion.fill(1)
  maxNeighbors=0
  for i,u in enumerate(self.units):
   if self.dead[i] or t<u['delay']:continue
   neighbors=grid.query(old[i]+[0,1.5],6.2,i,48);maxNeighbors=max(maxNeighbors,len(neighbors))
   self.congestion[i],self.neighbor[i]=self.compute_congestion(i,neighbors)
   lateral=self.compute_local_avoidance(i,neighbors,t)+self.compute_soft_formation_correction(i)
   self.targetSpeed[i]=self.compute_desired_speed(i,t,self.congestion[i]);desired=np.array([lateral,self.targetSpeed[i]])
   proposal[i]=self.limit_steering_and_speed(i,desired,dt)
   self.reason[i]=1 if self.hp[i]<self.config['redHitPoints'] else 2 if self.route[i]>=0 else 3 if self.congestion[i]<.98 else 0
  # Predictive local contact half-planes after steering. Stationary dead remain
  # occupied for the ENTIRE simulation; injury never removes or repacks a body.
  pairs=grid.pairs(1.25);iterations=0
  if len(pairs):
   ia,ib=pairs.T;delta=old[ia]-old[ib];dist=np.linalg.norm(delta,axis=1);norm=delta/np.maximum(dist[:,None],1e-8);required=(.615-dist)/dt
   for iterations in range(140):
    violations=required-np.sum((proposal[ia]-proposal[ib])*norm,axis=1);bad=np.where(violations>1e-5)[0]
    if not len(bad):break
    for q in bad:
     a,b=int(ia[q]),int(ib[q]);need=required[q]-float(np.dot(proposal[a]-proposal[b],norm[q]))
     if need<=1e-5:continue
     wa=0. if self.dead[a] else .2 if self.hp[a]<self.config['redHitPoints'] else 1.;wb=0. if self.dead[b] else .2 if self.hp[b]<self.config['redHitPoints'] else 1.;total=wa+wb
     if total==0:continue
     proposal[a]+=norm[q]*need*wa/total;proposal[b]-=norm[q]*need*wb/total
     for i,other in [(a,b),(b,a)]:
      proposal[i,0]=float(np.clip(proposal[i,0],-2.5,2.5));proposal[i,1]=float(np.clip(proposal[i,1],0,self.preferred[i]*1.08))
      if not self.dead[i] and self.hp[i]==self.config['redHitPoints']:self.reason[i]=3;self.neighbor[i]=other
  self.velocity=proposal;self.velocity[self.dead]=0;self.position+=self.velocity*dt
  assert np.all(self.position[:,1]>=old[:,1]-1e-10)
  assert np.all(self.position[self.dead]==self.deathPosition[self.dead])
  self.acceleration=(self.velocity[:,1]-oldv[:,1])/dt
  self.stride+=(self.strideBase*(1+.025*self.effort+.012*np.tanh(self.acceleration/12))-self.stride)*(1-math.exp(-dt/.14))
  self.cycles+=np.linalg.norm(self.position-old,axis=1)/np.maximum(.1,self.stride)
  self.posture+=(self.initialPosture+.05*self.effort+.035*np.tanh(self.acceleration/14)-self.posture)*(1-math.exp(-dt/.12))
  self.arm+=(.5*self.effort+.3*np.tanh(self.acceleration/14)-.25*(self.route>=0)-self.arm)*(1-math.exp(-dt/.12))
  self.yaw=np.arctan2(self.velocity[:,0],np.maximum(.01,self.velocity[:,1]))
  self.behavior=np.where(self.dead,3,np.where(self.hp<self.config['redHitPoints'],np.where(t-self.hitTime<self.config['hitStaggerSeconds'],1,2),0)).astype(np.uint8)
  self.time=t;self.ticks+=1;self.metrics.append(dict(time=t,stepMs=(time.perf_counter()-started)*1000,maxNeighbors=maxNeighbors,contactPairs=len(pairs),iterations=iterations+1))
  return self.position

 def control(self):
  return np.stack([self.targetSpeed,self.velocity[:,1],self.acceleration,self.stride,np.linalg.norm(self.velocity,axis=1)/self.stride,self.posture,self.arm,self.yaw,self.effort,self.reason],axis=1)
