"""Move only platoon centers, preserving each original local formation."""
from pathlib import Path
import json,numpy as np
from scene_occupancy_v22r import load_obstacles,signed_clearance
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-frontfield';D.mkdir(exist_ok=True)
S=json.loads((P/'variants/V22R-C1-melee/simulation.json').read_text(encoding='utf8'))
red=S['units'][S['blueCount']:];blue=S['units'][:S['blueCount']]
cursor=-27.4;trans={};mapping=[];points=[]
for color in ['red','orange','yellow']:
 for row in [2,1,0]:
  members=[u for u in red if u['color']==color and u['squadRow']==row]
  lo=min(u['start'][1] for u in members);hi=max(u['start'][1] for u in members)
  shift=cursor-lo
  for platoon in sorted(set(u['platoon'] for u in members)):
   trans[str(platoon)]=[0.,shift];mapping.append(dict(color=color,platoon=platoon,translation=[0.,shift]))
  points.extend([[u['start'][0],u['start'][1]+shift] for u in members])
  cursor+=hi-lo+.65
 cursor+=.05
blueShift=[0.,3.]
bluePoints=np.array([u['start'] for u in blue])+blueShift
redPoints=np.array([np.array(u['start'])+trans[str(u['platoon'])] for u in red])
obstacles=load_obstacles();allPoints=np.vstack([bluePoints,redPoints]);collisions=[]
for o in obstacles:
 clearance=signed_clearance(allPoints,o)
 for j in np.flatnonzero(clearance<.4):collisions.append(dict(index=int(j),obstacle=o['path'],clearance=float(clearance[j])))
C=dict(S['config']);C.update(duration=0.,checkpointFrame=0,autoCut=False,eventHitFlash=dict(duration=.09,strength=.98),redPlatoonTranslations=trans,blueArmyTranslation=blueShift,freshLayoutContinuation=True)
variant=P/'variants/V22R-frontfield-seed';variant.mkdir(exist_ok=True)
(variant/'params.json').write_text(json.dumps(C,indent=2),encoding='utf8')
evidence=dict(source='V22R-C1-melee',operations='Only per-platoon red rigid translations and one blue rigid translation; no member offsets, no rescale',redPlatoons=mapping,blueTranslation=blueShift,redBounds=[redPoints.min(0).tolist(),redPoints.max(0).tolist()],blueBounds=[bluePoints.min(0).tolist(),bluePoints.max(0).tolist()],wallFrontZ=-30.51,cameraGroundLowerEdgeApproxZ=46.9,spawnObstacleViolations=collisions,originalFullDepth=float(np.ptp(np.array([u['start'] for u in S['units']])[:,1])),newFullDepth=float(np.ptp(allPoints[:,1])))
(D/'layout-operations.json').write_text(json.dumps(evidence,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in evidence.items() if k!='redPlatoons'},indent=2))
assert not collisions
