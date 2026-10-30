"""Repeatable V22 specialist builds. Baseline V21 is never rewritten.

B: visible deployment lead; C: same + pre-aim (not pre-draw).
D-visible: longer visible preparation. This is NOT a prepared first frame.
"""
from pathlib import Path
import argparse,json,shutil,subprocess,sys
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('scheme',choices=['B','C','D-visible']);a=p.parse_args()
name='V22-'+a.scheme;d=root/'variants'/name;d.mkdir(parents=True,exist_ok=True)
c=json.loads((root/'docs/V22-baseline-params.json').read_text(encoding='utf8'))
c.update(version='V22',duration=5.,redChargeStart=1.8 if a.scheme=='D-visible' else 1.,
         preAim=a.scheme!='B',autoCut=True)
(d/'params.json').write_text(json.dumps(c,indent=2),encoding='utf8')
source=root/'variants/V21/asset-render-audit.json'
if source.exists():shutil.copy2(source,d/'asset-render-audit.json')
subprocess.run([sys.executable,str(root/'tools/build_simulation_v22.py'),name],cwd=root,check=True)
