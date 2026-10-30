"""Actual mesh footprints, spawn transforms, causal events and unchanged rules."""
from pathlib import Path
import json,numpy as np,hashlib,csv
from scipy.spatial import cKDTree
from scene_occupancy_v22r import load_obstacles,signed_clearance
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-frontfield';O=P/'output/v22r-frontfield';O.mkdir(exist_ok=True)
V=P/'variants/V22R-frontfield';old=P/'variants/V22R-C1-melee'
S=json.loads((V/'simulation.json').read_text(encoding='utf8'));B=json.loads((old/'simulation.json').read_text(encoding='utf8'))
C=S['config'];pos=np.load(V/'trajectories.npy');n=len(S['units']);nb=S['blueCount'];dt=1/60
obstacles=load_obstacles();walls=[o for o in obstacles if 'polySurface18' in o['path']]
vertices=np.vstack([o['vertices'] for o in walls]);center=vertices.mean(0)
_,_,axes=np.linalg.svd(vertices-center,full_matrices=False);along=axes[0];normal=np.array([-along[1],along[0]])
if normal@(np.array([0.,65.])-center)<0:normal=-normal
wallFront=float((vertices@normal).max());signed=pos@normal-wallFront
spawnViolations=[];pathViolations=[];segmentViolations=[]
for obstacle in obstacles:
 value=signed_clearance(pos.reshape(-1,2),obstacle).reshape(len(pos),n)
 ids=np.argwhere(value<.29)
 if len(ids):pathViolations.append(dict(path=obstacle['path'],count=len(ids),firstFrame=int(ids[0,0]),member=S['units'][int(ids[0,1])]['id'],worst=float(value.min())))
 for j in np.flatnonzero(value[0]<.29):spawnViolations.append(dict(member=S['units'][j]['id'],path=obstacle['path']))
 # Sweep against the same convex mesh footprint expanded by the body radius.
 eq=obstacle['equations'];a=pos[:-1].reshape(-1,2);d=(pos[1:]-pos[:-1]).reshape(-1,2)
 side=a@eq[:,:2].T+eq[:,2]-.29;rate=d@eq[:,:2].T
 entering=np.max(np.where(rate< -1e-10,-side/np.where(rate< -1e-10,rate,-1),-np.inf),axis=1)
 leaving=np.min(np.where(rate>1e-10,-side/np.where(rate>1e-10,rate,1),np.inf),axis=1)
 parallelOutside=np.any((np.abs(rate)<1e-10)&(side>0),axis=1)
 crosses=(np.maximum(entering,0)<=np.minimum(leaving,1))&(~parallelOutside)
 if crosses.any():segmentViolations.append(dict(path=obstacle['path'],segments=int(crosses.sum())))
rules=['redSpeed','arrowSpeed','archerRange','redHitPoints','blueAdvance','minHitInterval','deathSeconds','hitStaggerSeconds','hitRecoverySeconds','hitWoundSpeed','hitSeriousSpeed']
unchanged={k:C[k]==B['config'][k] for k in rules}
unitRules=['speed','maxAcceleration','aimSeconds','drawSeconds','recoverSeconds','cycle']
sameMembers={key:all(a.get(key)==b.get(key) for a,b in zip(S['units'],B['units'])) for key in unitRules}
layout=json.loads((D/'layout-operations.json').read_text(encoding='utf8'))
localExact=True
for i,u in enumerate(S['units']):
 before=np.array(B['units'][i]['start']);after=np.array(u['start'])
 offset=layout['blueTranslation'] if i<nb else next(x['translation'] for x in layout['redPlatoons'] if x['platoon']==u['platoon'])
 localExact &= bool(np.allclose(after-before,offset,atol=1e-10,rtol=0))
badArrow=[];badMelee=[];death=np.array([u['deathTime'] if u.get('deathTime') is not None else 1e6 for u in S['units']])
for e in S['events']:
 if e.get('damage',0) and np.linalg.norm(pos[e['impactFrame'],e['target']]-np.array(e['destination'])[::2])>.68001:badArrow.append(e['id'])
 if e['release']>=death[e['shooter']]-1e-8:badArrow.append(e['id']+' DEAD_SHOOTER')
