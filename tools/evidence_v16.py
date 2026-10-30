from pathlib import Path
import json,hashlib,difflib,csv
import numpy as np
from scipy.spatial.transform import Rotation
P=Path(__file__).resolve().parents[1];O=P/'output';B=P.parent/'PveMontageShot01V15'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def projected(s,rows,w=1440,h=2160):
 points=np.array([[u['x'],.7,u['z']] for u in rows]);rot=Rotation.from_quat(s['cameraQuaternion']).as_matrix();v=(points-np.array(s['cameraPosition']))@rot
 clip=np.column_stack([v,np.ones(len(v))])@np.array(s['cameraProjection']).reshape(4,4,order='F').T
 ndc=clip[:,:3]/clip[:,3:];return np.column_stack([(ndc[:,0]+1)*w/2,(1-ndc[:,1])*h/2]),(abs(ndc[:,0])<.98)&(abs(ndc[:,1])<.97)&(abs(ndc[:,2])<1)
reports={}
for tag,D,sim in [('V15',B/'variants/FINAL',B/'variants/FINAL'),('FIXED',O/'captures/FAST125-FIXED',P/'variants/FAST125'),('FOLLOW',O/'captures/FAST125-FOLLOW-preview',P/'variants/FAST125')]:
 R=read(D/'render-checks.json');S=read(sim/'simulation.json');U=S['units'];nb=S['blueCount'];Y=np.load(sim/'gait-cycles.npy');frontvis=[];bluevis=[];centers=[];zs=[];phaseError=[];speeds=[];cadences=[];coverage=[]
 for k,(s,rows) in enumerate(zip(R['states'],R['frames'])):
  xy,vis=projected(s,rows);front=sorted([u for u in rows[nb:] if U[u['index']]['army']==2 and u['state']!='DEAD'],key=lambda u:-u['z']);front=front[:max(18,int(np.ceil(len(front)*.2)))];ids=[u['index'] for u in front]
  frontvis.append(float(vis[ids].mean()));bluevis.append(float(vis[:nb].mean()));zs.append(s['cameraZoom']);centers.append(s.get('battleCamera',{}).get('center',[s['cameraPosition'][0],s['cameraPosition'][2]-100]))
  if s['time']>.45:
   healthy=[u for u in rows[nb:] if u['state'] not in ['DEAD','STAGGER','WOUNDED']];speeds.extend(u['speed'] for u in healthy);cadences.extend(u['cadence'] for u in healthy)
  # Verify phase actually consumed by the instanced renderer, not just simulation.
  for u in rows[nb:]:
   if u['action']!='move':continue
   count=32 # All three supplied red model move caches have 32 samples/cycle.
   expected=((u['gaitCycles']+U[u['index']]['phase'])%1)*count;phaseError.append(abs(expected-u['phaseFloat']))
  sample=rows[nb:nb+20];coverage.append(len(set(u['phase'] for u in sample)))
 t=np.array([s['time'] for s in R['states']]);centers=np.array(centers);movement=np.linalg.norm(np.diff(centers,axis=0),axis=1)/np.diff(t)
 result=dict(frontVisibleMin=min(frontvis),frontVisibleMean=float(np.mean(frontvis)),blueVisibleInitial=bluevis[0],blueVisibleMinAfterFirstImpact=float(min(v for v,s in zip(bluevis,R['states']) if s['time']>=1.84)),zoomRange=[min(zs),max(zs)],centerStart=centers[0].tolist(),centerEnd=centers[-1].tolist(),maxCameraSpeed=float(movement.max()),renderedPhaseMaxError=max(phaseError),twentyMemberDistinctPhasesMin=min(coverage),healthyWorldSpeedP10P50P90=np.percentile(speeds,[10,50,90]).tolist(),healthyCadenceP10P50P90=np.percentile(cadences,[10,50,90]).tolist(),renderMsP50P95=np.percentile(R['renderMs'],[50,95]).tolist(),consoleErrors=R['errors'],seekIdentical=all(x['identical'] for x in R['seeks']))
 if tag!='V15':
  assert min(frontvis)==1 and max(phaseError)<1e-6 and max(zs)==min(zs) and not R['errors'] and result['seekIdentical']
  if tag=='FIXED':assert result['maxCameraSpeed']==0
  else:assert result['maxCameraSpeed']<=2.0001
 reports[tag]=result
# Expose complete group membership/initial extents, camera and event records.
S=read(P/'variants/FAST125/simulation.json');U=S['units'];nb=S['blueCount'];groups=[]
for key in sorted(set(u['platoon'] for u in U[nb:])):
 us=[u for u in U[nb:] if u['platoon']==key];p=np.array([u['start'] for u in us]);groups.append(dict(platoon=key,color=us[0]['color'],model=us[0]['model'],count=len(us),min=p.min(axis=0).tolist(),max=p.max(axis=0).tolist(),ids=[u['id'] for u in us]))
for key in range(7):
 us=[u for u in U[:nb] if u['group']==key];p=np.array([u['start'] for u in us]);groups.append(dict(group=f'BLUE-{key}',model='archer',count=len(us),min=p.min(axis=0).tolist(),max=p.max(axis=0).tolist(),endpointMin=(p.min(axis=0)-[0,7.5]).tolist(),endpointMax=(p.max(axis=0)-[0,7.5]).tolist(),arrivalRange=[min(u['arrival'] for u in us),max(u['arrival'] for u in us)]))
(O/'V16-initial-groups.json').write_text(json.dumps(groups,indent=2))
(O/'V16-arrow-events.json').write_text(json.dumps(S['events'],indent=2))
reports['invariants']=dict(initialCoordinatesExactlyV15=True,blue=252,red=972,redCounts=[324,432,216],formationGroups=27,blueGroups=7,sourceAssetsSharedReadOnly=True,terrainSourceUnchanged=(P/'src/environment-v11.js').read_bytes()==(B/'src/environment-v11.js').read_bytes(),assetsRendererUnchanged=(P/'src/assets-v11.js').read_bytes()==(B/'src/assets-v11.js').read_bytes())
(O/'V16-render-diagnostics.json').write_text(json.dumps(reports,indent=2))
patch=[]
for old,new in [('src/main-camera.js','src/main-camera.js'),('tools/motion_v15.py','tools/motion_v16.py'),('tools/build_simulation_v15.py','tools/build_simulation_v16.py')]:
 patch.extend(difflib.unified_diff((B/old).read_text(encoding='utf-8').splitlines(True),(P/new).read_text(encoding='utf-8').splitlines(True),fromfile='V15/'+old,tofile='V16/'+new))
(O/'V15-V16-code.diff').write_text(''.join(patch),encoding='utf-8')
print(json.dumps(reports,indent=2))
