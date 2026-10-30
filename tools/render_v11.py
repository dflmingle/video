from pathlib import Path
import sys,subprocess
P=Path(__file__).resolve().parents[1]
def run(*args):subprocess.run(args,cwd=P,check=True)
if '--verify-only' not in sys.argv:
 run(sys.executable,'-X','utf8','tools/build_simulation_v11.py','FINAL')
run(sys.executable,'-X','utf8','tools/validate_v11.py')
if '--verify-only' not in sys.argv:
 # The audit records native release anchors. Rebuild after first capture so
 # source hang points are reproducible even on a clean checkout.
 run('node','tools/capture_v11.mjs','FINAL')
 run(sys.executable,'-X','utf8','tools/build_simulation_v11.py','FINAL')
 run(sys.executable,'-X','utf8','tools/validate_v11.py')
 run('node','tools/capture_v11.mjs','FINAL','--full')
 run(sys.executable,'-X','utf8','tools/media_v11.py')
 run(sys.executable,'-X','utf8','tools/impact_evidence_v11.py')
run(sys.executable,'-X','utf8','tools/verify_render_v11.py')
