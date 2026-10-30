from pathlib import Path
import sys,subprocess,urllib.request
P=Path(__file__).resolve().parents[1]
def run(*args):subprocess.run(args,cwd=P,check=True)
def py(name,*args):run(sys.executable,'-X','utf8','tools/'+name,*args)
if '--verify-only' in sys.argv:py('verify_preview_v10.py');raise SystemExit
with urllib.request.urlopen('http://127.0.0.1:5250/src/main-v10.js') as r:assert 'previewOnly' in r.read().decode()
py('build_simulation_v10.py','FINAL');py('validate_charge_v10.py');run('node','tools/capture_v10.mjs','FINAL','--full');py('preview_media_v10.py');run('node','tools/gait_probe_v10.mjs');py('validate_gait_v10.py');py('verify_preview_v10.py')
