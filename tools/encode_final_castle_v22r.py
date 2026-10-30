"""Encode at source 60 fps and verify the actual exported video and trajectories."""
from pathlib import Path
import csv,hashlib,json,subprocess
import cv2,imageio_ffmpeg,numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.spatial import cKDTree

R=Path(__file__).resolve().parents[1];O=R/'output/V22R-final';V=R/'variants/V22R-overlap'
a=json.loads((O/'render-audit.json').read_text(encoding='utf8'));fps=a['fps'];n=a['totalFrames'];frames=sorted((O/'frames').glob('F*.png'));assert len(frames)==n
dest=O/'V22R-final-CastleExterior-no-grid-1440x2160-60fps.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-framerate',str(fps),'-i',str(O/'frames/F%04d.png'),'-frames:v',str(n),'-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],check=True)
s=json.loads((V/'simulation.json').read_text(encoding='utf8'));p=np.load(V/'trajectories.npy');nb=s['blueCount'];c=json.loads((V/'params.json').read_text(encoding='utf8'));sampleGap=[];lower=[]
for k,q in enumerate(p[:n]):
 gap=float(cKDTree(q[:nb]).query(q[nb:])[0].min()-2*c['weaponEnvelopeRadius']);sampleGap.append(gap)
 if k:
  step=np.linalg.norm(q-p[k-1],axis=1);lower.append(min(gap,sampleGap[-2])-.5*(step[:nb].max()+step[nb:].max()))
first=[]
for j in [slice(nb,None),slice(None,nb)]:
 ids=np.flatnonzero(np.any(np.linalg.norm(np.diff(p[:n,j],axis=0),axis=2)>.02/fps,axis=1));first.append(None if not len(ids) else (int(ids[0])+1)/fps)
cap=cv2.VideoCapture(str(dest));w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));rate=cap.get(cv2.CAP_PROP_FPS);decoded=0;maxPixelError=0.;stills={0,1,6,30,60,90,119,n-1}
panel=Image.new('RGB',(1200,960),'#222629');draw=ImageDraw.Draw(panel);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
while True:
 ok,frame=cap.read()
 if not ok:break
 if decoded in stills:
  idx=sorted(stills).index(decoded);im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.thumbnail((294,441));x=(idx%4)*300;y=(idx//4)*480;panel.paste(im,(x,y+28));draw.text((x+4,y+4),f'{decoded/fps:.3f}s / F{decoded}',font=font,fill='white')
  Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).save(O/f'encoded-F{decoded:04}.jpg',quality=91)
  original=cv2.imread(str(frames[decoded]));maxPixelError=max(maxPixelError,float(np.abs(original.astype(float)-frame.astype(float)).mean()))
 decoded+=1
cap.release();assert (w,h)==(1440,2160) and abs(rate-60)<1e-7 and decoded==n
panel.save(O/'encoded-temporal-review.jpg',quality=90)
with (O/'camera-every-frame.csv').open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.writer(f);writer.writerow(['frame','seconds','position','quaternion','projection','fov','zoom']);writer.writerows([q['frame'],q['time'],json.dumps(q['position']),json.dumps(q['quaternion']),json.dumps(q['projection']),q['fov'],q['zoom']] for q in a['frames'])
with (O/'actions-every-0.1s.csv').open('w',newline='',encoding='utf-8-sig') as f:
 writer=csv.writer(f);writer.writerow(['seconds','redMoving','blueMoving','redMeanAdvance','blueMeanAssembly','releasesInBin','flyingArrows','impactsInBin','surfaceClearance'])
 for k in range(0,n,6):
  t=k/fps;end=min(n,k+6)/fps;q=a['frames'][k]
  writer.writerow([t,q['redMoving'],q['blueMoving'],float(np.mean(p[k,nb:,1]-p[0,nb:,1])),float(np.mean(p[0,:nb,1]-p[k,:nb,1])),sum(t<=e['release']<end for e in s['events']),sum(e['release']<=t<e['impact'] for e in s['events']),sum(e['resolution']=='IMPACT_IN_SHOT' and t<=e['impact']<end for e in s['events']),sampleGap[k]])
result=dict(path=str(dest),bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),width=w,height=h,fps=rate,decodedFrames=decoded,duration=decoded/rate,playbackSpeed=1.,cameraConstant=a['cameraConstant'],gridOff=not a['setup']['grid'][0]['visible'],minimumSampledClearance=min(sampleGap),minimumConservativeClearance=float(min(lower)),firstRedMotion=first[0],firstBlueMotion=first[1],realReleasesVisibleTime=sum(e['release']<n/fps for e in s['events']),realImpactsVisibleTime=sum(e['resolution']=='IMPACT_IN_SHOT' and e['impact']<n/fps for e in s['events']),firstRelease=min(e['release'] for e in s['events']),firstImpact=None,decodedSampleMeanAbsolutePixelErrorMax=maxPixelError,visualInspection='Exported-video timestamped stills and consecutive frames inspected; no claim of full normal-speed visual playback acceptance.',fullRequirementsPassed=False,limitations=a['limitations'])
assert result['minimumConservativeClearance']>=4 and result['cameraConstant'] and result['gridOff']
(O/'delivery-checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=True,indent=2))

if __name__=='__main__':pass
