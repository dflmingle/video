from pathlib import Path
import subprocess
import imageio_ffmpeg

root = Path(__file__).resolve().parents[1]
frames = root / 'output' / 'captures' / 'V21-FIXED' / 'frames'
files = sorted(frames.glob('F*.png'))
assert files
ff = imageio_ffmpeg.get_ffmpeg_exe()
out = root / 'output' / 'PVE-Shot01-U-Archers-v21.mp4'
subprocess.run([
    ff, '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '60',
    '-i', str(frames / 'F%04d.png'), '-frames:v', str(len(files)), '-an',
    '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt',
    'yuv420p', '-movflags', '+faststart', str(out)
], check=True)
print(out)
