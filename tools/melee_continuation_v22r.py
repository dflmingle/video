"""Post-C1 local melee and a single coupled, nonpenetrating velocity integral.

This module is never used for the accepted C1 prefix. Bodies (including dead
bodies) retain their identity and occupancy; no army translation/repacking.
"""
import sys, math
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.spatial import cKDTree
try:
 import osqp
except ImportError:
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'output/v22r-volley-deps'))
 import osqp


class MeleeContinuation:
 def __init__(self, motion, archers, blue_hp, blue_death):
  self.m,self.a=motion,archers;self.nb=archers.n;self.nr=motion.n
  self.bhp,self.bdeath=blue_hp,blue_death
  self.target=np.full(self.nr,-1,int);self.state=np.zeros(self.nr,int)
  self.elapsed=np.zeros(self.nr);self.cooldown=np.zeros(self.nr)
  self.struck=np.zeros(self.nr,bool);self.yaw=motion.yaw.copy()
  self.duration=.466667;self.impactPhase=.55;self.reach=1.5
  self.phase=np.zeros(self.nr);self.events=[];self.solverAudit=[]
  self.blocked=np.zeros(self.nb,bool);self.redProposal=motion.velocity.copy()
  self.redVelocity=motion.velocity.copy();self.time=0.
  self.a.jointVelocityProjector=self.project
  self.a.deadMask=self.bhp<=0;self.a.meleeBlocked=self.blocked
  self.a.evasionVelocity=np.zeros((self.nb,2))
  self.pathCache=None;self.pathAt=-10.

 def prepare(self,t,dt):
  self.time=t;m,a=self.m,self.a
  self.a.deadMask=self.bhp<=0
  living=np.flatnonzero(self.bhp>0)
  if not len(living):
   # The outcome is already decided, but surviving people finish their own
   # movement and recover rather than snapping every root to zero together.
   speed=np.linalg.norm(m.velocity,axis=1)
   factor=np.maximum(0.,speed-(24.+18.*m.phase)*dt)/np.maximum(speed,1e-9)
   self.redProposal=m.velocity*factor[:,None];self.state.fill(0);self.phase.fill(0);return
  d,idx=cKDTree(a.position[living]).query(m.position)
  nearest=living[idx]
  # A swing owns its original target until recovery, even if someone else
  # kills that target. A replacement must receive a fresh windup next cycle.
  lock=(self.state==2)&(self.target>=0)
  self.target[~lock]=nearest[~lock]
  goal=a.position[self.target];delta=goal-m.position
  dist=np.linalg.norm(delta,axis=1);direction=delta/np.maximum(dist[:,None],1e-9)
  # Far members retain the original per-ID forward pace; targeting starts only
  # within the local engagement neighborhood, never at the old 4-unit cut.
  m.bluePositions=a.position[living];m.update_formation_pressure()
  speed=np.array([m.compute_desired_speed(i,t,1.) if not m.dead[i] else 0. for i in range(m.n)])
  desired=np.column_stack([np.clip((m.initial[:,0]-m.position[:,0])*1.5,-1.,1.),speed])
  if m.config.get('freshLayoutContinuation'):
   for i,u in enumerate(m.units):
    if t<u['delay']:desired[i]=0.
  near=dist<10.
  localSpeed=np.minimum(speed,np.sqrt(2*65.*np.maximum(0.,dist-1.05)))
  desired[near]=direction[near]*localSpeed[near,None]
  # Reach a locally accessible attack ring around a corpse instead of running
  # into a fixed body. The field has every living blue member as a goal.
  self.route_corpses(desired,near,t)
  for i in np.flatnonzero((~m.dead)&near):
   if self.state[i]==2:
    self.elapsed[i]+=dt;self.phase[i]=min(.999,self.elapsed[i]/self.duration)
    desired[i]=0.
    if self.elapsed[i]>=self.duration:
     self.state[i]=1;self.cooldown[i]=t+.15+.09*m.phase[i]
   elif dist[i]<=self.reach and t>=self.cooldown[i]:
    self.state[i]=2;self.elapsed[i]=0.;self.phase[i]=0.;self.struck[i]=False
    desired[i]=0.
   else:self.state[i]=1
  self.state[~near]=0;self.state[m.dead]=0
  targetYaw=np.arctan2(direction[:,0],direction[:,1])
  moving=np.linalg.norm(desired,axis=1)>.1
  targetYaw[moving]=np.arctan2(desired[moving,0],desired[moving,1])
  difference=(targetYaw-self.yaw+math.pi)%(2*math.pi)-math.pi
  self.yaw+=np.clip(difference,-dt*5.5,dt*5.5)
  # Bounded acceleration. Dead roots are fixed; contacts are resolved jointly.
  change=desired-m.velocity;length=np.linalg.norm(change,axis=1)
  limit=np.where(np.linalg.norm(desired,axis=1)<np.linalg.norm(m.velocity,axis=1),85.,m.maxAcceleration)*dt
  self.redProposal=m.velocity+change*np.minimum(1.,limit/np.maximum(length,1e-9))[:,None]
  self.redProposal[m.dead]=0.
  alive=np.flatnonzero(~m.dead)
  bd,ri=cKDTree(m.position[alive]).query(a.position) if len(alive) else (np.full(a.n,1e6),np.zeros(a.n,int))
  self.blocked[:]=np.where(self.blocked,bd<3.6,bd<2.8)&(self.bhp>0)
  for j in np.flatnonzero(self.blocked):
   # A bounded retreat, not an escaping army or a new deployment target.
   away=a.position[j]-m.position[alive[ri[j]]];away/=max(np.linalg.norm(away),1e-9)
   goal=a.defenseSlots[j]+a.slotOffsets[j]+away*.85
   ev=(goal-a.position[j])*4.;ev*=min(1.,2.3/max(np.linalg.norm(ev),1e-9))
   a.evasionVelocity[j]=ev
   if a.state[j] in (3,4,5,6,7):a.enter(j,1,t);a.target[j]=-1

 def route_corpses(self,desired,near,t):
  from scipy.ndimage import distance_transform_edt
  from scipy.sparse.csgraph import dijkstra
  corpses=np.vstack([self.m.position[self.m.dead],self.a.position[self.bhp<=0]])
  if not len(corpses):return
  # Grid navigation only influences nearby obstructed members; the accepted
  # trajectories and far charge do not pass through this code.
  if t-self.pathAt>.25:
   step=.4;x=np.arange(-32.,32.01,step);z=np.arange(-35.,58.01,step)
   xx,zz=np.meshgrid(x,z);grid=np.column_stack([xx.ravel(),zz.ravel()])
   clear=cKDTree(corpses).query(grid)[0]>.67
   goals=cKDTree(self.a.position[self.bhp>0]).query(grid)[0]
   sources=np.flatnonzero(clear&(goals<1.35))
   h,w=xx.shape;ids=np.arange(len(grid)).reshape(h,w);rows=[];cols=[];vals=[]
   for dz,dx in [(0,1),(1,0),(1,1),(1,-1)]:
    y0,y1=max(0,-dz),min(h,h-dz);x0,x1=max(0,-dx),min(w,w-dx)
    aa=ids[y0:y1,x0:x1].ravel();bb=ids[y0+dz:y1+dz,x0+dx:x1+dx].ravel()
    ok=clear[aa]&clear[bb];aa,bb=aa[ok],bb[ok]
    cost=np.full(len(aa),math.hypot(dx,dz)*step)
    rows.extend([aa,bb]);cols.extend([bb,aa]);vals.extend([cost,cost])
   if len(sources):
    graph=sparse.csr_matrix((np.concatenate(vals),(np.concatenate(rows),np.concatenate(cols))),shape=(len(grid),len(grid)))
    field=dijkstra(graph,directed=False,indices=sources,min_only=True).reshape(h,w)
    self.pathCache=(field,x,z,clear.reshape(h,w));self.pathAt=t
  if self.pathCache is None:return
  field,x,z,clear=self.pathCache
  dc,ci=cKDTree(corpses).query(self.m.position)
  for i in np.flatnonzero(near&(~self.m.dead)&(dc<2.8)):
   # Use the field only when the nearest corpse is ahead of desired motion.
   obstacle=corpses[ci[i]]-self.m.position[i]
   if obstacle@desired[i]<=0:continue
   ix=int(np.clip(round((self.m.position[i,0]-x[0])/.4),0,len(x)-1));iz=int(np.clip(round((self.m.position[i,1]-z[0])/.4),0,len(z)-1))
   options=[]
   for dz in (-1,0,1):
    for dx in (-1,0,1):
     nz,nx=iz+dz,ix+dx
     if (dx or dz) and 0<=nz<len(z) and 0<=nx<len(x) and clear[nz,nx] and np.isfinite(field[nz,nx]):
      v=np.array([x[nx],z[nz]])-self.m.position[i]
      options.append((field[nz,nx]+.1*np.linalg.norm(v),v))
   if options:
    v=min(options,key=lambda q:q[0])[1];desired[i]=v/max(np.linalg.norm(v),1e-9)*min(8.,np.linalg.norm(desired[i]))

 def project(self,blueDesired,dt):
  p=np.vstack([self.a.position,self.m.position]);v=np.vstack([blueDesired,self.redProposal])
  dead=np.r_[self.bhp<=0,self.m.dead];n=len(p);v[dead]=0.
  pairs=cKDTree(p).query_pairs(2.1,output_type='ndarray')
  ia,ib=pairs.T;delta=p[ia]-p[ib];dist=np.linalg.norm(delta,axis=1);normal=delta/np.maximum(dist[:,None],1e-9)
  rows=np.repeat(np.arange(len(pairs)),4);cols=np.column_stack([ia*2,ia*2+1,ib*2,ib*2+1]).ravel()
  values=np.column_stack([normal[:,0],normal[:,1],-normal[:,0],-normal[:,1]]).ravel()
  contacts=sparse.csc_matrix((values,(rows,cols)),shape=(len(pairs),2*n))
  # A zero velocity remains feasible even inside a fully occupied contact
  # pocket. Restoring a larger gap there can invent an impossible constraint.
  target=np.minimum(.61502,dist-1e-9)
  lower=(target-dist)/dt
  bounds=np.full((n,2),30.);bounds[:self.nb]=5.;bounds[dead]=0.
  A=sparse.vstack([sparse.eye(2*n,format='csc'),contacts],format='csc')
  lo=np.r_[-bounds.ravel(),lower];hi=np.r_[bounds.ravel(),np.full(len(pairs),np.inf)]
  solver=osqp.OSQP();solver.setup(P=sparse.eye(2*n,format='csc'),q=-v.ravel(),A=A,l=lo,u=hi,verbose=False,eps_abs=2e-5,eps_rel=2e-5,max_iter=6000,polishing=True,rho=1.)
  solver.warm_start(x=np.zeros(2*n))
  solved=solver.solve(raise_error=False)
  if solved.info.status_val not in (1,2):
   solver.update_settings(max_iter=30000,eps_abs=3e-5,eps_rel=3e-5,rho=1.)
   solved=solver.solve(raise_error=False)
  if solved.x is None:raise RuntimeError('Body solver '+solved.info.status)
  residual=A@solved.x
  violation=max(float(np.max(lo-residual)),float(np.max(residual-hi)))
  if violation>.005:raise RuntimeError(f'Body solver {solved.info.status} residual {violation} at {self.time}')
  actual=solved.x.reshape(n,2);actual[dead]=0.
  nxt=p+actual*dt;minimum=float(np.linalg.norm(nxt[ia]-nxt[ib],axis=1).min())
  # The half-plane also bounds the whole swept segment, not just endpoints.
  dv=(actual[ia]-actual[ib])*dt
  tau=np.clip(-np.sum(delta*dv,axis=1)/np.maximum(np.sum(dv*dv,axis=1),1e-20),0,1)
  swept=float(np.linalg.norm(delta+dv*tau[:,None],axis=1).min())
  # .615 is preferred personal spacing, .58 is the physical body diameter.
  # Tight solving is necessary when physical reserve falls below .02, rather
  # than treating submillimetre personal-spacing residual as body penetration.
  if minimum<.60 or swept<.60:
   # Tighten the solution instead of enlarging impossible contact pockets.
   solver.update_settings(eps_abs=1e-8,eps_rel=1e-8,max_iter=100000)
   retry=solver.solve(raise_error=False)
   if retry.x is not None:
    actual=retry.x.reshape(n,2);actual[dead]=0.
    nxt=p+actual*dt;minimum=float(np.linalg.norm(nxt[ia]-nxt[ib],axis=1).min())
    dv=(actual[ia]-actual[ib])*dt;tau=np.clip(-np.sum(delta*dv,axis=1)/np.maximum(np.sum(dv*dv,axis=1),1e-20),0,1)
    swept=float(np.linalg.norm(delta+dv*tau[:,None],axis=1).min())
  if minimum<.60 or swept<.60:raise RuntimeError(f'Body reserve violation {minimum} swept {swept}')
  self.solverAudit.append(dict(time=self.time,minimumCenter=minimum,sweptMinimum=swept,iterations=int(solved.info.iter),pairs=len(pairs)))
  self.redVelocity=actual[self.nb:];return actual[:self.nb]

 def integrate_red(self,t,dt):
  m=self.m;old=m.position.copy();oldv=m.velocity.copy()
  m.velocity=self.redVelocity.copy();m.position+=m.velocity*dt
  m.cycles+=np.linalg.norm(m.position-old,axis=1)/np.maximum(.1,m.stride)
  m.yaw=self.yaw.copy();m.acceleration=(m.velocity[:,1]-oldv[:,1])/dt
  m.targetSpeed=np.linalg.norm(self.redProposal,axis=1)
  for i in np.flatnonzero((self.state==2)&(~self.struck)&(~m.dead)&(self.phase>=self.impactPhase)):
   self.struck[i]=True;j=int(self.target[i]);d=self.a.position[j]-m.position[i]
   distance=float(np.linalg.norm(d));angle=abs((math.atan2(d[0],d[1])-self.yaw[i]+math.pi)%(2*math.pi)-math.pi)
   valid=self.bhp[j]>0 and distance<=self.reach and angle<.65
   event=dict(id=f'M{len(self.events):05}',time=t,attacker=i,attackerID=m.units[i]['id'],target=j,targetID=self.a.units[j]['id'],phase=float(self.phase[i]),distance=distance,damage=1 if valid else 0,result='HIT' if valid else 'MISS',killed=False)
   if valid:
    self.bhp[j]-=1
    if self.bhp[j]<=0:self.bdeath[j]=t;event['killed']=True;self.a.velocity[j]=0.
   self.events.append(event)

 def control(self):
  return np.column_stack([self.state,self.phase,self.target,self.yaw])
