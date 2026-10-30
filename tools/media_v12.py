from pathlib import Path
import json, subprocess,cv2,numpy as np
from scipy.spatial.transform import Rotation
from media_v11 import encoder,check,fit,jpg,at,ff
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';C=json.loads((D/'params.json').read_text());S=json.loads((D/'simulation.json').read_text());U=S['units'];A=np.load(D/'trajectories.npy');nb=S['blueCount'];N=round(C['duration']*60)
assert len(list((D/'frames').glob('F*.png')))==N
main=O/'PVE-Shot01-U-Archers-v12.mp4'
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate','60','-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(main)],check=True)
meta=[check(main)];assert meta[0]['frames']==N and not meta[0]['adjacentExactRepeats']
new=cv2.VideoCapture(str(main));old=cv2.VideoCapture(str(P.parent/'PveMontageShot01V11/output/camera-revision/PVE-Shot01-U-Archers-v11-close.mp4'))
path=O/'V11-V12-same-camera-realtime.mp4';proc=encoder(path,1920,1500,60)
for f in range(N):
 t=f/60;out=np.full((1500,1920,3),25,np.uint8)
 for j,(cap,label) in enumerate([(old,'V11 close / 1.0x world speed'),(new,'V12 / 1.5x nominal world speed')]):
  out[60:,j*960:(j+1)*960]=fit(at(cap,t),960,1440);cv2.putText(out,f'{label} | {t:.3f}s',(j*960+12,36),0,.60,(240,240,240),1)
 proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0;meta.append(check(path))
E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];first=min(e['impact'] for e in E)
times=[max(0,first-.10),first+.10,C['duration']-.1]
sheet=np.full((1200,1600,3),235,np.uint8)
for col,t in enumerate(times):
 for row,(cap,label) in enumerate([(old,'V11'),(new,'V12')]):
  x=col*532;y=row*600;sheet[y+40:y+600,x:x+532]=fit(at(cap,t),532,560);cv2.putText(sheet,f'{label} {t:.3f}s',(x+10,y+27),0,.6,(0,0,0),1)
jpg(O/'V11-V12-before-after-sustained.jpg',sheet)
for name,t in [('initial',0),('before-first-hit',times[0]),('after-first-hit',times[1]),('sustained',times[2])]:jpg(O/f'V12-{name}.jpg',at(new,t))
sheet=np.full((1200,2000,3),235,np.uint8)
for j,t in enumerate(np.linspace(0,(N-1)/60,10)):
 x=j%5*400;y=j//5*600;sheet[y+30:y+600,x:x+400]=fit(at(new,float(t)),400,570);cv2.putText(sheet,f'V12 {t:.3f}s',(x+10,y+22),0,.55,(0,0,0),1)
jpg(O/'V12-encoded-overview.jpg',sheet)
# Use one fixed world-to-screen mapping for both videos and all evidence frames.
R=json.loads((D/'render-checks.json').read_text());state=R['states'][0];rot=Rotation.from_quat(state['cameraQuaternion']).as_matrix();proj=np.array(state['cameraProjection']).reshape(4,4,order='F');origin=np.array(state['cameraPosition'])
def center(t,i):
 f=np.clip(t*60,0,len(A)-1);a=int(f);b=min(len(A)-1,a+1);q=A[a,i]*(1-f+a)+A[b,i]*(f-a);h=proj@np.r_[(np.array([q[0],.7,q[1]])-origin)@rot,1];v=h[:3]/h[3];return np.array([(v[0]+1)*C['width']/2,(1-v[1])*C['height']/2])
hits={e['target'] for e in E};never=[i for i in range(nb,len(U)) if i not in hits];options=[]
for e in E:
 if e['killed'] or e['impact']>2.55 or U[e['target']]['army']!=2:continue
 i=e['target'];k=e['impactFrame'];end=min(len(A)-1,k+28)
 for j in never:
  if U[j]['army']!=2:continue
  delta=A[k,j]-A[k,i];later=A[end,j]-A[end,i]
  if abs(delta[0])<2.6 and -4<delta[1]<-.15 and later[1]>.1:options.append((later[1]-abs(later[0])*.2,i,j,e))
assert options;_,target,runner,event=max(options,key=lambda q:q[0]);start=event['impact']-.12;end=min((N-1)/60,event['impact']+.65)
pts=np.array([center(t,i) for t in np.linspace(start,end,20) for i in [target,runner]]);mid=(pts.min(axis=0)+pts.max(axis=0))/2;side=int(max(420,np.ptp(pts,axis=0).max()+150));x0=int(np.clip(mid[0]-side/2,0,C['width']-side));y0=int(np.clip(mid[1]-side/2,0,C['height']-side))
def crop(t):
 im=at(new,t)
 for i,color,label in [(target,(30,210,255),'HIT '+U[target]['id']),(runner,(70,240,70),'RUN '+U[runner]['id'])]:
  q=center(t,i).astype(int);cv2.circle(im,tuple(q),14,color,2);cv2.putText(im,label,(q[0]+14,q[1]-10),0,.52,color,1)
 return im[y0:y0+side,x0:x0+side]
sheet=np.full((1200,1600,3),235,np.uint8)
for j,t in enumerate(np.linspace(start,end,12)):
 x=j%4*400;y=j//4*400;sheet[y+40:y+400,x:x+400]=fit(crop(float(t)),400,360);k=round(t*60);z=A[k,target,1];cv2.putText(sheet,f'{t:.3f}s HIT z={z:.2f}',(x+7,y+25),0,.49,(0,0,0),1)
jpg(O/'V12-hit-runner-continuous.jpg',sheet)
path=O/'V12-hit-runner-detail-realtime.mp4';proc=encoder(path,1000,1060,60)
for k in range(round((end-start)*60)):
 t=start+k/60;im=np.full((1060,1000,3),25,np.uint8);im[60:]=fit(crop(t),1000,1000);cv2.putText(im,f'1.0x | {t:.3f}s | hit {event["impact"]:.3f}s',(15,37),0,.7,(240,240,240),1);proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0;meta.append(check(path))
# Exact consecutive encoded frames around the first impact and during sustained charge.
for page,startFrame in enumerate([round(first*60)-6,round(first*60)+6,N-19]):
 sheet=np.full((3*420,6*280,3),235,np.uint8)
 for j in range(18):
  f=min(N-1,startFrame+j);x=j%6*280;y=j//6*420;sheet[y+28:y+420,x:x+280]=fit(at(new,f/60),280,392);cv2.putText(sheet,f'{f/60:.3f}s',(x+6,y+21),0,.5,(0,0,0),1)
 jpg(O/f'V12-consecutive-{page}.jpg',sheet)
old.release();new.release();(O/'V12-media-validation.json').write_text(json.dumps(meta,indent=2));(O/'V12-impact-evidence.json').write_text(json.dumps(dict(event=event,hitMember=U[target]['id'],unhitMember=U[runner]['id'],interval=[start,end],comparisonMoments=times,crop=[x0,y0,side,side]),indent=2));print(json.dumps(meta,indent=2))
