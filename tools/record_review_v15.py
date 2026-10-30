from pathlib import Path
import json,hashlib,difflib
P=Path(__file__).resolve().parents[1];O=P/'output';B=P.parent/'PveMontageShot01V14'
r=json.loads((O/'V15-render-validation.json').read_text());r['visualStatus']='PARTIAL_ENCODED_FRAMES_REVIEWED';r['visualMethod']='Decoded MP4 overviews, keyframes and consecutive windows; not normal-speed playback and not every frame manually reviewed.'
r['reviewedFiles']=['V15-FINAL-overview.jpg','V15-FINAL-end.jpg','V15-FINAL-consecutive-2.jpg','V15-LOCAL-cruise.jpg','V15-LOCAL-avoid.jpg','V15-LOCAL-consecutive-1.jpg','V15-LOCAL-overview.jpg','V15-HEALTHY-end.jpg']
for p,h in json.loads((O/'protected-v14.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
(O/'V15-render-validation.json').write_text(json.dumps(r,indent=2))
diff=O/'V14-V15-code.diff';s=diff.read_text(encoding='utf-8')
s+=''.join(difflib.unified_diff((B/'index.html').read_text(encoding='utf-8').splitlines(True),(P/'index.html').read_text(encoding='utf-8').splitlines(True),fromfile='V14/index.html',tofile='V15/index.html'));diff.write_text(s,encoding='utf-8')
files=['V15-REVIEW.md','RENDER-V15.md','tools/motion_v15.py','tools/build_simulation_v15.py','tools/test_motion_v15.py','tools/validate_battle_v15.py','tools/capture_v15.mjs','tools/evidence_v15.py','output/PVE-Shot01-U-Archers-v15.mp4','output/V15-50-members-5s-validation.mp4','output/V15-50-members-5s-healthy-charge.mp4','output/V15-algorithm-tests.json','output/V15-battle-tests.json','output/V15-render-validation.json','output/V15-entry-validation.json']
manifest={p:dict(bytes=(P/p).stat().st_size,sha256=hashlib.sha256((P/p).read_bytes()).hexdigest()) for p in files}
(O/'V15-delivery-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(dict(artifacts=len(files),V14Protected=True,visualStatus=r['visualStatus'],videoFiles=[p for p in files if p.endswith('.mp4')]),indent=2))
