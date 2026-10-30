from pathlib import Path
import json,hashlib,subprocess,cv2,numpy as np,imageio_ffmpeg
from PIL import Image
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';C=json.loads((D/'params.json').read_text()) if (D/'params.json').exists() else {};ff=imageio_ffmpeg.get_ffmpeg_exe();N=round(C.get('duration',0)*C.get('fps',60))
def check(path):
 cap=cv2.VideoCapture(str(path));fps=cap.get(5);w,h=int(cap.get(3)),int(cap.get(4));n=0;black=[];repeated=[];last=None
 while True:
  ok,im=cap.read()
  if not ok:break
  digest=hashlib.sha256(im.tobytes()).hexdigest()
  if im.mean()<1:black.append(n)
  if digest==last:repeated.append(n)
  last=digest;n+=1
 cap.release();assert n and not black
 return dict(path=path.name,frames=n,fps=fps,width=w,height=h,duration=n/fps,blackFrames=black,adjacentExactRepeats=repeated,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
def encoder(path,w,h,rate=30):
 return subprocess.Popen([ff,'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(rate),'-i','pipe:0','-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
def fit(im,w,h):
 sh,sw=im.shape[:2];scale=min(w/sw,h/sh);nw,nh=round(sw*scale),round(sh*scale);out=np.full((h,w,3),25,np.uint8);x,y=(w-nw)//2,(h-nh)//2;out[y:y+nh,x:x+nw]=cv2.resize(im,(nw,nh));return out
def at(cap,t):
 cap.set(0 if False else cv2.CAP_PROP_POS_MSEC,t*1000);ok,im=cap.read();assert ok,t;return im
def jpg(path,im):cv2.imencode('.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,94])[1].tofile(str(path))
if __name__=='__main__':
 assert len(list((D/'frames').glob('F*.png')))==N
 main=O/'PVE-Shot01-U-Archers-v11.mp4'
 subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate',str(C['fps']),'-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(main)],check=True)
 meta=[check(main)];assert meta[0]['frames']==N and meta[0]['fps']==C['fps'] and not meta[0]['adjacentExactRepeats'];new=cv2.VideoCapture(str(main));old=cv2.VideoCapture('C:/Users/89trillion/PveMontageShot01V10/output/PVE-Shot01-ChargeOnly-v10-preview.mp4')
 name=O/'V10-V11-motion-comparison.mp4';proc=encoder(name,1920,1440)
 for f in range(round(C['duration']*30)):
  t=f/30;out=np.full((1440,1920,3),25,np.uint8)
  for j,(cap,label) in enumerate([(old,'V10 charge-only baseline'),(new,'V11 overhead / full archery')]):
   out[64:,j*960:(j+1)*960]=fit(at(cap,t),960,1376);cv2.putText(out,f'{label} / {t:.3f}s',(j*960+14,36),0,.65,(240,240,240),1)
  proc.stdin.write(out.tobytes())
 proc.stdin.close();assert proc.wait()==0;meta.append(check(name));old.release()
 for label,t in [('initial',0),('charge',1.25),('mid-battle',2.8),('late-battle',4.0)]:jpg(O/f'V11-{label}.jpg',at(new,t))
 pdf=cv2.imread(str(P/'docs/formation-page-7.png'));out=np.full((1440,1440,3),25,np.uint8);out[50:,:720]=fit(pdf,720,1390);out[50:,720:]=fit(at(new,0),720,1390);cv2.putText(out,'Planning formation',(20,32),0,.7,(240,240,240),1);cv2.putText(out,'V11 initial / exact V10 members',(735,32),0,.6,(240,240,240),1);jpg(O/'Planning-V11-initial.jpg',out)
 # Full-shot temporal overview, aspect ratio preserved. These are decoded MP4 frames.
 sheet=np.full((2*600,5*400,3),235,np.uint8)
 for j,t in enumerate(np.linspace(0,C['duration']-1/C['fps'],10)):
  x=j%5*400;y=j//5*600;sheet[y+28:y+600,x:x+400]=fit(at(new,float(t)),400,572);cv2.putText(sheet,f'V11 {t:.3f}s',(x+8,y+20),0,.55,(0,0,0),1)
 jpg(O/'V11-encoded-overview.jpg',sheet)
 for page,(start,step) in enumerate([(0,2),(60,2),(132,2),(210,2)]):
  sheet=np.full((3*600,4*400,3),235,np.uint8)
  for j in range(12):
   f=min(N-1,start+j*step);x=j%4*400;y=j//4*600;sheet[y+28:y+600,x:x+400]=fit(at(new,f/C['fps']),400,572);cv2.putText(sheet,f'{f/C["fps"]:.3f}s',(x+8,y+20),0,.55,(0,0,0),1)
  jpg(O/f'V11-encoded-sequence-{page}.jpg',sheet)
 new.release();(O/'V11-media-validation.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
