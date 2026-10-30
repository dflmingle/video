"""Native transforms, unchanged ground/materials, moved collision footprints."""
from pathlib import Path
import json,hashlib,numpy as np,sys
from measure_depth_v22r import project,vertices,M,normal
from scene_occupancy_v22r import load_obstacles
P=Path(__file__).resolve().parents[1];group=sys.argv[sys.argv.index('--group')+1] if '--group' in sys.argv else 'depth';D=P/('docs/v22r-'+group);setup=json.loads((D/'setup.json').read_text());runtime=json.loads((D/'environment-runtime.json').read_text());original=load_obstacles();rows=[]
regression=json.loads((D/'D2-environment-regression.json').read_text())
for o,r in zip(M['objects'],regression['objects']):
 expected=np.diag([1,1,-1,1])@np.array(o['matrix']).reshape(4,4,order='F')
 assert np.allclose(np.array(r['matrixWorld']).reshape(4,4,order='F'),expected,atol=1e-9,rtol=0)
for case,run in zip(setup['candidates'],runtime):
 shift=np.array(case['sceneLayout']['previewTranslation']);paths=case['sceneLayout']['objectPaths'];errors=[];changed=[];screen=[]
 for o,r in zip(M['objects'],run['objects']):
  expected=np.array(o['matrix']).reshape(4,4,order='F');reflection=np.diag([1,1,-1,1]);expected=reflection@expected
  if o['path'] in paths:expected[:3,3]+=shift;changed.append(o['path'])
  actual=np.array(r['matrixWorld']).reshape(4,4,order='F')
  if not np.allclose(actual,expected,atol=1e-9,rtol=0):errors.append(o['path'])
  assert r['scale']==[1,1,1] and r['materials']==[M['materials'][i]['name'] for i in o['materials']]
  if '/Building/' in o['path'] or '/CastleExterior_Building/' in o['path']:
   pix=project(vertices(o)+shift);screen.append(dict(path=o['path'],minPixelY=float(pix[:,1].min()),maxPixelY=float(pix[:,1].max()),vertexFractionWithinFrame=float(np.mean((pix[:,0]>=0)&(pix[:,0]<=720)&(pix[:,1]>=0)&(pix[:,1]<=1080)))))
 moved=load_obstacles(case['sceneLayout']);assert len(moved)==len(original)
 for a,b in zip(original,moved):
  owner=a['path'].split('#')[0];offset=shift[[0,2]] if owner in paths else np.zeros(2)
  assert np.allclose(b['vertices']-a['vertices'],offset,atol=1e-9)
 obstacles=[dict(path=o['path'],vertices=o['vertices'].tolist(),equations=o['equations'].tolist()) for o in moved]
 (D/(case['label']+'-obstacle-footprints.json')).write_text(json.dumps(obstacles,separators=(',',':')),encoding='utf8')
 central=[s for s in screen if s['path'].endswith('/polySurface18')]
 assert not errors and len(changed)==6 and min(s['minPixelY'] for s in (central if setup.get('peripheralTowerTopCroppingAllowed') else screen))>=8
 override=case['sceneLayout'].get('groundTextureOverride')
 for b in run.get('textureBindings',[]):
  if override and b['material']=='CastleExterior_Land_Mat':assert b['texture']==override
  elif 'originalTexture' in b:assert b['texture']==b['originalTexture']
 rows.append(dict(label=case['label'],all34RuntimeMatricesCorrect=not errors,movedObjects=changed,staticGroundTreesIndependentFencesUnchanged=True,materialsUnchanged=not bool(override),materialNamesUnchanged=True,onlyGroundTextureOverridden=bool(override),groundTextureOverride=override,modelScaleUnchanged=True,oldD2SceneRegressionUnchanged=True,collisionFootprints=len(moved),camera=run['camera'],buildingScreenBounds=screen,originalSceneManifestSHA256=hashlib.sha256((P/'public/native-scenes/CastleExterior-scene/manifest.json').read_bytes()).hexdigest()))
(D/'environment-checks.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps([dict(label=r['label'],allMatricesCorrect=r['all34RuntimeMatricesCorrect'],minCastlePixelY=min(s['minPixelY'] for s in r['buildingScreenBounds']),obstacles=r['collisionFootprints']) for r in rows],indent=2))
