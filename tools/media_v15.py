from pathlib import Path
import json,cv2,numpy as np,sys,subprocess,hashlib
from media_v11 import ff,encoder,check,jpg,at,fit
P=Path(__file__).resolve().parents[1];O=P/'output';variant=sys.argv[1] if len(sys.argv)>1 else 'LOCAL';D=P/'variants'/variant;C=json.loads((D/'params.json').read_text());R=json.loads((D/'render-checks.json').read_text());N=round(C['duration']*60)
assert len(R['states'])==N and not R['errors'] and all(s['identical'] for s in R['seeks'])
for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h,p
if variant=='LOCAL':
 name='V15-50-members-5s-validation.mp4';path=O/name;proc=encoder(path,1700,1180,60)
 for f,rows in enumerate(R['frames']):
  im=cv2.imread(str(D/f'frames/F{f:04}.png'));out=np.full((1180,1700,3),23,np.uint8)
  for i,r in enumerate(rows):
   if not (-30<r['screenX']<1130 and -30<r['screenY']<1130):continue
   x,y=round(r['screenX']),round(r['screenY']);color=(60,220,90) if i>=20 else (70,230,230)
   if r['state']=='DEAD':color=(70,70,240)
   cv2.putText(im,str(i+1),(x+8,y-5),0,.38,(0,0,0),3);cv2.putText(im,str(i+1),(x+8,y-5),0,.38,color,1)
  out[50:1150,:1100]=im
  cv2.putText(out,f'V15 / 50 real characters / {f/60:.3f}s / normal time',(15,32),0,.7,(240,240,240),1)
  for i,r in enumerate(rows[:20]):
   y=90+i*50;cv2.putText(out,f'{i+1:02} {r["id"]} {r["state"]}',(1110,y),0,.48,(80,220,230),1);cv2.putText(out,f'v {r["speed"]:5.2f} target {r["targetSpeed"]:5.2f} phase {r["phaseFloat"]:5.2f}',(1110,y+17),0,.43,(235,235,235),1);cv2.putText(out,f'cadence {r["cadence"]:.2f} stride {r["stride"]:.2f}',(1110,y+33),0,.43,(195,195,195),1)
  cv2.putText(out,'Fixture: member 1 falls at 1.5s; member 7 wounded at 1.8s. No battle arrows.',(18,1172),0,.53,(220,220,220),1);proc.stdin.write(out.tobytes())
 proc.stdin.close();assert proc.wait()==0
else:
 name='PVE-Shot01-U-Archers-v15.mp4';path=O/name
 subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate','60','-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
meta=check(path);assert meta['frames']==N and not meta['adjacentExactRepeats'];(O/f'V15-{variant}-media.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2));cap=cv2.VideoCapture(str(path))
for label,t in [('initial',0),('cruise',1.1),('avoid',min(2.6,C['duration']-.05)),('end',C['duration']-1/60)]:jpg(O/f'V15-{variant}-{label}.jpg',at(cap,t))
sheet=np.full((1200,2000,3),235,np.uint8)
for j,t in enumerate(np.linspace(0,C['duration']-1/60,10)):
 x=j%5*400;y=j//5*600;sheet[y+30:y+600,x:x+400]=fit(at(cap,float(t)),400,570);cv2.putText(sheet,f'{t:.3f}s',(x+8,y+21),0,.55,(0,0,0),1)
jpg(O/f'V15-{variant}-overview.jpg',sheet)
for page,start in enumerate(([54,117,210] if variant=='LOCAL' else [54,120,N-14])):
 sheet=np.full((1200,2120,3),235,np.uint8)
 for j in range(12):
  f=min(N-1,start+j);x=j%4*530;y=j//4*400;sheet[y+28:y+400,x:x+530]=fit(at(cap,f/60),530,372);cv2.putText(sheet,f'{f/60:.3f}s',(x+8,y+20),0,.5,(0,0,0),1)
 jpg(O/f'V15-{variant}-consecutive-{page}.jpg',sheet)
cap.release()
