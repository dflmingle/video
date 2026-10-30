from pathlib import Path
P=Path(__file__).resolve().parents[1]
p=P/'tools/build_simulation_v17.py';s=p.read_text(encoding='utf-8').replace('from motion_v16 import Crowd','from motion_v17 import Crowd\nfrom archers_v17 import Archers')
a=s.index('for j,u in enumerate(blue):');b=s.index('for u in red:',a);s=s[:a]+'archers=Archers(blue,C)\n\n'+s[b:]
s=s.replace('for f in range(N):\n t=f*dt', 'blueControls=np.zeros((N,nb,4),np.float32);pressureHistory=np.zeros((N,nr),np.float32)\nfor f in range(N):\n t=f*dt')
a=s.index(' for j,u in enumerate(blue):',s.index('for f in range(N):'));b=s.index(' alive=death>t',a)
s=s[:a]+" archers.move(t,dt);positions[f,:nb]=archers.position\n motion.bluePositions=archers.position\n"+s[b:]
s=s.replace('states[f]=motion.behavior;', 'pressureHistory[f]=motion.pressure;states[f]=motion.behavior;')
a=s.index(' if t>=firstDraw');b=s.index(' if f%120==0:',a)
s=s[:a]+''' if not C.get('disableCombat',False):
  pending=np.zeros(nr,int)
  for batch in scheduled.values():
   for target,e in batch:pending[target]+=1
  reserved=(pending>0)|(t<nextAllowed)|(hp<=0)
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
'''+s[b:]
s=s.replace('for target,e in scheduled.pop(f,[]):pass','pass # first unsafe state discarded; no contact frame is rendered')
s=s.replace('responses=[e for e in responses if', 'blueControls=blueControls[:N];pressureHistory=pressureHistory[:N]\nblueControls.tofile(O/\'blue-control.f32\');np.save(O/\'blue-control.npy\',blueControls);np.save(O/\'formation-pressure.npy\',pressureHistory)\nresponses=[e for e in responses if')
s=s.replace("dict(version='V16'","dict(version='V17'")
p.write_text(s,encoding='utf-8')
# Distance-conditioned weak regions; retain existing integrator, gait and hash.
p=P/'tools/motion_v17.py';s=p.read_text(encoding='utf-8')
s=s.replace('self.initialPosture=self.posture.copy()',"self.initialPosture=self.posture.copy();self.pressure=np.zeros(self.n);self.bluePositions=None;self.groupIndices=[np.array([i for i,u in enumerate(units) if u['platoon']==key]) for key in bounds];self.progressMedian=np.zeros(self.n)")
a=s.index(' def compute_soft_formation_correction');b=s.index(' def compute_local_avoidance',a)
s=s[:a]+''' def update_formation_pressure(self):
  if self.bluePositions is None:return
  for ids in self.groupIndices:
   active=ids[~self.dead[ids]]
   if not len(active):continue
   front=active[np.argsort(self.position[active,1])[-min(6,len(active)):]]
   distance=float(np.linalg.norm(self.position[front,None,:]-self.bluePositions[None,:,:],axis=2).min())
   a=self.config['formationNearDistance'];b=self.config['formationFarDistance'];q=float(np.clip((distance-a)/(b-a),0,1));pressure=1-q*q*(3-2*q)
   self.pressure[ids]=pressure;self.progressMedian[ids]=np.median(self.position[active,1]-self.initial[active,1])

 def compute_soft_formation_correction(self,i):
  pressure=self.pressure[i];freedom=.30+.90*pressure;strength=1.5-.85*pressure
  # Individual lateral corridor widens smoothly; platoon edges remain bounded.
  lower=max(self.lower[i]-.20,self.initial[i,0]-freedom);upper=min(self.upper[i]+.20,self.initial[i,0]+freedom);x=self.position[i,0]
  if x<lower:return min(.70,(lower-x)*strength)
  if x>upper:return -min(.70,(x-upper)*strength)
  return 0.

'''+s[b:]
s=s.replace('return self.preferred[i]*(1+rhythm)*congestion*self.get_hit_speed_multiplier(i,t)',"progress=self.position[i,1]-self.initial[i,1];free=2.5+5*self.pressure[i]\n  soft=min(.30,max(0.,progress-self.progressMedian[i]-free)*.10)\n  return max(0.,self.preferred[i]*(1+rhythm)*congestion*self.get_hit_speed_multiplier(i,t)-soft)")
s=s.replace('started=time.perf_counter();old=', 'self.update_formation_pressure()\n  started=time.perf_counter();old=')
p.write_text(s,encoding='utf-8')
# Original skeletal pose batching retained. Lower cadence and readable contact.
p=P/'src/assets-v17.js';s=p.read_text(encoding='utf-8').replace("key==='samurai'?.09:.07","key==='samurai'?.13:.11").replace("+.025*Math.sin(f/phases*Math.PI*4)","+.035*Math.sin(f/phases*Math.PI*4)")
p.write_text(s,encoding='utf-8')
p=P/'src/main-camera.js';s=p.read_text(encoding='utf-8').replace('./camera-v16.js','./camera-v17.js').replace('./assets-v11.js','./assets-v17.js')
s=s.replace("const [redControl,gaitCycles]=", "const blueControl=await load('blue-control.f32');\nconst [redControl,gaitCycles]=")
a=s.index('  if(i<nb){',s.index('function renderAt'));b=s.index('  }else if(combat',a)
s=s[:a]+'''  if(i<nb){
   const bc=Array.from({length:4},(_,k)=>blueControl[(frame*nb+i)*4+k]),state=Math.round(bc[0]),timer=bc[1],target=Math.round(bc[2]);
   memberState=['WAITING','MOVING','ARRIVING','AIMING','DRAWING','RELEASING','RECOVERING'][state];
   if(state===1||(state===2&&speed>.03)){action='move';clock=(distance/C.blueStride+u.phase)*a.clips.move.duration;lean=.045*Math.min(1,speed/4)}
   else if(state>=3){
    if(target>=0){const goal=row(t,nb+target);yaw=Math.atan2(goal[0]-p[0],goal[1]-p[1])}
    let e=null;for(const k of S.shooterEvents[i]){const v=S.events[k];if(t>=v.aimStart&&t<v.release+u.recoverSeconds+.04)e=v}
    if(e){currentEvent=e.id;yaw=Math.atan2(e.destination[0]-p[0],e.destination[2]-p[1])}
    action='attack';phaseFraction=state===3?.10:state===4?.12+.52*Math.min(1,timer/u.drawSeconds):state===5?.64:.64+.359*Math.min(1,timer/u.recoverSeconds);
    if(state===4){const ix=Math.min(a.clips.attack.phases-1,Math.floor(phaseFraction*a.clips.attack.phases)),loc=a.poseAnchors.attack[ix].leftHand;const h=new T.Vector3(p[0]+loc[0]*Math.cos(yaw)+loc[2]*Math.sin(yaw),loc[1],p[1]-loc[0]*Math.sin(yaw)+loc[2]*Math.cos(yaw)),d=new T.Vector3(Math.sin(yaw),.03,Math.cos(yaw));segment(arrowMesh,an++,h.clone().addScaledVector(d,-.4),h.clone().addScaledVector(d,.6));nocked++}
   }
'''+s[b:]
s=s.replace("version:'V16'","version:'V17'").replace('`V3 ·','`V17 ·').replace('const runningLift=0;',"const runningLift=i>=nb&&action==='move'?.025*Math.pow(Math.sin(clock/a.clips.move.duration*Math.PI*2),2):0;")
p.write_text(s,encoding='utf-8')
print('V17 code implemented')
