"""Real-time comparison, no freeze extension or source time warp.

python tools/compare_v22.py --input a.mp4 --input b.mp4 --label A --label B --out out.mp4
"""
import argparse,json,subprocess
from pathlib import Path
import cv2,numpy as np,imageio_ffmpeg

p=argparse.ArgumentParser();p.add_argument('--input',type=Path,action='append',required=True);p.add_argument('--label',action='append',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--fps',type=int,default=30);a=p.parse_args()
assert len(a.input)==len(a.label)
caps=[cv2.VideoCapture(str(x)) for x in a.input];infos=[(int(c.get(cv2.CAP_PROP_FRAME_COUNT)),c.get(cv2.CAP_PROP_FPS)) for c in caps]
assert all(n>0 and fps>0 for n,fps in infos)
duration=max(n/fps for n,fps in infos);w,h=600,900;a.out.parent.mkdir(parents=True,exist_ok=True)
cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w*len(caps)}x{h+60}','-r',str(a.fps),'-i','-','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(a.out)]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
try:
 for k in range(int(np.ceil(duration*a.fps))):
    t=k/a.fps;panels=[]
    for c,(n,fps),label in zip(caps,infos,a.label):
        frame=np.full((h+60,w,3),24,np.uint8)
        if t<n/fps:
            c.set(cv2.CAP_PROP_POS_FRAMES,min(n-1,round(t*fps)));ok,im=c.read();assert ok
            scale=min(w/im.shape[1],h/im.shape[0]);im=cv2.resize(im,(round(im.shape[1]*scale),round(im.shape[0]*scale)),interpolation=cv2.INTER_AREA)
            x=(w-im.shape[1])//2;y=60+(h-im.shape[0])//2;frame[y:y+im.shape[0],x:x+im.shape[1]]=im
        else:cv2.putText(frame,'ENDED AT SAFE CUT',(40,h//2),cv2.FONT_HERSHEY_SIMPLEX,.8,(230,230,230),2)
        cv2.putText(frame,f'{label} | t={t:.2f}s',(12,35),cv2.FONT_HERSHEY_SIMPLEX,.68,(255,255,255),2);panels.append(frame)
    proc.stdin.write(np.concatenate(panels,axis=1).tobytes())
finally:
 proc.stdin.close()
 for c in caps:c.release()
assert proc.wait()==0
a.out.with_suffix('.sources.json').write_text(json.dumps(dict(inputs=[str(x) for x in a.input],labels=a.label,realTime=True,fps=a.fps,endedPanels='blank, labelled ENDED AT SAFE CUT'),indent=2),encoding='utf8')
print(a.out)
