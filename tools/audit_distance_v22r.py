"""Distance-only candidates: frozen rules, actual transforms, geometry, causality."""
from pathlib import Path
import json, hashlib, csv
import sys
import numpy as np
from scipy.spatial import cKDTree
from scene_occupancy_v22r import load_obstacles, signed_clearance

P=Path(__file__).resolve().parents[1]; group=sys.argv[sys.argv.index('--group')+1] if '--group' in sys.argv else 'distance';D=P/('docs/v22r-'+group)
setup=json.loads((D/'setup.json').read_text(encoding='utf8'))
base=P/'variants'/setup['baseline']; B=json.loads((base/'simulation.json').read_text(encoding='utf8'))
bp=np.load(base/'trajectories.npy')[0].astype(float); nb=B['blueCount']; radius=B['config']['bodyRadius']
normal=np.array(setup.get('normal',setup['candidates'][0].get('normal'))); obstacles=load_obstacles()
wallFront=max(float((o['vertices']@normal).max()) for o in obstacles if 'polySurface18' in o['path'])
hashes={name:hashlib.sha256((P/name).read_bytes()).hexdigest()==value for name,value in setup['protectedSourceHashes'].items()}
assert all(hashes.values()), hashes
reports=[]
def timing(s):
 return dict(firstRelease=min(e['release'] for e in s['events']),firstArrowHit=min(e['impact'] for e in s['events'] if e.get('damage',0)),firstMeleeHit=min(e['time'] for e in s['meleeEvents'] if e['damage']),duration=s['config']['duration'],arrows=len(s['events']),arrowHits=sum(bool(e.get('damage')) for e in s['events']))
