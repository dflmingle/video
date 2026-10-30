from pathlib import Path
import json,csv,hashlib
import numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output'
S=json.loads((D/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];nr=S['redCount'];dt=1/C['simulationFps'];A=np.load(D/'trajectories.npy');G=np.load(D/'gait-distance.npy');V=np.diff(A,axis=0,prepend=A[:1])/dt;states=np.load(D/'member-states.npy')
baseline=json.loads((P/'baseline/V5-simulation.json').read_text());assert [u['id'] for u in U]==[u['id'] for u in baseline['units']];assert np.array_equal(A[0],np.array([u['start'] for u in baseline['units']],dtype=np.float32));assert nb==252 and nr==972
E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];assert E and not C['disableCombat'] and not C['previewOnly'];first={};records=[]
for e in E:
 i=e['target'];k=e['impactFrame'];first.setdefault(i,e)
 assert e['release']-C['drawSeconds']>=S['blueLastArrival']-1e-6
 assert np.allclose(np.array(e['destination'])[[0,2]],A[k,i],atol=1e-5)
 assert states[k,i-nb] in [1,3]
 assert e['impact']>e['release'] and e['shooterID']==U[e['shooter']]['id'] and e['targetID']==U[i]['id']
 records.append(dict(event=e['id'],shooter=e['shooterID'],target=e['targetID'],release=e['release'],impact=e['impact'],damage=e['damage'],remainingHP=e['remainingHP'],killed=e['killed'],beforeSpeed=float(V[max(1,k-1),i,1]),after50msSpeed=float(np.mean(V[k:min(len(V),k+3),i,1])),state=int(states[k,i-nb])))
minimum=100.;crowding=[];armyStats=[];centers=[]
for f,a in enumerate(A):
 live=np.array([i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>f*dt]);nn=cKDTree(a[live]).query(a[live],k=2)[0][:,1];minimum=min(minimum,float(nn.min()));centers.append(float(cKDTree(a[:nb]).query(a[nb:])[0].min()))
 if f%30==0:crowding.append(dict(t=f*dt,nearestNeighborP10P50P90=np.percentile(nn,[10,50,90]).tolist()))
assert minimum>=2*C['bodyRadius']-1e-4
steps=np.linalg.norm(np.diff(A,axis=0),axis=2);lower=np.minimum(centers[:-1],centers[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))-2*C['weaponEnvelopeRadius'];assert lower.min()>=C['minimumEnemyClearance'];assert np.diff(A[:,nb:,1],axis=0).min()>=-1e-5
for i,u in enumerate(U[nb:],nb):
 if u['deathTime'] is not None:
  k=round(u['deathTime']/dt);assert any(e['target']==i and e['killed'] and abs(e['impact']-u['deathTime'])<1e-5 for e in E);assert np.allclose(A[k:,i],A[k,i],atol=1e-5)
selected=[];formation=[]
for army in range(3):
 ids=[i for i in range(nb,len(U)) if U[i]['army']==army];healthy=[i for i in ids if i not in first];wounded=[i for i in ids if i in first and U[i]['deathTime'] is None];dead=[i for i in ids if U[i]['deathTime'] is not None]
 for pool in [healthy,wounded,dead]:
  selected+=pool[:2]
 armyStats.append(dict(army=army,model=U[ids[0]]['model'],count=len(ids),neverHit=len(healthy),wounded=len(wounded),dead=len(dead),advanceP10P50P90=np.percentile(A[-1,ids,1]-A[0,ids,1],[10,50,90]).tolist(),healthyEndSpeedP10P50P90=np.percentile(V[-1,healthy,1],[10,50,90]).tolist() if healthy else None))
 for platoon in sorted({U[i]['platoon'] for i in ids}):
  group=[i for i in ids if U[i]['platoon']==platoon];disp=A[-1,group]-A[0,group];formation.append(dict(army=army,model=U[group[0]]['model'],platoon=platoon,count=len(group),initialXRange=[float(A[0,group,0].min()),float(A[0,group,0].max())],initialZRange=[float(A[0,group,1].min()),float(A[0,group,1].max())],displacementResidualRMS=float(np.std(disp,axis=0).dot(np.std(disp,axis=0))**.5),members=[U[i]['id'] for i in group]))
