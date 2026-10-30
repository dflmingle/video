from pathlib import Path
import json,cv2,numpy as np,subprocess,imageio_ffmpeg,hashlib,csv
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];O=P/'output';D=P/'variants/FINAL';S=json.loads((D/'simulation.json').read_text());C=S['config'];N=round(C['duration']*C['fps']);fps=C['fps'];ff=imageio_ffmpeg.get_ffmpeg_exe();meta=[]
def encode(dest,w,h,rate=fps):return subprocess.Popen([ff,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(rate),'-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','fast','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdin=subprocess.PIPE)
def finish(proc,path,n):
 proc.stdin.close();assert proc.wait()==0;c=cv2.VideoCapture(str(path));rate=c.get(5);size=[int(c.get(3)),int(c.get(4))];count=0
 while c.read()[0]:count+=1
 c.release();assert count==n;meta.append(dict(path=path.name,frames=n,fps=rate,size=size,duration=n/rate,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
def at(c,f):
 c.set(cv2.CAP_PROP_POS_FRAMES,int(f));ok,im=c.read();assert ok;return im
final=O/'PVE-Shot01-U-Archers-v10.mp4';c=cv2.VideoCapture(str(final));fifth=cv2.VideoCapture(str(P/'baseline/PVE-Shot01-U-Archers-v8.mp4'))
# Every decoded final frame is available in bounded sheets for actual visual review.
for page in range((N+15)//16):
 sheet=np.full((1360,960,3),230,np.uint8)
 for j,f in enumerate(range(page*16,min(N,(page+1)*16))):
  x=j%4*240;y=j//4*340;sheet[y+20:y+340,x:x+240]=cv2.resize(at(c,f),(240,320));cv2.putText(sheet,f'V10 F{f:03} {f/fps:.3f}s',(x+4,y+16),0,.42,(0,0,0),1)
 cv2.imencode('.jpg',sheet)[1].tofile(str(O/f'all-encoded-frames-{page:02}.jpg'))
moments=json.loads((O/'key-moments.json').read_text());out=np.full((450,1620,3),25,np.uint8)
for j,m in enumerate(moments):
 f=min(N-1,round(m['time']*fps));old=at(fifth,f);new=at(c,f);out[40:400,j*540:j*540+270]=cv2.resize(old,(270,360));out[40:400,j*540+270:(j+1)*540]=cv2.resize(new,(270,360));cv2.putText(out,m['label'],(j*540+6,24),0,.55,(245,245,245),1)
 cv2.putText(out,f'V8 | V10   same time {f/fps:.3f}s',(j*540+5,427),0,.53,(245,245,245),1)
 # Actual red-group crop chosen from rendered track positions rather than a fake schematic.
 cv2.imencode('.jpg',out)[1].tofile(str(O/'three-key-moments-V8-V10.jpg'))
# Three short continuous windows; no loop or frozen padding.
segments=[]
for m in moments:
 start=max(0,round((m['time']-.25)*fps));end=min(N,round((m['time']+.45)*fps));segments.append(dict(**m,startFrame=start,endFrameExclusive=end))
proc=encode(O/'V8-V10-three-moments.mp4',1080,768);count=0
for m in segments:
 for f in range(m['startFrame'],m['endFrameExclusive']):
  im=np.full((768,1080,3),24,np.uint8);im[48:,:540]=cv2.resize(at(fifth,f),(540,720));im[48:,540:]=cv2.resize(at(c,f),(540,720));cv2.putText(im,f'V8 | {m["label"]} {f/fps:.3f}s',(8,30),0,.55,(245,245,245),1);cv2.putText(im,f'V10 | same actual time',(548,30),0,.55,(245,245,245),1);proc.stdin.write(im.tobytes());count+=1
finish(proc,O/'V8-V10-three-moments.mp4',count);(O/'three-moments-timing.json').write_text(json.dumps(segments,indent=2))
# Full V8/V10 same-time comparison over V10 runtime; V8 is not stretched.
commonN=min(N,int(fifth.get(cv2.CAP_PROP_FRAME_COUNT)));proc=encode(O/'V8-V10-same-time.mp4',1080,768)
for f in range(commonN):
 im=np.full((768,1080,3),24,np.uint8);im[48:,:540]=cv2.resize(at(fifth,f),(540,720));im[48:,540:]=cv2.resize(at(c,f),(540,720));cv2.putText(im,f'V8 {f/fps:.3f}s',(8,30),0,.65,(245,245,245),1);cv2.putText(im,f'V10 {f/fps:.3f}s',(548,30),0,.65,(245,245,245),1);proc.stdin.write(im.tobytes())
finish(proc,O/'V8-V10-same-time.mp4',commonN);fifth.release()
# Diagnostic overlays are composited only on decoded final MP4 crops.
tracked=json.loads((O/'representative-members.json').read_text());checks=json.loads((D/'render-checks.json').read_text());a=np.load(D/'trajectories.npy');states=np.load(D/'member-states.npy');speed=np.linalg.norm(np.diff(a,axis=0,prepend=a[:1])*C['simulationFps'],axis=2);names={0:'RUN',1:'STAGGER',2:'RECOVER',3:'DEAD',4:'LIGHT WOUND',5:'SERIOUS WOUND'}
proc=encode(O/'V10-twelve-member-tracking.mp4',1440,1080)
for f in range(N):
 im=at(c,f);canvas=np.full((1080,1440,3),24,np.uint8);k=round(f/fps*C['simulationFps']);points={x['id']:x for x in checks['screenTracks'][f]}
 for j,x in enumerate(tracked):
  point=points[x['id']];w=144;h=144;left=max(0,min(im.shape[1]-w,round(point['x']-w/2)));top=max(0,min(im.shape[0]-h,round(point['y']-h/2)));tile=cv2.resize(im[top:top+h,left:left+w],(360,280));xx=j%4*360;yy=j//4*360;canvas[yy+70:yy+350,xx:xx+360]=tile
  cv2.circle(canvas,(xx+round((point['x']-left)*360/w),yy+70+round((point['y']-top)*280/h)),15,(50,230,255),1)
  index=x['index'];state=names[int(states[k,index-S['blueCount']])];last=[e['impact'] for e in x['events'] if e['impact']<=f/fps];hit='none' if not last else f'{last[-1]:.3f}s'
  cv2.putText(canvas,f'{x["id"]} {x["model"]}  {f/fps:.3f}s',(xx+5,yy+19),0,.47,(245,245,245),1);cv2.putText(canvas,f'{state} speed {speed[k,index]:.2f} / hit {hit}',(xx+5,yy+40),0,.43,(245,245,245),1);cv2.putText(canvas,f'X {a[k,index,0]:.2f} Z {a[k,index,1]:.2f}',(xx+5,yy+61),0,.44,(245,245,245),1)
 proc.stdin.write(canvas.tobytes())
 if f in [15,round(moments[1]['time']*fps),N-1]:cv2.imencode('.jpg',canvas)[1].tofile(str(O/f'tracked-members-F{f:03}.jpg'))
finish(proc,O/'V10-twelve-member-tracking.mp4',N);c.release()
# Full actual encoder first frame vs PDF diagram.
cap=cv2.VideoCapture(str(final));ok,frame=cap.read();assert ok;cap.release();sheet=Image.new('RGB',(1240,1040),'#eeeeea');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22);ref=Image.open(P/'docs/formation-page-7.png');ref.thumbnail((440,880));shot=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));shot.thumbnail((690,920));sheet.paste(ref,(15,70));sheet.paste(shot,(510,70));draw.text((20,20),'Planning diagram / V10 first frame',font=font,fill='#222222');draw.text((20,980),'Initial IDs and coordinates retained; three 3x3 armies and seven blue squads',font=font,fill='#222222');sheet.save(O/'PDF-vs-V10-first-frame.jpg',quality=92)
# Exact-time counterfactual: same seed, IDs, initial positions and camera rule.
no=cv2.VideoCapture(str(O/'V10-noCombat.mp4'));yes=cv2.VideoCapture(str(final));proc=encode(O/'V10-noCombat-vs-combat.mp4',1080,768)
for f in range(N):
 im=np.full((768,1080,3),24,np.uint8);im[48:,:540]=cv2.resize(at(no,f),(540,720));im[48:,540:]=cv2.resize(at(yes,f),(540,720));cv2.putText(im,f'NO ARROWS / {f/fps:.3f}s',(8,30),0,.6,(245,245,245),1);cv2.putText(im,f'ARROW IMPACTS / {f/fps:.3f}s',(548,30),0,.6,(245,245,245),1);proc.stdin.write(im.tobytes())
 if f==N-1:cv2.imencode('.jpg',im)[1].tofile(str(O/'noCombat-vs-combat-final.jpg'))
finish(proc,O/'V10-noCombat-vs-combat.mp4',N);no.release();yes.release()
(O/'evidence-media.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
