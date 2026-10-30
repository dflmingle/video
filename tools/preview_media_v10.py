from pathlib import Path
import json,hashlib,subprocess,cv2,numpy as np,imageio_ffmpeg,bisect
from PIL import Image
p=Path('.');d=p/'variants/FINAL';o=p/'output';c=json.loads((d/'params.json').read_text());fps=c['fps'];N=round(c['duration']*fps);ff=imageio_ffmpeg.get_ffmpeg_exe()
def finish(path):
 cap=cv2.VideoCapture(str(path));r=dict(path=path.name,fps=cap.get(5),size=[int(cap.get(3)),int(cap.get(4))]);n=0;black=[];repeat=[];last=None
 while True:
  ok,im=cap.read()
  if not ok:break
  h=hashlib.sha256(im.tobytes()).hexdigest()
  if im.mean()<1:black.append(n)
  if h==last:repeat.append(n)
  last=h;n+=1
 cap.release();r.update(frames=n,duration=n/r['fps'],blackFrames=black,adjacentExactRepeats=repeat,sha256=hashlib.sha256(path.read_bytes()).hexdigest());assert n and not black;return r
def enc(path,w,h,rate):return subprocess.Popen([ff,'-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(rate),'-i','pipe:0','-an','-c:v','libx264','-crf','17','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
def fitted(src,w,h):
 sh,sw=src.shape[:2];scale=min(w/sw,h/sh);nw,nh=round(sw*scale),round(sh*scale);out=np.full((h,w,3),25,np.uint8);left=(w-nw)//2;top=(h-nh)//2;out[top:top+nh,left:left+nw]=cv2.resize(src,(nw,nh));return out
def at(cap,f):cap.set(1,f);ok,im=cap.read();assert ok;return im
assert len(list((d/'frames').glob('F*.png')))==N
main=o/'PVE-Shot01-ChargeOnly-v10-preview.mp4'
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate',str(fps),'-i',str(d/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(main)],check=True)
meta=[finish(main)];assert meta[0]['frames']==N and not meta[0]['adjacentExactRepeats'];(o/'preview-media-validation.json').write_text(json.dumps(meta[0],indent=2))
ref=json.loads((p/'docs/core-reference.json').read_text());gif=Image.open(ref['path']);refs=[];ends=[];t=0
for i,ms in enumerate(ref['frameDurationMilliseconds']):gif.seek(i);refs.append(cv2.cvtColor(np.array(gif.convert('RGB')),cv2.COLOR_RGB2BGR));t+=ms/1000;ends.append(t)
old=cv2.VideoCapture(r'C:/Users/89trillion/PveMontageShot01V9/output/V9-noCombat.mp4');new=cv2.VideoCapture(str(main));
for name,sources,count in [('GIF-V9-charge-analysis.mp4',['ref','old'],int(ref['duration']*30)),('GIF-V10-charge-comparison.mp4',['ref','new'],int(ref['duration']*30)),('V9-V10-charge-comparison.mp4',['old','new'],round(c['duration']*30))]:
 path=o/name;proc=enc(path,1440,1080,30)
 for f in range(count):
  time=f/30;out=np.full((1080,1440,3),25,np.uint8)
  for j,src in enumerate(sources):
   im=refs[min(len(refs)-1,bisect.bisect_right(ends,time))] if src=='ref' else at(old,f) if src=='old' else at(new,round(time*fps))
   out[64:,j*720:(j+1)*720]=fitted(im,720,1016);label={'ref':'Provided GIF','old':'V9 charge only','new':'V10 charge only'}[src];cv2.putText(out,f'{label} / {time:.3f}s',(j*720+12,35),0,.7,(240,240,240),1)
  proc.stdin.write(out.tobytes())
  if f in [0,30,60,90] and sources==['old','new']:cv2.imwrite(str(o/f'comparison-{f:03}.jpg'),out)
 proc.stdin.close();assert proc.wait()==0;meta.append(finish(path))
# Representative consecutive frames from actual encoded video; no diagnostic geometry.
for page,(start,step) in enumerate([(0,2),(42,2),(110,2),(210,2)]):
 sheet=np.full((4*260,4*360,3),235,np.uint8)
 for j in range(16):
  f=min(N-1,start+j*step);im=at(new,f);x=j%4*360;y=j//4*260;sheet[y+24:y+260,x:x+360]=cv2.resize(im,(360,236));cv2.putText(sheet,f'V10 {f/fps:.3f}s',(x+5,y+18),0,.45,(0,0,0),1)
 cv2.imwrite(str(o/f'encoded-sequence-{page:02}.jpg'),sheet)
old.release();new.release();(o/'preview-evidence-media.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
