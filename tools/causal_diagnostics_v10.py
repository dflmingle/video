from pathlib import Path
import json,csv,hashlib,math
import numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];d=P/'variants/FINAL';O=P/'output'
S=json.loads((d/'simulation.json').read_text());C=S['config'];nb=S['blueCount'];units=S['units'];nr=S['redCount'];dt=1/C['simulationFps']
a=np.load(d/'trajectories.npy');b=np.load(d/'motion-data/trajectories.npy');states=np.load(d/'member-states.npy');avoid=np.load(d/'avoidance-causes.npy')
events=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];first={};hitcount={};rows=[]
for e in events:
 first.setdefault(e['target'],e);hitcount[e['target']]=hitcount.get(e['target'],0)+1
 k=e['impactFrame'];i=e['target'];end=min(len(a)-1,k+round(.65/dt));before=max(0,k-3)
 merged=not e['killed'] and units[i]['deathTime'] is not None and abs(units[i]['deathTime']-e['impact'])<1e-6
 assert states[k,i-nb]==(3 if e['killed'] or merged else 1)
 rows.append(dict(event=e['id'],memberID=e['targetID'],shooterID=e['shooterID'],release=e['release'],impact=e['impact'],response='DEAD' if e['killed'] else 'SIMULTANEOUS_FATAL' if merged else 'STAGGER_RECOVER',speedBefore=float(np.linalg.norm(a[k-1,i]-a[before,i])/((k-1-before)*dt)),speedFirst50ms=float(np.linalg.norm(a[min(len(a)-1,k+3),i]-a[k,i])/(3*dt)),lagAt650msRelativeNoCombat=float((b[end,i,1]-a[end,i,1])-(b[k,i,1]-a[k,i,1]))))
with (O/'hit-response-events.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,rows[0].keys());w.writeheader();w.writerows(rows)
minimum=100;overlaps=0;min_motion=100
for f in range(len(a)):
 live=np.array([i for i in range(nb,len(units)) if units[i]['deathTime'] is None or units[i]['deathTime']>f*dt]);ds=cKDTree(a[f,live]).query(a[f,live],k=2)[0][:,1];minimum=min(minimum,float(ds.min()));overlaps+=int(np.count_nonzero(ds<2*C['bodyRadius']-1e-5));min_motion=min(min_motion,float(cKDTree(b[f,nb:]).query(b[f,nb:],k=2)[0][:,1].min()))
 assert np.all(np.diff(a[max(0,f-1):f+1,nb:,1],axis=0)>=-1e-5)
causes=np.argwhere(avoid>=0)
for f,j in causes:
 k=int(avoid[f,j]);assert units[nb+k]['deathTime'] is not None and units[nb+k]['deathTime']<=f*dt or states[f,k] in [1,2,4,5]
never=[i for i in range(nb,len(units)) if i not in first];hitids=list(first)
formation=[]
for army in range(3):
 for row in range(3):
  for col in range(3):
   ids=[i for i in range(nb,len(units)) if units[i]['army']==army and units[i]['squadRow']==row and units[i]['squadCol']==col];formation.append(dict(army=army,model=units[ids[0]]['model'],squadRow=row,squadCol=col,count=len(ids),startXRange=[float(a[0,ids,0].min()),float(a[0,ids,0].max())],startZRange=[float(a[0,ids,1].min()),float(a[0,ids,1].max())],members=[units[i]['id'] for i in ids]))
(O/'formation-members.json').write_text(json.dumps(formation,indent=2))
stats=dict(status='PASS',liveBodySeparationMinimum=minimum,noCombatBodySeparationMinimum=min_motion,bodyDiameter=C['bodyRadius']*2,bodyOverlapSamples=overlaps,avoidanceSamples=len(causes),allAvoidancesHaveHitOrCorpseCause=True,neverHitMembers=len(never),hitMembers=len(first),nonlethalImpacts=sum(not e['killed'] for e in events),dead=sum(e['killed'] for e in events),noCombatLateralDisplacementP50P95Max=np.percentile(abs(b[-1,nb:,0]-b[0,nb:,0]),[50,95,100]).tolist(),noCombatForwardAdvanceP10P50P90=np.percentile(b[-1,nb:,1]-b[0,nb:,1],[10,50,90]).tolist(),combatForwardDeficitP10P50P90=np.percentile(b[-1,nb:,1]-a[-1,nb:,1],[10,50,90]).tolist(),maxFrameDisplacement=float(np.linalg.norm(np.diff(a,axis=0),axis=2).max()),scope=f'All {len(a)} states at 60Hz; 2D body disks, not mesh collision. Causal counterfactual shares seed/IDs; no autonomous strategy AI.')
assert overlaps==0
(O/'causal-formation-diagnostics.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
# Correct stance metric is restricted to nominal full-speed stance frames, not all playback.
aud=json.loads((d/'asset-render-audit.json').read_text())['models'];g={}
for key,v in aud.items():
 if key=='archer':continue
 frames=v['actionAnatomy']['move'];slip=[]
 for side,k in [('leftFoot',0),('rightFoot',1)]:
  for j in range(31):
   if frames[j]['legDiagnostics'][k]['stance'] and frames[j+1]['legDiagnostics'][k]['stance']:
    delta=np.array(frames[j+1][side])-frames[j][side];slip.append(abs(1+np.dot(delta,[0,math.sin(.36),math.cos(.36)])/(C['runStride']/32)))
 g[key]=dict(stanceResidualBodySpeedFraction=float(np.mean(slip)),samples=len(slip),maxAllPoseReachError=max(x['reachError'] for f in frames for x in f['legDiagnostics']))
(O/'gait-diagnostics.json').write_text(json.dumps(dict(models=g,scope='Nominal speed, constant .36rad lean, consecutive sampled stance phases only. Not all limb pixels, startup, hit, or measured gait force.'),indent=2))
