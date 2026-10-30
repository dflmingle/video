from pathlib import Path
import json,hashlib,numpy as np
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V16';O=P/'output'
protected=[*B.glob('src/*'),*B.glob('variants/FAST125/*'),*B.glob('output/*.mp4'),B/'V16-REVIEW.md']
(O/'protected-v16.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()},indent=2))
C=json.loads((B/'variants/FAST125/params.json').read_text());C.update(version='V17',variant='FINAL',duration=6.,archerRange=34.,archerCycle=.61,runStride=4.5,runLean=.25,formationFarDistance=52.,formationNearDistance=18.,cameraMode='FIXED',cameraZoom=1.55,cameraFixedCenterZ=-35.)
(P/'variants/FINAL/params.json').write_text(json.dumps(C,indent=2))
pkg=json.loads((P/'package.json').read_text());pkg['name']='pve-montage-shot01-v17';pkg['scripts']['dev']='vite --host 127.0.0.1 --port 5257 --strictPort';(P/'package.json').write_text(json.dumps(pkg,indent=2))
for name in ['index.html','camera.html']:
 p=P/name;p.write_text(p.read_text(encoding='utf-8').replace('"FAST125"','"FINAL"').replace('V16','V17'),encoding='utf-8')
S=json.loads((B/'variants/FAST125/simulation.json').read_text());A=np.load(B/'variants/FAST125/trajectories.npy');nb=S['blueCount'];K=np.load(B/'variants/FAST125/red-control.npy');last=S['config']['duration']
tests=[]
for radius in [38,36,34,32]:
 for f,p in enumerate(A):
  delta=p[nb:,None,:]-p[None,:nb,:];dist=np.linalg.norm(delta,axis=2);r,j=np.unravel_index(dist.argmin(),dist.shape)
  if dist[r,j]<=radius:
   rel=delta[r,j];v=np.array([0,K[f,r,1]]);qa=v@v-72**2;qb=2*rel@v;qc=rel@rel;roots=np.roots([qa,qb,qc]);flight=min(float(x.real) for x in roots if abs(x.imag)<1e-8 and x.real>0)
   tests.append(dict(range=radius,earliestRangeEntry=f/60,instantReadyFirstHit=f/60+flight,optimisticWindow=last-f/60-flight));break
report=dict(baselineEnd=last,initialRedBounds=[A[0,nb:].min(axis=0).tolist(),A[0,nb:].max(axis=0).tolist()],blueInitialBounds=[A[0,:nb].min(axis=0).tolist(),A[0,:nb].max(axis=0).tolist()],blueDeploymentDistance=7.5,baselineFirstRelease=1.4,baselineFirstHit=1.8166666666666667,arrowSpeed=72,requiredSafety=4,rangeUpperBoundTests=tests,note='Optimistic bound: even instant readiness at range entry. Deployment and draw time can only delay hit. Positions not changed.')
(O/'V17-timing-feasibility.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
