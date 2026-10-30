"""Encode comparisons from decoded deliverables. No time retiming or end holds."""
from pathlib import Path
import json,math,shutil,cv2,numpy as np,subprocess
from media_v11 import ff,check,encoder,at,fit,jpg
P=Path(__file__).resolve().parents[1];O=P/'output';V15=P.parent/'PveMontageShot01V15/output/PVE-Shot01-U-Archers-v15.mp4'
main=O/'PVE-Shot01-U-Archers-v16.mp4';shutil.copy2(O/'V16-FAST125-FIXED.mp4',main)
shutil.copy2(O/'V16-BASE100-FIXED.mp4',O/'V16-1x-longer-battle.mp4')
validation=[]
def compare(name,sources,height=1280):
 caps=[cv2.VideoCapture(str(p)) for p,label in sources];dur=min(c.get(7)/c.get(5) for c in caps);n=math.floor(dur*30)
 width=720*len(caps);proc=encoder(O/name,width,height)
 for f in range(n):
  t=f/30;im=np.full((height,width,3),25,np.uint8)
  for j,(cap,(_,label)) in enumerate(zip(caps,sources)):
   im[64:,j*720:(j+1)*720]=fit(at(cap,t),720,height-64)
   cv2.putText(im,f'{label}  {t:.3f}s',(j*720+12,26),0,.60,(240,240,240),1)
   cv2.putText(im,'REAL TIME / no playback acceleration',(j*720+12,51),0,.43,(190,190,190),1)
  proc.stdin.write(im.tobytes())
 proc.stdin.close();assert proc.wait()==0
 for cap in caps:cap.release()
 validation.append(check(O/name))
compare('V15-V16-same-time.mp4',[(V15,'V15 original'),(main,'V16 fixed / world speed 1.25x')])
compare('V16-camera-fixed-vs-follow.mp4',[(O/'V16-FAST125-FIXED-preview.mp4','FIXED / 1.25x'),(O/'V16-FAST125-FOLLOW-preview.mp4','SMOOTH FOLLOW / 1.25x')])
compare('V16-world-speed-1x-125x-150x.mp4',[(O/'V16-BASE100-FIXED-preview.mp4','world speed 1.0x'),(O/'V16-FAST125-FIXED-preview.mp4','world speed 1.25x'),(O/'V16-FAST150-FIXED-preview.mp4','world speed 1.5x')])
old=cv2.VideoCapture(str(V15));new=cv2.VideoCapture(str(main))
for label,t in [('initial',0),('charge',1.),('first-hit',1.8333333333),('late-charge',2.25)]:
 out=np.full((1440,1920,3),25,np.uint8)
 for j,(cap,title) in enumerate([(old,'V15'),(new,'V16')]):
  out[50:,j*960:(j+1)*960]=fit(at(cap,t),960,1390);cv2.putText(out,f'{title}  SAME TIME {t:.3f}s',(j*960+12,31),0,.7,(235,235,235),1)
 jpg(O/f'V15-V16-{label}.jpg',out)
S=json.loads((P/'variants/FAST125/simulation.json').read_text());R=json.loads((O/'captures/FAST125-FIXED/render-checks.json').read_text())
# Fixed crop around a causal fatal event: preserve its initial screen location
# so the uninjured neighbours visibly pass, rather than tracking the victim.
death=next(e for e in S['events'] if e.get('killed') and e['impact']<S['config']['duration']-.12)
f=death['impactFrame'];person=R['frames'][f][death['target']];cx,cy=int(person['screenX']),int(person['screenY']);x=max(0,min(1440-640,cx-320));y=max(0,min(2160-640,cy-320))
times=[max(0,death['impact']-.05)+i/60 for i in range(18)];times=[t for t in times if t<S['config']['duration']-1/60]
sheet=np.full((3*380,6*380,3),235,np.uint8)
for j,t in enumerate(times):
 im=at(new,t);crop=im[y:y+640,x:x+640];xx=j%6*380;yy=j//6*380
 sheet[yy+28:yy+380,xx:xx+380]=fit(crop,380,352);cv2.putText(sheet,f'{t:.3f}s',(xx+6,yy+20),0,.5,(0,0,0),1)
jpg(O/'V16-hit-dropout-consecutive.jpg',sheet)
rows=[]
for frame in R['frames']:
 u=frame[death['target']];rows.append({k:u[k] for k in ['id','x','z','state','speed','phaseFloat','hitAge']})
(O/'V16-inspected-causal-event.json').write_text(json.dumps(dict(event=death,crop=[x,y,640,640],times=times,member=rows),indent=2))
old.release();new.release()
clip=O/'V16-continuous-charge-clip.mp4'
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-ss','0.50','-i',str(main),'-an','-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(clip)],check=True)
validation.extend([check(main),check(O/'V16-1x-longer-battle.mp4'),check(clip)])
(O/'V16-deliverable-media.json').write_text(json.dumps(validation,indent=2));print(json.dumps(validation,indent=2))
