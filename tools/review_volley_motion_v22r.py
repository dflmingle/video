"""Expose slow crowds explicitly; 'somebody moves' is not a charge verdict."""
import csv,json,shutil
from pathlib import Path
import numpy as np

R=Path(__file__).resolve().parents[1];V=R/'variants/V22R-volley';D=R/'docs/v22r-volley'
s=json.loads((V/'simulation.json').read_text(encoding='utf8'));p=np.load(V/'trajectories.npy');nb=s['blueCount'];fps=60
death=np.array([u.get('deathTime') if u.get('deathTime') is not None else 1e6 for u in s['units'][nb:]])
v=np.concatenate([np.zeros_like(p[:1]),np.diff(p,axis=0)*fps]);rows=[]
for k in range(0,len(p),6):
 t=k/fps;live=death>t;speed=np.linalg.norm(v[k,nb:][live],axis=1);forward=v[k,nb:,1][live]
 row=dict(time=t,live=int(live.sum()),medianSpeed=float(np.median(speed)),p90Speed=float(np.quantile(speed,.9)),meanForward=float(forward.mean()),belowPointFive=int(np.sum(speed<.5)),aboveOne=int(np.sum(speed>1)),aboveFive=int(np.sum(speed>5)),aboveTen=int(np.sum(speed>10)),meanRedForwardDistance=float((p[k,nb:,1]-p[0,nb:,1]).mean()),meanBlueAssemblyDistance=float((p[0,:nb,1]-p[k,:nb,1]).mean()))
 rows.append(row)
with (D/'movement-quality-0.1s.csv').open('w',encoding='utf-8-sig',newline='') as file:
 w=csv.DictWriter(file,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
shots=[]
for j in range(nb):
 releases=[e['release'] for e in s['events'] if e['shooter']==j]
 shots.append(releases)
cycles=[b-a for r in shots for a,b in zip(r,r[1:])]
report=dict(redPreferredSpeed=s['config']['redSpeed'],arrowSpeed=s['config']['arrowSpeed'],range=s['config']['archerRange'],blueAdvance=s['config']['blueAdvance'],blueWalkSpeedReferenceDistance=s['config']['blueWalkSpeedReferenceDistance'],actualShotIntervals=dict(min=float(min(cycles)),median=float(np.median(cycles)),max=float(max(cycles))),rounds={str(k+1):dict(first=float(min(r[k] for r in shots if len(r)>k)),last=float(max(r[k] for r in shots if len(r)>k))) for k in range(3)},motionSamples=rows,warning='Movement count at .02 units/s is insufficient to certify ongoing charge; inspect speed distribution and encoded images. Preferred speed is unchanged, actual speed is constrained.')
(D/'movement-quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
shutil.copyfile(V/'params.json',D/'params-snapshot.json')
# A plot supports comparison without substituting for actual video inspection.
try:
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axes=plt.subplots(2,1,figsize=(8,6),sharex=True)
 axes[0].plot([r['time'] for r in rows],[r['meanRedForwardDistance'] for r in rows],label='Red mean forward distance')
 axes[0].plot([r['time'] for r in rows],[r['meanBlueAssemblyDistance'] for r in rows],label='Blue mean assembly distance')
 axes[0].set_ylabel('World units');axes[0].legend();axes[0].grid(alpha=.3)
 axes[1].plot([r['time'] for r in rows],[r['medianSpeed'] for r in rows],label='Live red median speed')
 axes[1].plot([r['time'] for r in rows],[r['p90Speed'] for r in rows],label='Live red 90th percentile speed')
 axes[1].set_ylabel('World units / s');axes[1].set_xlabel('Simulation time (s)');axes[1].legend();axes[1].grid(alpha=.3)
 fig.tight_layout();fig.savefig(D/'movement-curves.png',dpi=130);plt.close(fig)
except ImportError:
 pass
print(json.dumps({k:v for k,v in report.items() if k!='motionSamples'},indent=2))
print(json.dumps([r for r in rows if r['time'] in [0.,.5,1.,1.5,2.,3.,3.5,4.]],indent=2))
