from pathlib import Path
import json,cv2,numpy as np
from media_v11 import encoder,check,jpg,at
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';old=json.loads((D/'v13-red20-states.json').read_text());new=json.loads((D/'red20-states.json').read_text());assert old['indices']==new['indices'];N=min(len(old['frames']),len(new['frames']));assert N==174
path=O/'V13-V14-same20-local-comparison.mp4';proc=encoder(path,2000,1120,60)
for f in range(N):
 out=np.full((1120,2000,3),24,np.uint8)
 for j,(label,folder,states) in enumerate([('V13 fixed personal cruise','v13-red20-frames',old['frames'][f]),('V14 continuous personal control','red20-frames',new['frames'][f])]):
  im=cv2.imread(str(D/f'{folder}/F{f:04}.png'));assert im is not None
  for n,a in enumerate(states):
   x,y=round(a['screenX']),round(a['screenY']);cv2.circle(im,(x,y),10,(0,0,0),3);cv2.circle(im,(x,y),9,(70,240,100),2);cv2.putText(im,str(n+1),(x+10,y-8),0,.42,(0,0,0),3);cv2.putText(im,str(n+1),(x+10,y-8),0,.42,(70,240,100),1)
  out[60:1060,j*1000:(j+1)*1000]=im;cv2.putText(out,f'{label} | {f/60:.3f}s',(j*1000+12,35),0,.7,(240,240,240),1)
  speeds=[a['speed'] for a in states];cv2.putText(out,f'Same 20 IDs / speed range {min(speeds):.1f} - {max(speeds):.1f} / normal time',(j*1000+10,1095),0,.57,(220,220,220),1)
 proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0;meta=check(path);(O/'V14-local-comparison-media.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2));cap=cv2.VideoCapture(str(path));jpg(O/'V13-V14-local-1.7s.jpg',at(cap,1.7));cap.release()
