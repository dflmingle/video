"""Top-edge castle and a deeper opening, with every combat rule untouched."""
from pathlib import Path
import copy,json,hashlib,numpy as np
from measure_depth_v22r import normal,project,vertices,M
from scene_occupancy_v22r import load_obstacles,signed_clearance
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-topfield';D.mkdir(exist_ok=True)
base=P/'variants/V22R-frontfield';S=json.loads((base/'simulation.json').read_text());pos=np.load(base/'trajectories.npy')[0].astype(float);nb=S['blueCount'];radius=S['config']['bodyRadius']
old=json.loads((P/'docs/v22r-depth/setup.json').read_text());layout=copy.deepcopy(old['candidates'][1]['sceneLayout'])
wall=next(o for o in M['objects'] if o['path'].endswith('/polySurface18'));wv=vertices(wall)
# Keep the entire central wall/gate mesh with an 8px top margin. Peripheral
# tall tower roofs may now be cropped, per the latest top-edge composition.
castle=max(float(s) for s in np.arange(0,25,.01) if project(wv+[-normal[0]*s,0,-normal[1]*s])[:,1].min()>=8)
layout.update(previewTranslation=[float(-normal[0]*castle),0.,float(-normal[1]*castle)],castleBackDistance=castle)
layout['groundTextureOverride']='/native-scenes/layout-derived/topfield/CastleExterior_Land_C-shadow-moved.png'
obs=load_obstacles(layout)
def fits(red,blue):
 moved=pos.copy();moved[nb:]-=normal*red;moved[:nb]+=normal*blue
 xyz=np.zeros((len(pos),3));xyz[:,0]=moved[:,0];xyz[:,2]=moved[:,1]
 p=project(np.concatenate([xyz+[dx,h,dz] for dx in [-.45,.45] for dz in [-.45,.45] for h in [0,1.8]]))
 return p[:,0].min()>=8 and p[:,0].max()<=712 and p[:,1].min()>=8 and p[:,1].max()<=1072 and all(signed_clearance(moved,o).min()>=radius+.1 for o in obs)
maxRed=max(float(s) for s in np.arange(0,24,.025) if fits(s,0))
# Leave ground between castle and red rear ranks rather than using the last
# collision-safe centimetre. Keep blue roots unchanged for lower-frame room.
red=max(0.,maxRed-1.5);blue=0.;assert fits(red,blue)
c=copy.deepcopy(S['config']);c.update(duration=0.,checkpointFrame=0,autoCut=False,sceneLayout=layout)
c['redArmyTranslations']={color:(np.array(c.get('redArmyTranslations',{}).get(color,[0.,0.]))-normal*red).tolist() for color in ['red','orange','yellow']}
name='V22R-topfield-T1';seed=P/'variants'/(name+'-seed');seed.mkdir(exist_ok=True);(seed/'params.json').write_text(json.dumps(c,indent=2),encoding='utf8')
gap=float((pos[:nb]@normal).min()-(pos[nb:]@normal).max()-2*radius)
case=dict(label='T1',variant=name,seed=name+'-seed',baselineFrontNetGap=gap,actualFrontNetGap=gap+red,actualIncreaseRatio=red/gap,redRigidTranslation=(-normal*red).tolist(),blueRigidTranslation=[0.,0.],castleBackDistance=castle,sceneLayout=layout)
pixels=project(wv+np.array(layout['previewTranslation']))
report=dict(baseline='V22R-frontfield',baselineCommit='dad41db',normal=normal.tolist(),centralWallTopPixels=float(pixels[:,1].min()),centralWallBottomPixels=float(pixels[:,1].max()),redMaximumMeasured=maxRed,redReservedCastleMargin=1.5,peripheralTowerTopCroppingAllowed=True,candidates=[case],protectedSourceHashes=old['protectedSourceHashes'])
(D/'setup.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='protectedSourceHashes'},indent=2))
