"""E1/E2/E3: native building rigid placement and whole-army translations only."""
from pathlib import Path
import json,copy,hashlib,numpy as np
from measure_depth_v22r import normal,project,vertices,M
from scene_occupancy_v22r import load_obstacles,signed_clearance
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-depth';D.mkdir(exist_ok=True)
S=json.loads((P/'variants/V22R-frontfield/simulation.json').read_text());pos=np.load(P/'variants/V22R-frontfield/trajectories.npy')[0].astype(float);nb=S['blueCount'];radius=S['config']['bodyRadius']
gap=float((pos[:nb]@normal).min()-(pos[nb:]@normal).max()-2*radius)
buildings=[o for o in M['objects'] if '/CastleExterior_Building/' in o['path']]
boundStakes=[o for o in M['objects'] if 'Stakes' in o['path'] and o['boundsCenter']['z']>27]
paths=[o['path'] for o in buildings+boundStakes]
def layout(shift):return dict(objectPaths=paths,previewTranslation=[float(-normal[0]*shift),0.,float(-normal[1]*shift)],castleBackDistance=shift,source='Unity CastleExterior original meshes; same rigid delta for building and four immediately adjoining stakes')
castleMax=0.
for shift in np.arange(0,10,.01):
 top=min(project(vertices(o)+[-normal[0]*shift,0,-normal[1]*shift])[:,1].min() for o in buildings)
 if top>=8:castleMax=float(shift)
def fits(red,blue,castle):
 moved=pos.copy();moved[nb:]-=normal*red;moved[:nb]+=normal*blue
 # Conservative full-character envelope, including feet/shadow and head.
 xyz=np.zeros((len(pos),3));xyz[:,0]=moved[:,0];xyz[:,2]=moved[:,1]
 corners=np.concatenate([xyz+[dx,h,dz] for dx in [-.45,.45] for dz in [-.45,.45] for h in [0,1.8]])
 px=project(corners)
 if px[:,0].min()<8 or px[:,0].max()>712 or px[:,1].min()<8 or px[:,1].max()>1072:return False
 return all(np.min(signed_clearance(moved,o))>=radius+.1 for o in load_obstacles(layout(castle)))
# Cache footprints once for the search rather than reparsing native geometry.
obs=load_obstacles(layout(castleMax))
def quickfits(red,blue):
 moved=pos.copy();moved[nb:]-=normal*red;moved[:nb]+=normal*blue
 xyz=np.zeros((len(pos),3));xyz[:,0]=moved[:,0];xyz[:,2]=moved[:,1]
 corners=np.concatenate([xyz+[dx,h,dz] for dx in [-.45,.45] for dz in [-.45,.45] for h in [0,1.8]])
 px=project(corners)
 return px[:,0].min()>=8 and px[:,0].max()<=712 and px[:,1].min()>=8 and px[:,1].max()<=1072 and all(np.min(signed_clearance(moved,o))>=radius+.1 for o in obs)
redMax=max(x for x in np.arange(0,12,.025) if quickfits(x,0));blueMax=max(x for x in np.arange(0,4,.025) if quickfits(0,x))
assert quickfits(redMax,blueMax)
results=[]
for label,red,blue,castle in [('E1',gap*.5,0.,3.),('E2',gap,0.,castleMax),('E3',float(redMax),float(blueMax),castleMax)]:
 assert fits(red,blue,castle),(label,red,blue,castle)
 c=copy.deepcopy(S['config']);c.update(duration=0.,checkpointFrame=0,autoCut=False,sceneLayout=layout(castle))
 c['blueArmyTranslation']=(np.array(c.get('blueArmyTranslation',[0.,0.]))+normal*blue).tolist()
 c['redArmyTranslations']={color:(np.array(c.get('redArmyTranslations',{}).get(color,[0.,0.]))-normal*red).tolist() for color in ['red','orange','yellow']}
 name='V22R-depth-'+label;seed=P/'variants'/(name+'-seed');seed.mkdir(exist_ok=True)
 (seed/'params.json').write_text(json.dumps(c,indent=2),encoding='utf8')
 results.append(dict(label=label,variant=name,seed=name+'-seed',baselineFrontNetGap=gap,actualFrontNetGap=gap+red+blue,actualIncreaseRatio=(red+blue)/gap,redRigidTranslation=(-normal*red).tolist(),blueRigidTranslation=(normal*blue).tolist(),castleBackDistance=castle,sceneLayout=layout(castle)))
protected=['src/main-v22.js','src/assets-v22.js','src/camera-v22.js','src/castle-approved-v22r.js','src/archer-pose-v22.js','tools/motion_v22.py','tools/combat_response_v22.py','tools/build_simulation_v22.py','tools/build_melee_continuation_v22r.py','tools/melee_continuation_v22r.py','tools/archers_v22.py','tools/archers_burst_v22r.py','public/native-scenes/CastleExterior-scene/manifest.json']
report=dict(baseline='V22R-frontfield',baselineCommit='a64a654',normal=normal.tolist(),maximumCastleTranslation=castleMax,searchStep=.025,castleStep=.01,screenMarginPixels=8,fullActorEnvelope=dict(radius=.45,height=1.8),buildingOriginalSideCroppingRetained=True,candidates=results,protectedSourceHashes={p:hashlib.sha256((P/p).read_bytes()).hexdigest() for p in protected})
(D/'setup.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k not in ['protectedSourceHashes']},indent=2))
