from pathlib import Path
import json,hashlib,numpy as np
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V13';O=P/'output'
files=list((B/'src').glob('*'))+list((B/'variants/FINAL').glob('*.*'))+list((B/'output').glob('*.mp4'))
(O/'protected-v13.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()},indent=2))
c=json.loads((P/'variants/FINAL/params.json').read_text());c.update(version='V14',duration=3.0,paceAmplitude=.075,pacePeriodMin=.83,pacePeriodMax=1.38,dynamicStrideAmplitude=.045)
(P/'variants/FINAL/params.json').write_text(json.dumps(c,indent=2))
# Measure the old plateau on the actual healthy-member paths, not phase diversity.
s=json.loads((B/'variants/FINAL/simulation.json').read_text());a=np.load(B/'variants/FINAL/trajectories.npy');v=np.diff(a,axis=0)*60;nb=s['blueCount'];first={}
for e in s['events']:
 if e['resolution']=='IMPACT_IN_SHOT':first.setdefault(e['target'],e['impact'])
rows=[]
for army in range(3):
 ids=[i for i in range(nb,len(s['units'])) if s['units'][i]['army']==army and first.get(i,99)>2.2]
 temporal=np.std(v[35:130,ids,1],axis=0);speed=np.mean(v[35:130,ids,1],axis=0)
 rows.append(dict(army=army,healthyMembers=len(ids),speedTemporalStdP10P50P90=np.percentile(temporal,[10,50,90]).tolist(),averageSpeedP10P50P90=np.percentile(speed,[10,50,90]).tolist()))
(O/'V13-plateau-audit.json').write_text(json.dumps(dict(window=[.6,2.1666666667],rows=rows,findings=['Per-member root integration and phases already exist.','After individual startup, preferred forward velocity is nominal constant speed times injury factor.','Personal gaitStride and personalPosture remain constant for the whole run.','No fixed forward slot spring; only lateral platoon boundary and actual occupancy corrections.','V13 phase counts do not test persistent variation in each individual speed or cadence.']),indent=2))
print(json.dumps(rows,indent=2))
