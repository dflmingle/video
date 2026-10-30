from pathlib import Path
import json,hashlib,numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output'
R=json.loads((D/'render-checks.json').read_text());C=json.loads((D/'params.json').read_text());S=json.loads((D/'simulation.json').read_text());audit=json.loads((D/'asset-render-audit.json').read_text())
assert not R['errors'] and all(x['identical'] for x in R['seeks'])
for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h,p
assert len(R['states'])==round(C['duration']*60)
z=np.array([s['cameraZoom'] for s in R['states']]);pos=np.array([s['cameraPosition'] for s in R['states']]);quats=np.array([s['cameraQuaternion'] for s in R['states']])
assert np.max(np.abs(np.diff(z)))<.008 and np.max(np.linalg.norm(np.diff(pos,axis=0),axis=1))<.04
assert np.max(np.linalg.norm(np.diff(quats,axis=0),axis=1))<1e-6
for p,h in json.loads((O/'protected-v12.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
manifest=json.loads((P/'assets/runtime/manifest.json').read_text())
for key,m in manifest.items():
 for ext,tag in [('fbx','sourceSHA256'),('png','textureSHA256')]:assert hashlib.sha256((P/f'assets/runtime/{key}.{ext}').read_bytes()).hexdigest()==m[tag]
 assert any(f'/{key}.fbx' in q['url'] and q['status']==200 for q in audit['requests'])
T=json.loads((D/'behavior-tracks.json').read_text());assert len(T['frames'])==len(R['states']) and len(T['indices'])==32
U=S['units'];red=[i for i in T['indices'] if i>=S['blueCount']];blue=[i for i in T['indices'] if i<S['blueCount']];assert len(red)==len(blue)==16
assert len({U[i]['platoon'] for i in red})==1 and len({U[i]['group'] for i in blue})==1
detail={}
for label,ids in [('red',red),('blue',blue)]:
 selected=[[(k/60),[v for v in frame if v['index'] in ids]] for k,frame in enumerate(T['frames'])]
 distinct=[len({(v['action'],v['phase']) for v in a}) for t,a in selected]
 detail[label]=dict(sameSquad=True,members=[U[i]['id'] for i in ids],distinctPoseRange=[min(distinct),max(distinct)],allSamePoseFrameCount=sum(n==1 for n in distinct),independentStartTimes=len({U[i]['delay'] for i in ids}),independentAnimationPhases=len({U[i]['phase'] for i in ids}))
 assert detail[label]['independentStartTimes']>=6 and detail[label]['independentAnimationPhases']==16
 assert min(distinct)>1
Rout=dict(status='PASS',renderInputHashesMatch=True,deterministicSeeks=R['seeks'],browserErrors=R['errors'],specifiedAssetsSHA256Match=True,sources={k:v['source'] for k,v in manifest.items()},camera=dict(continuous=True,initialZoom=float(z[0]),finalZoom=float(z[-1]),maxFrameZoomStep=float(np.max(np.abs(np.diff(z)))),maxFramePositionStep=float(np.max(np.linalg.norm(np.diff(pos,axis=0),axis=1))),angleConstant=True,slowInitialFramingSeconds=1.45,scope='Continuous small lens advance only; no cuts or diagnostic overlays in main video.'),individualMainRender=detail,protectedV12=True)
(O/'V13-render-asset-validation.json').write_text(json.dumps(Rout,indent=2));print(json.dumps(Rout,indent=2))
