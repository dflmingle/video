from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1];S=json.loads((P/'variants/FINAL/simulation.json').read_text());C=S['config'];nb=S['blueCount'];a=np.load(P/'variants/FINAL/trajectories.npy');b=np.load(P/'variants/FINAL/motion-data/trajectories.npy');t=np.arange(len(a))/C['simulationFps'];colors=['#c92328','#ef7519','#c8a316']
fig,axes=plt.subplots(2,2,figsize=(13,10));ax=axes[0,0]
for army,c in enumerate(colors):
 ids=[i for i,u in enumerate(S['units']) if i>=nb and u['army']==army];ax.scatter(a[0,ids,0],-a[0,ids,1],s=3,c=c,label=['Rear flail','Middle sword','Front samurai'][army])
ax.scatter(a[0,:nb,0],-a[0,:nb,1],s=3,c='#2476be',label='7-squad blue U');ax.set_aspect('equal');ax.legend(fontsize=8);ax.set_title('Initial members: 3 armies x 3x3 squads')
ax=axes[0,1]
for army,c in enumerate(colors):
 ids=[i for i,u in enumerate(S['units']) if i>=nb and u['army']==army];front=np.percentile(a[:,ids,1],95,axis=1);rear=np.percentile(a[:,ids,1],5,axis=1);ax.plot(t,front,c=c);ax.plot(t,rear,c=c,linestyle='--')
ax.set_title('Member front P95 (solid), rear P05 (dashed)');ax.set_xlabel('seconds');ax.set_ylabel('world Z')
ax=axes[1,0];v=np.diff(b[:,nb:,1],axis=0)*C['simulationFps'];w=np.diff(a[:,nb:,1],axis=0)*C['simulationFps'];ax.plot(t[1:],np.median(v,axis=1),label='No combat median');ax.plot(t[1:],np.median(w,axis=1),label='Combat median incl. casualties');ax.set_title('Actual forward world speed');ax.legend();ax.set_xlabel('seconds')
ax=axes[1,1];hits=np.array([e['impact'] for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT']);deaths=np.array([u['deathTime'] for u in S['units'][nb:] if u['deathTime'] is not None]);ax.plot(t,[sum(hits<=x) for x in t],label='Bound impacts');ax.plot(t,[sum(deaths<=x) for x in t],label='Deaths');ax.set_title('Causal accumulation, no random despawn');ax.legend();ax.set_xlabel('seconds');fig.tight_layout();fig.savefig(P/'output/movement-and-hit-diagnostics.png',dpi=140);plt.close(fig)
