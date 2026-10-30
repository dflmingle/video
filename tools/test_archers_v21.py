from pathlib import Path
import json, numpy as np
P=Path('variants/FINAL'); S=json.loads((P/'simulation.json').read_text()); C=S['config']; n=S['blueCount']; F=S['frames'];
traj=np.fromfile(P/'trajectories.f32',dtype=np.float32).reshape(F,n+S['redCount'],2)[:,:n]
ctrl=np.fromfile(P/'blue-control.f32',dtype=np.float32).reshape(F,n,12)
units=S['units'][:n]
start=np.array([u['start'] for u in units],float); initial_err=float(np.max(np.linalg.norm(traj[0]-start,axis=1)))
# final blue endpoints and stable slot offsets
final=traj[-1]; expected_endpoint=start+np.array([[u.get('slotOffset',[0,0])[0],-C['blueAdvance']+u.get('slotOffset',[0,0])[1]] for u in units]); endpoint_shift=np.linalg.norm((expected_endpoint-expected_endpoint),axis=1)
# attack transition/release spread
release_times=[]
for j in range(n):
 idx=np.where(np.diff((ctrl[:,j,0]>=4).astype(np.int8))>0)[0]
 if len(idx):release_times.append((j,(idx[0]+1)/C['simulationFps']))
state_spread={str(g):{} for g in range(C['blueGroups'])}
for g in range(C['blueGroups']):
 ids=[j for j,u in enumerate(units) if u['group']==g]
 for st,name in [(1,'moving'),(2,'arriving'),(3,'aiming'),(4,'drawing')]:
  times=[]
  for j in ids:
   ix=np.where(ctrl[:,j,0].astype(int)==st)[0]
   if len(ix):times.append(ix[0]/C['simulationFps'])
  if times:state_spread[str(g)][name]=[float(min(times)),float(max(times)),float(np.std(times))]
# nearest blue spacing at expected U endpoints, row-wise.
same_group=[]
for g in range(C['blueGroups']):
 ids=[j for j,u in enumerate(units) if u['group']==g]
 for row in range(6):
  rowids=ids[row*6:(row+1)*6]; x=np.sort(expected_endpoint[rowids,0]); same_group += list(np.diff(x))
report={'version':'V21','frames':F,'initialPositionMaxError':initial_err,'maxEndpointShiftError':float(endpoint_shift.max()),'slotOffsetMax':float(np.max(np.linalg.norm(np.array([u['slotOffset'] for u in units]),axis=1))), 'releaseCount':len(release_times),'releaseTimeRange':[float(min(t for _,t in release_times)),float(max(t for _,t in release_times))] if release_times else None,'releaseTimeStd':float(np.std([t for _,t in release_times])) if release_times else None,'stateSpread':state_spread,'sameGroupSpacingMin':float(min(same_group))}
Path('output/V21-archer-tests.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
assert initial_err < 1e-5
assert report['slotOffsetMax'] <= .08
assert report['releaseTimeStd'] > .02
assert report['sameGroupSpacingMin'] > .7