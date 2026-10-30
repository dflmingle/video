from pathlib import Path
import json,csv,hashlib,numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V12/variants/FINAL'
S=json.loads((D/'simulation.json').read_text());U=S['units'];C=S['config'];nb=S['blueCount'];nr=S['redCount'];A=np.load(D/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*60;E=S['events'];imp=[e for e in E if e['resolution']=='IMPACT_IN_SHOT'];Q=json.loads((B/'simulation.json').read_text());A0=np.load(B/'trajectories.npy')
assert [u['id'] for u in U]==[u['id'] for u in Q['units']] and np.array_equal(A[0],A0[0]);assert nb==252 and nr==972
assert np.min(np.diff(A[:,nb:,1],axis=0))>=-1e-5
first={};ranges=[];arrows=[]
for e in E:
 i,j=e['target'],e['shooter'];rf=e['releaseFrame'];u=U[j];dist=float(np.linalg.norm(A[rf,i]-A[rf,j]));ranges.append(dist);assert dist<=C['archerRange']+1e-4
 assert e['drawStart']-u['turnSeconds']>=u['arrival']-1e-5
 assert e['aimStart']>=e['drawStart'] and e['release']>=e['aimStart'];assert e['shooterID']==u['id'];assert e['targetID']==U[i]['id']
 if e['resolution']=='IMPACT_IN_SHOT':
  first.setdefault(i,e['impact']);assert np.allclose(A[e['impactFrame'],i],np.array(e['destination'])[[0,2]],atol=1e-5)
 arrows.append(dict(id=e['id'],shooter=e['shooterID'],target=e['targetID'],draw=e['drawStart'],aim=e['aimStart'],release=e['release'],impact=e['impact'],releaseDistance=dist,resolution=e['resolution'],damage=e['damage'],killed=e['killed']))
with (O/'V13-arrow-events.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,arrows[0].keys());w.writeheader();w.writerows(arrows)
mind=1e6;blueMin=1e6;faction=[]
for k,a in enumerate(A):
 live=[i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>k/60];mind=min(mind,float(cKDTree(a[live]).query(a[live],k=2)[0][:,1].min()));blueMin=min(blueMin,float(cKDTree(a[:nb]).query(a[:nb],k=2)[0][:,1].min()));faction.append(float(cKDTree(a[:nb]).query(a[nb:])[0].min()))
assert mind>=2*C['bodyRadius']-1e-4;assert blueMin>=2*C['bodyRadius']-1e-4
step=np.linalg.norm(np.diff(A,axis=0),axis=2);bound=np.minimum(faction[:-1],faction[1:])-.5*(step[:,:nb].max(axis=1)+step[:,nb:].max(axis=1))-2*C['weaponEnvelopeRadius'];assert bound.min()>=C['minimumEnemyClearance']
for i in range(nb,len(U)):
 if U[i]['deathTime'] is not None:
  k=round(U[i]['deathTime']*60);assert np.allclose(A[k:,i],A[k,i]);assert any(e['target']==i and e['killed'] for e in imp)
for p,h in json.loads((O/'protected-v12.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
selected=[]
for army in range(3):
 ids=[i for i in range(nb,len(U)) if U[i]['army']==army]
 for category in ['healthy','hurt','dead']:
  pool=[i for i in ids if (i not in first if category=='healthy' else i in first and U[i]['deathTime'] is None if category=='hurt' else U[i]['deathTime'] is not None)];selected+=pool[:2]
(O/'representative-members.json').write_text(json.dumps([dict(index=i,id=U[i]['id'],model=U[i]['model'],firstHit=first.get(i),death=U[i]['deathTime']) for i in selected],indent=2))
with (O/'V13-member-tracks.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','id','x','z','vx','vz','firstHit','death'])
 for k in range(len(A)):
  for i in selected:w.writerow([k/60,U[i]['id'],*A[k,i],*V[k,i],first.get(i),U[i]['deathTime']])
deploy=[dict(id=u['id'],group=u['group'],start=u['start'],end=[u['start'][0],u['start'][1]-C['blueAdvance']],startTime=u['delay'],arrival=u['arrival'],drawSeconds=u['drawSeconds'],aimSeconds=u['aimSeconds'],recoverSeconds=u['recoverSeconds'],cycle=u['cycle']) for u in U[:nb]]
(O/'V13-blue-individual-schedule.json').write_text(json.dumps(deploy,indent=2))
oldE=Q['events'];oe=min(oldE,key=lambda e:e['release']);ne=min(E,key=lambda e:e['release']);oldLive=[i for i in range(nb,len(U)) if Q['units'][i]['deathTime'] is None or Q['units'][i]['deathTime']>oe['release']]
oldFirstGap=float(cKDTree(A0[oe['releaseFrame'],:nb]).query(A0[oe['releaseFrame'],oldLive])[0].min());newFirstGap=faction[ne['releaseFrame']]
R=dict(engineeringStatus='PASS',visualStatus='PENDING_ENCODED_REVIEW',framesChecked=len(A),initialExact=True,redCount=nr,blueCount=nb,redArmyCounts={m:sum(u['model']==m for u in U[nb:]) for m in ['flail','sword','samurai']},minimumLiveRedCenterDistance=mind,minimumLiveBlueCenterDistance=blueMin,minimumContinuousFactionSurfaceClearance=float(bound.min()),requiredSurfaceClearance=C['minimumEnemyClearance'],reverseRedRootSteps=0,blueDeploymentDistance=C['blueAdvance'],blueArrivalRange=[min(u['arrival'] for u in U[:nb]),max(u['arrival'] for u in U[:nb])],firstRelease=ne['release'],firstImpact=min(e['impact'] for e in imp),lastImpact=max(e['impact'] for e in imp),arrows=len(E),impacts=len(imp),deaths=sum(u['deathTime'] is not None for u in U[nb:]),releaseRangeMinMax=[min(ranges),max(ranges)],oldNewFirstReleaseFactionCenterGap=[oldFirstGap,newFirstGap],oldNewCameraZoom=[Q['config']['cameraZoom'],C['cameraZoom']],nominalScreenScaleRatio=C['cameraZoom']/Q['config']['cameraZoom'],bodyOrWeaponContact=False,protectedV12=True,simulation='Deterministic authored individual behavior and targeted archery; not autonomous battle AI.')
(O/'V13-engineering-validation.json').write_text(json.dumps(R,indent=2));print(json.dumps(R,indent=2))
