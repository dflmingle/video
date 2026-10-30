"""Audit real charge, archery and unchanged rules. Candidate B remains rejected."""
import collections,csv,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scene_occupancy_v22r import load_obstacles,signed_clearance
R=Path(__file__).resolve().parents[1];V=R/'variants/V22R-fast-A';D=R/'docs/v22r-fast-charge'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
s=load(V/'simulation.json');old=load(R/'variants/V22R-overlap/simulation.json');c=s['config'];nb=s['blueCount'];p=np.load(V/'trajectories.npy');bc=np.load(V/'blue-control.npy');control=np.load(V/'red-control.npy');op=np.load(R/'variants/V22R-overlap/trajectories.npy');n=len(p);fps=60;videoFrames=round(c['duration']*fps);duration=videoFrames/fps
death=np.array([u.get('deathTime') if u.get('deathTime') is not None else 1e6 for u in s['units'][nb:]])
vel=np.concatenate([np.zeros_like(p[:1]),np.diff(p,axis=0)*fps]);gaps=[];rs=[];bs=[];rows=[];groups=collections.defaultdict(list)
for j,u in enumerate(s['units'][nb:]):groups[u['platoon']].append(j)
for k,q in enumerate(p):
 t=k/fps;alive=death>t;speed=np.linalg.norm(vel[k,nb:][alive],axis=1);gap=float(cKDTree(q[:nb]).query(q[nb:])[0].min()-2*c['weaponEnvelopeRadius']);gaps.append(gap);rs.append(float(cKDTree(q[nb:]).query(q[nb:],k=2)[0][:,1].min()));bs.append(float(cKDTree(q[:nb]).query(q[:nb],k=2)[0][:,1].min()))
 if k%6==0:
  rows.append(dict(time=t,redLive=int(alive.sum()),redMoving=int((speed>.02).sum()),redSpeedMedian=float(np.median(speed)),redSpeedP10=float(np.quantile(speed,.1)),redSpeedMean=float(speed.mean()),redForwardMean=float(vel[k,nb:,1][alive].mean()),redAdvanceMean=float((q[nb:,1]-p[0,nb:,1]).mean()),blueMoving=int((np.linalg.norm(vel[k,:nb],axis=1)>.02).sum()),blueAssemblyMean=float((p[0,:nb,1]-q[:nb,1]).mean()),bluePreparing=int(np.isin(np.rint(bc[k,:,0]),[3,4]).sum()),releases=sum(t<=e['release']<min(t+.1,duration) for e in s['events']),arrowsFlying=sum(e['release']<=t<e['impact'] for e in s['events']),hits=sum(e['resolution']=='IMPACT_IN_SHOT' and t<=e['impact']<min(t+.1,duration) for e in s['events']),surfaceGap=gap))
