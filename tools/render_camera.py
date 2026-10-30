from pathlib import Path
import subprocess,sys,shutil
P=Path(__file__).resolve().parents[1];O=P/'output/camera-revision'
def run(*cmd):subprocess.run(cmd,cwd=P,check=True)
if '--verify-only' not in sys.argv:
 for key in ['A','B']:run('node','tools/capture_camera.mjs',f'CAMERA-{key}','--full')
 run(sys.executable,'-X','utf8','tools/media_camera.py')
 shutil.copy2(O/'PVE-Shot01-V11-Camera-B.mp4',O/'PVE-Shot01-U-Archers-v11-close.mp4')
 run(sys.executable,'-X','utf8','tools/impact_camera.py')
run(sys.executable,'-X','utf8','tools/verify_camera.py')
