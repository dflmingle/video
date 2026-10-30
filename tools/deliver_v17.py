from pathlib import Path
import json,math,shutil,cv2,numpy as np,subprocess
from media_v11 import ff,check,encoder,at,fit,jpg
P=Path(__file__).resolve().parents[1];O=P/'output';S=json.loads((P/'variants/FINAL/simulation.json').read_text(encoding='utf-8'));C=S['config']
main=O/'PVE-Shot01-U-Archers-v17.mp4';shutil.copy2(O/'V17-FINAL-FIXED.mp4',main);validation=[]
def compare(name,sources):
 caps=[cv2.VideoCapture(str(p)) for p,label in sources];dur=min(c.get(7)/c.get(5) for c in caps);n=math.floor(dur*30);proc=encoder(O/name,len(caps)*720,1280)
 for f in range(n):
  t=f/30;im=np.full((1280,len(caps)*720,3),25,np.uint8)
  for j,(cap,(_,label)) in enumerate(zip(caps,sources)):
   im[60:,j*720:(j+1)*720]=fit(at(cap,t),720,1220);cv2.putText(im,f'{label} / {t:.3f}s',(j*720+10,25),0,.55,(235,235,235),1);cv2.putText(im,'SAME REAL TIME / no retiming',(j*720+10,49),0,.46,(200,200,200),1)
  proc.stdin.write(im.tobytes())
 proc.stdin.close();assert proc.wait()==0
 for cap in caps:cap.release()
 validation.append(check(O/name))
compare('V16-V17-same-time-same-camera.mp4',[(O/'V17-BASELINE-FIXED.mp4','V16 motion / V17 fixed camera'),(main,'V17 motion / V17 fixed camera')])
compare('V17-fixed-vs-continuous-push.mp4',[(O/'V17-FINAL-FIXED-preview.mp4','FIXED / complete initial armies'),(O/'V17-FINAL-PUSH-preview.mp4','CONTINUOUS PUSH / alternative')])
cap=cv2.VideoCapture(str(main));events=S['events'];release=min(e['release'] for e in events);hit=min(e['impact'] for e in events if e['resolution']=='IMPACT_IN_SHOT')
for label,t in [('initial',0),('first-release',release),('first-hit',hit),('before-end',C['duration']-1/60)]:jpg(O/f'V17-{label}.jpg',at(cap,t))
pdf=cv2.imread(str(P/'docs/pdf-page-07.png'));out=np.full((1440,1920,3),25,np.uint8);out[50:,:960]=fit(pdf,960,1390);out[50:,960:]=fit(at(cap,0),960,1390);cv2.putText(out,'PDF7 / formation 1',(16,32),0,.7,(240,240,240),1);cv2.putText(out,'V17 / exact original world positions',(976,32),0,.65,(240,240,240),1);jpg(O/'PDF-V17-initial.jpg',out)
# Three CONTINUOUS portions of the local recording, no normalized-time remap.
local=O/'V17-FINAL-REDLOCAL-preview.mp4';lc=cv2.VideoCapture(str(local));proc=encoder(O/'V17-red-distance-stages.mp4',1920,1000)
segments=[(0,.45,'FAR / 0.00-0.45s'),(.85,1.30,'MID / 0.85-1.30s'),(1.85,2.30,'ARROW ZONE / 1.85-2.30s')]
for f in range(13):
 im=np.full((1000,1920,3),25,np.uint8)
 for j,(start,end,label) in enumerate(segments):
  t=start+f/30;im[60:,j*640:(j+1)*640]=fit(at(lc,t),640,940);cv2.putText(im,label,(j*640+10,25),0,.55,(235,235,235),1);cv2.putText(im,f'SOURCE {t:.3f}s',(j*640+10,49),0,.5,(200,200,200),1)
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0;lc.release();validation.append(check(O/'V17-red-distance-stages.mp4'))
# Encoded archer closeup validates per-member continuous states, separate video.
shutil.copy2(O/'V17-FINAL-ARCHERS-preview.mp4',O/'V17-archer-independent-behavior.mp4')
for tag,path in [('archers',O/'V17-archer-independent-behavior.mp4'),('red-local',local)]:
 cc=cv2.VideoCapture(str(path));sheet=np.full((1200,2120,3),235,np.uint8)
 for j,t in enumerate(np.linspace(.8,C['duration']-1/30,12)):
  x=j%4*530;y=j//4*400;sheet[y+28:y+400,x:x+530]=fit(at(cc,float(t)),530,372);cv2.putText(sheet,f'{t:.3f}s',(x+8,y+20),0,.5,(0,0,0),1)
 jpg(O/f'V17-{tag}-continuous-overview.jpg',sheet);cc.release()
cap.release();validation.extend([check(main),check(O/'V17-archer-independent-behavior.mp4')]);(O/'V17-deliverable-media.json').write_text(json.dumps(validation,indent=2));print(json.dumps(validation,indent=2))