with (D/'A-actions-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
steps=np.linalg.norm(np.diff(p,axis=0),axis=2);lower=np.minimum(gaps[:-1],gaps[1:])-.5*(steps[:,:nb].max(1)+steps[:,nb:].max(1))
events=[e for e in s['events'] if e['release']<duration];hits=[e for e in s['events'] if e['resolution']=='IMPACT_IN_SHOT' and e['impact']<duration];counts=collections.Counter(e['shooter'] for e in events)
perShooter=[]
for j,u in enumerate(s['units'][:nb]):
 es=[e for e in s['events'] if e['shooter']==j];first=lambda st:next((k/fps for k in range(n) if round(bc[k,j,0])==st),None)
 perShooter.append(dict(id=u['id'],group=u['group'],firstAim=first(3),firstDraw=first(4),releases=[e['release'] for e in es],arrows=[e['id'] for e in es],intervals=np.diff([e['release'] for e in es]).tolist(),drawSeconds=u['drawSeconds'],aimSeconds=u['aimSeconds'],recoverSeconds=u['recoverSeconds'],cycle=u['cycle']))
(D/'A-each-shooter.json').write_text(json.dumps(perShooter,indent=2),encoding='utf8')
formation=[]
for name,ids in groups.items():
 ids=np.array(ids);width=np.ptp(p[:,nb+ids,0],axis=1);depth=np.ptp(p[:,nb+ids,1],axis=1);delta=p[:,nb+ids,0]-p[0,nb+ids,0]
 formation.append(dict(platoon=name,initialWidth=float(width[0]),finalWidth=float(width[-1]),maximumWidth=float(width.max()),initialDepth=float(depth[0]),finalDepth=float(depth[-1]),maximumPersonalLateralDeviation=float(np.abs(delta).max())))
(D/'A-squad-formation.json').write_text(json.dumps(formation,indent=2),encoding='utf8')
params=['walkSpeed','walkAccel','walkBrake','aimSeconds','drawSeconds','recoverSeconds','cycle','turnSeconds']
sameParams=all(u[key]==v[key] for u,v in zip(s['units'][:nb],old['units'][:nb]) for key in params)
beforeHit=min(e['impactFrame'] for e in s['events'] if e['resolution']=='IMPACT_IN_SHOT');common=min(beforeHit,len(op));deviation=float(np.max(np.linalg.norm(p[:common,nb:]-op[:common,nb:],axis=2)))
proposal=load(D/'proposal-and-B-geometry.json');unchanged={key:hashlib.sha256((R/key).read_bytes()).hexdigest()==value for key,value in proposal['sourceHashes'].items()}
result=dict(variant='V22R-fast-A',requestedDuration=3.5,acceptedStateTime=(n-1)/fps,videoDuration=duration,videoFrames=videoFrames,firstRelease=min(e['release'] for e in events),firstActualImpact=min(e['impact'] for e in hits),releasesInVideo=len(events),hitsInVideo=len(hits),killsInVideo=sum(bool(e.get('killed')) for e in hits),releasesIncludingBoundary=len(s['events']),hitsIncludingBoundary=sum(e['resolution']=='IMPACT_IN_SHOT' for e in s['events']),shootersFired=len(counts),shootersWithTwoOrMore=sum(v>=2 for v in counts.values()),groupReleaseCounts=dict(collections.Counter(s['units'][e['shooter']]['group'] for e in events)),flightCoverage=sum(any(e['release']<=k/fps<e['impact'] for e in events) for k in range(videoFrames))/fps,allOriginalBluePersonalTimingAndWalkingParametersUnchanged=sameParams,redStartPositionsUnchanged=all(u['start']==v['start'] for u,v in zip(s['units'][nb:],old['units'][nb:])),blueStartPositionsUnchanged=all(u['start']==v['start'] for u,v in zip(s['units'][:nb],old['units'][:nb])),sourceHashChecks=unchanged,minimumSampleGap=min(gaps),minimumConservativeGap=float(min(lower)),minimumRedCenterSpacing=min(rs),minimumBlueCenterSpacing=min(bs),maximumRedReverseStep=float(np.max(np.maximum(0,-np.diff(p[:,nb:,1],axis=0)))),maximumRedLateralDeviation=float(np.max(np.abs(p[:,nb:,0]-p[0,nb:,0]))),redPreImpactTrajectoryDifferenceFromOriginal=deviation,whyNotBitIdentical='Original red controller reads actual blue distances for formation pressure. Earlier blue attack stance slightly changes actual blue positions; true earlier impacts then change wounded trajectories. Red controller, speed and acceleration are not replaced.',releasePhaseMaximumError=max(abs(float(bc[e['releaseFrame'],e['shooter'],6])-.64) for e in s['events']),invalidReleases=[e['id'] for e in s['events'] if e['releaseDistance']>c['archerRange']+1e-5 or round(bc[e['releaseFrame'],e['shooter'],0])!=5],termination=load(V/'termination-evidence.json'),movementSamples=rows,visualAcceptance='PENDING',B=proposal['B'])
assert sameParams and all(unchanged.values()) and not result['invalidReleases'] and result['minimumConservativeGap']>=4
result['firstMotion']={team:next((k/fps for k in range(1,n) if np.any(np.linalg.norm(p[k,ids]-p[k-1,ids],axis=1)>.02/fps)),None) for team,ids in [('red',slice(nb,None)),('blue',slice(None,nb))]}
result['firstRealRange']=next((k/fps for k,q in enumerate(p) if cKDTree(q[nb:]).query(q[:nb])[0].min()<=c['archerRange']),None)
def width_ratios(q):
 return [float(np.ptp(q[:,nb+np.array(ids),0],axis=1).max()/np.ptp(q[0,nb+np.array(ids),0])) for ids in groups.values()]
x=width_ratios(op);y=width_ratios(p[:len(op)]);z=width_ratios(p)
result['formationBaselineComparison']=dict(originalMaximumSquadWidthRatio=max(x),ACommonMaximumSquadWidthRatio=max(y),AEndMaximumSquadWidthRatio=max(z),originalMedianSquadWidthRatio=float(np.median(x)),ACommonMedianSquadWidthRatio=float(np.median(y)),sameLargeLateralSpreadAlreadyPresent=True,warning='Baseline squad outlines already loosen considerably; no claim that rigid outlines persist.')
obstacles=load_obstacles();minimum=1e6;worst=None;badFrames=0
for k,q in enumerate(p):
 distances=np.min(np.array([signed_clearance(q,o) for o in obstacles]),axis=0);m=float(distances.min());badFrames+=int(np.any(distances<c['bodyRadius']))
 if m<minimum:minimum=m;worst=dict(frame=k,time=k/fps,unitIndex=int(np.argmin(distances)))
result['sceneCollisionCheck']=dict(minimumConservativeFootprintClearance=minimum,worst=worst,framesWithAnyFootprintViolation=badFrames,method='Original world-mesh islands, living-body height band conservative hulls',verdict='FAIL: original approach crosses native scenery; no scene or path changed')
result['visualAcceptance']='PARTIAL_ONLY: early real shooting and high red speed demonstrated; original scene crossing, cropping and loose squad outlines remain. B spatially rejected.'
(D/'A-audit.json').write_text(json.dumps(result,indent=2),encoding='utf8');shutil.copyfile(V/'params.json',D/'A-accepted-params.json')
print(json.dumps({k:v for k,v in result.items() if k not in ['movementSamples','B','termination']},indent=2))
