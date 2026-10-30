from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V14'
files=[*B.glob('src/*'),B/'tools/build_simulation_v11.py',B/'tools/motion_v15.py',*B.glob('variants/FINAL/*.json'),*B.glob('variants/FINAL/*.npy'),*B.glob('variants/FINAL/*.f32'),*B.glob('output/*.mp4')]
protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
(P/'output/protected-v14.json').write_text(json.dumps(protected,indent=2))
C=json.loads((P/'variants/FINAL/params.json').read_text());C['version']='V15';(P/'variants/FINAL/params.json').write_text(json.dumps(C,indent=2))
pkg=json.loads((P/'package.json').read_text());pkg['name']='pve-montage-shot01-v15';pkg['scripts']['dev']='vite --host 127.0.0.1 --port 5255 --strictPort';(P/'package.json').write_text(json.dumps(pkg,indent=2))
# Keep battle/blue pipeline; replace the complete red motion authority.
s=(B/'tools/build_simulation_v11.py').read_text(encoding='utf-8')
s=s.replace('import numpy as np','import numpy as np\nfrom motion_v15 import Crowd\nimport time')
s=s.replace("for u in red:\n u['deathTime']", "for u in red:\n u['deathTime']",1)
a=s.index('for u in red:\n');b=s.index('\nsquadBounds={}',a)
s=s[:a]+'''for u in red:
 u['deathTime']=None
 u['delay']=float(.035+.125*u['phase']+.018*u['squadRow']+.006*u['row'])
 u['accelerationSeconds']=.25
motion=Crowd(red,C)
''' +s[b:]
s=s.replace("control[0,:,3]=stride;control[0,:,5]=posture","control[0]=motion.control();simulationStart=time.perf_counter()")
s=s.replace("damage=int(e['plannedDamage']);hp[target]-=damage;hit[target]=t;", "damage=int(e['plannedDamage']);motion.apply_hit(target,damage,t);hp[target]-=damage;hit[target]=t;")
a=s.index(' if f:\n  previous=rp.copy()');b=s.index(' positions[f,nb:]=rp;',a)
s=s[:a]+''' if f:
  motion.step(t,dt);rp=motion.position.copy();control[f]=motion.control()
  states[f]=motion.behavior;avoidance[f]=motion.route;reason[f]=motion.reason;slowCause[f]=motion.neighbor
''' +s[b:]
s=s.replace("cycles[f,nb:]=cycles[f-1,nb:]+np.linalg.norm(step[nb:],axis=1)/np.maximum(.1,(control[f,:,3]+control[f-1,:,3])*.5)","cycles[f,nb:]=motion.cycles")
s=s.replace("dict(version='V14'","dict(version='V15'")
s=s.replace("print({k:v for k,v in report.items() if k!='distanceByFrame'},flush=True)","(O/'simulation-performance.json').write_text(json.dumps(dict(wallSeconds=time.perf_counter()-simulationStart,steps=motion.metrics),indent=2));print({k:v for k,v in report.items() if k!='distanceByFrame'},flush=True)")
(P/'tools/build_simulation_v15.py').write_text(s,encoding='utf-8')
print('V15 prepared; protected',len(protected),'V14 files')
