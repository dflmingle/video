"""Encode uncropped normal-speed continuation deliverables and decoded samples."""
import json,subprocess,hashlib
from pathlib import Path
import cv2,numpy as np,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];O=P/'output/v22r-melee';D=P/'docs/v22r-melee';ff=imageio_ffmpeg.get_ffmpeg_exe()
audit=json.loads((O/'preview/audit.json').read_text(encoding='utf8'));n=len(audit['frames']);fps=60;outputs=[]
def encode(name,start,count):
 path=O/name
 subprocess.run([ff,'-y','-loglevel','error','-framerate','60','-start_number',str(start),'-i',str(O/'preview/frames/F%04d.png'),'-frames:v',str(count),'-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
 return path
full=encode('C1-continued-full-preview-480x720-60fps.mp4',0,n)
tail=encode('C1-continued-from-2.3s-preview-480x720-60fps.mp4',138,n-138)
pair=O/'C1-original-vs-continued-opening-2.65s-60fps.mp4'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
proc=subprocess.Popen([ff,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x752','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(pair)],stdin=subprocess.PIPE)
for f in range(159):
 im=Image.new('RGB',(960,752),'#222629');draw=ImageDraw.Draw(im)
 for j,(label,folder) in enumerate([('C1 ORIGINAL',P/'output/v22r-burst/C1-preview/frames'),('CONTINUED',O/'prefix/frames')]):
  draw.text((j*480+8,5),f'{label} | {f/60:.3f}s',fill='white',font=font)
  im.paste(Image.open(folder/f'F{f:04}.png').resize((480,720)),(j*480,32))
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
sampleTimes=[0,2.3,2.65,3,3.5,4,5,6,8,10,(n-1)/60]
panel=Image.new('RGB',(1200,1236),'#222629');draw=ImageDraw.Draw(panel)
for path in [full,tail,pair]:
 cap=cv2.VideoCapture(str(path));count=0;samples={round(t*60):i for i,t in enumerate(sampleTimes)}
 while True:
  ok,frame=cap.read()
  if not ok:break
  if path==full and count in samples:
   i=samples[count];rgb=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));rgb.save(O/f'encoded-F{count:04}.jpg',quality=95)
   rgb=rgb.resize((300,450));x=i%4*300;y=i//4*412
   rgb.thumbnail((270,380));panel.paste(rgb,(x,y+28));draw.text((x+5,y+5),f'{count/60:.3f}s F{count}',font=font,fill='white')
  count+=1
 rate=cap.get(cv2.CAP_PROP_FPS);width=cap.get(cv2.CAP_PROP_FRAME_WIDTH);height=cap.get(cv2.CAP_PROP_FRAME_HEIGHT);cap.release()
 expected=159 if path==pair else n-138 if path==tail else n
 assert count==expected and rate==60
 outputs.append(dict(path=str(path),frames=count,fps=rate,width=width,height=height,duration=count/rate,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
panel.save(O/'encoded-timeline.jpg',quality=92)
(D/'encode-checks.json').write_text(json.dumps(dict(outputs=outputs,cameraConstant=audit['constant'],browserErrors=audit['errors'],normalSpeed=True,noLoop=True,noRetime=True,noAddedStillFrames=True,formalRender=False,fullNormalSpeedVisualViewing=False),indent=2),encoding='utf8')
print(json.dumps(outputs,indent=2))
