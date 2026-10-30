from pathlib import Path
import subprocess,json,cv2,numpy as np,imageio_ffmpeg,sys,hashlib
p=Path(__file__).resolve().parents[1];d=p/'variants/FINAL';c=json.loads((d/'params.json').read_text());mode=sys.argv[1];frames=d/('A-frames' if mode=='A' else 'frames');out=p/'output'/f'V10-Camera-{mode}-Preview.mp4'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-framerate',str(c['fps']),'-i',str(frames/'F%04d.png'),'-frames:v',str(round(c['fps']*c['duration'])),'-an','-c:v','libx264','-crf','17','-preset','fast','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
cap=cv2.VideoCapture(str(out));ims=[]
while True:
 ok,im=cap.read()
 if not ok:break
 ims.append(im)
assert len(ims)==round(c['duration']*c['fps'])
for k in range((len(ims)+15)//16):
 sheet=np.full((1360,960,3),235,np.uint8)
 for j,im in enumerate(ims[k*16:k*16+16]):
  x=j%4*240;y=j//4*340;sheet[y+20:y+340,x:x+240]=cv2.resize(im,(240,320));cv2.putText(sheet,f'{mode} F{k*16+j:03} {(k*16+j)/30:.3f}s',(x+3,y+16),0,.42,(0,0,0),1)
 cv2.imwrite(str(p/'output'/f'preview-{mode}-frames-{k:02}.jpg'),sheet)
(p/'output'/f'preview-{mode}-media.json').write_text(json.dumps(dict(path=out.name,frames=len(ims),fps=cap.get(5),width=cap.get(3),height=cap.get(4),sha256=hashlib.sha256(out.read_bytes()).hexdigest()),indent=2));print(out.name,len(ims))
