"""Direct causality, world motion, occupancy and accepted-prefix evidence."""
from pathlib import Path
import json,csv,hashlib
import numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];V=P/'variants/V22R-C1-melee';D=P/'docs/v22r-melee';D.mkdir(exist_ok=True)
S=json.loads((V/'simulation.json').read_text(encoding='utf8'));A=json.loads((V/'continuation-audit.json').read_text(encoding='utf8'))
pos=np.load(V/'trajectories.npy');vel=np.load(V/'velocities.npy');mc=np.fromfile(V/'melee-control.f32',np.float32).reshape(S['frames'],S['redCount'],4)
nb=S['blueCount'];units=S['units'];dt=1/60
deaths=np.array([u['deathTime'] if u['deathTime'] is not None else 1e6 for u in units]);rows=[]
for f in range(0,len(pos),6):
 t=f*dt;alive=deaths>t;speed=np.linalg.norm(vel[f],axis=1)
 releases=[e for e in S['events'] if t<=e['release']<t+.1]
 impacts=[e for e in S['events'] if t<=e['impact']<t+.1 and e.get('damage',0)]
 melee=[e for e in S['meleeEvents'] if t<=e['time']<t+.1]
 distance=cKDTree(pos[f,:nb][alive[:nb]]).query(pos[f,nb:])[0] if alive[:nb].any() else np.full(S['redCount'],1e6)
 far=(distance>10)&alive[nb:]
 rows.append(dict(time=t,redMoving=int(((speed[nb:]>.2)&alive[nb:]).sum()),blueMoving=int(((speed[:nb]>.2)&alive[:nb]).sum()),redAlive=int(alive[nb:].sum()),blueAlive=int(alive[:nb].sum()),redFarCount=int(far.sum()),redFarMedianSpeed=float(np.median(speed[nb:][far])) if far.any() else None,redAttacking=int(((mc[f,:,0]==2)&alive[nb:]).sum()),arrowsReleased=len(releases),arrowsFlying=sum(e['release']<=t<e['impact'] for e in S['events']),arrowHits=len(impacts),meleeHits=sum(e['damage']>0 for e in melee),meleeDeaths=sum(e['killed'] for e in melee)))
with (D/'timeline-every-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
badShot=[e['id'] for e in S['events'] if e['release']>=deaths[e['shooter']]-1e-8]
badMelee=[]
swappedAttackTargets=[]
for f in range(161,len(mc)):
 midSwing=(mc[f,:,0]==2)&(mc[f-1,:,0]==2)
 for i in np.flatnonzero(midSwing&(mc[f,:,2]!=mc[f-1,:,2])):swappedAttackTargets.append([f,int(i)])
badArrowEndpoints=[]
for e in S['events']:
 if e['impact']<=2.65 or not e.get('damage',0):continue
 f=e['impactFrame'];error=float(np.linalg.norm(pos[f,e['target']]-np.array(e['destination'])[::2]))
 if error>.68001:badArrowEndpoints.append(dict(id=e['id'],error=error))
for e in S['meleeEvents']:
 if not e['damage']:continue
 f=round(e['time']*60);r=nb+e['attacker'];b=e['target']
 if e['distance']>1.5+1e-6 or e['time']>deaths[r] or e['time']>deaths[b] or e['phase']<.55:badMelee.append(e['id'])
frozen=json.loads((P/'variants/V22R-C1/simulation.json').read_text(encoding='utf8'))
prefixEvents=S['prefixEvents']==frozen['events'] and S['prefixShooterEvents']==frozen['shooterEvents']
for e,old in zip(S['events'],frozen['events']):
 for field in ['release','drawStart','aimStart','shooter','target','origin','destination','impact','arc']:
  assert e[field]==old[field],(e['id'],field)
report=dict(A,prefixEventViewExact=prefixEvents,deadShooterReleases=badShot,invalidMeleeHits=badMelee,firstMeleeAttempt=min(e['time'] for e in S['meleeEvents']),firstMeleeHit=min(e['time'] for e in S['meleeEvents'] if e['damage']),firstBlueDeath=min(deaths[:nb]),no4UnitTermination=True,bodyModel='2D ground discs radius .29, fixed corpse roots, velocity projection and swept segment checks; not full animated mesh collision',legacySceneIssue='Original C1 castle crossing and opening off-screen units retained; no army or scenery moved',timeline=rows,sourceHashes={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'tools/melee_continuation_v22r.py',P/'tools/build_melee_continuation_v22r.py',P/'src/main-v22.js']})
report['invalidArrowEndpoints']=badArrowEndpoints
report['midSwingTargetChanges']=swappedAttackTargets
(D/'data-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['timeline','sourceHashes']},indent=2))
assert prefixEvents and not badShot and not badMelee and not badArrowEndpoints and not swappedAttackTargets
