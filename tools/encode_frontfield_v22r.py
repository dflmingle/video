"""Encode actual 720p portrait frames and common-time, normal-speed comparisons."""
from pathlib import Path
import json,subprocess,hashlib,cv2,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];O=P/'output/v22r-frontfield';D=P/'docs/v22r-frontfield';ff=imageio_ffmpeg.get_ffmpeg_exe()
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18);outputs=[]
def encode(folder,name):
 audit=json.loads((O/folder/'audit.json').read_text(encoding='utf8'));n=len(audit['frames']);assert audit['width']==720 and audit['height']==1080 and audit['constant'] and not audit['errors']
 dest=O/name
 subprocess.run([ff,'-y','-loglevel','error','-framerate','60','-i',str(O/folder/'frames/F%04d.png'),'-frames:v',str(n),'-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
 return dest,n
layout,ln=encode('layout-preview','C1-frontfield-layout-candidate-720x1080-60fps.mp4')
flash,fn=encode('flash-only','C1-preserved-battle-hitflash-720x1080-60fps.mp4')
def compare(folder,name,n,label):
 dest=O/name;proc=subprocess.Popen([ff,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x752','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdin=subprocess.PIPE)
 for f in range(n):
  image=Image.new('RGB',(960,752),'#222629');draw=ImageDraw.Draw(image)
  for j,(title,root) in enumerate([('BEFORE / ACCEPTED',P/'output/v22r-melee/preview/frames'),(label,O/folder/'frames')]):
   draw.text((j*480+7,4),f'{title}  {f/60:.3f}s',font=font,fill='white');image.paste(Image.open(root/f'F{f:04}.png').resize((480,720)),(j*480,32))
  proc.stdin.write(image.tobytes())
 proc.stdin.close();assert proc.wait()==0;return dest
layoutCompare=compare('layout-preview','BEFORE-vs-frontfield-common-time-60fps.mp4',ln,'FRONTFIELD CANDIDATE')
flashCompare=compare('flash-only','BEFORE-vs-hitflash-same-battle-60fps.mp4',fn,'HIT FLASH ONLY')
for file,n in [(layout,ln),(flash,fn),(layoutCompare,ln),(flashCompare,fn)]:
 cap=cv2.VideoCapture(str(file));rate=cap.get(cv2.CAP_PROP_FPS);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));count=0
 sampleFrames=[0,30,60,120,240,n-1]
 sheet=Image.new('RGB',(1080,1152),'#222629');draw=ImageDraw.Draw(sheet)
 while True:
  ok,bgr=cap.read()
  if not ok:break
  if file in [layout,flash] and count in sampleFrames:
   i=sampleFrames.index(count);im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));im.save(O/f'{file.stem}-F{count:04}.jpg',quality=95);im.thumbnail((350,525));x=(i%3)*360;y=(i//3)*576;sheet.paste(im,(x,y+28));draw.text((x+4,y+3),f'{count/60:.3f}s / F{count}',font=font,fill='white')
  count+=1
 cap.release();assert count==n and rate==60
 if file in [layout,flash]:sheet.save(O/f'{file.stem}-encoded-timeline.jpg',quality=92)
 outputs.append(dict(path=str(file),frames=count,fps=rate,width=width,height=height,duration=count/rate,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
# Decode the actual MP4 again around each damage event, not just PNG sources.
evidence=json.loads((O/'evidence/evidence.json').read_text(encoding='utf8'))
cap=cv2.VideoCapture(str(layout));encodedEvidence=O/'encoded-hit-evidence';encodedEvidence.mkdir(exist_ok=True)
for kind in ['arrow','melee']:
 rows=[r for r in evidence['rows'] if r['event']['type']==kind];sheet=Image.new('RGB',(1280,216),'#222629');draw=ImageDraw.Draw(sheet)
 for i,row in enumerate(rows):
  f=round(row['time']*60);cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,bgr=cap.read();assert ok;im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));im.save(encodedEvidence/f'{kind}-F{f:04}.jpg',quality=95)
  x,y=row['screen'];crop=im.crop((round(x)-30,round(y)-36,round(x)+30,round(y)+24)).resize((160,160));sheet.paste(crop,(i*160,48));draw.text((i*160+3,4),f"F{f} {row['time']:.3f}s",font=font,fill='white');draw.text((i*160+3,25),f"flash {row['hitFlash']:.3f}",font=font,fill='white')
 sheet.save(encodedEvidence/f'{kind}-sequence.jpg',quality=95)
cap.release()
(D/'encode-checks.json').write_text(json.dumps(dict(outputs=outputs,noRetime=True,noLoop=True,noFrozenComparisonTail=True,cameraConstant=True,formalRender=False,fullNormalSpeedVisualViewing=False,comparisonNote='Accepted before source is 480x720; comparison panes are equally resized. Candidate and flash-only standalone previews are native720x1080.'),indent=2),encoding='utf8');print(json.dumps(outputs,indent=2))
