from pathlib import Path
src=Path('tools/archers_v17.py').read_text(encoding='utf8')
# keep header and class rewrite entirely for explicit V18 behavior
new='''"""V18 per-archer movement and firing FSM with integrated gait/action phases."""
import math,numpy as np
NAMES=['WAITING','MOVING','ARRIVING','AIMING','DRAWING','RELEASING','RECOVERING']
class Archers:
 def __init__(self,units,C):
  self.units=units;self.C=C;self.n=len(units)
  self.starts=np.array([u['start'] for u in units],dtype=np.float64);self.position=self.starts.copy();self.previous=self.position.copy();self.velocity=np.zeros_like(self.position)
  self.state=np.zeros(self.n,dtype=np.uint8);self.timer=np.zeros(self.n);self.target=np.full(self.n,-1,int);self.pendingStart=np.full(self.n,-1.);self.lastRelease=np.full(self.n,-10.)
  self.progress=np.zeros(self.n);self.moveSpeed=np.zeros(self.n);self.walkPhase=np.array([float(u.get('phase',0.0))%1.0 for u in units]);self.actionPhase=np.zeros(self.n);self.turnPhase=np.zeros(self.n);self.records=[]
  for j,u in enumerate(units):
   row=(j%36)//6;col=j%6;q=((j+1)*.61803398875)%1;r=((col+1)*.41421356237+u['group']*.19)%1
   early=u['group'] in [0,6];squadLag=[0,.09,.17,.22,.15,.07,.04][u['group']]
   u.update(delay=.025+squadLag+.026*row+.018*r,moveSeconds=(.99 if early else 1.55)+.065*row+.035*r,turnSeconds=.06+.05*r,aimSeconds=.055+.055*q,drawSeconds=.18+.07*r,recoverSeconds=.23+.12*q,cycle=.53+.13*r,arrival=0,shootYaw=math.pi)
   bend=1.20*math.cos(u['group']*math.pi/6)
   path=np.column_stack([bend*np.sin(np.linspace(0,math.pi,128)),-C['blueAdvance']*np.linspace(0,1,128)])
   pathLength=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum())
   u['moveSeconds']*=pathLength/C['blueAdvance'];u['arrival']=u['delay']+u['moveSeconds'];u['readyAt']=u['arrival']+u['turnSeconds'];u['target']=[u['start'][0],u['start'][1]-C['blueAdvance']];u['pathBend']=bend;u['deploymentPathLength']=pathLength
   u['walkSpeed']=pathLength/u['moveSeconds']*(.91+.16*r);u['walkAccel']=max(2.2,u['walkSpeed']*3.4);u['walkBrake']=max(3.4,u['walkSpeed']*5.0);u['phaseOffset']=float(u.get('phase',0.0))%1.0
 def _path(self,j,s):
  u=self.units[j];s=float(np.clip(s,0,1));return self.starts[j]+[u['pathBend']*math.sin(math.pi*s),-self.C['blueAdvance']*s]
 def enter(self,j,state):self.state[j]=state;self.timer[j]=0.;self.actionPhase[j]=0.
 def move(self,t,dt):
  self.previous[:]=self.position
  for j,u in enumerate(self.units):
   if t < u['delay']:
    self.progress[j]=0.;self.moveSpeed[j]=0.;self.position[j]=self.starts[j];self.state[j]=0;self.timer[j]=0.;self.actionPhase[j]=0.;continue
   if t >= u['arrival']:
    self.progress[j]=1.;self.moveSpeed[j]=0.;self.position[j]=self._path(j,1.0)
    if self.state[j] < 3:self.enter(j,2)
    if t >= u['readyAt'] and self.state[j] < 3:self.enter(j,3)
    continue
   # Integrate path progress with acceleration and braking. The target speed is
   # continuous and derived from remaining distance, not a per-frame offset.
   remaining=max(0.,1.-self.progress[j]);remainTime=max(dt,u['arrival']-t)
   required=remaining/remainTime
   desired=max(min(u['walkSpeed']/max(u['deploymentPathLength'],.001),required*.92),0.)
   brakeLimit=math.sqrt(max(0.,2*u['walkBrake']*remaining/max(u['deploymentPathLength'],.001)))
   desired=min(desired,brakeLimit if remaining>.02 else desired)
   accel=u['walkAccel']/max(u['deploymentPathLength'],.001)
   self.moveSpeed[j]+=float(np.clip(desired-self.moveSpeed[j],-u['walkBrake']/max(u['deploymentPathLength'],.001)*dt,accel*dt))
   self.progress[j]=min(1.,self.progress[j]+self.moveSpeed[j]*dt)
   self.position[j]=self._path(j,self.progress[j]);self.walkPhase[j]=(self.walkPhase[j]+self.moveSpeed[j]*u['deploymentPathLength']*dt/(self.C['blueStride']*max(u['deploymentPathLength'],.001)))%1.0
   if t >= u['arrival']-.16:self.state[j]=2
   else:self.state[j]=1
  self.velocity=(self.position-self.previous)/max(dt,1e-6)
  for j,u in enumerate(self.units):
   s=int(self.state[j])
   if s==1:self.actionPhase[j]=self.walkPhase[j]
   elif s==2:self.actionPhase[j]=self.walkPhase[j]
   elif s==3:self.actionPhase[j]=.10+.018*math.sin(2*math.pi*(self.walkPhase[j]+u['phaseOffset']))
   elif s==4:self.actionPhase[j]=.12+.52*min(1.,self.timer[j]/max(u['drawSeconds'],.001))
   elif s==5:self.actionPhase[j]=.64
   elif s==6:self.actionPhase[j]=.64+.36*min(1.,self.timer[j]/max(u['recoverSeconds'],.001))
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
     if target>=0:claimed[target]=j
    if target>=0 and self.timer[j]>=u['aimSeconds']:
     self.pendingStart[j]=t;self.enter(j,4)
   elif self.state[j]==4:
    if not valid:self.target[j]=-1;self.enter(j,3)
    elif self.timer[j]>=u['drawSeconds']:
     e=spawn(j,target,t,self.pendingStart[j]);reserved[target]=True;self.records.append(e);self.lastRelease[j]=t;self.enter(j,5)
   elif self.state[j]==5:self.enter(j,6)
   elif self.state[j]==6 and self.timer[j]>=u['recoverSeconds']:
    self.target[j]=-1;self.enter(j,3)
   s=int(self.state[j])
   if s==3:self.actionPhase[j]=.10+.018*math.sin(2*math.pi*(self.walkPhase[j]+u['phaseOffset']))
   elif s==4:self.actionPhase[j]=.12+.52*min(1.,self.timer[j]/max(u['drawSeconds'],.001))
   elif s==5:self.actionPhase[j]=.64
   elif s==6:self.actionPhase[j]=.64+.36*min(1.,self.timer[j]/max(u['recoverSeconds'],.001))
 def control(self):
  return np.column_stack([self.state,self.timer,self.target,self.lastRelease,self.walkPhase,self.turnPhase,self.actionPhase,self.moveSpeed])
'''
Path('tools/archers_v18.py').write_text(new,encoding='utf8')
