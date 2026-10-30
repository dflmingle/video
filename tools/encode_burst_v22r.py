"""Actual normal-speed prefixes, with encoded event-frame review artifacts."""
import csv,hashlib,json,subprocess
from pathlib import Path
import cv2,imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1];D=R/'docs/v22r-burst';O=R/'output/v22r-burst';ff=imageio_ffmpeg.get_ffmpeg_exe();font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16);checks=[]
for label in ['C1','C2']:
 audit=json.loads((O/(label+'-preview/audit.json')).read_text(encoding='utf8'));data=json.loads((D/(label+'-audit.json')).read_text());n=data['frames'];dest=O/f'V22R-{label}-{n/60:.3f}s-preview-720x1080-60fps.mp4'
 assert len(audit['frames'])==n and audit['constant'] and not audit['errors'] and not audit['consoleErrors']
 subprocess.run([ff,'-y','-loglevel','error','-framerate','60','-i',str(O/(label+'-preview/frames/F%04d.png')),'-frames:v',str(n),'-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
 release=round(data['firstRelease']*60);impact=round(data['firstActualHit']*60);wanted=[0,60,release-1,release,release+1,impact-1,impact,impact+1,120,138,n-3,n-2,n-1];panel=Image.new('RGB',(1200,1880),'#222629');draw=ImageDraw.Draw(panel);cap=cv2.VideoCapture(str(dest));decoded=0
 while True:
  ok,frame=cap.read()
  if not ok:break
  if decoded in wanted:
   i=wanted.index(decoded);im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.save(O/f'{label}-encoded-F{decoded:04}.jpg',quality=93);im.thumbnail((294,441));x=i%4*300;y=i//4*470;panel.paste(im,(x,y+26));draw.text((x+4,y+4),f'{label} {decoded/60:.3f}s / F{decoded}',font=font,fill='white')
  decoded+=1
 rate=cap.get(cv2.CAP_PROP_FPS);width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));cap.release();assert decoded==n and rate==60 and (width,height)==(720,1080);panel.save(O/(label+'-encoded-timeline.jpg'),quality=90)
 with (D/(label+'-camera-visibility-every-frame.csv')).open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['frame','time','position','quaternion','projection','fov','zoom','redVisible','blueVisible'])
  for k,row in enumerate(audit['frames']):
   c=row['camera'];w.writerow([k,row['time'],json.dumps(c['position']),json.dumps(c['quaternion']),json.dumps(c['projection']),c['fov'],c['zoom'],row['redVisible'],row['blueVisible']])
 checks.append(dict(label=label,path=str(dest),frames=decoded,fps=rate,width=width,height=height,duration=decoded/rate,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),cameraConstant=audit['constant'],minimumRedVisible=min(x['redVisible'] for x in audit['frames']),minimumBlueVisible=min(x['blueVisible'] for x in audit['frames']),noLoop=True,noRetime=True,noAddedStillFrames=True,fullNormalSpeedVisualViewing=False))
# Common interval only; no frozen/blank tail on A's pane.
pair=O/'V22R-A-C1-C2-common-2.317s-60fps.mp4';proc=subprocess.Popen([ff,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x572','-r','60','-i','-','-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(pair)],stdin=subprocess.PIPE)
for k in range(139):
 im=Image.new('RGB',(1080,572),'#222629');draw=ImageDraw.Draw(im)
 for j,label in enumerate(['A','C1','C2']):
  path=R/f'output/v22r-fast-charge/A-preview/frames/F{k:04}.png' if label=='A' else O/f'{label}-preview/frames/F{k:04}.png'
  draw.text((j*360+6,6),f'{label}  {k/60:.3f}s',font=font,fill='white');im.paste(Image.open(path).resize((360,540)),(j*360,32))
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
cap=cv2.VideoCapture(str(pair));commonDecoded=0;commonFPS=cap.get(cv2.CAP_PROP_FPS)
while cap.read()[0]:commonDecoded+=1
cap.release();assert commonDecoded==139 and commonFPS==60
result=dict(candidates=checks,commonComparison=str(pair),commonFrames=139,commonComparisonDecodedFrames=commonDecoded,commonComparisonFPS=commonFPS,formalRender=False,visualMethod='Actual encoded timeline samples and consecutive release/impact/ending frames; no claim of full normal-speed visual viewing')
(D/'encode-checks.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result,indent=2))
