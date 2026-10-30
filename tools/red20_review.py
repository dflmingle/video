from pathlib import Path
import json,hashlib,numpy as np,cv2
from media_v11 import at,fit,jpg
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';R=json.loads((D/'red20-states.json').read_text());F=R['frames'];assert len(F)==180 and all(len(f)==20 for f in F)
for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h
S=json.loads((D/'simulation.json').read_text());nb=S['blueCount'];K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');details=[]
for n in range(20):
 rows=[f[n] for f in F];i=rows[0]['index'];assert all(r['index']==i for r in rows)
 for k,r in enumerate(rows):
  assert abs(r['stride']-K[k,i-nb,3])<1e-4 and abs(r['gaitCycles']-Y[k,i])<1e-4
 during=rows[36:130]
 details.append(dict(id=rows[0]['id'],speedStd=float(np.std([r['speed'] for r in during])),speedRange=[min(r['speed'] for r in during),max(r['speed'] for r in during)],cadenceRange=[min(r['cadence'] for r in during),max(r['cadence'] for r in during)],strideRange=[min(r['stride'] for r in during),max(r['stride'] for r in during)],postureRange=[min(r['posture'] for r in during),max(r['posture'] for r in during)],armSwingRange=[min(r['armSwing'] for r in during),max(r['armSwing'] for r in during)],states=sorted({r['state'] for r in rows})))
 assert details[-1]['speedStd']>.15 and np.ptp(details[-1]['cadenceRange'])>.04
distinct=[len({(r['action'],r['phase']) for r in f}) for f in F]
out=dict(status='PASS',realDuration=3.,trackedMembers=20,samePlatoon=R['platoon'],everyMemberSpeedVariesAfterStartup=True,dynamicControlInputsMatch=True,distinctPoseRange=[min(distinct),max(distinct)],details=details,method='Independent deterministic exertion rhythm plus occupancy and injury response; no frame-wise random velocity/position, no formation-center path or slot spring. This is authored deterministic motion, not autonomous battle AI.')
(O/'V14-red20-behavior-validation.json').write_text(json.dumps(out,indent=2))
cap=cv2.VideoCapture(str(O/'V14-red20-continuous-behavior.mp4'))
# Source MP4 is 60fps. Sheets sample exact successive frames in each window.
for p,start in enumerate([48,96,153]):
 sheet=np.full((3*400,4*530,3),235,np.uint8)
 for j in range(12):
  f=start+j;im=at(cap,f/60);x=j%4*530;y=j//4*400;sheet[y+28:y+400,x:x+530]=fit(im,530,372);cv2.putText(sheet,f'{f/60:.3f}s',(x+7,y+21),0,.5,(0,0,0),1)
 jpg(O/f'V14-red20-consecutive-{p}.jpg',sheet)
cap.release();print(json.dumps(dict(status='PASS',speedStdRange=[min(d['speedStd'] for d in details),max(d['speedStd'] for d in details)],poseRange=out['distinctPoseRange']),indent=2))
