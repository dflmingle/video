from pathlib import Path
import json,hashlib,numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V13/variants/FINAL'
R=json.loads((D/'render-checks.json').read_text());T=json.loads((D/'behavior-tracks.json').read_text());S=json.loads((D/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy')
assert len(R['states'])==180 and len(T['frames'])==180 and len(T['indices'])==36
assert not R['errors'] and all(s['identical'] for s in R['seeks'])
for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h,p
old=json.loads((B/'render-checks.json').read_text())
for k,s in enumerate(R['states'][:len(old['states'])]):
 for key in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert s[key]==old['states'][k][key],key
ids=json.loads((O/'tracked-v14.json').read_text())['indices'];assert len(ids)==20 and len({U[i]['platoon'] for i in ids})==1
seen=[]
for f,frame in enumerate(T['frames']):
 red=[a for a in frame if a['index']>=nb];assert len(red)==20
 for a in red:
  j=a['index']-nb
  assert abs(a['stride']-K[f,j,3])<1e-4 and abs(a['cadence']-K[f,j,4])<1e-4
  if a['action']=='move':
   expected=((float(Y[f,a['index']])+U[a['index']]['phase'])%1)*32
   assert abs(a['phaseFloat']-expected)<.001,(f,a['id'])
 seen.append(len({(a['action'],a['phase']) for a in red}))
manifest=json.loads((P/'assets/runtime/manifest.json').read_text());audit=json.loads((D/'asset-render-audit.json').read_text())
for key,m in manifest.items():
 for ext,tag in [('fbx','sourceSHA256'),('png','textureSHA256')]:assert hashlib.sha256((P/f'assets/runtime/{key}.{ext}').read_bytes()).hexdigest()==m[tag]
 assert any(f'/{key}.fbx' in q['url'] and q['status']==200 for q in audit['requests'])
for p,h in json.loads((O/'protected-v13.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
out=dict(status='PASS',renderInputsMatch=True,browserAndShaderErrors=R['errors'],deterministicSeeks=R['seeks'],cameraMatchesV13EveryCommonFrame=True,specifiedAssetHashesMatch=True,rendererUsesIntegratedDynamicCycles=True,rendererUsesDynamicStrideCadence=True,red20DistinctActionPhaseRange=[min(seen),max(seen)],sources={k:v['source'] for k,v in manifest.items()},protectedV13=True)
(O/'V14-render-validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
