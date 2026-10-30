from pathlib import Path
import json,csv,cv2,numpy as np
from media_v11 import encoder,check,fit,jpg,at
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';C=json.loads((D/'params.json').read_text());N=round(C['duration']*60)
records={team:json.loads((D/f'behavior-{team}/states.json').read_text()) for team in ['red','blue']};proc=encoder(O/'V13-individual-behavior-validation.mp4',1920,1300,60);rows=[];stats={}
colors={'DEPLOY':(255,195,70),'DECEL':(240,210,80),'WAIT':(180,180,180),'READY':(190,190,190),'TURN':(200,180,255),'DRAW':(150,240,180),'AIM':(80,240,220),'RELEASE':(50,255,255),'RECOVER':(220,180,250),'CHARGE':(80,240,100),'ACCELERATE':(160,255,180),'WOUNDED':(100,180,255),'STAGGER':(60,160,255),'DEAD':(100,100,220)}
for team,r in records.items():
 states=r['frames'];assert len(states)==N and all(len(f)==16 for f in states)
 phaseCounts=[len({(q['action'],q['phase']) for q in frame}) for frame in states]
 stats[team]=dict(indices=r['indices'],members=[q['id'] for q in states[0]],minDistinctActionPhase=min(phaseCounts),maxDistinctActionPhase=max(phaseCounts),snapshots=[])
 for t in [.12,.6,1.5,1.9,2.2,2.55,2.8]:
  frame=states[round(t*60)];stats[team]['snapshots'].append(dict(time=t,distinctActionPhase=len({(q['action'],q['phase']) for q in frame}),states={a:sum(q['state']==a for q in frame) for a in sorted({q['state'] for q in frame})}))
for f in range(N):
 out=np.full((1300,1920,3),25,np.uint8)
 for col,team in enumerate(['red','blue']):
  r=records[team];im=cv2.imread(str(D/f'behavior-{team}/F{f:04}.png'));assert im is not None
  for rank,q in enumerate(r['frames'][f]):
   x,y=round(q['screenX']),round(q['screenY']);color=colors.get(q['state'],(200,200,200));cv2.circle(im,(x,y),12,(0,0,0),3);cv2.circle(im,(x,y),11,color,2);cv2.putText(im,str(rank+1),(x+12,y-10),0,.5,(0,0,0),3);cv2.putText(im,str(rank+1),(x+12,y-10),0,.5,color,1)
   label=f'{rank+1:02} {q["id"]} {q["state"]:10} {q["action"]}:{q["phase"]:02} v={q["speed"]:4.1f}'
   tx=col*960+(rank%2)*480+12;ty=1036+(rank//2)*30;cv2.putText(out,label,(tx,ty),0,.44,color,1)
   rows.append(dict(team=team,time=f/60,**{k:q[k] for k in ['id','state','action','phase','phaseFloat','speed','x','z','event','hitAge']}))
  out[60:1020,col*960:(col+1)*960]=im;cv2.putText(out,f'{team.upper()} / same squad 16 members / {f/60:.3f}s',(col*960+15,35),0,.7,(240,240,240),1)
 proc.stdin.write(out.tobytes())
proc.stdin.close();assert proc.wait()==0
with (O/'V13-individual-behavior-frames.csv').open('w',newline='',encoding='utf-8-sig') as file:
 w=csv.DictWriter(file,rows[0].keys());w.writeheader();w.writerows(rows)
stats['video']=check(O/'V13-individual-behavior-validation.mp4');stats['scope']='Separate diagnostic camera follows actual selected individuals, same real shot time and same simulation, no point substitutes. Not inserted into main movie.'
(O/'V13-individual-behavior-validation.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
cap=cv2.VideoCapture(str(O/'V13-individual-behavior-validation.mp4'))
for label,t in [('starting',.12),('deploying',1.5),('shooting',2.2),('battle',2.7)]:jpg(O/f'V13-behavior-{label}.jpg',at(cap,t))
cap.release()
