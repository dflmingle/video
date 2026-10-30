"""Normal-speed low-cost A preview and original/A common-time comparison."""
import json,subprocess,hashlib
from pathlib import Path
import cv2,imageio_ffmpeg,numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];O=R/'output/v22r-fast-charge';D=R/'docs/v22r-fast-charge';P=O/'A-preview';a=json.loads((D/'A-audit.json').read_text(encoding='utf8'));audit=json.loads((P/'audit.json').read_text(encoding='utf8'));ff=imageio_ffmpeg.get_ffmpeg_exe();n=a['videoFrames'];font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
assert len(audit['frames'])==n and audit['constant'] and not audit['errors'] and not audit['consoleErrors']
dest=O/'V22R-A-fast-charge-2.317s-preview-720x1080-60fps.mp4'
subprocess.run([ff,'-y','-loglevel','error','-framerate','60','-i',str(P/'frames/F%04d.png'),'-frames:v',str(n),'-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
pair=O/'V22R-original-vs-A-common-2.2s-60fps.mp4';proc=subprocess.Popen([ff,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x752','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(pair)],stdin=subprocess.PIPE)
for k in range(132):
 im=Image.new('RGB',(960,752),'#222629');draw=ImageDraw.Draw(im);draw.text((8,7),f'原版  {k/60:.3f}s',font=font,fill='white');draw.text((488,7),'A：原冲锋 + 蓝方提前准备',font=font,fill='white')
 im.paste(Image.open(R/f'output/V22R-final/frames/F{k:04}.png').resize((480,720)),(0,32));im.paste(Image.open(P/f'frames/F{k:04}.png').resize((480,720)),(480,32));proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
cap=cv2.VideoCapture(str(dest));wanted=[0,30,60,78,81,82,83,90,99,100,101,120,132,136,137,138];panel=Image.new('RGB',(1200,1880),'#222629');draw=ImageDraw.Draw(panel);count=0
while True:
 ok,frame=cap.read()
 if not ok:break
 if count in wanted:
  k=wanted.index(count);im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.save(O/f'A-encoded-F{count:04}.jpg',quality=93);im.thumbnail((294,441));x=k%4*300;y=k//4*470;panel.paste(im,(x,y+26));draw.text((x+4,y+4),f'{count/60:.3f}s / F{count}',font=font,fill='white')
 count+=1
assert count==n and cap.get(cv2.CAP_PROP_FPS)==60;cap.release();panel.save(O/'A-encoded-timeline.jpg',quality=90)
checks=[]
for path,expected in [(dest,n),(pair,132)]:
 cap=cv2.VideoCapture(str(path));decoded=0;fps=cap.get(cv2.CAP_PROP_FPS);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 while cap.read()[0]:decoded+=1
 cap.release();assert decoded==expected and fps==60;checks.append(dict(path=str(path),frames=decoded,width=width,height=height,fps=fps,duration=decoded/fps,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
visible={team:dict(min=min(f[team+'Visible'] for f in audit['frames']),max=max(f[team+'Visible'] for f in audit['frames'])) for team in ['red','blue']}
result=dict(files=checks,allFramesFixedCamera=True,visibilityRootCounts=visible,totalRed=972,totalBlue=252,errors=[],normalSpeed=True,loop=False,retime=False,BRendered=False,visualReviewMethod='Decoded actual MP4 timeline samples and consecutive release/impact/ending frames; full normal-speed visual viewing unavailable',finalFullResolutionRendered=False)
(D/'A-encode-checks.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
