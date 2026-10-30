from pathlib import Path
import json,sys,numpy as np,csv,hashlib
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];variant=sys.argv[1];d=P/'variants'/variant;S=json.loads((d/'simulation.json').read_text());C=S['config'];a=np.load(d/'trajectories.npy');nb=S['blueCount'];dt=1/C['simulationFps'];n=len(S['units']);results={}
for label,data in [('combat',a),('noCombat',np.load(d/'motion-data/trajectories.npy'))]:
 center=np.array([cKDTree(frame[:nb]).query(frame[nb:])[0].min() for frame in data]);steps=np.linalg.norm(np.diff(data,axis=0),axis=2);lower=np.minimum(center[:-1],center[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))-2*C['weaponEnvelopeRadius']
 assert lower.min()>=C['minimumEnemyClearance'],(label,lower.min())
 results[label]=dict(continuousSurfaceLowerBound=float(lower.min()),minimumCenterDistance=float(center.min()),maximumFrameDisplacement=float(steps.max()),required=C['minimumEnemyClearance'])
assert np.diff(a[:,nb:,1],axis=0).min()>=-1e-5
dead={u['id']:u['deathTime'] for u in S['units'][nb:] if u['deathTime'] is not None};kills={e['targetID']:e['impact'] for e in S['events'] if e['killed']};assert dead==kills
for e in S['events']:
 assert e['drawStart']<e['release']<e['impact'] and e['release']>=S['blueLastArrival']
 if e['resolution']=='IMPACT_IN_SHOT':assert np.linalg.norm(np.array(e['destination'])[[0,2]]-a[e['impactFrame'],e['target']])<1e-4
 else:assert e['impact']>C['duration'] and e['damage'] is None and not e['killed']
groups=[]
for army in range(3):
 for row in range(3):
  for col in range(3):
   ids=[i for i,u in enumerate(S['units']) if i>=nb and u['army']==army and u['squadRow']==row and u['squadCol']==col];assert len(ids)==C['armyMemberRows'][army]*C['redMemberColumns'];assert len({S['units'][i]['model'] for i in ids})==1
   samples=[]
   for t in [0,1,2,3,4,C['duration']]:
    k=round(t/dt);live=[i for i in ids if S['units'][i]['deathTime'] is None or S['units'][i]['deathTime']>t];p=a[k,live];samples.append(dict(time=t,alive=len(live),frontZ=float(p[:,1].max()) if len(p) else None,rearZ=float(p[:,1].min()) if len(p) else None))
   groups.append(dict(army=army,squadRow=row,squadCol=col,model=S['units'][ids[0]]['model'],count=len(ids),IDs=[S['units'][i]['id'] for i in ids],startXRange=[float(a[0,ids,0].min()),float(a[0,ids,0].max())],startZRange=[float(a[0,ids,1].min()),float(a[0,ids,1].max())],samples=samples))
gait=np.load(d/'gait-distance.npy');surv=[i for i in range(nb,n) if S['units'][i]['deathTime'] is None];vel=np.diff(a,axis=0)/dt;speed=np.linalg.norm(vel,axis=2);rows=[]
for k in range(0,len(a),6):
 t=k*dt;live=[i for i in range(nb,n) if S['units'][i]['deathTime'] is None or S['units'][i]['deathTime']>t];p=a[k,live];neighbors=cKDTree(p).query_ball_point(p,2,return_length=True)-1
 rows.append(dict(time=t,alive=len(live),speedMedian=float(np.median(speed[max(0,k-1),live])),forwardSpeedP10=float(np.percentile(vel[max(0,k-1),live,1],10)),forwardSpeedP90=float(np.percentile(vel[max(0,k-1),live,1],90)),frontP95=float(np.percentile(p[:,1],95)),frontMax=float(p[:,1].max()),rearP05=float(np.percentile(p[:,1],5)),neighbors2uMean=float(np.mean(neighbors))))
for j,r in enumerate(rows):r['medianAcceleration']=0 if not j else (r['speedMedian']-rows[j-1]['speedMedian'])/(r['time']-rows[j-1]['time'])
with (d/'motion-density.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
with (d/'arrow-events.csv').open('w',newline='',encoding='utf-8-sig') as f:
 fields=['id','shooterID','targetID','drawStart','release','impact','resolution','damage','remainingHP','killed','origin','destination','destinationEvidence'];w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(S['events'])
report=dict(variant=variant,redCount=S['redCount'],blueCount=nb,groups=groups,safety=results,backwardSteps=0,survivorTerminalForwardP10P50P90=np.percentile(np.median(vel[-20:,surv,1],axis=0),[10,50,90]).tolist(),survivorAdvanceP10P50P90=np.percentile(a[-1,surv,1]-a[0,surv,1],[10,50,90]).tolist(),runCycleFrequencyMedian=float(np.median(speed[-20:,surv])/C['runStride']),arrows=len(S['events']),resolvedImpacts=sum(e['resolution']=='IMPACT_IN_SHOT' for e in S['events']),pendingAtCut=sum(e['resolution']=='IN_FLIGHT_AT_CUT' for e in S['events']),deaths=len(dead),blueLastArrival=S['blueLastArrival'],blueAdvance=C['blueAdvance'],firstRelease=min(e['release'] for e in S['events']),motionSamples=rows)
if (d/'render-checks.json').exists():
 r=json.loads((d/'render-checks.json').read_text());assert not r['errors'] and all(s['identical'] for s in r['seeks']);assert r['states'][-1]['arrows']>0
 assert r.get('inputs'),'Capture needs bound input hashes'
 for path,h in r['inputs'].items():assert hashlib.sha256((P/path).read_bytes()).hexdigest()==h,('Stale capture',path)
 for state in r['states']:assert state['arrows']==sum(e['release']<=state['time']<e['impact'] for e in S['events'])
 report['captureMsP50P90']=np.percentile(r['frameCaptureMs'],[50,90]).tolist();report['captureCostScope']='Headless SwiftShader render plus browser PNG capture, not a realtime GPU FPS claim'
(d/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['groups','motionSamples']},indent=2))
