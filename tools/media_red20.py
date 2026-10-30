from pathlib import Path
import json,cv2,numpy as np,csv
from media_v11 import encoder,check,fit,jpg,at
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';R=json.loads((D/'red20-states.json').read_text());frames=R['frames'];N=len(frames);C=json.loads((D/'params.json').read_text());assert N==180 and len(R['indices'])==20 and not R['errors']
path=O/'V14-red20-continuous-behavior.mp4';proc=encoder(path,1600,1200,60)
colors={'YIELD':(40,160,255),'PASS':(220,200,70),'PUSH':(90,250,120),'SETTLE':(230,190,100),'CHARGE':(130,230,150),'WOUNDED':(90,160,240),'STAGGER':(70,140,255),'DEAD':(70,80,220),'WAIT':(160,160,160),'ACCELERATE':(180,250,190)};rows=[]
for f,states in enumerate(frames):
 out=np.full((1200,1600,3),24,np.uint8);im=cv2.imread(str(D/f'red20-frames/F{f:04}.png'));assert im is not None
 for n,a in enumerate(states):
  x,y=round(a['screenX']),round(a['screenY']);color=colors.get(a['state'],(210,210,210));cv2.circle(im,(x,y),11,(0,0,0),4);cv2.circle(im,(x,y),10,color,2);cv2.putText(im,str(n+1),(x+11,y-8),0,.45,(0,0,0),3);cv2.putText(im,str(n+1),(x+11,y-8),0,.45,color,1)
  tx=1012;ty=91+n*51;cv2.putText(out,f'{n+1:02} {a["id"]} {a["state"]}',(tx,ty),0,.55,color,1);cv2.putText(out,f'v {a["speed"]:4.1f} target {a["targetSpeed"]:4.1f} a {a["acceleration"]:5.1f}',(tx,ty+18),0,.43,(230,230,230),1);cv2.putText(out,f'Hz {a["cadence"]:.2f} stride {a["stride"]:.2f} phase {a["phase"]:02}',(tx,ty+34),0,.43,(200,200,200),1)
  rows.append(dict(time=f/60,**{k:a[k] for k in ['id','state','speed','targetSpeed','acceleration','stride','cadence','phase','phaseFloat','x','z','posture','armSwing','turn','reason','hitAge']}))
 out[60:1060,:1000]=im;cv2.putText(out,f'V14 | same squad 20 members | {f/60:.3f}s | REAL TIME',(15,34),0,.75,(240,240,240),1);cv2.putText(out,'Actual simulation / original character assets / diagnostic camera only',(15,1105),0,.6,(220,220,220),1)
 proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0
with (O/'V14-rendered-red20-states.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
meta=check(path);assert meta['frames']==180 and not meta['adjacentExactRepeats'];(O/'V14-red20-media.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
cap=cv2.VideoCapture(str(path))
for label,t in [('start',.20),('cruise-1',.90),('cruise-2',1.7),('avoidance',2.70)]:jpg(O/f'V14-red20-{label}.jpg',at(cap,t))
cap.release()
