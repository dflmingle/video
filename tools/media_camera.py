from pathlib import Path
import json,subprocess,shutil,cv2,numpy as np,imageio_ffmpeg
from media_v11 import check,encoder,fit,jpg,at
P=Path(__file__).resolve().parents[1];O=P/'output/camera-revision';ff=imageio_ffmpeg.get_ffmpeg_exe();media=[]
for key in ['A','B']:
 D=P/f'variants/CAMERA-{key}';C=json.loads((D/'params.json').read_text());N=round(C['duration']*C['fps']);assert len(list((D/'frames').glob('F*.png')))==N
 path=O/f'PVE-Shot01-V11-Camera-{key}.mp4'
 subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate',str(C['fps']),'-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
 meta=check(path);assert meta['frames']==N and meta['fps']==60 and not meta['adjacentExactRepeats'];media.append(meta)
 caps=cv2.VideoCapture(str(path))
 for label,t in [('initial',0),('charge',1.3),('first-impact',2.4),('battle',2.8),('late',3.8)]:jpg(O/f'{key}-{label}.jpg',at(caps,t))
 caps.release()
 print('Encoded',key,flush=True)
a=cv2.VideoCapture(str(O/'PVE-Shot01-V11-Camera-A.mp4'));b=cv2.VideoCapture(str(O/'PVE-Shot01-V11-Camera-B.mp4'));old=cv2.VideoCapture(str(P/'output/PVE-Shot01-U-Archers-v11.mp4'))
for name,pairs in [('V11-Camera-A-B-comparison.mp4',[(a,'A / closer'),(b,'B / battle area')]),('V11-original-close-comparison.mp4',[(old,'Original V11'),(b,'B / battle area')])]:
 path=O/name;proc=encoder(path,1920,1500,30)
 for k in range(126):
  t=k/30;im=np.full((1500,1920,3),25,np.uint8)
  for j,(cap,label) in enumerate(pairs):
   im[60:,j*960:(j+1)*960]=fit(at(cap,t),960,1440);cv2.putText(im,f'{label} | {t:.3f}s',(j*960+18,38),0,.7,(235,235,235),1)
  proc.stdin.write(im.tobytes())
 proc.stdin.close();assert proc.wait()==0;media.append(check(path))
# Actual encoded time windows, preserving aspect ratio.
for key,cap in [('A',a),('B',b)]:
 for page,(start,step) in enumerate([(0,2),(96,2),(138,2),(222,2)]):
  sheet=np.full((2*620,4*410,3),235,np.uint8)
  for j in range(8):
   f=start+j*step;x=j%4*410;y=j//4*620;sheet[y+28:y+620,x:x+410]=fit(at(cap,f/60),410,592);cv2.putText(sheet,f'{key} {f/60:.3f}s',(x+8,y+20),0,.55,(0,0,0),1)
  jpg(O/f'{key}-sequence-{page}.jpg',sheet)
sheet=np.full((3*740,3*500,3),235,np.uint8)
for col,(cap,label) in enumerate([(old,'Original'),(a,'A'),(b,'B')]):
 for row,t in enumerate([0,2.4,3.8]):
  x=col*500;y=row*740;sheet[y+28:y+740,x:x+500]=fit(at(cap,t),500,712);cv2.putText(sheet,f'{label} {t:.2f}s',(x+8,y+20),0,.6,(0,0,0),1)
jpg(O/'Original-A-B-framing.jpg',sheet)
for cap in [a,b,old]:cap.release()
(O/'media-validation.json').write_text(json.dumps(media,indent=2));print(json.dumps(media,indent=2))
