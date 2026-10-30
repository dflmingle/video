from pathlib import Path
import json,hashlib,difflib,csv,math
import numpy as np
from scipy.spatial.transform import Rotation
P=Path(__file__).resolve().parents[1];O=P/'output';D=P/'variants/FINAL';B=P.parent/'PveMontageShot01V16'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
S=read(D/'simulation.json');C=S['config'];U=S['units'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');R=read(O/'captures/FINAL-FIXED/render-checks.json');audit=read(O/'captures/FINAL-FIXED/asset-render-audit.json')
assert not R['errors'] and all(s['identical'] for s in R['seeks']);err=[];initialFull=[];phaseCounts=[];speeds=[]
for f,(s,rows) in enumerate(zip(R['states'],R['frames'])):
 assert s['cameraZoom']==1.5 and s['battleCamera']['center']==[0,-29]
 if f==0:
  rot=Rotation.from_quat(s['cameraQuaternion']).as_matrix();proj=np.array(s['cameraProjection']).reshape(4,4,order='F')
  for u in rows[nb:]:
   points=np.array([[u['x']+dx,y,u['z']+dz] for dx in [-2.9,2.9] for dz in [-2.9,2.9] for y in [0,1.5]])
   v=(points-np.array(s['cameraPosition']))@rot;clip=np.column_stack([v,np.ones(len(v))])@proj.T;n=clip[:,:3]/clip[:,3:];initialFull.append(bool((abs(n[:,:2])<.98).all()))
 for u in rows[nb:]:
  if u['action']=='move':err.append(abs(((u['gaitCycles']+U[u['index']]['phase'])%1)*32-u['phaseFloat']))
 phaseCounts.append(len(set(u['phase'] for u in rows[nb:nb+20])))
 if s['time']>.5:speeds.extend(u['speed'] for u in rows[nb:] if u['state'] not in ['DEAD','STAGGER','WOUNDED'])
assert all(initialFull) and max(err)<1e-6 and min(s['frontVisible'] for s in R['states'])==1
models={}
for name,m in audit['models'].items():
 legs=[l for p in m['actionAnatomy']['move'] for l in p['legDiagnostics']];models[name]=dict(source=m['source'],sourceSHA256=m['sourceSHA256'],horizontalEnvelope=m['horizontalEnvelope'],reachErrorP95=float(np.percentile([l['reachError'] for l in legs],95)) if legs else None)
 assert m['horizontalEnvelope']<=3.1
 for key,hkey in [('file','sourceSHA256'),('texture','textureSHA256')]:
  entry=read(P/'assets/runtime/manifest.json')[name];assert hashlib.sha256((P/entry[key].lstrip('/')).read_bytes()).hexdigest()==entry[hkey]
first=min((e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'),key=lambda e:e['impact']);f=first['impactFrame'];r=R['frames'][f];screenGap=math.hypot(r[first['target']]['screenX']-r[first['shooter']]['screenX'],r[first['target']]['screenY']-r[first['shooter']]['screenY'])
oldS=read(B/'variants/FAST125/simulation.json');oldR=read(B/'output/captures/FAST125-FIXED/render-checks.json');oldFirst=min((e for e in oldS['events'] if e['resolution']=='IMPACT_IN_SHOT'),key=lambda e:e['impact']);orr=oldR['frames'][oldFirst['impactFrame']];oldGap=math.hypot(orr[oldFirst['target']]['screenX']-orr[oldFirst['shooter']]['screenX'],orr[oldFirst['target']]['screenY']-orr[oldFirst['shooter']]['screenY'])
result=dict(initialAll972RedConservativeCornersVisible=True,fixedZoom=1.5,fixedCenter=[0,-29],frontVisibleMin=min(s['frontVisible'] for s in R['states']),blueVisibleStartEnd=[R['states'][0]['blueVisible'],R['states'][-1]['blueVisible']],phaseRenderMaxError=max(err),first20UniquePhaseMin=min(phaseCounts),renderMsP50P95=np.percentile(R['renderMs'],[50,95]).tolist(),healthySpeedP10P50P90=np.percentile(speeds,[10,50,90]).tolist(),frontHeightPixelsMinMax=[min(s['frontHeightPixels'] for s in R['states']),max(s['frontHeightPixels'] for s in R['states'])],V16firstImpactPixelGap=oldGap,V17firstImpactPixelGap=screenGap,models=models,consoleErrors=R['errors'],seekScreenshotsIdentical=True,visualAcceptance='FAIL: fixed full-initial-army scale is smaller; engagement under 1.5s; normal-speed human viewing not completed')
(O/'V17-render-diagnostics.json').write_text(json.dumps(result,indent=2))
# Piecewise comparison time samples use genuine forward direction, never endpoints as path length.
rows=[]
for t in list(np.arange(0,C['duration'],.25))+[C['duration']-1/60]:
 f=round(t*60);f=min(f,len(A)-1);alive=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>t]);hitTargets={e['target'] for e in S['events'] if e['impact']<=t and e['resolution']=='IMPACT_IN_SHOT'};healthy=np.array([i-nb for i in alive if i not in hitTargets]);row=dict(time=t,frontProgress=float(A[f,alive,1].max()-A[0,nb:,1].max()),healthyAverageProgress=float((A[f,nb+healthy,1]-A[0,nb+healthy,1]).mean()),healthyAverageSpeed=float(K[f,healthy,1].mean()),healthyCadence=float(K[f,healthy,4].mean()),pressure=float(np.load(D/'formation-pressure.npy')[f].mean()));rows.append(row)
with (O/'V17-progress.csv').open('w',newline='',encoding='utf-8-sig') as fp:w=csv.DictWriter(fp,rows[0].keys());w.writeheader();w.writerows(rows)
patch=[]
for old,new in [('tools/motion_v16.py','tools/motion_v17.py'),('tools/build_simulation_v16.py','tools/build_simulation_v17.py'),('src/main-camera.js','src/main-camera.js'),('src/assets-v11.js','src/assets-v17.js')]:patch.extend(difflib.unified_diff((B/old).read_text(encoding='utf-8').splitlines(True),(P/new).read_text(encoding='utf-8').splitlines(True),fromfile='V16/'+old,tofile='V17/'+new))
(O/'V16-V17-code.diff').write_text(''.join(patch),encoding='utf-8');print(json.dumps(result,indent=2))
