from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';C=json.loads((D/'params.json').read_text());S=json.loads((D/'simulation.json').read_text());R=json.loads((D/'render-checks.json').read_text());h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,digest in R['inputs'].items():assert h(P/path)==digest,('Stale render',path)
assert len(R['states'])==round(C['duration']*C['fps']) and not R['errors'] and all(x['identical'] for x in R['seeks'])
for field in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert all(x[field]==R['states'][0][field] for x in R['states'])
assert max(x['arrows'] for x in R['states'])>100 and max(x['nocked'] for x in R['states'])>0 and max(x['impactParticles'] for x in R['states'])>0
assert R['states'][0]['aliveRed']==972 and R['states'][-1]['aliveRed']<972
audit=json.loads((D/'asset-render-audit.json').read_text());assert not audit['errors'] and len(audit['requests'])>=8 and all(x['status']==200 for x in audit['requests'])
for e in S['events']:assert e['originMapping'].startswith('sampled native'),e['id']
m=json.loads((P/'assets/runtime/manifest.json').read_text());(O/'ASSET-PROVENANCE.json').write_text(json.dumps(dict(manifest=m,actualLoads=audit['requests'],notes='Original FBX, original textures and weapon attachments; team tint and analytically adapted red run. No traced or replacement geometry.'),indent=2))
media=json.loads((O/'V11-media-validation.json').read_text());assert media[0]['frames']==round(C['duration']*C['fps']) and media[0]['width']==C['width'] and media[0]['height']==C['height'] and media[0]['fps']==C['fps']
for item in media:assert h(O/item['path'])==item['sha256']
result=dict(status='PASS',scope='Current render inputs, fixed camera, actual full-combat render counts, deterministic seek, loaded source assets, encoded media hashes. Artistic charge quality is separate.',media=media,inputs=R['inputs'],assetLoads=len(audit['requests']))
(O/'V11-render-validation.json').write_text(json.dumps(result,indent=2));print('V11 current sources, fixed overhead shot, combat visible render pipeline, seek determinism and encoded media: PASS')
