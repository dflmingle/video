from pathlib import Path
import json,csv,hashlib,difflib,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V12';S=json.loads((D/'simulation.json').read_text());U=S['units'];C=S['config'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*60;T=json.loads((D/'behavior-tracks.json').read_text());E=S['events'];imp=[e for e in E if e['resolution']=='IMPACT_IN_SHOT']
first={}
for e in sorted(imp,key=lambda e:e['impact']):first.setdefault(e['target'],e['impact'])
ids=[r['index'] for r in json.loads((O/'representative-members.json').read_text())];fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True)
for i in ids[:12]:
 line,=axes[0].plot(np.arange(len(A))/60,A[:,i,1]-A[0,i,1],label=U[i]['id'],lw=1.2);axes[1].plot(np.arange(len(A))/60,V[:,i,1],color=line.get_color(),lw=1)
 if i in first:
  k=round(first[i]*60);axes[0].scatter(first[i],A[k,i,1]-A[0,i,1],marker='x',color=line.get_color())
edges=np.arange(0,3.001,.1);counts,_=np.histogram([e['release'] for e in E],edges);axes[2].bar(edges[:-1],counts,width=.09,color='#347baa');axes[2].set_ylabel('Arrow releases / 100ms');axes[2].set_xlabel('Actual shot seconds');axes[0].set_ylabel('Forward world advance');axes[1].set_ylabel('Forward world speed');axes[0].legend(ncol=6,fontsize=8)
for ax in axes:ax.grid(alpha=.2);ax.axhline(0,color='black',lw=.7)
fig.suptitle('V13: independent members, bound impacts and interleaved archery');fig.tight_layout();fig.savefig(O/'V13-member-motion-and-release.png',dpi=140);plt.close(fig)
rows=[]
for t in [0,.1,.3,.6,1,1.5,2,2.4,2.7,2.8833333]:
 k=round(t*60);unhit=[i for i in range(nb,len(U)) if first.get(i,99)>t];yellow=[i for i in unhit if U[i]['army']==2]
 rows.append(dict(time=k/60,healthy=len(unhit),forwardSpeedP10P50P90=np.percentile(V[k,unhit,1],[10,50,90]).tolist(),healthyYellowAdvanceMedian=float(np.median(A[k,yellow,1]-A[0,yellow,1]))))
releases=[dict(start=round(edges[i],2),end=round(edges[i+1],2),arrows=int(n)) for i,n in enumerate(counts)]
report=dict(healthyMotion=rows,releaseWindows100ms=releases,individualPolicy='ID-derived stable parameters and actual integrated path; no per-frame coordinate randomness.',runGaitScaleRange=[min(u['gaitScale'] for u in U[nb:]),max(u['gaitScale'] for u in U[nb:])],sourceRun='Specified FBX skeleton; adapted procedural IK run, not native sprint.',sourceAssetsUnchanged=True)
(O/'V13-motion-release-diagnostics.json').write_text(json.dumps(report,indent=2))
files=['src/main-camera.js','src/assets-v11.js','tools/build_simulation_v11.py','variants/FINAL/params.json'];diff=''
for f in files:diff+=''.join(difflib.unified_diff((B/f).read_text(encoding='utf-8').splitlines(True),(P/f).read_text(encoding='utf-8').splitlines(True),fromfile='V12/'+f,tofile='V13/'+f))
(O/'V12-V13-code.diff').write_text(diff,encoding='utf-8')
for p,h in json.loads((O/'protected-v12.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
print(json.dumps(dict(releaseWindows=[r for r in releases if r['arrows']],lateHealthyMotion=rows[-1]),indent=2))
