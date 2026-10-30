from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1];O=P/'output'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=json.loads((O/'protected-v16.json').read_text(encoding='utf-8'));assert all(sha(Path(p))==h for p,h in protected.items())
manifest=json.loads((P/'assets/runtime/manifest.json').read_text(encoding='utf-8'));assets=[]
for name,e in manifest.items():
 model=P/e['file'].lstrip('/');tex=P/e['texture'].lstrip('/');assert sha(model)==e['sourceSHA256'] and sha(tex)==e['textureSHA256'];assets.append(dict(name=name,source=e['source'],modelSHA256=sha(model),textureSHA256=sha(tex)))
files=[p for p in O.glob('*.mp4')]+[p for p in O.glob('*.jpg')]+[p for p in O.glob('V17*.json')]+[O/'V17-progress.csv',P/'V17-REVIEW.md',P/'RENDER-V17.md']
out=dict(version='V17',main='output/PVE-Shot01-U-Archers-v17.mp4',overallVisualAcceptance='FAIL/PARTIAL',reason='0.633s post-hit window and full-opening framing makes characters small; no normal-speed full human playback',V16Protected=True,assets=assets,files={str(p.relative_to(P)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in files if p.is_file()})
(O/'V17-delivery-manifest.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(dict(version='V17',files=len(out['files']),assets=len(assets),protected=True))
