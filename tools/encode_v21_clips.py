from pathlib import Path
import subprocess, imageio_ffmpeg

root=Path(__file__).resolve().parents[1]
frames=root/'output/captures/V21-FIXED/frames'; ff=imageio_ffmpeg.get_ffmpeg_exe()
def encode(name, start, count, vf=None):
    out=root/'output'/name
    cmd=[ff,'-hide_banner','-loglevel','error','-y','-framerate','60','-start_number',str(start),'-i',str(frames/'F%04d.png'),'-frames:v',str(count),'-an']
    if vf: cmd += ['-vf',vf]
    cmd += ['-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    subprocess.run(cmd,check=True); print(out)

# The formal camera remains one continuous shot; these are diagnostic extracts.
encode('V21-archer-and-arrow-diagnostic.mp4', 78, 61, 'crop=960:1200:240:760,scale=720:900')
encode('V21-local-response-diagnostic.mp4', 90, 49)
