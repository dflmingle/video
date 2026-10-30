from pathlib import Path
import json,numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';s=json.loads((D/'simulation.json').read_text());a=np.load(D/'trajectories.npy');nb=s['blueCount'];u=s['units'];hit={e['target'] for e in s['events'] if e['resolution']=='IMPACT_IN_SHOT'};options=[]
for e in s['events']:
 if e['resolution']!='IMPACT_IN_SHOT' or e['killed'] or e['impact']>2.8 or u[e['target']]['deathTime'] is not None:continue
 i=e['target'];k=e['impactFrame'];end=min(len(a)-1,k+65)
 for j in range(nb,len(u)):
  if j in hit or u[j]['army']!=u[i]['army']:continue
  dx=abs(a[k,j,0]-a[k,i,0]);z0=a[k,j,1]-a[k,i,1];z1=a[end,j,1]-a[end,i,1]
  if dx<1.8 and -3.0<z0<-.4 and z1>1:options.append((z1-z0,e,j,z0,z1))
assert options,'No verified overtaking pair';options.sort(key=lambda x:-x[0]);q=options[0];e=q[1];r=dict(event=e,victim=e['targetID'],follower=u[q[2]]['id'],followerIndex=q[2],relativeZAtImpact=float(q[3]),relativeZAfter=float(q[4]),endTime=min(s['config']['duration'],e['impact']+65/60));(P/'output/overtaking-pair.json').write_text(json.dumps(r,indent=2))
