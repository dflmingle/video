"""Per-member deployment/aim/draw/release FSM, squad windows are only readiness hints."""
import math,numpy as np
NAMES=['WAITING','MOVING','ARRIVING','AIMING','DRAWING','RELEASING','RECOVERING']
class Archers:
 def __init__(self,units,C):
  self.units=units;self.C=C;self.n=len(units);self.starts=np.array([u['start'] for u in units]);self.position=self.starts.copy();self.previous=self.position.copy();self.velocity=np.zeros_like(self.position)
  self.state=np.zeros(self.n,dtype=np.uint8);self.timer=np.zeros(self.n);self.target=np.full(self.n,-1,int);self.pendingStart=np.full(self.n,-1.);self.lastRelease=np.full(self.n,-10.);self.records=[]
  for j,u in enumerate(units):
   row=j%36//6;col=j%6;q=((j+1)*.61803398875)%1;r=((col+1)*.41421356237+u['group']*.19)%1
   early=u['group'] in [0,6];squadLag=[0,.09,.17,.22,.15,.07,.04][u['group']]
   u.update(delay=.025+squadLag+.026*row+.018*r,moveSeconds=(.99 if early else 1.55)+.065*row+.035*r,turnSeconds=.03+.025*r,aimSeconds=.035+.035*q,drawSeconds=.145+.065*r,recoverSeconds=.21+.10*q,cycle=.53+.13*r,arrival=0,shootYaw=math.pi)
   # Symmetric outward deployment arcs. All members of a squad share the
   # corridor, but keep their own start/arrival and gait; endpoints unchanged.
   bend=1.20*math.cos(u['group']*math.pi/6)
   path=np.column_stack([bend*np.sin(np.linspace(0,math.pi,128)),-C['blueAdvance']*np.linspace(0,1,128)])
   pathLength=float(np.linalg.norm(np.diff(path,axis=0),axis=1).sum())
   u['moveSeconds']*=pathLength/C['blueAdvance']
   u['arrival']=u['delay']+u['moveSeconds'];u['readyAt']=u['arrival']+u['turnSeconds'];u['target']=[u['start'][0],u['start'][1]-C['blueAdvance']];u['pathBend']=bend;u['deploymentPathLength']=pathLength
 def enter(self,j,state):self.state[j]=state;self.timer[j]=0
 def move(self,t,dt):
  self.previous[:]=self.position
  for j,u in enumerate(self.units):
   a=float(np.clip((t-u['delay'])/u['moveSeconds'],0,1));s=a*a*(3-2*a)
   self.position[j]=self.starts[j]+[u['pathBend']*math.sin(math.pi*s),-self.C['blueAdvance']*s]
   if t<u['delay']:self.state[j]=0
   elif t<u['arrival']-.14:self.state[j]=1
   elif t<u['readyAt']:self.state[j]=2
   elif self.state[j]<3:self.enter(j,3)
  self.velocity=(self.position-self.previous)/dt
 def select(self,j,red,hp,reserved,t):
  delta=red-self.position[j];d=np.linalg.norm(delta,axis=1);valid=np.where((hp>0)&(~reserved)&(d<=self.C['archerRange']))[0]
  if not len(valid):return -1
  # Nearest front members first, with stable ID-dependent selection among six.
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
     self.target[j]=self.select(j,red,hp,excluded,t);self.timer[j]=0;target=int(self.target[j])
     if target>=0:claimed[target]=j
    if target>=0 and self.timer[j]>=u['aimSeconds']:
     self.pendingStart[j]=t;self.enter(j,4)
   elif self.state[j]==4:
    if not valid:self.target[j]=-1;self.enter(j,3)
    elif self.timer[j]>=u['drawSeconds']:
     # Actual release is a one-tick state, rechecked at real current distance.
     e=spawn(j,target,t,self.pendingStart[j]);reserved[target]=True;self.records.append(e);self.lastRelease[j]=t;self.enter(j,5)
   elif self.state[j]==5:self.enter(j,6)
   elif self.state[j]==6 and self.timer[j]>=u['recoverSeconds']:
    self.target[j]=-1;self.enter(j,3)
 def control(self):return np.column_stack([self.state,self.timer,self.target,self.lastRelease])
