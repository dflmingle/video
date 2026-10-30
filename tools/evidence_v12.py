from pathlib import Path
import json,csv,cv2,numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from media_v11 import at,jpg,fit,encoder,check
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';S=json.loads((D/'simulation.json').read_text());C=S['config'];U=S['units'];A=np.load(D/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*60;E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];nb=S['blueCount']
M=json.loads((O/'V12-impact-evidence.json').read_text());target=M['event']['target'];runner=next(i for i,u in enumerate(U) if u['id']==M['unhitMember']);impact=M['event']['impact']
ids=[r['index'] for r in json.loads((O/'representative-members.json').read_text())];ids=list(dict.fromkeys([target,runner]+ids))
first={}
for e in E:first.setdefault(e['target'],e['impact'])
fig,axes=plt.subplots(2,1,figsize=(12,8),sharex=True)
for i in ids[:12]:
 color=None;line,=axes[0].plot(np.arange(len(A))/60,A[:,i,1]-A[0,i,1],label=U[i]['id'],lw=1.25);color=line.get_color();axes[1].plot(np.arange(len(A))/60,V[:,i,1],color=color,lw=1.1)
 if i in first:
  k=round(first[i]*60);axes[0].scatter(first[i],A[k,i,1]-A[0,i,1],color=color,s=25,marker='x');axes[1].scatter(first[i],V[k,i,1],color=color,s=25,marker='x')
axes[0].set_ylabel('Forward advance (world units)');axes[1].set_ylabel('Forward speed (world units / sec)');axes[1].set_xlabel('Actual shot seconds');axes[0].legend(ncol=6,fontsize=8);axes[0].set_title('V12 member trajectories: crosses mark first bound arrow impacts')
for ax in axes:ax.grid(alpha=.25);ax.axhline(0,color='black',lw=.8)
fig.tight_layout();fig.savefig(O/'V12-member-position-speed.png',dpi=140);plt.close(fig)
rows=[]
for t in [impact-.10,impact+.05,impact+.14,impact+.32,min(3.0,impact+.55)]:
 k=round(t*60)
 for i in [target,runner]:rows.append(dict(time=k/60,id=U[i]['id'],x=float(A[k,i,0]),z=float(A[k,i,1]),vz=float(V[k,i,1]),firstHit=first.get(i),death=U[i]['deathTime']))
(O/'V12-selected-member-evidence.json').write_text(json.dumps(rows,indent=2))
# Encoded-frame overlays use high contrast labels; never modify the main MP4.
state=json.loads((D/'render-checks.json').read_text())['states'][0];rot=Rotation.from_quat(state['cameraQuaternion']).as_matrix();proj=np.array(state['cameraProjection']).reshape(4,4,order='F');origin=np.array(state['cameraPosition'])
def center(t,i):
 k=round(t*60);x,z=A[k,i];h=proj@np.r_[(np.array([x,.7,z])-origin)@rot,1];v=h[:3]/h[3];return np.array([(v[0]+1)*C['width']/2,(1-v[1])*C['height']/2]).astype(int)
start=max(0,impact-.12);end=min((len(A)-2)/60,impact+.6)
allpts=np.array([center(t,i) for t in np.linspace(start,end,15) for i in [target,runner]])
side=int(max(440,np.ptp(allpts,axis=0).max()+200));mid=(allpts.min(axis=0)+allpts.max(axis=0))/2;x0=int(np.clip(mid[0]-side/2,0,C['width']-side));y0=int(np.clip(mid[1]-side/2,0,C['height']-side))
cap=cv2.VideoCapture(str(O/'PVE-Shot01-U-Archers-v12.mp4'))
def frame(t):
 im=at(cap,t)
 for i,color,tag,offset in [(target,(255,70,200),'HIT',-30),(runner,(30,255,60),'RUN',30)]:
  q=center(t,i);cv2.circle(im,tuple(q),18,(0,0,0),5);cv2.circle(im,tuple(q),17,color,3);label=f'{tag} {U[i]["id"]}';point=(q[0]+22,q[1]+offset);cv2.putText(im,label,point,0,.65,(0,0,0),4);cv2.putText(im,label,point,0,.65,color,2)
 return im[y0:y0+side,x0:x0+side]
sheet=np.full((3*450,4*450,3),235,np.uint8)
for j,t in enumerate(np.linspace(start,end,12)):
 x=j%4*450;y=j//4*450;k=round(t*60);sheet[y+45:y+450,x:x+450]=fit(frame(float(t)),450,405);cv2.putText(sheet,f'{t:.3f}s z={A[k,target,1]:.2f} v={V[k,target,1]:.1f}',(x+7,y+26),0,.48,(0,0,0),1)
jpg(O/'V12-hit-runner-continuous.jpg',sheet)
path=O/'V12-hit-runner-detail-realtime.mp4';proc=encoder(path,1000,1060,60)
for k in range(round((end-start)*60)):
 t=start+k/60;out=np.full((1060,1000,3),25,np.uint8);out[60:]=fit(frame(t),1000,1000);cv2.putText(out,f'1.0x | {t:.3f}s | hit {impact:.3f}s',(15,37),0,.7,(240,240,240),1);proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0;cap.release()
media=json.loads((O/'V12-media-validation.json').read_text());media[-1]=check(path);(O/'V12-media-validation.json').write_text(json.dumps(media,indent=2))
print(json.dumps(rows,indent=2))
