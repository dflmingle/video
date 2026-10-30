"""Join the accepted C1 PNG prefix to continuation frames without overlap."""
from pathlib import Path
import subprocess,json,hashlib
from PIL import Image
import cv2,imageio_ffmpeg
P=Path(__file__).resolve().parents[1]
old=P/'output/v22r-burst/C1-preview/frames'; new=P/'output/v22r-melee/preview/frames'; out=P/'output/v22r-melee/C1-plus-continuation-joined-720x1080-60fps.mp4'; ff=imageio_ffmpeg.get_ffmpeg_exe()
prefix=159;total=len(list(new.glob('F*.png')));assert total>prefix
proc=subprocess.Popen([ff,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','720x1080','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
try:
 for f in range(prefix):proc.stdin.write(Image.open(old/f'F{f:04}.png').convert('RGB').tobytes())
 for f in range(prefix,total):proc.stdin.write(Image.open(new/f'F{f:04}.png').convert('RGB').resize((720,1080),Image.Resampling.LANCZOS).tobytes())
 proc.stdin.close();assert proc.wait()==0
finally:
 if proc.stdin and not proc.stdin.closed:proc.stdin.close()
cap=cv2.VideoCapture(str(out));frames=0;fps=cap.get(cv2.CAP_PROP_FPS);w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
while cap.read()[0]:frames+=1
cap.release();assert frames==total and fps==60 and (w,h)==(720,1080)
report=dict(path=str(out),prefixFrames=prefix,continuationFrames=total-prefix,totalFrames=frames,fps=fps,width=w,height=h,duration=frames/fps,joinFrame='C1 F158 (2.633333s) -> continuation F159 (2.650000s), no overlap',sha256=hashlib.sha256(out.read_bytes()).hexdigest(),sourcePrefix='output/v22r-burst/C1-preview/frames',sourceContinuation='output/v22r-melee/preview/frames/F0159..F0794',normalSpeed=True,noLoop=True,noRetime=True)
(P/'docs/v22r-melee/join-check.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
