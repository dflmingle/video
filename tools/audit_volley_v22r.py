"""Direct world/event/occupancy evidence for three normal-speed timeline prefixes."""
import collections,csv,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scene_occupancy_v22r import load_obstacles,signed_clearance

R=Path(__file__).resolve().parents[1];V=R/'variants/V22R-volley';O=R/'docs/v22r-volley';O.mkdir(exist_ok=True)
s=json.loads((V/'simulation.json').read_text(encoding='utf8'));c=json.loads((V/'params.json').read_text());p=np.load(V/'trajectories.npy');bc=np.load(V/'blue-control.npy');rc=np.load(V/'red-control.npy');nb=s['blueCount'];fps=60;dt=1/fps
vel=np.concatenate([np.zeros_like(p[:1]),np.diff(p,axis=0)*fps]);death=np.array([u.get('deathTime') if u.get('deathTime') is not None else 1e6 for u in s['units']]);events=s['events'];n=len(p)
gaps=[];redSpace=[];blueSpace=[];bodyDeadErrors=[]
for f,q in enumerate(p):
 gaps.append(float(cKDTree(q[:nb]).query(q[nb:])[0].min()-2*c['weaponEnvelopeRadius']))
 redSpace.append(float(cKDTree(q[nb:]).query(q[nb:],k=2)[0][:,1].min()))
 blueSpace.append(float(cKDTree(q[:nb]).query(q[:nb],k=2)[0][:,1].min()))
 if f:
  dead=(death[nb:]<(f-1)/fps-1e-8)
  bodyDeadErrors.append(float(np.max(np.linalg.norm(q[nb:][dead]-p[f-1,nb:][dead],axis=1))) if np.any(dead) else 0.)
gaps=np.array(gaps);steps=np.linalg.norm(np.diff(p,axis=0),axis=2);lower=np.minimum(gaps[:-1],gaps[1:])-.5*(steps[:,:nb].max(axis=1)+steps[:,nb:].max(axis=1))
obstacles=load_obstacles();staticMin=[min(float(signed_clearance(q,o).min()) for o in obstacles) for q in p]
old=json.loads((R/'baseline/V5-simulation.json').read_text());translationErrors=[]
for i,u in enumerate(s['units']):
 offset=c['blueArmyTranslation'] if i<nb else c['redArmyTranslations'][u['color']]
 translationErrors.append(float(np.linalg.norm(np.array(u['start'])-np.array(old['units'][i]['start'])-offset)))
firstMotion={}
for team,ids in [('red',slice(nb,None)),('blue',slice(None,nb))]:
 idsF=np.flatnonzero(np.any(np.linalg.norm(vel[:,ids],axis=2)>.02,axis=1));firstMotion[team]=None if not len(idsF) else float(idsF[0]/fps)
rangeTimes=np.full(nb,np.nan)
for f,q in enumerate(p):
 nearest=cKDTree(q[nb:]).query(q[:nb])[0];inside=(nearest<=c['archerRange'])&np.isnan(rangeTimes);rangeTimes[inside]=f/fps
firsts=[]
for j,u in enumerate(s['units'][:nb]):
 shots=[e for e in events if e['shooter']==j];a=[f/fps for f in range(n) if np.linalg.norm(vel[f,j])>.02];arr=np.flatnonzero((np.linalg.norm(p[:,j]-(np.array(u['target'])+u['slotOffset']),axis=1)<.08)&(np.linalg.norm(vel[:,j],axis=1)<.5))
 firsts.append(dict(id=u['id'],group=u['group'],firstMove=a[0] if a else None,arrival=float(arr[0]/fps) if len(arr) else None,firstAim=next((f/fps for f in range(n) if int(round(bc[f,j,0]))==3),None),firstDraw=next((f/fps for f in range(n) if int(round(bc[f,j,0]))==4),None),firstRange=float(rangeTimes[j]) if np.isfinite(rangeTimes[j]) else None,firstRelease=shots[0]['release'] if shots else None,releaseIds=[e['id'] for e in shots],releaseTimes=[e['release'] for e in shots],intervals=np.diff([e['release'] for e in shots]).tolist(),configured=dict(aim=u['aimSeconds'],draw=u['drawSeconds'],recover=u['recoverSeconds'],cycle=u['cycle'])))
(O/'each-shooter.json').write_text(json.dumps(firsts,indent=2),encoding='utf8')
releaseErrors=[abs(float(bc[e['releaseFrame'],e['shooter'],6])-.64) for e in events]
invalidRelease=[e['id'] for e in events if e['releaseDistance']>c['archerRange']+1e-5 or round(bc[e['releaseFrame'],e['shooter'],0])!=5 or round(bc[e['releaseFrame'],e['shooter'],11])!=int(e['id'][1:])]
with (O/'every-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','redMoving','redLive','redMeanForwardSpeed','redAdvance','redSpeedP90','blueMoving','blueAssemblyDistance','bluePreparing','releases','arrowsInFlight','hits','kills','redAvoiding','minimumSurfaceGap','redMinSpacing','blueMinSpacing'])
 records=[]
 for k in range(0,n,6):
  t=k/fps;end=min(n,k+6)/fps;alive=death[nb:]>t;rv=vel[k,nb:,1];prepared=np.isin(np.rint(bc[k,:,0]),[3,4]);redMoving=int(np.sum((np.linalg.norm(vel[k,nb:],axis=1)>.02)&alive))
  row=[t,redMoving,int(alive.sum()),float(rv[alive].mean()) if np.any(alive) else 0.,float(np.mean(p[k,nb:,1]-p[0,nb:,1])),float(np.quantile(rv[alive],.9)) if np.any(alive) else 0.,int(np.sum(np.linalg.norm(vel[k,:nb],axis=1)>.02)),float(np.mean(p[0,:nb,1]-p[k,:nb,1])),int(prepared.sum()),sum(t<=e['release']<end for e in events),sum(e['release']<=t<e['impact'] for e in events),sum(e['resolution']=='IMPACT_IN_SHOT' and t<=e['impact']<end for e in events),sum(e.get('killed') and t<=e['impact']<end for e in events),int(np.sum(np.rint(rc[k,:,9])==2)),float(gaps[k]),redSpace[k],blueSpace[k]]
  w.writerow(row);records.append(row)
