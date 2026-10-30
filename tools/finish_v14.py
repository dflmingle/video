from pathlib import Path
import json, hashlib, subprocess, numpy as np
from media_v11 import ff

P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output'
S=json.loads((D/'simulation.json').read_text());U=S['units'];nb=S['blueCount']
A=np.load(D/'trajectories.npy');K=np.load(D/'red-control.npy');slow=np.load(D/'slow-causes.npy');avoid=np.load(D/'avoidance-causes.npy')
ids=json.loads((O/'tracked-v14.json').read_text())['indices'];examples=[]
first={}
for e in S['events']:
 if e['resolution']=='IMPACT_IN_SHOT':first.setdefault(e['target'],e['impact'])
for i in ids:
 j=i-nb
 for k in range(36,len(A)-7):
  q=int(slow[k,j]);t=k/60
  if q<0 or first.get(i,99)<=t:continue
  if K[k,j,0]-K[k,j,1]<1:continue
  dist=float(np.linalg.norm(A[k,i]-A[k,nb+q]))
  if dist>1.3:continue
  end=k+1+int(np.argmax(K[k+1:min(k+19,len(A)),j,1]))
  if K[end,j,1]<=K[k,j,1]+1:continue
  examples.append(dict(id=U[i]['id'],time=t,actualSpeed=float(K[k,j,1]),targetSpeed=float(K[k,j,0]),obstacle=U[nb+q]['id'],centerDistance=dist,recoveryTime=end/60,recoverySpeed=float(K[end,j,1]),lateralDisplacement=float(A[end,i,0]-A[k,i,0]),passingTarget=U[nb+int(avoid[k,j])]['id'] if avoid[k,j]>=0 else None));break
protected=json.loads((O/'protected-v13.json').read_text())
for p,h in protected.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
files=['PVE-Shot01-U-Archers-v14.mp4','V14-red20-continuous-behavior.mp4','V13-V14-realtime-comparison.mp4','V13-V14-same20-local-comparison.mp4']
media=[]
for name in files:
 p=O/name;r=subprocess.run([ff,'-hide_banner','-i',str(p)],capture_output=True,text=True,encoding='utf-8',errors='replace')
 stream=[l.strip() for l in r.stderr.splitlines() if 'Video:' in l]
 assert stream and 'h264' in stream[0] and 'yuv420p' in stream[0]
 media.append(dict(file=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),stream=stream[0]))
out=dict(currentArtifactsVerified=True,protectedV13Files=len(protected),protectedV13Unchanged=True,localPhysicalYieldExamples=examples,media=media,visualReview=dict(status='PARTIAL',method='Decoded MP4 overview, keyframes and successive-frame sheets; no normal-speed playback capability and no claim of watching every frame.',findings=['Persistent local pose and relative-position variation visible.','Forward charge and target-bound stagger/death visible.','Macro view remains organized colored cohorts; improved individuality is clearest in local verification.','Broad shoulders and weapons still overlap in projection; center-distance constraints do not prove full articulated mesh nonintersection.']))
(O/'V14-final-validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
eng=json.loads((O/'V14-engineering-validation.json').read_text());eng['visualStatus']='PARTIAL_ENCODED_FRAMES_REVIEWED';(O/'V14-engineering-validation.json').write_text(json.dumps(eng,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
