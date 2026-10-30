from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scene_occupancy_v22r import load_obstacles
P=Path(__file__).resolve().parents[1];S=json.loads((P/'docs/v22r-depth/setup.json').read_text());fig,axs=plt.subplots(1,3,figsize=(15,10))
for ax,c in zip(axs,S['candidates']):
 sim=json.loads((P/'variants'/c['seed']/'simulation.json').read_text());p=np.load(P/'variants'/c['seed']/'trajectories.npy')[0]
 for o in load_obstacles(c['sceneLayout']):ax.fill(*o['vertices'].T,color='#647080' if 'Building' in o['path'] else '#9b8c66',alpha=.7)
 for color in ['red','orange','yellow','blue']:
  ids=[i for i,u in enumerate(sim['units']) if (u['team']=='blue' if color=='blue' else u.get('color')==color)]
  ax.scatter(*p[ids].T,s=2,color=color)
 ax.annotate('RED CHARGE',xy=(0,18),xytext=(0,5),ha='center',arrowprops=dict(arrowstyle='->'))
 ax.annotate('BLUE ASSEMBLY',xy=(24,29),xytext=(24,42),ha='center',rotation=90,arrowprops=dict(arrowstyle='->'))
 ax.set(xlim=(-33,33),ylim=(49,-46),title=f"{c['label']} gap {c['actualFrontNetGap']:.3f} / +{100*c['actualIncreaseRatio']:.1f}%",xlabel='World X',ylabel='Camera-facing world depth');ax.set_aspect('equal');ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(P/'output/v22r-depth/layout-topdown.png',dpi=120);plt.close(fig)