candidates=[]
for duration in [3.,3.5,4.]:
 frames=min(n,round(duration*fps));eligible=[e for e in events if e['release']<duration];hits=[e for e in events if e['resolution']=='IMPACT_IN_SHOT' and e['impact']<duration];count=collections.Counter(e['shooter'] for e in eligible);first=eligible[0]['release'] if eligible else None;last=eligible[-1]['release'] if eligible else None
 start=int(math.floor((first or duration)*fps));coverage=sum(any(e['release']<=f/fps<e['impact'] for e in eligible) for f in range(start,frames))/fps
 active=[r for r in records if .1<=r[0]<duration];tail=[r for r in records if max(0,duration-.5)<=r[0]<duration]
 complete=frames==round(duration*fps)
 numeric=complete and min(lower[:max(1,frames-1)])>=4 and min(redSpace[:frames])>=.614 and min(blueSpace[:frames])>=.614 and min(staticMin[:frames])>=c['bodyRadius']
 candidates.append(dict(label={3.:'A',3.5:'B',4.:'C'}[duration],duration=duration,available=complete,status='NUMERIC_PASS_VISUAL_PENDING' if numeric else 'FAIL',releases=len(eligible),hits=len(hits),kills=sum(bool(e.get('killed')) for e in hits),shootersTwoOrMore=sum(v>=2 for v in count.values()),shootersThreeOrMore=sum(v>=3 for v in count.values()),firstRelease=first,lastRelease=last,firstHit=min((e['impact'] for e in hits),default=None),continuousFlightCoverageSeconds=coverage,releaseSpanSeconds=None if first is None else last-first,minimumSurfaceGap=float(min(gaps[:frames])),minimumConservativeGap=float(min(lower[:max(1,frames-1)])),gapAtEnd=float(gaps[min(n-1,round(duration*fps))]),minimumRedSpacing=min(redSpace[:frames]),minimumBlueSpacing=min(blueSpace[:frames]),redMeanAdvance=float(np.mean(p[frames-1,nb:,1]-p[0,nb:,1])),redTailMeanSpeed=float(np.mean([r[3] for r in tail])),redTailMovingMean=float(np.mean([r[1] for r in tail])),blueMeanAssembly=float(np.mean(p[0,:nb,1]-p[frames-1,:nb,1])),noAllArmyFreeze=all(r[1]>0 for r in active),allBodyDeathRootsFixed=max(bodyDeadErrors[:max(1,frames-1)],default=0.)<1e-7))
proposal=json.loads((O/'proposal.json').read_text());hashes={path:hashlib.sha256((R/path).read_bytes()).hexdigest() for path in proposal['sourceHashes']}
result=dict(variant='V22R-volley',frames=n,lastComputedTime=(n-1)/fps,candidates=candidates,firstMotion=firstMotion,firstRange=float(np.nanmin(rangeTimes)),initialCenterDistance=float(cKDTree(p[0,:nb]).query(p[0,nb:])[0].min()),initialSurfaceGap=float(gaps[0]),redStartsBounds={axis:[float(p[0,nb:,k].min()),float(p[0,nb:,k].max())] for k,axis in enumerate(['x','z'])},blueStartsBounds={axis:[float(p[0,:nb,k].min()),float(p[0,:nb,k].max())] for k,axis in enumerate(['x','z'])},wallFrontZ=-29.7378,allRedStartsInFrontOfWall=bool(np.all(p[0,nb:,1]>-29.7378)),translationMaxError=max(translationErrors),releasePhaseMaxError=max(releaseErrors,default=0.),invalidReleaseEvents=invalidRelease,sceneAndCameraFilesUnchanged=hashes==proposal['sourceHashes'],sourceHashes=hashes,simulationHashes={name:hashlib.sha256((V/name).read_bytes()).hexdigest() for name in ['params.json','simulation.json','trajectories.f32','blue-control.f32']},visualAcceptance='PENDING: numeric tests cannot establish normal-speed visual acceptance')
result['staticOccupancy']=dict(meshIslands=len(obstacles),minimumSignedClearance=float(min(staticMin)),requiredBodyRadius=c['bodyRadius'],method='Original world mesh disconnected islands, convex hull of vertices in living-body height band; conservative boundary, not hand-drawn arena sectors')
(O/'feasibility.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=True,indent=2))
