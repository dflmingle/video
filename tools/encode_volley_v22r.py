"""Three real normal-speed prefix candidates of the same audited 4-second run."""
import csv,hashlib,json,subprocess
from pathlib import Path
import cv2,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parents[1];O=R/'output/v22r-volley';D=R/'docs/v22r-volley';P=O/'preview';a=json.loads((P/'audit.json').read_text(encoding='utf8'));f=json.loads((D/'feasibility.json').read_text(encoding='utf8'));fps=60
assert a['constant'] and not a['errors'] and not a['consoleErrors']
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();checks=[]
for c in f['candidates']:
 n=round(c['duration']*fps);name=f"V22R-{c['label']}-{c['duration']:.1f}s-preview-720x1080-60fps.mp4";dest=O/name
 if not c['available']:continue
 subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','60','-i',str(P/'frames/F%04d.png'),'-frames:v',str(n),'-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
 cap=cv2.VideoCapture(str(dest));count=0;frameRate=cap.get(cv2.CAP_PROP_FPS);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 while True:
  ok,frame=cap.read()
  if not ok:break
  if count==n-1:cv2.imwrite(str(O/f"{c['label']}-encoded-last.jpg"),frame)
  count+=1
 cap.release();assert count==n and frameRate==60 and (width,height)==(720,1080)
 checks.append(dict(label=c['label'],path=str(dest),bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),frames=count,fps=frameRate,width=width,height=height,duration=count/frameRate,cameraConstant=True,looped=False,retimed=False,addedStillFrames=0,numericStatus=c['status'],visualWholeVideoWatched=False))
# Review actual encoded C video. Consecutive frames surround the first release
# and impact; time samples also cover early movement, late congestion/deaths.
source=O/'V22R-C-4.0s-preview-720x1080-60fps.mp4';cap=cv2.VideoCapture(str(source));release=round(f['candidates'][0]['firstRelease']*fps);impact=round(f['candidates'][0]['firstHit']*fps);wanted=[0,6,release-1,release,release+1,impact-1,impact,impact+1,60,90,120,150,180,210,238,239];font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
panel=Image.new('RGB',(1200,1880),'#222629');draw=ImageDraw.Draw(panel)
for idx,k in enumerate(wanted):
 cap.set(cv2.CAP_PROP_POS_FRAMES,k);ok,frame=cap.read();assert ok
 im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.save(O/f'encoded-F{k:04}.jpg',quality=92);im.thumbnail((294,441));x=idx%4*300;y=idx//4*470;panel.paste(im,(x,y+26));draw.text((x+3,y+4),f'{k/60:.3f}s / F{k}',font=font,fill='white')
cap.release();panel.save(O/'encoded-continuous-and-timeline.jpg',quality=89)
with (D/'camera-every-frame.csv').open('w',newline='',encoding='utf-8-sig') as file:
 w=csv.writer(file);w.writerow(['frame','time','position','quaternion','projection','zoom','fov'])
 for k,row in enumerate(a['frames']):
  c=row['camera'];w.writerow([k,row['time'],json.dumps(c['position']),json.dumps(c['quaternion']),json.dumps(c['projection']),c['zoom'],c['fov']])
report=dict(candidates=checks,sourceVariant='V22R-volley',sameSimulationForABC=True,sameSceneAndCamera=True,visualReviewMethod='Actual encoded frames sampled across full timeline, with consecutive frames around release/impact; not a claim of normal-speed full video visual inspection.',fullResolutionFinalRendered=False)
(D/'encode-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(report,ensure_ascii=True,indent=2))
