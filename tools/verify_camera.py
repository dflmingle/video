from pathlib import Path
import json,hashlib,math,numpy as np
from scipy.spatial.transform import Rotation
P=Path(__file__).resolve().parents[1];O=P/'output/camera-revision';D=P/'variants/FINAL';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();C=json.loads((D/'params.json').read_text());S=json.loads((D/'simulation.json').read_text());A=np.load(D/'trajectories.npy');base=json.loads((D/'render-checks.json').read_text());allowed={'cameraPosition','cameraTarget','cameraZoom','cameraShiftX','cameraShiftY','cameraTravelZ'}
for path,digest in json.loads((O/'protected-baseline.json').read_text()).items():assert h(P/path)==digest,('Baseline changed',path)
def project(xyz,state):
 rot=Rotation.from_quat(state['cameraQuaternion']).as_matrix();projection=np.array(state['cameraProjection']).reshape(4,4,order='F');q=(np.array(xyz)-state['cameraPosition'])@rot;ndc=projection@np.r_[q,1];ndc=ndc[:3]/ndc[3];return np.array([(ndc[0]+1)*C['width']/2,(1-ndc[1])*C['height']/2])
result=[]
for key in ['A','B']:
 d=P/f'variants/CAMERA-{key}';c=json.loads((d/'params.json').read_text());diff={k for k in set(c)|set(C) if c.get(k)!=C.get(k)};assert diff<=allowed
 for f in ['simulation.json','trajectories.f32','hit-times.f32','gait-distance.f32','member-states.npy','hit-responses.json']:assert h(d/f)==h(D/f)
 r=json.loads((d/'render-checks.json').read_text());assert len(r['states'])==252 and not r['errors'] and all(x['identical'] for x in r['seeks'])
 for f,digest in r['inputs'].items():assert h(P/f)==digest,('Stale input',f)
 for field in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert all(x[field]==r['states'][0][field] for x in r['states'])
 for i,state in enumerate(r['states']):
  for field in ['arrows','nocked','impactParticles','aliveRed']:assert state[field]==base['states'][i][field],(i,field)
 st=r['states'][0];v=np.array(c['cameraPosition'])-c['cameraTarget'];elevation=math.degrees(math.atan2(v[1],np.linalg.norm(v[[0,2]])));assert elevation>60
 measures=[]
 for t in [0,1.3,2.8,3.8]:
  f=round(t*60);sizes=[];oldSizes=[];visible=0;armyVisible={}
  for i,u in enumerate(S['units']):
   q=A[f,i];pt=project([q[0],.7,q[1]],st);isVisible=0<=pt[0]<C['width'] and 0<=pt[1]<C['height'];visible+=isVisible
   if i>=S['blueCount']:armyVisible[str(u['army'])]=armyVisible.get(str(u['army']),0)+int(isVisible)
   if isVisible:
    sizes.append(float(np.linalg.norm(project([q[0]+1,.7,q[1]],st)-pt)));bs=base['states'][0];oldSizes.append(float(np.linalg.norm(project([q[0]+1,.7,q[1]],bs)-project([q[0],.7,q[1]],bs))))
  measures.append(dict(time=t,visibleCenters=int(visible),redVisible=armyVisible,projectedOneWorldUnitMedian=float(np.median(sizes)),magnificationMedian=float(np.median(np.array(sizes)/oldSizes))))
 result.append(dict(camera=key,status='PASS',elevation=elevation,onlyCameraChanged=True,identicalCombatAllFrames=True,fixedCameraAllFrames=True,screenMeasures=measures))
for item in json.loads((O/'media-validation.json').read_text()):assert h(O/item['path'])==item['sha256']
R=dict(status='PASS',cameras=result,scope='Camera-only inputs and exact battle/animation counts. Body occupancy, faction clearance and event causality inherit unchanged validated world trajectories. Visibility counts do not prove mood.')
(O/'camera-validation.json').write_text(json.dumps(R,indent=2));print(json.dumps(R,indent=2))
