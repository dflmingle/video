from pathlib import Path
import json,hashlib,cv2,numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((D/'params.json').read_text());S=json.loads((D/'simulation.json').read_text());r=json.loads((D/'render-checks.json').read_text());N=round(c['duration']*c['fps']);assert c['previewOnly'] and c['disableCombat'];assert not S['events'] and all(u['deathTime'] is None for u in S['units'][S['blueCount']:]);assert len(r['states'])==N
for path,digest in r['inputs'].items():assert h(P/path)==digest,('Stale capture',path)
assert not r['errors'] and all(x['identical'] for x in r['seeks'])
for field in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert all(x[field]==r['states'][0][field] for x in r['states'])
assert all(x['arrows']==0 and x['nocked']==0 and x['impactParticles']==0 and x['aliveRed']==972 for x in r['states'])
for path,digest in json.loads((P/'baseline/protected-v9.json').read_text()).items():assert h(Path(path))==digest
validation=json.loads((O/'charge-motion-validation.json').read_text());assert validation['initialIDsAndCoordinatesExact'] and validation['continuousFactionSurfaceLowerBound']>=4 and validation['minimumBodyDistance']>=.58
media=json.loads((O/'preview-evidence-media.json').read_text())
for m in media:
 assert h(O/m['path'])==m['sha256'];cap=cv2.VideoCapture(str(O/m['path']));n=0
 while cap.read()[0]:n+=1
 cap.release();assert n==m['frames']
audit=json.loads((D/'asset-render-audit.json').read_text());manifest=json.loads((P/'assets/runtime/manifest.json').read_text())
for k,m in manifest.items():assert h(P/f'assets/runtime/{k}.fbx')==m['sourceSHA256'] and h(P/f'assets/runtime/{k}.png')==m['textureSHA256']
assert len(audit['requests'])>=8 and all(x['status']==200 for x in audit['requests'])
(O/'ASSET-PROVENANCE.json').write_text(json.dumps(dict(source=manifest,loaded=audit['requests'],notes='Original FBX meshes, textures, skeleton lengths and weapon attachments; analytical running pose built on idle skeleton. No tracing, no substitute geometry.'),indent=2))
result=dict(engineeringStatus='PASS',visualApproval='Pending user review; not inferred from metrics',fixedCameraAllFrames=True,arrows=0,casualties=0,media=media,inputs={str(p.relative_to(P)):h(p) for p in [*P.glob('src/*-v10.js'),*P.glob('tools/*v10*'),D/'params.json',D/'simulation.json',D/'trajectories.f32',D/'gait-distance.f32'] if p.is_file()})
(O/'preview-delivery-manifest.json').write_text(json.dumps(result,indent=2));print('Preview only: current encoded media, no arrows/deaths, fixed camera, initial members, sources and unchanged V9: PASS')
