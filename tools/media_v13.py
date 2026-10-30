from pathlib import Path
import json,subprocess,cv2,numpy as np
from media_v11 import encoder,check,fit,jpg,at,ff
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';S=json.loads((D/'simulation.json').read_text());C=S['config'];N=round(C['duration']*60)
assert len(list((D/'frames').glob('F*.png')))==N
main=O/'PVE-Shot01-U-Archers-v13.mp4';subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate','60','-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(main)],check=True)
meta=[check(main)];assert meta[0]['frames']==N and not meta[0]['adjacentExactRepeats']
new=cv2.VideoCapture(str(main));old=cv2.VideoCapture(str(P.parent/'PveMontageShot01V12/output/PVE-Shot01-U-Archers-v12.mp4'))
path=O/'V12-V13-realtime-comparison.mp4';proc=encoder(path,1920,1500,60)
for f in range(N):
 t=f/60;out=np.full((1500,1920,3),25,np.uint8)
 for j,(cap,label) in enumerate([(old,'V12 baseline'),(new,'V13 individual deployment / range gate')]):
  out[60:,j*960:(j+1)*960]=fit(at(cap,t),960,1440);cv2.putText(out,f'{label} | {t:.3f}s',(j*960+12,36),0,.58,(240,240,240),1)
 proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0;meta.append(check(path))
E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];release=min(e['release'] for e in E);impact=min(e['impact'] for e in E)
for name,t in [('initial',0),('deployment',1.50),('first-release',release),('first-impact',impact),('late',C['duration']-1/60)]:jpg(O/f'V13-{name}.jpg',at(new,t))
sheet=np.full((1200,2000,3),235,np.uint8)
for j,t in enumerate(np.linspace(0,(N-1)/60,10)):
 x=j%5*400;y=j//5*600;sheet[y+30:y+600,x:x+400]=fit(at(new,float(t)),400,570);cv2.putText(sheet,f'V13 {t:.3f}s',(x+8,y+21),0,.55,(0,0,0),1)
jpg(O/'V13-encoded-overview.jpg',sheet)
for page,start in enumerate([84,round(impact*60)-5,N-19]):
 sheet=np.full((1260,1680,3),235,np.uint8)
 for j in range(18):
  f=min(N-1,start+j);x=j%6*280;y=j//6*420;sheet[y+28:y+420,x:x+280]=fit(at(new,f/60),280,392);cv2.putText(sheet,f'{f/60:.3f}s',(x+6,y+21),0,.5,(0,0,0),1)
 jpg(O/f'V13-consecutive-{page}.jpg',sheet)
old.release();new.release();(O/'V13-media-validation.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
