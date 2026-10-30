from pathlib import Path
import cv2,json,numpy as np,csv,hashlib,math
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];O=P/'output';S=json.loads((P/'variants/FINAL/simulation.json').read_text());C=S['config'];cap=cv2.VideoCapture(str(O/'PVE-Shot01-U-Archers-v10.mp4'));n=round(C['duration']*C['fps'])
def frame(t):
 cap.set(1,min(n-1,round(t*C['fps'])));ok,im=cap.read();assert ok;return im
for page in range(math.ceil(C['duration'])):
 times=[page+j*.1 for j in range(10) if page+j*.1<=C['duration']-1/C['fps']]
 if page==math.ceil(C['duration'])-1:times.append(C['duration']-1/C['fps'])
 sheet=np.full((640,1200,3),235,np.uint8)
 for j,t in enumerate(times):
  x=j%5*240;y=j//5*320;sheet[y+20:y+320,x:x+240]=cv2.resize(frame(t),(240,300));cv2.putText(sheet,f'V10 {t:.3f}s',(x+4,y+16),0,.4,(0,0,0),1)
 cv2.imencode('.jpg',sheet)[1].tofile(str(O/f'final-timeline-{page:02}.jpg'))
e=json.loads((O/'final-event-evidence.json').read_text())
def crop(im,p,w,h):
 x=max(0,min(im.shape[1]-w,round(p[0]-w/2)));y=max(0,min(im.shape[0]-h,round(p[1]-h/2)));return im[y:y+h,x:x+w]
out=np.full((560,1920,3),235,np.uint8)
for j,s in enumerate(e['samples']):
 im=frame(s['time']);x=j*240
 for row,key in enumerate(['shooter','target']):
  visible=0<=s[key][0]<im.shape[1] and 0<=s[key][1]<im.shape[0]
  if visible:out[row*280+30:(row+1)*280,x:x+240]=cv2.resize(crop(im,s[key],210,220),(240,250))
  else:cv2.putText(out,'OFFSCREEN: see Camera A',(x+3,row*280+150),0,.36,(30,30,30),1)
  cv2.putText(out,f'{s["time"]:.3f}s {key}',(x+3,row*280+20),0,.38,(0,0,0),1)
cv2.imencode('.jpg',out)[1].tofile(str(O/'final-encoded-hit-chain.jpg'))
out=np.full((600,1120,3),235,np.uint8)
for j,s in enumerate(e['runSamples']):
 im=crop(frame(s['time']),s['screen'],200,190);x=j%4*280;y=j//4*300;out[y+30:y+300,x:x+280]=cv2.resize(im,(280,270));cv2.putText(out,f'Run {s["time"]:.3f}s',(x+4,y+21),0,.45,(0,0,0),1)
cv2.imencode('.jpg',out)[1].tofile(str(O/'final-encoded-run-detail.jpg'));cap.release()
# Original PDF diagram and actual encoded first frame.
cap=cv2.VideoCapture(str(O/'PVE-Shot01-U-Archers-v10.mp4'));ok,im=cap.read();cap.release();assert ok
sheet=Image.new('RGB',(1240,1040),'#eeeeea');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
ref=Image.open(P/'docs/formation-page-7.png');ref.thumbnail((440,880));shot=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));shot.thumbnail((690,920));sheet.paste(ref,(15,70));sheet.paste(shot,(510,70));draw.text((20,20),'策划原图 / V10 实际编码第一帧',font=font,fill='#222222');draw.text((20,980),'保留三军前后归属、各军3×3小队及蓝方七队U型；组内合理差异按最新指令执行。',font=font,fill='#222222');sheet.save(O/'PDF-vs-V10-first-frame.jpg',quality=92)
# Individual source/trajectory/formation/deployment records.
a=np.load(P/'variants/FINAL/trajectories.npy');gait=np.load(P/'variants/FINAL/gait-distance.npy');dt=1/C['simulationFps'];nb=S['blueCount']
with (O/'member-trajectories.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['time','id','model','army','squadRow','squadCol','x','z','cumulativePath','life'])
 for k in range(0,len(a),6):
  for i,u in enumerate(S['units']):w.writerow([round(k*dt,3),u['id'],u['model'],u.get('army','blue'),u.get('squadRow',u.get('group')),u.get('squadCol'),*a[k,i],gait[k,i],'dead' if u.get('deathTime') is not None and u['deathTime']<=k*dt else 'alive'])
endpoints=[dict(id=u['id'],group=u['group'],start=u['start'],end=a[-1,i].tolist(),arrival=u['delay']+C['blueMoveSeconds']) for i,u in enumerate(S['units'][:nb])];(O/'blue-deployment-endpoints.json').write_text(json.dumps(endpoints,indent=2))
manifest=json.loads((P/'assets/runtime/manifest.json').read_text());audit=json.loads((P/'variants/FINAL/asset-render-audit.json').read_text());sources={}
for key,m in manifest.items():
 model=P/'assets/runtime'/f'{key}.fbx';texture=P/'assets/runtime'/f'{key}.png';assert hashlib.sha256(model.read_bytes()).hexdigest()==m['sourceSHA256'];assert hashlib.sha256(texture.read_bytes()).hexdigest()==m['textureSHA256'];sources[key]=m
(O/'ASSET-PROVENANCE.json').write_text(json.dumps(dict(inputs=json.loads((P/'docs/input-provenance.json').read_text()),models=sources,browserLoads=audit['requests'],runtimeModels=audit['models'],referenceTracing=False,environment='Original package ArenaScene/texture adapted to enlarged flat cinematic ground; original package trees'),ensure_ascii=False,indent=2),encoding='utf8')
print('Final encoded continuous evidence, source chain and trajectories saved')