with (O/'arrow-hit-events.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,records[0].keys());w.writeheader();w.writerows(records)
with (O/'representative-tracks.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','id','model','x','z','vx','vz','path','firstImpact','state'])
 for k,a in enumerate(A):
  for i in selected:w.writerow([k*dt,U[i]['id'],U[i]['model'],*a[i],*V[k,i],G[k,i],first[i]['impact'] if i in first else '',int(states[k,i-nb])])
(O/'representative-members.json').write_text(json.dumps([dict(index=i,id=U[i]['id'],model=U[i]['model'],firstImpact=first[i]['impact'] if i in first else None,death=U[i]['deathTime']) for i in selected],indent=2));(O/'formation-members.json').write_text(json.dumps(formation,indent=2))
for label in ['v9','v10']:
 for path,digest in json.loads((P/f'baseline/protected-{label}.json').read_text()).items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
m=json.loads((P/'assets/runtime/manifest.json').read_text())
for key,u in m.items():
 for ext,tag in [('fbx','sourceSHA256'),('png','textureSHA256')]:assert hashlib.sha256((P/f'assets/runtime/{key}.{ext}').read_bytes()).hexdigest()==u[tag]
R=dict(engineeringStatus='PASS',visualStatus='REQUIRES_ENCODED_REVIEW',initialExact=True,arrows=len(S['events']),impacts=len(E),inFlightAtCut=len(S['events'])-len(E),casualties=sum(u['deathTime'] is not None for u in U[nb:]),firstImpact=min(e['impact'] for e in E),lastImpact=max(e['impact'] for e in E),minimumLiveCenterDistance=minimum,bodyDiameter=2*C['bodyRadius'],minimumContinuousFactionSurfaceClearance=float(lower.min()),required=C['minimumEnemyClearance'],blueLastArrival=S['blueLastArrival'],blueAdvance=C['blueAdvance'],armies=armyStats,crowding=crowding,tracked=len(selected),scope='All 253 simulation states; body disks and conservative weapon envelope; deterministic authored battle, not autonomous strategy AI.')
# Formation checks concern original IDs and placement, not preserving rectangles.
# Report measurable pre-impact freedom without treating it as a failure.
firstImpact=min(e['impact'] for e in E);kf=max(1,round((firstImpact-.15)/dt));pre=[]
for army in range(3):
 for squad in sorted({u['platoon'] for u in U[nb:] if u['army']==army}):
  ids=[i for i in range(nb,len(U)) if U[i]['army']==army and U[i]['platoon']==squad];disp=A[kf,ids]-A[0,ids]
  pre.append(dict(army=army,platoon=squad,forwardDisplacementRange=float(np.ptp(disp[:,1])),lateralDisplacementRange=float(np.ptp(disp[:,0]))))
speedProfile={}
for t in [0,.1,.2,.3,.4,.6,1,2,3,4.18]:
 k=min(len(V)-1,round(t/dt));ids=[i for i in range(nb,len(U)) if first.get(i,dict(impact=99))['impact']>t]
 speedProfile[str(t)]=dict(unhitCount=len(ids),forwardSpeedP10P50P90=np.percentile(V[k,ids,1],[10,50,90]).tolist(),advanceP10P50P90=np.percentile(A[k,ids,1]-A[0,ids,1],[10,50,90]).tolist())
(O/'charge-speed-profile.json').write_text(json.dumps(speedProfile,indent=2))
R['preImpactFormationPolicy']='Natural continuous deformation allowed; no requirement for rectangular boundaries; no fixed-slot spring.'
R['preImpactDeformation']=pre
(O/'V11-engineering-validation.json').write_text(json.dumps(R,indent=2));print(json.dumps({k:v for k,v in R.items() if k not in ['crowding','preImpactDeformation']},indent=2))
