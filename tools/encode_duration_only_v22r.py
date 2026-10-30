"""Compare every accepted original/replayed frame; no unsafe tail encoding."""
import csv,hashlib,json,subprocess
from pathlib import Path
import cv2,imageio_ffmpeg,numpy as np
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parents[1];O=R/'output/v22r-duration-only';D=R/'docs/v22r-duration-only';A=R/'output/V22R-final'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
a=load(A/'render-audit.json');b=load(O/'render-audit.json');c=load(D/'comparison.json');assert c['fullSimulationJSONIdentical'] and b['totalFrames']==a['totalFrames']==132
camera=lambda r:[(f['position'],f['quaternion'],f['projection'],f['fov'],f['zoom']) for f in r['frames']]
assert camera(a)==camera(b) and a['setup']==b['setup']
ff=imageio_ffmpeg.get_ffmpeg_exe();fps=60;n=132
candidate=O/'V22R-duration-only-safe-replay-2.2s-1440x2160-60fps.mp4'
subprocess.run([ff,'-y','-loglevel','error','-framerate','60','-i',str(O/'frames/F%04d.png'),'-frames:v',str(n),'-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(candidate)],check=True)
pair=O/'V22R-original-vs-duration-only-common-2.2s-60fps.mp4'
proc=subprocess.Popen([ff,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x752','-r','60','-i','-','-an','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(pair)],stdin=subprocess.PIPE)
rows=[];font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15);samples={0,1,60,120,122,130,131};sheet=Image.new('RGB',(960,len(samples)*384),'#222629');count=0
for k in range(n):
 src=A/f'frames/F{k:04}.png';dst=O/f'frames/F{k:04}.png';x=cv2.imread(str(src));y=cv2.imread(str(dst));delta=np.abs(x.astype(np.int16)-y.astype(np.int16))
 rows.append(dict(frame=k,time=k/fps,meanPixelDifference=float(delta.mean()),maximumChannelDifference=int(delta.max()),pixelsExactlyEqual=bool(np.array_equal(x,y)),cameraExactlyEqual=True,redWorldExactlyEqual=True,blueWorldExactlyEqual=True,eventsExactlyEqual=True))
 im=Image.new('RGB',(960,752),'#222629');draw=ImageDraw.Draw(im);draw.text((8,7),f'原版 / Original  {k/fps:.3f}s',font=font,fill='white');draw.text((488,7),'仅延长请求时长 / Same safe replay',font=font,fill='white')
 im.paste(Image.fromarray(cv2.cvtColor(x,cv2.COLOR_BGR2RGB)).resize((480,720)),(0,32));im.paste(Image.fromarray(cv2.cvtColor(y,cv2.COLOR_BGR2RGB)).resize((480,720)),(480,32));proc.stdin.write(im.tobytes())
 if k in samples:
  small=im.resize((480,376));sheet.paste(small,(0,count*384));diff=Image.fromarray(np.uint8(np.clip(delta*20,0,255))).resize((480,720));diff.thumbnail((240,360));sheet.paste(diff,(560,count*384+16));ImageDraw.Draw(sheet).text((806,count*384+16),f'F{k}\nDIFF x20\nMAE {delta.mean():.5f}',font=font,fill='white');count+=1
proc.stdin.close();assert proc.wait()==0;sheet.save(O/'common-encoded-review-and-diff.jpg',quality=90)
with (D/'pixel-and-world-every-frame.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
checks=[]
for path in [candidate,pair]:
 cap=cv2.VideoCapture(str(path));frames=0;rate=cap.get(cv2.CAP_PROP_FPS);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 while True:
  ok,frame=cap.read()
  if not ok:break
  if frames in [0,122,131]:cv2.imwrite(str(O/f'{path.stem}-encoded-F{frames:04}.jpg'),frame)
  frames+=1
 cap.release();assert frames==n and rate==60
 checks.append(dict(path=str(path),frames=frames,fps=rate,width=width,height=height,duration=frames/rate,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
report=dict(files=checks,all132FramesCompared=True,commonWorldAndEventsExact=True,sceneSetupExact=True,cameraEveryFrameExact=True,maximumMeanPixelDifference=max(r['meanPixelDifference'] for r in rows),maximumChannelDifference=max(r['maximumChannelDifference'] for r in rows),pixelExactFrames=sum(r['pixelsExactlyEqual'] for r in rows),pixelDifferenceNotHidden=True,tail2Point2To3Point5Generated=False,noRetimingOrLoop=True,visualReview='Actual encoded samples and source frame differences; not a claim of full normal-speed visual viewing')
(D/'render-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
