from pathlib import Path
import sys,json,subprocess,cv2,numpy as np,hashlib,imageio_ffmpeg
P=Path(__file__).resolve().parents[1];v=sys.argv[1];d=P/'variants'/v;C=json.loads((d/'params.json').read_text());N=round(C['duration']*C['fps']);final='--final' in sys.argv;name='PVE-Shot01-U-Archers-v10.mp4' if final else f'V10-Preview-{v}.mp4';out=P/'output'/name
assert len(list((d/'frames').glob('F*.png')))==N
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-framerate',str(C['fps']),'-i',str(d/'frames/F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','medium','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
c=cv2.VideoCapture(str(out));fps=c.get(5);size=[int(c.get(3)),int(c.get(4))];frames=0;black=[];repeated=[];last=None;times=np.array([0,.5,1.3,2.6,3.8,C['duration']-1/C['fps']]);idx={round(t*C['fps']):j for j,t in enumerate(times)};sheet=np.full((2*350,3*250,3),235,np.uint8)
while True:
 ok,im=c.read()
 if not ok:break
 h=hashlib.sha256(im.tobytes()).hexdigest()
 if im.mean()<1:black.append(frames)
 if last==h:repeated.append(frames)
 if frames in idx:
  j=idx[frames];x=j%3*250;y=j//3*350;sheet[y+20:y+340,x+5:x+245]=cv2.resize(im,(240,320));cv2.putText(sheet,f'{v} {frames/C["fps"]:.2f}s',(x+4,y+16),0,.45,(0,0,0),1)
 last=h;frames+=1
c.release();assert frames==N and fps==C['fps'] and size==[C['width'],C['height']] and not black and not repeated
cv2.imencode('.jpg',sheet)[1].tofile(str(P/'output'/f'{"final" if final else v}-encoded-overview.jpg'))
r=dict(path=name,variant=v,frames=frames,fps=fps,size=size,duration=frames/fps,blackFrames=black,adjacentExactRepeats=repeated,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),codec='H264/yuv420p',audio='none',bytes=out.stat().st_size)
(P/'output'/f'{"final" if final else v}-media-validation.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))

