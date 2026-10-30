from pathlib import Path
import json,subprocess,cv2,numpy as np
from media_v11 import encoder,check,fit,jpg,at,ff
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';S=json.loads((D/'simulation.json').read_text());C=S['config'];N=round(C['duration']*60)
assert len(list((D/'frames').glob('F*.png')))==N
main=O/'PVE-Shot01-U-Archers-v14.mp4';subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate','60','-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(main)],check=True)
meta=[check(main)];assert meta[0]['frames']==N and not meta[0]['adjacentExactRepeats']
new=cv2.VideoCapture(str(main));old=cv2.VideoCapture(str(P.parent/'PveMontageShot01V13/output/PVE-Shot01-U-Archers-v13.mp4'))
oldN=int(old.get(cv2.CAP_PROP_FRAME_COUNT));common=min(N,oldN);path=O/'V13-V14-realtime-comparison.mp4';proc=encoder(path,1920,1500,60)
# Only the shared time span; never freeze V13's ending to match V14.
for f in range(common):
 ok0,im0=old.read();ok1,im1=new.read();assert ok0 and ok1;out=np.full((1500,1920,3),25,np.uint8)
 for j,(im,label) in enumerate([(im0,'V13 fixed personal cruise'),(im1,'V14 continuous individual control')]):
  out[60:,j*960:(j+1)*960]=fit(im,960,1440);cv2.putText(out,f'{label} | {f/60:.3f}s',(j*960+12,36),0,.58,(240,240,240),1)
 proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0;meta.append(check(path))
E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];impact=min(e['impact'] for e in E)
for name,t in [('initial',0),('early',.75),('cruise',1.5),('first-impact',impact),('late',(N-1)/60)]:jpg(O/f'V14-{name}.jpg',at(new,t))
sheet=np.full((1200,2000,3),235,np.uint8)
for j,t in enumerate(np.linspace(0,(N-1)/60,10)):
 x=j%5*400;y=j//5*600;sheet[y+30:y+600,x:x+400]=fit(at(new,float(t)),400,570);cv2.putText(sheet,f'V14 {t:.3f}s',(x+8,y+21),0,.55,(0,0,0),1)
jpg(O/'V14-encoded-overview.jpg',sheet)
for page,start in enumerate([45,93,round(impact*60)-4,N-19]):
 sheet=np.full((1260,1680,3),235,np.uint8)
 for j in range(18):
  f=min(N-1,start+j);x=j%6*280;y=j//6*420;sheet[y+28:y+420,x:x+280]=fit(at(new,f/60),280,392);cv2.putText(sheet,f'{f/60:.3f}s',(x+6,y+21),0,.5,(0,0,0),1)
 jpg(O/f'V14-consecutive-{page}.jpg',sheet)
old.release();new.release();(O/'V14-media-validation.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
