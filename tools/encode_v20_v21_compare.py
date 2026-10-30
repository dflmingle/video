from pathlib import Path
import subprocess, imageio_ffmpeg
root=Path(__file__).resolve().parents[1]
ff=imageio_ffmpeg.get_ffmpeg_exe()
old=root/'output/captures/V20-B-B/frames/F%04d.png'
new=root/'output/captures/V21-FIXED/frames/F%04d.png'
out=root/'output/V20-V21-same-time.mp4'
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-framerate','60','-i',str(old),'-i',str(new),'-filter_complex','[0:v][1:v]hstack=inputs=2,scale=1440:1080,format=yuv420p[v]','-map','[v]','-an','-c:v','libx264','-crf','18','-preset','fast','-movflags','+faststart',str(out)],check=True)
print(out)
