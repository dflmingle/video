from pathlib import Path
import json,numpy as np,difflib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V13';S=json.loads((D/'simulation.json').read_text());U=S['units'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');K=np.load(D/'red-control.npy');A0=np.load(B/'variants/FINAL/trajectories.npy');V0=np.diff(A0,axis=0,prepend=A0[:1])*60;ids=json.loads((O/'tracked-v14.json').read_text())['indices'];t=np.arange(len(A))/60
fig,axes=plt.subplots(4,1,figsize=(13,12),sharex=True)
for i in ids[:10]:
 j=i-nb;line,=axes[0].plot(t,K[:,j,1],lw=1,label=U[i]['id']);axes[1].plot(t,K[:,j,4],color=line.get_color(),lw=1);axes[2].plot(t,K[:,j,3],color=line.get_color(),lw=1);axes[3].plot(t,A[:,i,1]-np.mean(A[:,ids,1],axis=1),color=line.get_color(),lw=1)
axes[0].set_ylabel('Forward speed');axes[1].set_ylabel('Stride cycles/sec');axes[2].set_ylabel('Dynamic stride');axes[3].set_ylabel('Z relative to tracked center');axes[3].set_xlabel('Real shot seconds');axes[0].legend(ncol=10,fontsize=7);axes[0].set_title('Same squad: sustained individual motion, not initial-position jitter')
for ax in axes:ax.grid(alpha=.25)
fig.tight_layout();fig.savefig(O/'V14-continuous-controls.png',dpi=140);plt.close(fig)
fig,ax=plt.subplots(2,1,figsize=(12,7),sharex=True)
for i in ids[:10]:
 ax[0].plot(np.arange(len(A0))/60,V0[:,i,1],lw=1);ax[1].plot(t,K[:,i-nb,1],lw=1)
ax[0].set_title('V13: each member settles onto an almost constant cruise speed');ax[1].set_title('V14: personal exertion, occupancy yielding and recovery continue during charge')
for a in ax:a.set_ylabel('Forward world speed');a.grid(alpha=.2)
ax[1].set_xlabel('Real shot seconds');fig.tight_layout();fig.savefig(O/'V13-V14-temporal-speed.png',dpi=140);plt.close(fig)
R=json.loads((O/'V14-engineering-validation.json').read_text());examples=R['trackedRecoveryExamples'];examples=sorted(examples,key=lambda e:abs(e['xMove']),reverse=True)
(O/'V14-selected-avoidance.json').write_text(json.dumps(examples[:5],indent=2))
for e in examples[:1]:
 i=e['index'];j=e['neighborIndex'];a=max(0,round(e['slowTime']*60)-12);b=min(len(A),round(e['recoverTime']*60)+15);fig,ax=plt.subplots(figsize=(8,8));ax.plot(A[a:b,i,0],A[a:b,i,1],'-o',markersize=2,label=U[i]['id']);ax.plot(A[a:b,j,0],A[a:b,j,1],'-o',markersize=2,label=U[j]['id']);ax.set_aspect('equal');ax.set_xlabel('World X');ax.set_ylabel('World Z (forward)');ax.legend();ax.grid(alpha=.2);fig.savefig(O/'V14-avoidance-world-path.png',dpi=140);plt.close(fig)
diff=''
for f in ['src/main-camera.js','src/assets-v11.js','tools/build_simulation_v11.py','variants/FINAL/params.json']:diff+=''.join(difflib.unified_diff((B/f).read_text(encoding='utf-8').splitlines(True),(P/f).read_text(encoding='utf-8').splitlines(True),fromfile='V13/'+f,tofile='V14/'+f))
(O/'V13-V14-code.diff').write_text(diff,encoding='utf-8');print(json.dumps(examples[:3],indent=2))
