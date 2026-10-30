"""D1/D2: only rigid whole-army translations over the current frontfield."""
from pathlib import Path
import copy,hashlib,json
import numpy as np
from scene_occupancy_v22r import load_obstacles,signed_clearance
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-distance';D.mkdir(exist_ok=True)
source=P/'variants/V22R-frontfield';S=json.loads((source/'simulation.json').read_text(encoding='utf8'))
pos=np.load(source/'trajectories.npy')[0].astype(float);nb=S['blueCount'];radius=S['config']['bodyRadius']
normal=np.array(json.loads((P/'docs/v22r-frontfield/audit.json').read_text(encoding='utf8'))['wallNormalTowardCamera'])
gap=float((pos[:nb]@normal).min()-(pos[nb:]@normal).max()-2*radius)
obstacles=load_obstacles();results=[]
protected=['src/main-v22.js','src/assets-v22.js','src/castle-approved-v22r.js','src/environment-native-v22.js','tools/build_simulation_v22.py','tools/build_melee_continuation_v22r.py','tools/melee_continuation_v22r.py','tools/archers_v22.py','tools/archers_burst_v22r.py','public/native-scenes/CastleExterior-scene/manifest.json']
for label,ratio in [('D1',.1),('D2',.2)]:
 # D1 keeps the blue opening roots unchanged, retaining more lower-frame
 # margin. The first balanced D1 trial is preserved separately: its original
 # melee/corpse rules stalled with two blue survivors. No rules are patched.
 extra=gap*ratio;redShare=1. if label=='D1' else .5
 redMove=-normal*extra*redShare;blueMove=normal*extra*(1-redShare)
 moved=pos.copy();moved[:nb]+=blueMove;moved[nb:]+=redMove
 collisions=[]
 for o in obstacles:
  clearance=signed_clearance(moved,o)
  for j in np.flatnonzero(clearance<radius+.1):collisions.append(dict(member=S['units'][int(j)]['id'],path=o['path'],clearance=float(clearance[j])))
 C=copy.deepcopy(S['config']);C.update(duration=0.,checkpointFrame=0,autoCut=False)
 C['blueArmyTranslation']=(np.array(C.get('blueArmyTranslation',[0.,0.]))+blueMove).tolist()
 C['redArmyTranslations']={color:(np.array(C.get('redArmyTranslations',{}).get(color,[0.,0.]))+redMove).tolist() for color in ['red','orange','yellow']}
 name='V22R-distance-'+label;seed=P/'variants'/(name+'-seed');seed.mkdir(exist_ok=True)
 (seed/'params.json').write_text(json.dumps(C,indent=2),encoding='utf8')
 actual=float((moved[:nb]@normal).min()-(moved[nb:]@normal).max()-2*radius)
 results.append(dict(label=label,variant=name,seed=name+'-seed',definition='Projected opposing front root bounds along actual camera-facing wall normal, minus two body radii',normal=normal.tolist(),baselineFrontNetGap=gap,targetIncreaseRatio=ratio,actualFrontNetGap=actual,actualIncrease=actual-gap,actualIncreaseRatio=actual/gap-1,redRigidTranslation=redMove.tolist(),blueRigidTranslation=blueMove.tolist(),spawnObstacleViolations=collisions))
 assert not collisions
report=dict(baseline='V22R-frontfield',baselineCommit='c7f0e43',candidates=results,protectedSourceHashes={name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in protected})
(D/'setup.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(results,indent=2))
