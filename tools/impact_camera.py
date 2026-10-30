from pathlib import Path
import json,math,cv2,numpy as np
from scipy.spatial.transform import Rotation
from media_v11 import encoder,check,jpg,fit
P=Path(__file__).resolve().parents[1];D=P/'variants/CAMERA-B';O=P/'output/camera-revision';S=json.loads((D/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*C['simulationFps'];E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];first={}
for e in sorted(E,key=lambda e:e['impact']):first.setdefault(e['target'],e)
never=[i for i in range(nb,len(U)) if i not in first];options=[]
for e in E:
 if e['killed'] or not 2.3<=e['impact']<=3.25:continue
 i=e['target'];k=e['impactFrame'];end=min(len(A)-1,k+48)
 for j in never:
  if U[j]['army']!=U[i]['army']:continue
  delta=A[k,j]-A[k,i];later=A[end,j]-A[end,i]
  if abs(delta[0])<2.4 and -4<delta[1]<-.4 and later[1]>1 and abs(later[0])<4:
   options.append((later[1]-abs(later[0])*.4,i,j,e))
assert options;_,target,runner,event=max(options,key=lambda q:q[0]);impact=event['impact'];start=max(0,impact-.25);end=min(C['duration']-1/C['fps'],impact+.9)
R=json.loads((D/'render-checks.json').read_text());state=R['states'][0];rot=Rotation.from_quat(state['cameraQuaternion']).as_matrix();proj=np.array(state['cameraProjection']).reshape(4,4,order='F');origin=np.array(state['cameraPosition'])
def point(xyz):
 q=(np.array(xyz)-origin)@rot;h=proj@np.r_[q,1];ndc=h[:3]/h[3];return np.array([(ndc[0]+1)*C['width']/2,(1-ndc[1])*C['height']/2])
def center(t,i):
 f=np.clip(t*C['simulationFps'],0,len(A)-1);a=int(f);b=min(len(A)-1,a+1);q=A[a,i]*(1-f+a)+A[b,i]*(f-a);return point([q[0],.7,q[1]])
pts=np.array([center(t,i) for t in np.linspace(start,end,30) for i in [target,runner]]);mid=(pts.min(axis=0)+pts.max(axis=0))/2;side=max(430,float(np.ptp(pts,axis=0).max()+170));x0=int(np.clip(mid[0]-side/2,0,C['width']-side));y0=int(np.clip(mid[1]-side/2,0,C['height']-side));side=int(side)
cap=cv2.VideoCapture(str(O/'PVE-Shot01-U-Archers-v11-close.mp4'))
def frame(t):
 cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,im=cap.read();assert ok
 for i,color,label in [(target,(30,210,255),'HIT '+U[target]['id']),(runner,(70,240,70),'RUN '+U[runner]['id'])]:
  q=center(t,i).astype(int);cv2.circle(im,tuple(q),15,color,2);cv2.putText(im,label,(q[0]+18,q[1]-12),0,.6,color,2)
 return im[y0:y0+side,x0:x0+side]
sheet=np.full((3*390,4*390,3),235,np.uint8)
for k,t in enumerate(np.linspace(start,end,12)):
 crop=frame(float(t));x=k%4*390;y=k//4*390;sheet[y+36:y+390,x:x+390]=fit(crop,390,354);cv2.putText(sheet,f'{t:.3f}s / hit {impact:.3f}s',(x+7,y+23),0,.45,(0,0,0),1)
jpg(O/'V11-hit-fallbehind-continuous.jpg',sheet)
path=O/'V11-hit-fallbehind-slowmotion.mp4';proc=encoder(path,1000,1060,60);count=round((end-start)*120)
for k in range(count):
 t=start+k/120;out=np.full((1060,1000,3),25,np.uint8);out[60:]=fit(frame(t),1000,1000);cv2.putText(out,f'0.5x | {t:.3f}s | hit {impact:.3f}s',(18,36),0,.7,(240,240,240),1);proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0
# Arrow source and direction before flight, mid-flight and near impact.
e=next(e for e in sorted(E,key=lambda e:e['release']) if .1<e['impact']-e['release']<1.1)
sheet=np.full((2*650,3*480,3),235,np.uint8)
for j,t in enumerate([e['release']-.08,e['release'],e['release']+.08,(e['release']+e['impact'])/2,e['impact']-.04,e['impact']+.08]):
 cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,im=cap.read();assert ok
 f=np.clip((t-e['release'])/(e['impact']-e['release']),0,1);a=np.array(e['origin']);b=np.array(e['destination']);q=a*(1-f)+b*f;q[1]+=4*e['arc']*f*(1-f);screen=point(q).astype(int);cv2.circle(im,tuple(screen),18,(40,150,255),2)
 x=j%3*480;y=j//3*650;sheet[y+42:y+650,x:x+480]=fit(im,480,608);cv2.putText(sheet,f'{e["id"]} {t:.3f}s',(x+8,y+25),0,.55,(0,0,0),1)
jpg(O/'V11-arrow-lifecycle.jpg',sheet)
# Separate death continuation: the body's authoritative position remains fixed.
fatal=next(e for e in E if e['killed'] and e['impact']<3.25 and U[e['target']]['army']==2)
sheet=np.full((2*420,4*420,3),235,np.uint8)
for j,t in enumerate(np.linspace(fatal['impact']-.12,fatal['impact']+.78,8)):
 cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,im=cap.read();assert ok
 q=center(t,fatal['target']).astype(int);cv2.circle(im,tuple(q),17,(40,170,255),2)
 size=280;left=int(np.clip(q[0]-size//2,0,C['width']-size));top=int(np.clip(q[1]-size//2,0,C['height']-size));crop=im[top:top+size,left:left+size]
 x=j%4*420;y=j//4*420;sheet[y+36:y+420,x:x+420]=fit(crop,420,384);cv2.putText(sheet,f'{fatal["targetID"]} {t:.3f}s',(x+8,y+24),0,.55,(0,0,0),1)
jpg(O/'V11-death-continuous.jpg',sheet);cap.release()
result=dict(selectedEvent=event,target=U[target]['id'],unhitRunner=U[runner]['id'],sourceInterval=[start,end],crop=[x0,y0,side,side],annotations='Diagnostic rings only; main movie has no overlays',video=check(path))
(O/'V11-impact-evidence.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:result[k] for k in ['target','unhitRunner','sourceInterval','video']},indent=2))