for case in setup['candidates']:
 if '--label' in sys.argv and case['label']!=sys.argv[sys.argv.index('--label')+1]:continue
 v=P/'variants'/case['variant']; s=json.loads((v/'simulation.json').read_text(encoding='utf8')); c=s['config']
 pos=np.load(v/'trajectories.npy'); vel=np.load(v/'velocities.npy'); n=len(s['units'])
 obstacles=load_obstacles(c.get('sceneLayout'))
 wallFront=max(float((o['vertices']@normal).max()) for o in obstacles if 'polySurface18' in o['path'])
 changes={k:{'baseline':B['config'].get(k),'candidate':c.get(k)} for k in set(c)|set(B['config']) if c.get(k)!=B['config'].get(k)}
 allowed={'redArmyTranslations','blueArmyTranslation','duration','checkpointFrame','autoCut','meleeContinuation','continuationStart','sceneLayout','previewFailure'}
 assert not set(changes)-allowed, changes
 unitKeys=['speed','maxAcceleration','aimSeconds','drawSeconds','recoverSeconds','cycle','color','platoon','id','team']
 memberRules={key:all(a.get(key)==b.get(key) for a,b in zip(s['units'],B['units'])) for key in unitKeys}
 assert all(memberRules.values())
 expected=np.empty_like(bp); expected[:nb]=case['blueRigidTranslation']; expected[nb:]=case['redRigidTranslation']
 error=float(np.max(np.abs(pos[0]-bp-expected))); assert error<3e-6, error
 gap=float((pos[0,:nb]@normal).min()-(pos[0,nb:]@normal).max()-2*radius)
 spawnClosest=float(cKDTree(pos[0,:nb]).query(pos[0,nb:])[0].min()-2*radius)
 paths=[]; sweeps=[]; a=pos[:-1].reshape(-1,2); delta=np.diff(pos,axis=0).reshape(-1,2)
 for obstacle in obstacles:
  clearance=signed_clearance(pos.reshape(-1,2),obstacle)
  if clearance.min()<radius-1e-5:paths.append(dict(path=obstacle['path'],samples=int((clearance<radius-1e-5).sum()),minimum=float(clearance.min())))
  eq=obstacle['equations']; side=a@eq[:,:2].T+eq[:,2]-radius; rate=delta@eq[:,:2].T
  entering=np.max(np.where(rate < -1e-10,-side/np.where(rate < -1e-10,rate,-1),-np.inf),axis=1)
  leaving=np.min(np.where(rate > 1e-10,-side/np.where(rate > 1e-10,rate,1),np.inf),axis=1)
  crossing=(np.maximum(entering,0)<=np.minimum(leaving,1))&(~np.any((np.abs(rate)<1e-10)&(side>0),axis=1))
  if crossing.any():sweeps.append(dict(path=obstacle['path'],segments=int(crossing.sum())))
 deaths=np.array([u['deathTime'] if u.get('deathTime') is not None else 1e6 for u in s['units']])
 invalidArrows=[]; invalidMelee=[]
 for e in s['events']:
  if e.get('damage',0) and np.linalg.norm(pos[e['impactFrame'],e['target']]-np.array(e['destination'])[::2])>.68001:invalidArrows.append(e['id'])
  if e['release']>=deaths[e['shooter']]-1e-8:invalidArrows.append(e['id']+' DEAD_SHOOTER')
 for e in s['meleeEvents']:
  if e['damage'] and (e['distance']>1.5 or e['phase']<.55 or e['time']>deaths[e['attacker']+nb] or e['time']>deaths[e['target']]):invalidMelee.append(e['id'])
 firstRed=next(f/60 for f in range(1,len(pos)) if np.max(np.linalg.norm(pos[f,nb:]-pos[f-1,nb:],axis=1))>1e-4)
 firstBlue=next(f/60 for f in range(1,len(pos)) if np.max(np.linalg.norm(pos[f,:nb]-pos[f-1,:nb],axis=1))>1e-4)
 firstContact=None
 for f in range(len(pos)):
  live=deaths>f/60
  if live[:nb].any() and live[nb:].any() and cKDTree(pos[f,:nb][live[:nb]]).query(pos[f,nb:][live[nb:]])[0].min()<=1.5+1e-6:firstContact=f/60;break
 forward=np.array([0.,-98.,-60.]);forward/=np.linalg.norm(forward);up=np.cross([1.,0.,0.],forward)
 xyz=np.zeros((*pos.shape[:2],3));xyz[:,:,0]=pos[:,:,0];xyz[:,:,2]=pos[:,:,1];rel=xyz-[0.,98.,65.];depth=rel@forward;tan=np.tan(np.deg2rad(21))
 visible=(np.abs(rel[:,:,0]/(depth*tan*2/3))<1)&(np.abs((rel@up)/(depth*tan))<1)
 rows=[]
 for f in range(0,len(pos),6):
  t=f/60;live=deaths>t;speed=np.linalg.norm(vel[f],axis=1)
  rows.append(dict(time=t,redMoving=int(((speed[nb:]>.2)&live[nb:]).sum()),blueMoving=int(((speed[:nb]>.2)&live[:nb]).sum()),redMedianLivingSpeed=float(np.median(speed[nb:][live[nb:]])) if live[nb:].any() else 0.,releases=sum(t<=e['release']<t+.1 for e in s['events']),inFlight=sum(e['release']<=t<e['impact'] for e in s['events']),arrowHits=sum(t<=e['impact']<t+.1 and bool(e.get('damage',0)) for e in s['events']),meleeHits=sum(t<=e['time']<t+.1 and e['damage']>0 for e in s['meleeEvents']),redAlive=int(live[nb:].sum()),blueAlive=int(live[:nb].sum())))
 with (D/(case['label']+'-timeline.csv')).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 solver=json.loads((v/'continuation-audit.json').read_text(encoding='utf8'))
 deadDrift=0.
 for j,d in enumerate(deaths):
  if d>1e5:continue
  f=round(d*60);deadDrift=max(deadDrift,float(np.linalg.norm(pos[f:,j]-pos[f,j],axis=1).max()))
 cruising={}
 for t in [.1,.3,.5]:
  f=round(t*60);live=deaths[nb:]>t;control=np.linalg.norm(vel[f,nb:],axis=1)
  cruising[str(t)]=dict(redMedianLivingSpeed=float(np.median(control[live])),redMoving=int(((control>.2)&live).sum()))
 r=dict(label=case['label'],configChanges=changes,memberRulesUnchanged=memberRules,maximumInitialRigidTranslationError=error,frontNetGap=gap,actualIncreaseRatio=gap/case['baselineFrontNetGap']-1,nearestInitialBodyNetDistance=spawnClosest,minimumWallFrontDistance=float((pos@normal-wallFront).min()),obstacleBodyViolations=paths,sweptObstacleViolations=sweeps,invalidArrowEvents=invalidArrows,invalidMeleeEvents=invalidMelee,firstRedMovement=firstRed,firstBlueMovement=firstBlue,firstRelease=min(e['release'] for e in s['events']),firstArrowHit=min(e['impact'] for e in s['events'] if e.get('damage',0)),firstMeleeRangeContact=firstContact,firstMeleeHit=min(e['time'] for e in s['meleeEvents'] if e['damage']),openingRootVisible=int(visible[0].sum()),minimumAllFrameRootVisible=int(visible.sum(1).min()),totalMembers=n,maximumDeadRootDrift=deadDrift,openingChargeWorldSpeeds=cruising,battle=solver)
 reports.append(r)
 r['firstRootOutsideFrame']=next((i/60 for i in range(len(pos)) if not visible[i].all()),None)
 r['rootVisibleAtSeconds']={str(t):int(visible[min(round(t*60),len(pos)-1)].sum()) for t in [0,1,2,4,6,7]}
 r['sceneLayout']=c.get('sceneLayout');r['terminationSucceeded']=solver['termination']=='SIDE_ELIMINATED'
 assert not paths and not sweeps and not invalidArrows and not invalidMelee
 assert solver['minimumSweptBodyCenter']>=2*radius-1e-5
 print(json.dumps({k:r[k] for k in ['label','frontNetGap','actualIncreaseRatio','firstRelease','firstArrowHit','firstMeleeRangeContact','firstMeleeHit','openingRootVisible','minimumAllFrameRootVisible','battle']},indent=2),flush=True)
output='audit.json' if '--label' not in sys.argv else 'audit-'+sys.argv[sys.argv.index('--label')+1]+'.json'
(D/output).write_text(json.dumps(dict(baseline=timing(B),protectedSourcesUnchanged=hashes,candidates=reports,formalRender=False),indent=2),encoding='utf8')
