from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1];O=P/'output'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assets=json.loads((P/'assets/runtime/manifest.json').read_text(encoding='utf-8'));aud=[]
for name,v in assets.items():
 model=P/v['file'].lstrip('/');tex=P/v['texture'].lstrip('/');assert h(model)==v['sourceSHA256'];assert h(tex)==v['textureSHA256'];aud.append(dict(name=name,source=v['source'],runtime=str(model),sha256=h(model),originalHashMatches=True))
(O/'V16-assets-source-verification.json').write_text(json.dumps(aud,indent=2))
for path,expected in json.loads((O/'protected-v15.json').read_text()).items():assert h(Path(path))==expected
tags=['FAST125-FIXED','BASE100-FIXED','FAST125-FIXED-preview','FAST125-FOLLOW-preview','BASE100-FIXED-preview','FAST150-FIXED-preview']
for tag in tags:
 R=json.loads((O/f'captures/{tag}/render-checks.json').read_text())
 for file,expected in R['inputs'].items():assert h(P/file)==expected,(tag,file)
files=[P/'V16-REVIEW.md',P/'RENDER-V16.md',*P.glob('src/*'),P/'tools/motion_v16.py',P/'tools/build_simulation_v16.py',P/'tools/test_v16.py',P/'tools/capture_v16.mjs',P/'tools/media_v16.py',P/'tools/evidence_v16.py',P/'tools/finalize_v16.py',P/'tools/smoke_v16.mjs',P/'tools/manifest_v16.py',*O.glob('*.mp4'),*O.glob('*.jpg'),*O.glob('V16-*.json'),O/'V16-progress-every-half-second.csv',O/'V15-V16-code.diff']
data=dict(version='V16',main='output/PVE-Shot01-U-Archers-v16.mp4',overallVisualAcceptance='FAIL',reason='Sustained battle too short; charge weight not visually accepted',V15Protected=True,captureInputsCurrent=True,assetsOriginalHashesMatch=True,files={str(p.relative_to(P)):dict(bytes=p.stat().st_size,sha256=h(p)) for p in files if p.is_file() and p.name!='V16-delivery-manifest.json'})
(O/'V16-delivery-manifest.json').write_text(json.dumps(data,indent=2));print(dict(version='V16',files=len(data['files']),V15Protected=True,captureInputsCurrent=True,assetsOriginalHashesMatch=True))
