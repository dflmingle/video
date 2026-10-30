from pathlib import Path
import json,cv2,numpy as np
from scipy.spatial.transform import Rotation
from media_v11 import at,fit,jpg
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';S=json.loads((D/'simulation.json').read_text());U=S['units'];C=S['config'];A=np.load(D/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*60;R=json.loads((D/'render-checks.json').read_text());E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];targeted={e['target'] for e in E};nb=S['blueCount'];never=[i for i in range(nb,len(U)) if i not in targeted];options=[]
for e in E:
 if e['killed'] or e['impact']>2.55:continue
 k=e['impactFrame'];i=e['target'];end=min(len(A)-2,k+25)
 for j in never:
  if U[j]['army']!=U[i]['army']:continue
  d=A[k,j]-A[k,i];later=A[end,j]-A[end,i]
  if abs(d[0])<2.6 and -3<d[1]<0 and later[1]>.2:options.append((later[1]-abs(later[0])*.3,i,j,e))
assert options;_,i,j,e=max(options,key=lambda x:x[0]);times=np.linspace(e['impact']-.1,min(C['duration']-1/60,e['impact']+.45),10)
def point(t,i):
 k=round(t*60);s=R['states'][min(len(R['states'])-1,k)];rot=Rotation.from_quat(s['cameraQuaternion']).as_matrix();p=np.array(s['cameraProjection']).reshape(4,4,order='F');x,z=A[k,i];h=p@np.r_[(np.array([x,.7,z])-s['cameraPosition'])@rot,1];v=h[:3]/h[3];return np.array([(v[0]+1)*C['width']/2,(1-v[1])*C['height']/2]).astype(int)
pts=np.array([point(t,k) for t in times for k in [i,j]]);side=int(max(380,np.ptp(pts,axis=0).max()+150));mid=(pts.min(axis=0)+pts.max(axis=0))/2;x0=int(np.clip(mid[0]-side/2,0,C['width']-side));y0=int(np.clip(mid[1]-side/2,0,C['height']-side));cap=cv2.VideoCapture(str(O/'PVE-Shot01-U-Archers-v13.mp4'));sheet=np.full((2*460,5*460,3),235,np.uint8);rows=[]
for n,t in enumerate(times):
 im=at(cap,float(t));k=round(t*60)
 for index,color,tag in [(i,(255,60,200),'HIT'),(j,(50,255,80),'RUN')]:
  q=point(t,index);cv2.circle(im,tuple(q),15,(0,0,0),4);cv2.circle(im,tuple(q),14,color,2);label=tag+' '+U[index]['id'];p=(q[0]+18,q[1]-15);cv2.putText(im,label,p,0,.52,(0,0,0),3);cv2.putText(im,label,p,0,.52,color,1)
  rows.append(dict(time=k/60,id=U[index]['id'],z=float(A[k,index,1]),vz=float(V[k,index,1]),hit=e['impact'] if index==i else None))
 x=n%5*460;y=n//5*460;sheet[y+40:y+460,x:x+460]=fit(im[y0:y0+side,x0:x0+side],460,420);cv2.putText(sheet,f'{t:.3f}s HIT v={V[k,i,1]:.1f}',(x+7,y+25),0,.53,(0,0,0),1)
jpg(O/'V13-hit-fallbehind-continuous.jpg',sheet);cap.release();(O/'V13-hit-fallbehind-coordinates.json').write_text(json.dumps(dict(event=e,runner=U[j]['id'],rows=rows),indent=2));print(json.dumps(dict(hit=U[i]['id'],runner=U[j]['id'],impact=e['impact']),indent=2))