for e in S['meleeEvents']:
 if e['damage'] and (e['distance']>1.5 or e['phase']<.55 or e['time']>death[e['attacker']+nb] or e['time']>death[e['target']]):badMelee.append(e['id'])
def timing(s):
 return dict(firstRelease=min(e['release'] for e in s['events']),lastRelease=max(e['release'] for e in s['events']),firstArrowHit=min(e['impact'] for e in s['events'] if e.get('damage',0)),firstMeleeHit=min(e['time'] for e in s['meleeEvents'] if e['damage']),arrows=len(s['events']),arrowHits=sum(bool(e.get('damage')) for e in s['events']))
flash=P/'variants/V22R-hitflash';flashUnchanged={name:hashlib.sha256((flash/name).read_bytes()).hexdigest()==hashlib.sha256((old/name).read_bytes()).hexdigest() for name in ['trajectories.f32','red-control.f32','blue-control.f32','hit-times.f32','blue-hit-times.f32','melee-control.f32','gait-cycles.f32']}
audit=json.loads((V/'continuation-audit.json').read_text(encoding='utf8'))
report=dict(rulesUnchanged=unchanged,memberRulesUnchanged=sameMembers,platoonRigidTranslationsExact=localExact,flashOnlyBinaryDataIdentical=flashUnchanged,wallNormalTowardCamera=normal.tolist(),wallFrontProjection=wallFront,minimumSpawnFrontDistance=float(signed[0].min()),minimumAllFramesFrontDistance=float(signed.min()),spawnObstacleViolations=spawnViolations,bodyFootprintViolations=pathViolations,sweptObstacleViolations=segmentViolations,invalidArrows=badArrow,invalidMeleeHits=badMelee,originalTiming=timing(B),candidateTiming=timing(S),battleResult=audit,visualVerdict='CANDIDATE_ONLY: same-side layout fits but sustained archery/timing materially changed; do not replace accepted battle',formalRender=False)
(D/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
fig,ax=plt.subplots(figsize=(9,11))
for o in obstacles:
 v=o['vertices'];ax.fill(*v.T,color='#606a80' if 'Building' in o['path'] else '#61955b',alpha=.7)
colors={'red':'#d92326','orange':'#f76b09','yellow':'#e9bc20','blue':'#1879e8'}
for color in ['red','orange','yellow','blue']:
 ids=[i for i,u in enumerate(S['units']) if (u['team']=='blue' if color=='blue' else u.get('color')==color)]
 pp=pos[0,ids];ax.scatter(pp[:,0],pp[:,1],s=5,color=colors[color],label=color)
for t in [.5,1.,2.]:
 frame=round(t*60);ax.plot(np.median(pos[:frame+1,nb:,0],axis=1),np.median(pos[:frame+1,nb:,1],axis=1),color='crimson',alpha=.35)
ax.axhspan(20,45,color='#c2b398',alpha=.15,label='engagement area')
ax.annotate('CASTLE / WALL',xy=(0,-34),ha='center',fontsize=12)
ax.annotate('RED CHARGE',xy=(0,10),xytext=(0,-5),ha='center',arrowprops=dict(arrowstyle='->',color='crimson'))
ax.annotate('BLUE ASSEMBLY',xy=(24,29),xytext=(24,39),ha='center',arrowprops=dict(arrowstyle='->',color='royalblue'))
ax.set(xlim=(-34,34),ylim=(50,-42),xlabel='evaluated Unity world X',ylabel='evaluated world Z (camera side increases down)');ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend(loc='upper right');fig.tight_layout();fig.savefig(O/'layout-topdown.png',dpi=160);plt.close(fig)
print(json.dumps({k:v for k,v in report.items() if k not in ['battleResult','memberRulesUnchanged','flashOnlyBinaryDataIdentical']},indent=2))
assert all(unchanged.values()) and all(sameMembers.values()) and localExact and all(flashUnchanged.values()) and not badArrow and not badMelee and not spawnViolations and not pathViolations and not segmentViolations
