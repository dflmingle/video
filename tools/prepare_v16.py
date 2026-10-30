from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V15'
files=[*B.glob('src/*'),*B.glob('variants/FINAL/*.json'),*B.glob('variants/FINAL/*.npy'),*B.glob('variants/FINAL/*.f32'),*B.glob('output/*.mp4'),B/'tools/motion_v15.py',B/'tools/build_simulation_v15.py']
(P/'output/protected-v15.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2))
pkg=json.loads((P/'package.json').read_text());pkg['name']='pve-montage-shot01-v16';pkg['scripts']['dev']='vite --host 127.0.0.1 --port 5256 --strictPort';(P/'package.json').write_text(json.dumps(pkg,indent=2))
base=json.loads((B/'variants/FINAL/params.json').read_text())
for name,mult in [('BASE100',1.),('FAST125',1.25),('FAST150',1.5)]:
 C=dict(base,version='V16',variant=name,duration=6.,autoCut=True,chargeMultiplier=mult,redSpeed=base['redSpeed']*mult,blueMoveSeconds=1.62,cameraMode='FIXED',cameraZoom=3.2,cameraFixedCenterZ=-6.,cameraFollowSmoothTime=.8,cameraFollowMaxSpeed=6.)
 (P/f'variants/{name}/params.json').write_text(json.dumps(C,indent=2));(P/f'variants/{name}/asset-render-audit.json').write_bytes((B/'variants/FINAL/asset-render-audit.json').read_bytes())
# Retain generation/archery and replace duration with measured safe cut.
s=(B/'tools/build_simulation_v15.py').read_text(encoding='utf-8').replace('from motion_v15 import Crowd','from motion_v16 import Crowd')
s=s.replace("u['moveSeconds']=C['blueMoveSeconds']*(.92+.017*row+.050*r)","u['moveSeconds']=C['blueMoveSeconds']*(.88+.025*row+.080*r)")
# Detect safety before adding a future frame: safety envelope includes intra-tick
# motion, not just root centers. Discard this violating state; never brake army.
s=s.replace("if m<minimum:minimum=m;minf=f", """if f and C.get('autoCut'):
  prior=distanceByFrame[-2];maxStep=np.linalg.norm(positions[f]-positions[f-1],axis=1)
  lower=min(prior,m)-.5*(maxStep[:nb].max()+maxStep[nb:].max())-2*C['weaponEnvelopeRadius']
  if lower<C['minimumEnemyClearance']+.05:
   N=f;cutFrame=f-1;C['duration']=cutFrame*dt
   for target,e in scheduled.pop(f,[]):pass
   break
 if m<minimum:minimum=m;minf=f""")
# First unsafe state has not fired any arrows. Any later pending hits remain
# in flight; classify from the final actual cut, not the old six-second horizon.
needle="audit=json.loads((O/'asset-render-audit.json').read_text())"
idx=s.index(needle)
s=s[:idx]+'''# Trim all authoritative arrays to the last safe state. Reclassify arrows
# beyond that state instead of claiming their damage happened on screen.
positions=positions[:N];velocities=velocities[:N];gait=gait[:N];lastHit=lastHit[:N];control=control[:N];cycles=cycles[:N];states=states[:N];avoidance=avoidance[:N];reason=reason[:N];slowCause=slowCause[:N]
distanceByFrame=distanceByFrame[:N];minimum=min(distanceByFrame);minf=int(np.argmin(distanceByFrame))
for j in range(nr):
 if death[j]>C['duration']:death[j]=1e6
for e in events:
 if e['impactFrame']>=N:
  e.update(resolution='IN_FLIGHT_AT_CUT',damage=None,remainingHP=None,killed=False,destinationEvidence='Extrapolated beyond safe cut; no visible impact claimed')
responses=[e for e in responses if e['time']<=C['duration']]
(O/'params.json').write_text(json.dumps(C,indent=2))
''' +s[idx:]
s=s.replace("dict(version='V15'","dict(version='V16'")
(P/'tools/build_simulation_v16.py').write_text(s,encoding='utf-8')
print('Prepared V16; V15 protected')
