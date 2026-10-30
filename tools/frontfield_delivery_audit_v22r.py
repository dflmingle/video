from pathlib import Path
import json,csv,hashlib,cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parents[1];D=P/'docs/v22r-frontfield';O=P/'output/v22r-frontfield'
S=json.loads((P/'variants/V22R-frontfield/simulation.json').read_text(encoding='utf8'));pos=np.load(P/'variants/V22R-frontfield/trajectories.npy');vel=np.load(P/'variants/V22R-frontfield/velocities.npy');nb=S['blueCount'];n=len(S['units']);deaths=np.array([u.get('deathTime') if u.get('deathTime') is not None else 1e6 for u in S['units']])
forward=np.array([0.,-98.,-60.]);forward/=np.linalg.norm(forward);right=np.array([1.,0.,0.]);up=np.cross(right,forward);xyz=np.zeros((len(pos),n,3));xyz[:,:,0]=pos[:,:,0];xyz[:,:,2]=pos[:,:,1];rel=xyz-[0.,98.,65.];depth=rel@forward;tan=np.tan(np.deg2rad(21));px=(rel@right)/(depth*tan*2/3);py=(rel@up)/(depth*tan);visible=(np.abs(px)<1)&(np.abs(py)<1)
rows=[]
for f in range(0,len(pos),6):
 t=f/60;alive=deaths>t;speed=np.linalg.norm(vel[f],axis=1)
 rows.append(dict(time=t,redMoving=int(((speed[nb:]>.2)&alive[nb:]).sum()),blueMoving=int(((speed[:nb]>.2)&alive[:nb]).sum()),redMedianLivingSpeed=float(np.median(speed[nb:][alive[nb:]])) if alive[nb:].any() else 0.,redVisible=int(visible[f,nb:].sum()),blueVisible=int(visible[f,:nb].sum()),releases=sum(t<=e['release']<t+.1 for e in S['events']),inFlight=sum(e['release']<=t<e['impact'] for e in S['events']),arrowHits=sum(t<=e['impact']<t+.1 and bool(e.get('damage',0)) for e in S['events']),meleeHits=sum(t<=e['time']<t+.1 and e['damage']>0 for e in S['meleeEvents'])))
with (D/'timeline-every-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
firstRed=next(f/60 for f in range(1,len(pos)) if np.max(np.linalg.norm(pos[f,nb:]-pos[f-1,nb:],axis=1))>1e-4);firstBlue=next(f/60 for f in range(1,len(pos)) if np.max(np.linalg.norm(pos[f,:nb]-pos[f-1,:nb],axis=1))>1e-4)
flashEvidence={}
for folder in ['evidence','flash-only-evidence']:
 evidence=json.loads((O/folder/'evidence.json').read_text(encoding='utf8'));source=P/'variants'/evidence['variant'];sim=json.loads((source/'simulation.json').read_text(encoding='utf8'))
 impacts={u['id']:[] for u in sim['units']}
 for e in sim['events']:
  if e.get('damage',0):impacts[sim['units'][e['target']]['id']].append(e['impact'])
 for e in sim['meleeEvents']:
  if e['damage']:impacts[sim['units'][e['target']]['id']].append(e['time'])
 invalid=[]
 for row in evidence['rows']:
  for uid in row['activeFlashIds']:
   if not any(-1e-5<=row['time']-t<.09001 for t in impacts[uid]):invalid.append([row['time'],uid])
 flashEvidence[folder]=dict(onlyActualDamagedMembers=not invalid,invalid=invalid,peak=max(r['hitFlash'] for r in evidence['rows']),preHitZero=all(r['hitFlash']==0 for r in evidence['rows'] if r['frameOffset']==-1),endedAt150ms=all(r['hitFlash']==0 for r in evidence['rows'] if r['frameOffset']==9))
# Final encoded flash-only damage sheets preserve the accepted timing.
evidence=json.loads((O/'flash-only-evidence/evidence.json').read_text(encoding='utf8'));cap=cv2.VideoCapture(str(O/'C1-preserved-battle-hitflash-720x1080-60fps.mp4'));font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
for kind in ['arrow','melee']:
 rs=[r for r in evidence['rows'] if r['event']['type']==kind];im=Image.new('RGB',(1280,216),'#222629');d=ImageDraw.Draw(im)
 for i,r in enumerate(rs):
  frame=round(r['time']*60);cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,b=cap.read();assert ok;a=Image.fromarray(cv2.cvtColor(b,cv2.COLOR_BGR2RGB));x,y=r['screen'];im.paste(a.crop((round(x)-30,round(y)-36,round(x)+30,round(y)+24)).resize((160,160)),(i*160,48));d.text((i*160+3,4),f"F{frame} {r['time']:.3f}s",font=font,fill='white');d.text((i*160+3,25),f"flash {r['hitFlash']:.3f}",font=font,fill='white')
 im.save(O/'encoded-hit-evidence'/f'preserved-{kind}-sequence.jpg',quality=95)
cap.release()
camera={}
with (D/'camera-every-frame.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['version','frame','time','position','quaternion','projection','zoom'])
 for folder in ['layout-preview','flash-only']:
  a=json.loads((O/folder/'audit.json').read_text(encoding='utf8'));camera[folder]=dict(frames=len(a['frames']),constant=a['constant'],errors=a['errors'])
  for i,r in enumerate(a['frames']):w.writerow([folder,i,r['time'],json.dumps(r['cameraPosition']),json.dumps(r['cameraQuaternion']),json.dumps(r['cameraProjection']),r['cameraZoom']])
report=dict(firstRedMovement=firstRed,firstBlueMovement=firstBlue,openingRootVisible=int(visible[0].sum()),minimumAllFrameRootVisible=int(visible.sum(1).min()),flash=flashEvidence,camera=camera,comparisonIsNormalSpeed=True,formalRender=False,unresolved='Compact layout materially shortens archery window; retained accepted battle plus flash is the conservative usable result',sourceHashes={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'src/main-v22.js',P/'src/assets-v22.js',P/'src/castle-approved-v22r.js',P/'public/native-scenes/CastleExterior-scene/manifest.json']})
(D/'delivery-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='sourceHashes'},indent=2))
assert all(v['onlyActualDamagedMembers'] and v['preHitZero'] and v['endedAt150ms'] for v in flashEvidence.values())
