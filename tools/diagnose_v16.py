from pathlib import Path
import json,numpy as np,csv,hashlib
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];O=P/'output';B=P.parent/'PveMontageShot01V15';summary={};allrows=[]
for label,D in [('V15',B/'variants/FINAL'),*[(v,P/'variants'/v) for v in ['BASE100','FAST125','FAST150']]]:
 if not (D/'simulation.json').exists():continue
 S=json.loads((D/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];A=np.load(D/'trajectories.npy');K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');first={}
 for e in S['events']:
  if e['resolution']=='IMPACT_IN_SHOT':first.setdefault(e['target'],e['impact'])
 assert len(U)==1224 and np.array_equal(A[0],np.load(B/'variants/FINAL/trajectories.npy')[0]);assert np.min(np.diff(A[:,nb:,1],axis=0))>=-1e-5
 # Cover every simulated safe frame, body occupancy including ALL dead.
 distances=[];minbody=100.;mincorpse=100.
 for f,p in enumerate(A):
  live=[i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>f/60];dead=[i for i in range(nb,len(U)) if U[i]['deathTime'] is not None and U[i]['deathTime']<=f/60]
  distances.append(float(cKDTree(p[:nb]).query(p[nb:])[0].min()));minbody=min(minbody,float(cKDTree(p[live]).query(p[live],k=2)[0][:,1].min()))
  if dead:mincorpse=min(mincorpse,float(cKDTree(p[dead]).query(p[live])[0].min()))
 step=np.linalg.norm(np.diff(A,axis=0),axis=2);bound=np.minimum(distances[:-1],distances[1:])-.5*(step[:,:nb].max(axis=1)+step[:,nb:].max(axis=1))-6.2
 assert bound.min()>=4-1e-5 and minbody>=.58 and mincorpse>=.58,(label,bound.min(),minbody,mincorpse)
 for i,u in enumerate(U[nb:],nb):
  if u['deathTime'] is not None:
   f=round(u['deathTime']*60);assert np.allclose(A[f:,i],A[f,i]);assert any(e['target']==i and e.get('killed') for e in S['events'])
 times=list(np.arange(0,C['duration'],.5))+[C['duration']-1/60]
 rows=[];initialFront=float(A[0,-216:,1].max())
 for t in times:
  f=min(len(A)-1,round(t*60));healthy=np.array([i for i in range(nb,len(U)) if first.get(i,99)>t]);alive=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>t]);front=float(A[f,alive,1].max());speed=K[f,healthy-nb,1]
  row=dict(variant=label,time=t,frontProgress=front-initialFront,healthyMeanProgress=float(np.mean(A[f,healthy,1]-A[0,healthy,1])),healthyMeanSpeed=float(np.mean(speed)),healthySpeedP10=float(np.percentile(speed,10)),healthySpeedP50=float(np.percentile(speed,50)),healthySpeedP90=float(np.percentile(speed,90)),factionCenterDistance=distances[f],phaseCircularCoherence=float(abs(np.mean(np.exp(2j*np.pi*(Y[f,healthy]+np.array([U[i]['phase'] for i in healthy])))))))
  rows.append(row);allrows.append(row)
 e=[e for e in S['events'] if e['release']<C['duration']];hits=[e for e in e if e['impactFrame']<round(C['duration']*60)];firstRelease=min(x['release'] for x in e) if e else None;firstHit=min(x['impact'] for x in hits) if hits else None
 summary[label]=dict(duration=C['duration'],multiplier=C.get('chargeMultiplier',1),rows=rows,firstRelease=firstRelease,firstVisibleImpact=firstHit,visibleImpactCount=len(hits),arrows=len(e),deaths=sum(u.get('deathTime') is not None for u in U[nb:]),visibleCombatAfterFirstImpact=0 if firstHit is None else C['duration']-firstHit,minimumContinuousEnvelope=float(bound.min()),minimumBodyCenter=minbody,minimumCorpseCenter=mincorpse,initialExact=True,reverseSteps=0,blueArrivalRange=[min(u['arrival'] for u in U[:nb]),max(u['arrival'] for u in U[:nb])])
for p,h in json.loads((O/'protected-v15.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
with (O/'V16-progress-every-half-second.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,allrows[0].keys());w.writeheader();w.writerows(allrows)
(O/'V16-motion-diagnostics.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:{q:v[q] for q in ['duration','firstRelease','firstVisibleImpact','visibleImpactCount','deaths','minimumContinuousEnvelope']} for k,v in summary.items()},indent=2))
