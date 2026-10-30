"""Encode distance previews without changing their simulation time base."""
from pathlib import Path
import json, subprocess, hashlib, cv2, imageio_ffmpeg, sys
from PIL import Image, ImageDraw, ImageFont
P=Path(__file__).resolve().parents[1];group=sys.argv[sys.argv.index('--group')+1] if '--group' in sys.argv else 'distance';O=P/('output/v22r-'+group);D=P/('docs/v22r-'+group)
ff=imageio_ffmpeg.get_ffmpeg_exe();font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
selected=sys.argv[sys.argv.index('--label')+1] if '--label' in sys.argv else None
audit=json.loads((D/('audit-'+selected+'.json' if selected else 'audit.json')).read_text(encoding='utf8'));outputs=[];cameras={}
baseCamera=json.loads((P/'output/v22r-frontfield/layout-preview/audit.json').read_text(encoding='utf8'))['frames'][0]
for r in audit['candidates']:
 label=r['label'];folder=O/label;a=json.loads((folder/'audit.json').read_text(encoding='utf8'));n=len(a['frames'])
 assert a['constant'] and not a['errors'] and a['width']==720 and a['height']==1080
 assert all(a['frames'][0][k]==baseCamera[k] for k in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom'])
 name=f'{label}-distance-plus{10 if label=="D1" else 20}' if group=='distance' else f'{label}-battlefield-depth'
 if group=='depth' and not r['terminationSucceeded']:name+='-FAILED-incomplete-safe-prefix'
 file=O/f'{name}-preview-720x1080-60fps.mp4'
 subprocess.run([ff,'-y','-loglevel','error','-framerate','60','-i',str(folder/'frames/F%04d.png'),'-frames:v',str(n),'-an','-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(file)],check=True)
 cap=cv2.VideoCapture(str(file));assert cap.get(cv2.CAP_PROP_FPS)==60
 samples={0:'opening',60:'one-second',120:'two-seconds',round(r['firstMeleeRangeContact']*60):'first-melee-range',round(r['firstMeleeHit']*60):'first-melee-hit',n-1:'end'}
 contact=round(r['firstMeleeHit']*60);sequences=[contact-2,contact-1,contact,contact+1,contact+2,contact+5]
 timelineFrames=sorted(set([0,30,60,120,240,n-1,*samples]))
 sheet=Image.new('RGB',(1440,((len(timelineFrames)+3)//4)*576),'#222629');draw=ImageDraw.Draw(sheet)
 sequence=Image.new('RGB',(1440,390),'#222629');sd=ImageDraw.Draw(sequence);count=0
 while True:
  ok,bgr=cap.read()
  if not ok:break
  if count in timelineFrames or count in sequences:
   im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
   if count in samples:im.save(O/f'{label}-{samples[count]}.jpg',quality=95)
   if count in timelineFrames:
    j=timelineFrames.index(count);x=j%4*360;y=j//4*576;sheet.paste(im.resize((360,540)),(x,y+30));draw.text((x+5,y+4),f'{label} {count/60:.3f}s F{count}',font=font,fill='white')
   if count in sequences:
    j=sequences.index(count);sequence.paste(im.resize((240,360)),(j*240,30));sd.text((j*240+3,4),f'F{count} {count/60:.3f}s',font=font,fill='white')
  count+=1
 cap.release();assert count==n
 sheet.save(O/f'{label}-encoded-timeline.jpg',quality=94);sequence.save(O/f'{label}-melee-continuous-frames.jpg',quality=94)
 outputs.append(dict(label=label,path=str(file),frames=count,fps=60,duration=count/60,width=720,height=1080,sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
 cameras[label]=dict(constant=a['constant'],errors=a['errors'],frames=n)
if group=='distance' and all((O/(label+'-opening.jpg')).exists() for label in ['D1','D2']):
 comparison=Image.new('RGB',(1440,788),'#222629');draw=ImageDraw.Draw(comparison)
 for j,(title,path) in enumerate([('CURRENT / gap 4.9238',P/'output/v22r-frontfield/layout-preview/frames/F0000.png'),('D1 +10% / gap 5.4161',O/'D1-opening.jpg'),('D2 +20% / gap 5.9085',O/'D2-opening.jpg')]):
  comparison.paste(Image.open(path).resize((480,720)),(j*480,60));draw.text((j*480+10,16),title,font=font,fill='white')
 comparison.save(O/'opening-current-D1-D2.jpg',quality=95)
with (D/('camera-every-frame-'+selected+'.csv' if selected else 'camera-every-frame.csv')).open('w',newline='',encoding='utf-8-sig') as f:
 import csv
 w=csv.writer(f);w.writerow(['candidate','frame','time','position','quaternion','projection','zoom'])
 for label in ([selected] if selected else [r['label'] for r in audit['candidates']]):
  a=json.loads((O/label/'audit.json').read_text(encoding='utf8'))
  for i,r in enumerate(a['frames']):w.writerow([label,i,r['time'],json.dumps(r['cameraPosition']),json.dumps(r['cameraQuaternion']),json.dumps(r['cameraProjection']),r['cameraZoom']])
(D/('encode-checks-'+selected+'.json' if selected else 'encode-checks.json')).write_text(json.dumps(dict(outputs=outputs,camera=cameras,noRetime=True,noLoop=True,noFrozenTail=True,formalRender=False,fullNormalSpeedVisualViewing=False,visualReview='Encoded key frames and contact continuous-frame strips; not a claim of full normal-speed perceptual viewing.'),indent=2),encoding='utf8')
print(json.dumps(outputs,indent=2))
if group=='depth' and all((O/(label+'-opening.jpg')).exists() for label in ['E1','E2','E3']):
 im=Image.new('RGB',(1440,2312),'#222629');draw=ImageDraw.Draw(im)
 for j,(title,path) in enumerate([('D2 +20% / gap 5.9085',P/'output/v22r-distance/D2-opening.jpg'),('E1 +50% / gap 7.3856',O/'E1-opening.jpg'),('E2 +100% / gap 9.8475',O/'E2-opening.jpg'),('E3 +147.75% / gap 12.1988',O/'E3-opening.jpg')]):
  x=(j%2)*720;y=(j//2)*1156;im.paste(Image.open(path),(x,y+60));draw.text((x+10,y+20),title,font=font,fill='white')
 im.save(O/'opening-D2-E1-E2-E3.jpg',quality=95)
