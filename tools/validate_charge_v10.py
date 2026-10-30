from pathlib import Path
import json,numpy as np,hashlib,csv,math
from scipy.spatial import cKDTree
p=Path('.');d=p/'variants/FINAL';s=json.loads((d/'simulation.json').read_text());c=json.loads((d/'params.json').read_text());u=s['units'];nb=s['blueCount'];a=np.load(d/'trajectories.npy');g=np.load(d/'gait-distance.npy');v=np.diff(a,axis=0,prepend=a[:1])*60;base=json.loads((p/'baseline/V5-simulation.json').read_text());old=np.load(p/'baseline/V5-trajectories.npy');assert [x['id'] for x in u]==[x['id'] for x in base['units']];assert np.array_equal(a[0],old[0]);assert not s['events'] and all(x['deathTime'] is None for x in u[nb:])
minimum=min(float(cKDTree(q).query(q,k=2)[0][:,1].min()) for q in a[:,nb:]);assert minimum>=2*c['bodyRadius'];assert np.min(np.diff(a[:,nb:,1],axis=0))>=-1e-5
center=np.array([cKDTree(q[:nb]).query(q[nb:])[0].min() for q in a]);steps=np.linalg.norm(np.diff(a,axis=0),axis=2);lower=np.minimum(center[:-1],center[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))-2*c['weaponEnvelopeRadius'];assert lower.min()>=c['minimumEnemyClearance']
rows=[];selected=[]
for army in range(3):
 for r in range(3):
  for col in range(3):
   ids=[i for i in range(nb,len(u)) if u[i]['army']==army and u[i]['squadRow']==r and u[i]['squadCol']==col];disp=a[-1,ids]-a[0,ids];rows.append(dict(army=army,row=r,col=col,count=len(ids),advanceMinMedianMax=np.percentile(disp[:,1],[0,50,100]).tolist(),withinSquadDisplacementResidualRMS=float(np.sqrt(np.mean(np.sum((disp-disp.mean(axis=0))**2,axis=1))))))
 for row in range(3):
  ids=[i for i in range(nb,len(u)) if u[i]['army']==army and u[i]['squadRow']==row and u[i]['squadCol']==1];selected.append(ids[len(ids)//2])
ids=list(range(nb,len(u)));selected.extend([min(ids,key=lambda i:v[-1,i,1]),max(ids,key=lambda i:v[-1,i,1]),nb]);selected=list(dict.fromkeys(selected));
with (p/'output/charge-member-tracks.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','id','army','squadRow','squadCol','x','z','vx','vz','pathDistance','gaitCycles','state'])
 for k in range(len(a)):
  for i in selected:w.writerow([k/60,u[i]['id'],u[i]['army'],u[i]['squadRow'],u[i]['squadCol'],*a[k,i],*v[k,i],g[k,i],g[k,i]/u[i]['gaitStride']+u[i]['phase'],'START' if k/60<u[i]['delay']+u[i]['accelerationSeconds'] else 'RUN'])
(p/'output/representative-members.json').write_text(json.dumps([dict(index=i,id=u[i]['id'],model=u[i]['model'],army=u[i]['army']) for i in selected],indent=2))
r=dict(initialIDsAndCoordinatesExact=True,redCount=s['redCount'],blueCount=nb,arrows=0,casualties=0,minimumBodyDistance=minimum,bodyDiameter=c['bodyRadius']*2,continuousFactionSurfaceLowerBound=float(lower.min()),required=c['minimumEnemyClearance'],noBackward=True,advanceP10P50P90=np.percentile(a[-1,nb:,1]-a[0,nb:,1],[10,50,90]).tolist(),terminalForwardSpeedP10P50P90=np.percentile(v[-1,nb:,1],[10,50,90]).tolist(),maxLateralDisplacement=float(abs(a[-1,nb:,0]-a[0,nb:,0]).max()),speedAtTime={str(t):np.percentile(v[round(t*60),nb:,1],[10,50,90]).tolist() for t in[0,.1,.2,.4,.6,1,2,3,4]},groups=rows,tracked=len(selected),scope='Engineering only; independent integration and nonrigid motion do not prove fierce charge quality.')
(p/'output/charge-motion-validation.json').write_text(json.dumps(r,indent=2));print({k:v for k,v in r.items() if k not in ['groups','speedAtTime']})
# Validate original shared assets and preserve V9.
for path,h in json.loads((p/'baseline/protected-v9.json').read_text()).items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h
m=json.loads((p/'assets/runtime/manifest.json').read_text())
for k,z in m.items():assert hashlib.sha256((p/f'assets/runtime/{k}.fbx').read_bytes()).hexdigest()==z['sourceSHA256'];assert hashlib.sha256((p/f'assets/runtime/{k}.png').read_bytes()).hexdigest()==z['textureSHA256']
print('All original sources and V9 protected hashes unchanged')
