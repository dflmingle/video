from pathlib import Path
import sys,json,subprocess,cv2,numpy as np,hashlib
from media_v11 import ff,check,encoder,at,fit,jpg
P=Path(__file__).resolve().parents[1];O=P/'output';tag=sys.argv[1];D=O/'captures'/tag;R=json.loads((D/'render-checks.json').read_text());C=json.loads((P/f'variants/{R["variant"]}/params.json').read_text());N=len(R['states']);fps=R['fps'];path=O/f'V17-{tag}.mp4'
assert not R['errors'] and all(s['identical'] for s in R['seeks'])
for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h,p
subprocess.run([ff,'-y','-hide_banner','-loglevel','error','-framerate',str(fps),'-i',str(D/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
meta=check(path);assert meta['frames']==N and not meta['adjacentExactRepeats'];(O/f'{tag}-media.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2));cap=cv2.VideoCapture(str(path))
for label,t in [('initial',0),('charge',min(1,C['duration']-.05)),('first-arrows',min(1.95,C['duration']-.05)),('end',(N-1)/fps)]:jpg(O/f'{tag}-{label}.jpg',at(cap,t))
sheet=np.full((1200,2000,3),235,np.uint8)
for j,t in enumerate(np.linspace(0,(N-1)/fps,10)):
 x=j%5*400;y=j//5*600;sheet[y+30:y+600,x:x+400]=fit(at(cap,float(t)),400,570);cv2.putText(sheet,f'{t:.3f}s',(x+8,y+21),0,.55,(0,0,0),1)
jpg(O/f'{tag}-overview.jpg',sheet)
for page,start in enumerate([max(0,round(fps*.8)),max(0,N-15)]):
 sheet=np.full((1200,2120,3),235,np.uint8)
 for j in range(12):
  f=min(N-1,start+j);x=j%4*530;y=j//4*400;sheet[y+28:y+400,x:x+530]=fit(at(cap,f/fps),530,372);cv2.putText(sheet,f'{f/fps:.3f}s',(x+8,y+20),0,.5,(0,0,0),1)
 jpg(O/f'{tag}-consecutive-{page}.jpg',sheet)
cap.release()
