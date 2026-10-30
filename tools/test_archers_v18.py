from pathlib import Path
import json,numpy as np
P=Path('variants/FINAL'); S=json.loads((P/'simulation.json').read_text()); C=S['config']; n=S['blueCount']; F=S['frames']; ctrl=np.fromfile(P/'blue-control.f32',dtype=np.float32).reshape(F,n,12); pos=np.fromfile(P/'trajectories.f32',dtype=np.float32).reshape(F,S['blueCount']+S['redCount'],2)[:,:n]
report={'frames':F,'blueCount':n,'columns':S['controlColumns'],'safeDistance':json.loads((P/'safety-and-causality.json').read_text())['minimumSurfaceClearance']}
# state transition times per representative first/center/last group
for g,label in [(0,'left'),(3,'center'),(6,'right')]:
 ids=[i for i,u in enumerate(S['units'][:n]) if u['group']==g][:12]; rows=[]
 for i in ids:
  seq=[]; last=None
  for f,s in enumerate(ctrl[:,i,0].astype(int)):
   if s!=last: seq.append({'t':round(f/C['simulationFps'],3),'state':int(s)}); last=s
  rows.append({'id':S['units'][i]['id'],'transitions':seq})
 report[label]=rows
# actual path speed while moving, per archer
v=np.linalg.norm(np.diff(pos,axis=0),axis=2)*C['simulationFps']; report['movingSpeedP10P50P90']=np.percentile(v[ctrl[:-1,:,0]==1],[10,50,90]).tolist(); report['speedStd']=float(np.std(v[ctrl[:-1,:,0]==1])); report['phaseStdAt1s']=float(np.std(ctrl[min(F-1,60),:,4])); report['actionPhaseStdAt1s']=float(np.std(ctrl[min(F-1,60),:,6]));
Path('output/V18-archer-behavior-tests.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'movingSpeedP10P50P90':report['movingSpeedP10P50P90'],'speedStd':report['speedStd'],'phaseStdAt1s':report['phaseStdAt1s'],'actionPhaseStdAt1s':report['actionPhaseStdAt1s']},indent=2))



