from pathlib import Path
import json,hashlib,numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output'
R=json.loads((D/'render-checks.json').read_text());C=json.loads((D/'params.json').read_text());audit=json.loads((D/'asset-render-audit.json').read_text());S=json.loads((D/'simulation.json').read_text());A=np.load(D/'trajectories.npy');nb=S['blueCount']
assert not R['errors'] and all(x['identical'] for x in R['seeks'])
for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h,p
assert len(R['states'])==round(C['duration']*C['fps'])
for k in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert all(s[k]==R['states'][0][k] for s in R['states'])
for p,h in json.loads((O/'protected-v11.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
manifest=json.loads((P/'assets/runtime/manifest.json').read_text())
for key,m in manifest.items():
 for ext,tag in [('fbx','sourceSHA256'),('png','textureSHA256')]:assert hashlib.sha256((P/f'assets/runtime/{key}.{ext}').read_bytes()).hexdigest()==m[tag]
 assert any(f'/{key}.fbx' in q['url'] and q['status']==200 for q in audit['requests'])
# Native skeleton lengths and reach diagnostics, plus planted-foot travel along Z.
footAudit={}
for key in ['flail','sword','samurai']:
 rows=audit['models'][key]['actionAnatomy']['move'];ground=[];errors=[]
 for r in rows:
  errors.extend(d['reachError'] for d in r['legDiagnostics'])
 for side,offset,name in [('L',0,'leftFoot'),('R',.5,'rightFoot')]:
  samples=[]
  for j,r in enumerate(rows):
   d=next(v for v in r['legDiagnostics'] if v['side']==side)
   if d['stance']:
    y,z=r[name][1:];worldZ=np.sin(C['runLean'])*y+np.cos(C['runLean'])*z
    samples.append((d['phase'],worldZ))
  samples.sort()
  for (qa,za),(qb,zb) in zip(samples,samples[1:]):ground.append(abs(zb-za+C['runStride']*(qb-qa)))
 footAudit[key]=dict(maxIKReachError=max(errors),maxStanceForwardResidual=max(ground,default=0),sampledAt32Poses=True,limitation='Local planted-foot forward residual, not a claim of zero perceptual sliding at all transitions or full 3D surface contact.')
report=dict(renderInputHashesMatch=True,frameCount=len(R['states']),fixedCamera=True,deterministicSeeks=R['seeks'],browserErrors=R['errors'],specifiedAssetFilesSHA256Match=True,assetSources={k:v['source'] for k,v in manifest.items()},footAudit=footAudit,
 renderCaptureMedianMs=float(np.median(R['frameCaptureMs'])),renderCaptureMaxMs=max(R['frameCaptureMs']),v11Protected=True)
(O/'V12-render-asset-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
