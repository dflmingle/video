from pathlib import Path
import json,csv,numpy as np
from scipy.spatial import cKDTree
P=Path(__file__).resolve().parents[1];d=P/'variants/FINAL';O=P/'output';S=json.loads((d/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount'];a=np.load(d/'trajectories.npy');v=np.load(d/'velocities.f32') if False else np.diff(a,axis=0,prepend=a[:1])*C['simulationFps'];b=np.load(d/'motion-data/trajectories.npy');st=np.load(d/'member-states.npy');rs=np.load(d/'movement-reasons.npy');ca=np.load(d/'slow-causes.npy');av=np.load(d/'avoidance-causes.npy')
E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];hits={i:[e for e in E if e['target']==i] for i in range(nb,len(U))};selected=[]
def add(i,role):
 if i not in [x['index'] for x in selected]:selected.append(dict(index=i,id=U[i]['id'],model=U[i]['model'],army=U[i]['army'],squadRow=U[i]['squadRow'],squadCol=U[i]['squadCol'],role=role,events=[{k:e[k] for k in ['id','release','impact','damage','remainingHP','killed','shooterID']} for e in hits[i]]))
for model in ['flail','sword']:
 for row in range(3):
  ids=[i for i,u in enumerate(U) if i>=nb and u['model']==model and u['squadRow']==row and u['squadCol']==1]
  i=min(ids,key=lambda i:float(v[-1,i,1])) if model=='sword' and row==0 else ids[len(ids)//2]
  add(i,f'{model}: formation depth {row}, '+('slowest terminal member of center-front squad' if model=='sword' and row==0 else 'central representative'))
sam=[i for i in range(nb,len(U)) if U[i]['model']=='samurai'];never=[i for i in sam if not hits[i]];add(max(never,key=lambda i:v[-1,i,1]),'unhit fast survivor');add(min(never,key=lambda i:v[-1,i,1]),'unhit worst terminal speed; include obstruction rather than hide it')
light=[i for i in sam if len(hits[i])==1 and not hits[i][0]['killed']];add(min(light,key=lambda i:hits[i][0]['impact']),'light wound, survives and falls behind')
serious=[i for i in sam if np.any(st[:,i-nb]==5) and U[i]['deathTime'] is None];add(serious[0] if serious else max(light,key=lambda i:hits[i][0]['impact']),'serious wound survivor' if serious else 'late light-wound survivor; no serious-wound interval occurs in this shot')
dead=sorted([i for i in sam if U[i]['deathTime'] is not None],key=lambda i:U[i]['deathTime']);add(dead[0],'earliest arrow death');add(dead[-1],'late arrow death')
assert len(selected)>=12
names={0:'CHARGE',1:'STAGGER',2:'RECOVER',3:'DEAD',4:'LIGHT_WOUND',5:'SERIOUS_WOUND'};reasons={0:'OWN_FORWARD_PATH',1:'OWN_ARROW_IMPACT',2:'AVOID_CONCRETE_WOUNDED',3:'OCCUPIED_BODY_YIELD'}
with (O/'representative-members-60hz.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','id','role','x','z','vx','vz','worldSpeed','state','reason','causeID','impactsThisFrame'])
 for k in range(len(a)):
  for x in selected:
   i=x['index'];j=i-nb;state=names[int(st[k,j])];time=k/C['simulationFps']
   if state=='CHARGE' and time<U[i]['delay']+U[i]['accelerationSeconds']:state='START_ACCEL'
   cause=int(ca[k,j]) if ca[k,j]>=0 else int(av[k,j]);w.writerow([time,x['id'],x['role'],*a[k,i],*v[k,i],np.linalg.norm(v[k,i]),state,reasons[int(rs[k,j])],U[nb+cause]['id'] if cause>=0 else '',','.join(e['id'] for e in hits[i] if e['impactFrame']==k)])
for x in selected:
 i=x['index'];x.update(initial=U[i]['start'],final=a[-1,i].tolist(),advance=float(a[-1,i,1]-a[0,i,1]),terminalSpeed=float(np.linalg.norm(v[-1,i])),counterfactualLag=float(b[-1,i,1]-a[-1,i,1]),minSpeedAfterStartup=float(v[60:,i,1].min()),stateSamples=[dict(time=k/C['simulationFps'],state=names[int(st[k,i-nb])],x=float(a[k,i,0]),z=float(a[k,i,1]),speed=float(np.linalg.norm(v[k,i]))) for k in range(0,len(a),12)])
(O/'representative-members.json').write_text(json.dumps(selected,indent=2));first=min(E,key=lambda e:e['impact']);moments=[dict(label='Initial formation',time=0),dict(label='High-speed charge',time=1.8),dict(label='Wounded members lag behind',time=3.35)]
(O/'key-moments.json').write_text(json.dumps(moments,indent=2))
# Population checks protect against selecting only successful examples.
base=json.loads((P/'baseline/V5-simulation.json').read_text());assert [u['id'] for u in U]==[u['id'] for u in base['units']];assert np.array_equal(a[0],np.load(P/'baseline/V5-trajectories.npy')[0]);minimum=100;overlaps=0
for k in range(len(a)):
 live=[i for i in range(nb,len(U)) if U[i]['deathTime'] is None or U[i]['deathTime']>k/C['simulationFps']];ds=cKDTree(a[k,live]).query(a[k,live],k=2)[0][:,1];minimum=min(minimum,float(ds.min()));overlaps+=int(np.count_nonzero(ds<.58-1e-5))
assert not overlaps,(minimum,overlaps)
assert abs(v[:,:,0]).max()<=1.8002 and np.min(v[:,nb:,1])>=-1e-5
army=[]
for model in ['flail','sword','samurai']:
 ids=[i for i in range(nb,len(U)) if U[i]['model']==model and not hits[i]];speeds=v[60:,ids,1];fractions=speeds/np.array([U[i]['speed'] for i in ids])[None,:];slowed=(fractions<.9);rr=rs[60:,np.array(ids)-nb];bad=slowed&(rr==0)
 army.append(dict(model=model,neverHitMembers=len(ids),neverHitTerminalForwardP10P50P90=np.percentile(v[-1,ids,1],[10,50,90]).tolist(),neverHitAdvanceP10P50P90=np.percentile(a[-1,ids,1]-a[0,ids,1],[10,50,90]).tolist(),below90PercentSamples=int(slowed.sum()),unexplainedSlowSamples=int(bad.sum()),neverHitSpeedP01P50P99=np.percentile(speeds,[1,50,99]).tolist()))
report=dict(initialMembersExactlyEqualV5=True,bodyRadius=.29,minimumLiveBodyDistance=minimum,bodyOverlapSamples=overlaps,maximumActualLateralSpeed=float(abs(v[:,nb:,0]).max()),maximumActualFrameStep=float(np.linalg.norm(np.diff(a,axis=0),axis=2).max()),maximumXDisplacement=float(abs(a[-1,nb:,0]-a[0,nb:,0]).max()),armies=army,allDeathsBoundToArrow=True,trackedCount=len(selected),motionStateNames=names,reasonNames=reasons,scope='Whole population at60Hz, circle bodies; not triangle-mesh collision. Any unhit slowdowns are explicitly included, not deleted from statistics.')
for u in U[nb:]:
 if u['deathTime'] is not None:assert any(e['targetID']==u['id'] and e['killed'] and e['impact']==u['deathTime'] for e in E)
(O/'member-motion-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
