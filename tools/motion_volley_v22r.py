"""Optional local enemy occupancy bounds on the unchanged V22 single integral."""
import math
import numpy as np
import sys
from pathlib import Path
from scipy import sparse
try:
 import osqp
except ImportError:
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'output/v22r-volley-deps'))
 import osqp
from motion_v22 import Crowd as V22Crowd
from scene_occupancy_v22r import load_obstacles

class Crowd(V22Crowd):
 def __init__(self,units,config):
  super().__init__(units,config)
  self.blueDefensePositions=None
  self.frontSpeedCaps=np.full(self.n,np.inf)
  self.frontStopZ=np.full(self.n,np.inf)
  self.frontConstraintFrames=[]
  self.projectionStats=[]
  self.sceneObstacles=load_obstacles()

 def update_formation_pressure(self):
  super().update_formation_pressure()
  if self.blueDefensePositions is None:return
  b=self.blueDefensePositions
  radius=2*self.config['weaponEnvelopeRadius']+self.config['minimumEnemyClearance']+self.config.get('safeFrontMargin',.65)
  dx=self.position[:,None,0]-b[None,:,0]
  dz=b[None,:,1]-self.position[:,None,1]
  valid=(np.abs(dx)<radius)&(dz>0)
  stop=b[None,:,1]-np.sqrt(np.maximum(0.,radius*radius-dx*dx))
  self.frontStopZ=np.min(np.where(valid,stop,np.inf),axis=1)
  gap=np.maximum(0.,self.frontStopZ-self.position[:,1])
  self.frontSpeedCaps=np.sqrt(2*self.config.get('safeFrontBrake',52.5)*gap)

 def compute_desired_speed(self,i,t,congestion):
  return min(super().compute_desired_speed(i,t,congestion),self.frontSpeedCaps[i])

 def constrain_front_proposals(self,proposal,old,dt,pairs):
  # Velocity projection only, before the one existing position integral.
  # Future end slots anticipate the blue advance; no marching schedule/global stop.
  cap=np.maximum(0.,(self.frontStopZ-old[:,1])/dt)
  cap=np.minimum(cap,np.maximum(self.velocity[:,1]-self.config.get('safeFrontBrake',52.5)*dt,self.frontSpeedCaps))
  cap=np.maximum(0.,cap)
  # Coupled least-change velocity projection. All contact half-planes and
  # forward bounds must hold together; sequential clamping previously broke
  # an already solved neighbor constraint near an immovable casualty.
  lower=np.tile([-2.5,0.],self.n);upper=np.column_stack([np.full(self.n,2.5),cap]).ravel()
  lower[np.repeat(self.dead,2)]=0.;upper[np.repeat(self.dead,2)]=0.
  constraints=[sparse.eye(2*self.n,format='csc')];lows=[lower];highs=[upper]
  obstacleRows=[];obstacleCols=[];obstacleValues=[];obstacleLow=[]
  for obstacle in self.sceneObstacles:
   eq=obstacle['equations'];sides=old@eq[:,:2].T+eq[:,2];face=np.argmax(sides,axis=1);distance=sides[np.arange(self.n),face]
   for j in np.flatnonzero(distance<2.):
    row=len(obstacleLow);normal=eq[face[j],:2];obstacleRows.extend([row,row]);obstacleCols.extend([2*j,2*j+1]);obstacleValues.extend(normal);obstacleLow.append((.31-distance[j])/dt)
  if obstacleLow:
   constraints.append(sparse.csc_matrix((obstacleValues,(obstacleRows,obstacleCols)),shape=(len(obstacleLow),2*self.n)));lows.append(np.array(obstacleLow));highs.append(np.full(len(obstacleLow),np.inf))
  if len(pairs):
   ia,ib=pairs.T;delta=old[ia]-old[ib];dist=np.linalg.norm(delta,axis=1);normal=delta/np.maximum(dist[:,None],1e-9)
   rows=np.repeat(np.arange(len(pairs)),4);cols=np.column_stack([ia*2,ia*2+1,ib*2,ib*2+1]).ravel();values=np.column_stack([normal[:,0],normal[:,1],-normal[:,0],-normal[:,1]]).ravel()
   constraints.append(sparse.csc_matrix((values,(rows,cols)),shape=(len(pairs),2*self.n)))
   # Already fixed corpse pairs keep their actual >= .615 separation. Do not
   # demand the additional numerical margin by moving two immutable bodies.
   target=np.minimum(.61502,dist-1e-8)
   lows.append((target-dist)/dt);highs.append(np.full(len(pairs),np.inf))
  matrix=sparse.vstack(constraints,format='csc');lo=np.concatenate(lows);hi=np.concatenate(highs)
  solver=osqp.OSQP();solver.setup(P=sparse.eye(2*self.n,format='csc'),q=-proposal.ravel(),A=matrix,l=lo,u=hi,verbose=False,eps_abs=1e-5,eps_rel=1e-5,max_iter=3000,polishing=True,rho=1.,adaptive_rho_interval=25)
  solver.warm_start(x=np.zeros(2*self.n));solved=solver.solve(raise_error=False)
  if solved.x is None:raise RuntimeError('Local velocity projection: '+solved.info.status)
  evaluated=matrix@solved.x;violation=max(float(np.max(lo-evaluated)),float(np.max(evaluated-hi)))
  proposal=solved.x.reshape(self.n,2);proposal[self.dead]=0.;proposal[:,1]=np.maximum(0.,proposal[:,1])
  predicted=old+proposal*dt
  minimumPair=float(np.min(np.linalg.norm(predicted[ia]-predicted[ib],axis=1))) if len(pairs) else 1e6
  # Validate physical world separation, not an arbitrary velocity residual.
  # The extra .00002 target margin is solely solver round-off allowance.
  if minimumPair<.6145 or np.max(proposal[:,1]-cap)>1e-3 or violation>1e-2:
   solver.update_settings(max_iter=18000);solver.warm_start(x=solved.x);retry=solver.solve(raise_error=False)
   if retry.x is not None:
    evaluated=matrix@retry.x;retryViolation=max(float(np.max(lo-evaluated)),float(np.max(evaluated-hi)))
    if retryViolation<violation:
     solved=retry;violation=retryViolation;proposal=solved.x.reshape(self.n,2);proposal[self.dead]=0.;proposal[:,1]=np.maximum(0.,proposal[:,1]);predicted=old+proposal*dt;minimumPair=float(np.min(np.linalg.norm(predicted[ia]-predicted[ib],axis=1))) if len(pairs) else 1e6
  # .001 world-unit solver allowance remains .034 above two .29 body radii.
  # The independent audit retains .614 required clearance, never .58 overlap.
  if minimumPair<.614 or np.max(proposal[:,1]-cap)>1e-3:raise RuntimeError(f'Local velocity projection at {self.time:.4f}: {solved.info.status}, worldSpacing={minimumPair}, velocityViolation={violation}')
  self.projectionStats.append(dict(time=self.time,iterations=int(solved.info.iter),status=solved.info.status,primalResidual=float(solved.info.prim_res),maximumConstraintViolation=violation))
  self.frontConstraintFrames.append(dict(time=self.time,limited=int(np.sum((self.frontSpeedCaps<self.preferred)&(~self.dead))),hardBound=int(np.sum(proposal[:,1]>=cap-1e-6))))
  return proposal
