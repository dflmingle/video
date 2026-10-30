"""V18 per-archer movement and firing FSM with integrated gait/action phases."""
import math,numpy as np
NAMES=['WAITING','MOVING','ARRIVING','AIMING','DRAWING','RELEASING','RECOVERING']
class Archers:
 def __init__(self,units,C):
  self.units=units;self.C=C;self.n=len(units)
  self.starts=np.array([u['start'] for u in units],dtype=np.float64);self.position=self.starts.copy();self.previous=self.position.copy();self.velocity=np.zeros_like(self.position)
  self.state=np.zeros(self.n,dtype=np.uint8);self.timer=np.zeros(self.n);self.target=np.full(self.n,-1,int);self.pendingStart=np.full(self.n,-1.);self.lastRelease=np.full(self.n,-10.)
  self.pathPoints=[];self.pathCum=[];self.progress=np.zeros(self.n);self.moveSpeed=np.zeros(self.n);self.walkPhase=np.array([float(u.get('phase',0.0))%1.0 for u in units]);self.actionPhase=np.zeros(self.n);self.turnPhase=np.zeros(self.n);self.facingYaw=np.full(self.n,math.pi);self.targetYaw=np.full(self.n,math.pi);self.stateProgress=np.zeros(self.n);self.releaseEventId=np.full(self.n,-1,np.int32);self.records=[]
  for j,u in enumerate(units):
   row=(j%36)//6;col=j%6;q=((j+1)*.61803398875)%1;r=((col+1)*.41421356237+u['group']*.19)%1
   early=u['group'] in [0,6];squadLag=[0,.09,.17,.22,.15,.07,.04][u['group']]
   u.update(delay=.025+squadLag+.026*row+.018*r,moveSeconds=(.99 if early else 1.55)+.065*row+.035*r,turnSeconds=.03+.025*r,aimSeconds=.035+.035*q,drawSeconds=.145+.065*r,recoverSeconds=.21+.10*q,cycle=.53+.13*r,arrival=0,shootYaw=math.pi)
   bend=1.20*math.cos(u['group']*math.pi/6)
   path=np.column_stack([bend*np.sin(np.linspace(0,math.pi,256)),-C['blueAdvance']*np.linspace(0,1,256)])
   seg=np.linalg.norm(np.diff(path,axis=0),axis=1);cum=np.concatenate([[0.],np.cumsum(seg)]);pathLength=float(cum[-1]);self.pathPoints.append(path);self.pathCum.append(cum)
   u['moveSeconds']*=pathLength/C['blueAdvance'];u['arrival']=u['delay']+u['moveSeconds'];u['readyAt']=u['arrival']+u['turnSeconds'];u['target']=[u['start'][0],u['start'][1]-C['blueAdvance']];u['pathBend']=bend;u['deploymentPathLength']=pathLength
   u['walkSpeed']=pathLength/u['moveSeconds']*(.91+.16*r);u['walkAccel']=max(2.2,u['walkSpeed']*3.4);u['walkBrake']=max(3.4,u['walkSpeed']*5.0);u['phaseOffset']=float(u.get('phase',0.0))%1.0
 def _path(self,j,s):
  s=float(np.clip(s,0,1)); path=self.pathPoints[j]; cum=self.pathCum[j]; q=s*cum[-1]; k=int(np.searchsorted(cum,q,side='right')-1); k=max(0,min(len(cum)-2,k)); w=(q-cum[k])/max(cum[k+1]-cum[k],1e-8); return self.starts[j]+path[k]*(1-w)+path[k+1]*w
 def enter(self,j,state):self.state[j]=state;self.timer[j]=0.;self.actionPhase[j]=0.
 def move(self,t,dt):
  self.previous[:]=self.position
  for j,u in enumerate(self.units):
   # WAITING: no teleport and no accumulated timer.
   if t < u['delay']:
    self.progress[j]=0.;self.moveSpeed[j]=0.;self.position[j]=self.starts[j];self.state[j]=0;self.timer[j]=0.;self.actionPhase[j]=0.;self.stateProgress[j]=0.;continue
   # MOVING: integrate normalized path progress with acceleration and braking.
   if self.progress[j] < 0.999:
    remaining=max(0.,1.-self.progress[j]);L=max(u['deploymentPathLength'],1e-4)
    desired=min(u['walkSpeed']/L, math.sqrt(max(0.,2*u['walkBrake']*remaining/L)))
    # Smoothly ramp up and clamp to a braking-safe speed. No global smoothstep.
    accel=u['walkAccel']/L;brake=u['walkBrake']/L
    delta=desired-self.moveSpeed[j]
    self.moveSpeed[j]+=float(np.clip(delta,-brake*dt,accel*dt))
    step=min(remaining,self.moveSpeed[j]*dt);self.progress[j]+=step
    self.position[j]=self._path(j,self.progress[j]);
    self.walkPhase[j]=(self.walkPhase[j]+step/max(self.C['blueStride'],1e-4))%1.0
    self.stateProgress[j]=self.progress[j]
    self.timer[j]=0.
    if t >= u['arrival']-.16:self.state[j]=2
    else:self.state[j]=1
   else:
    # Arrive exactly once, then spend turnSeconds orienting before aiming.
    self.progress[j]=1.;self.position[j]=self._path(j,1.0);self.moveSpeed[j]=0.;self.stateProgress[j]=1.
    if self.state[j] < 2:self.state[j]=2;self.timer[j]=0.
    if self.state[j] < 3:self.timer[j]+=dt
    self.turnPhase[j]=min(1.,self.timer[j]/max(u['turnSeconds'],1e-4))
    self.facingYaw[j]=math.pi
    if self.timer[j]>=u['turnSeconds'] and self.state[j]<3:self.enter(j,3)
  self.velocity=(self.position-self.previous)/max(dt,1e-6)
  for j,u in enumerate(self.units):
   st=int(self.state[j])
   if st==1:self.actionPhase[j]=self.walkPhase[j];self.stateProgress[j]=self.progress[j]
   elif st==2:self.actionPhase[j]=self.walkPhase[j];self.stateProgress[j]=self.turnPhase[j]
   elif st==3:self.actionPhase[j]=.10+.018*math.sin(2*math.pi*(self.walkPhase[j]+u['phaseOffset']));self.stateProgress[j]=1.
   elif st==4:self.actionPhase[j]=.12+.52*min(1.,self.timer[j]/max(u['drawSeconds'],.001));self.stateProgress[j]=min(1.,self.timer[j]/max(u['drawSeconds'],.001))
   elif st==5:self.actionPhase[j]=.64;self.stateProgress[j]=1.
   elif st==6:self.actionPhase[j]=.64+.36*min(1.,self.timer[j]/max(u['recoverSeconds'],.001));self.stateProgress[j]=min(1.,self.timer[j]/max(u['recoverSeconds'],.001))
 def select(self,j,red,hp,reserved,t):
  delta=red-self.position[j];d=np.linalg.norm(delta,axis=1);valid=np.where((hp>0)&(~reserved)&(d<=self.C['archerRange']))[0]
  if not len(valid):return -1
  pool=valid[np.argsort(d[valid],kind='stable')[:6]];return int(pool[(j+int(t*2))%len(pool)])
 def update_fire(self,t,dt,red,hp,reserved,spawn):
  claimed={int(target):j for j,target in enumerate(self.target) if target>=0 and self.state[j] in [3,4]}
  for j,u in enumerate(self.units):
   if self.state[j]<3:continue
   self.timer[j]+=dt;target=int(self.target[j]);valid=target>=0 and hp[target]>0 and not reserved[target] and claimed.get(target,j)==j and np.linalg.norm(red[target]-self.position[j])<=self.C['archerRange']
   if self.state[j]==3:
    if not valid:
     if claimed.get(target)==j:claimed.pop(target)
     excluded=reserved.copy()
     for other,owner in claimed.items():
      if owner!=j:excluded[other]=True
     self.target[j]=self.select(j,red,hp,excluded,t);self.timer[j]=0.;target=int(self.target[j])
     if target>=0:
      claimed[target]=j;d=red[target]-self.position[j];self.targetYaw[j]=math.atan2(float(d[0]),float(d[1]))
    if target>=0 and self.timer[j]>=u['aimSeconds']:
     self.pendingStart[j]=t;self.enter(j,4)
   elif self.state[j]==4:
    if not valid:self.target[j]=-1;self.enter(j,3)
    elif self.timer[j]>=u['drawSeconds']:
     e=spawn(j,target,t,self.pendingStart[j]);reserved[target]=True;self.records.append(e);self.lastRelease[j]=t;self.releaseEventId[j]=len(self.records)-1;self.enter(j,5)
   elif self.state[j]==5:self.enter(j,6)
   elif self.state[j]==6 and self.timer[j]>=u['recoverSeconds']:
    self.target[j]=-1;self.enter(j,3)
   s=int(self.state[j])
   if s==3:self.actionPhase[j]=.10+.018*math.sin(2*math.pi*(self.walkPhase[j]+u['phaseOffset']))
   elif s==4:self.actionPhase[j]=.12+.52*min(1.,self.timer[j]/max(u['drawSeconds'],.001))
   elif s==5:self.actionPhase[j]=.64
   elif s==6:self.actionPhase[j]=.64+.36*min(1.,self.timer[j]/max(u['recoverSeconds'],.001))
 def control(self):
  return np.column_stack([self.state,self.timer,self.target,self.lastRelease,self.walkPhase,self.turnPhase,self.actionPhase,self.moveSpeed,self.facingYaw,self.targetYaw,self.stateProgress,self.releaseEventId.astype(np.float64)])



