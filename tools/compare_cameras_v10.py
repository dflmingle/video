from pathlib import Path
import json,cv2,numpy as np,subprocess,imageio_ffmpeg
p=Path(__file__).resolve().parents[1];o=p/'output';x=json.loads((o/'overtaking-pair.json').read_text());track=json.loads((o/'overtaking-screen-tracks.json').read_text());meta=[];ff=imageio_ffmpeg.get_ffmpeg_exe()
def enc(path,w,h):return subprocess.Popen([ff,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r','30','-i','pipe:0','-an','-c:v','libx264','-crf','18','-threads','4','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)
def at(c,f):c.set(1,f);ok,im=c.read();assert ok;return im
c=cv2.VideoCapture(str(o/'PVE-Shot01-U-Archers-v10.mp4'));start=round((x['event']['impact']-.35)*30);end=min(round(x['endTime']*30),115);proc=enc(o/'V10-hit-and-overtake.mp4',1080,768);tiles=[]
for f in range(start,end+1):
 im=at(c,f);pts=track[f]['points'];mid=np.mean([[a['x'],a['y']] for a in pts],axis=0);cw=min(im.shape[1],max(420,int(abs(pts[0]['x']-pts[1]['x'])+120)));ch=min(im.shape[0],max(460,int(abs(pts[0]['y']-pts[1]['y'])+120)));left=int(np.clip(mid[0]-cw/2,0,im.shape[1]-cw));top=int(np.clip(mid[1]-ch/2,0,im.shape[0]-ch));tile=cv2.resize(im[top:top+ch,left:left+cw],(540,690));can=np.full((768,1080,3),25,np.uint8);can[78:,:540]=cv2.resize(im,(540,690));can[78:,540:]=tile
 for j,z in enumerate(pts):
  color=(40,210,255) if j==0 else (75,240,90);q=(540+round((z['x']-left)*540/cw),78+round((z['y']-top)*690/ch));cv2.circle(can,q,13,color,2);cv2.putText(can,f"{z['id']} speed {z['speed']:.2f}",(548,23+j*22),0,.52,color,1)
 cv2.putText(can,f"V10 {f/30:.3f}s | impact {x['event']['impact']:.3f}s",(8,28),0,.58,(240,240,240),1);cv2.putText(can,'Actual encoded MP4 / victim yellow, unhit green',(8,55),0,.50,(240,240,240),1);proc.stdin.write(can.tobytes())
 if f in [start,round(x['event']['impact']*30),round((x['event']['impact']+.3)*30),end]:tiles.append(can)
proc.stdin.close();assert proc.wait()==0;cv2.imwrite(str(o/'hit-overtake-continuous.jpg'),np.vstack([np.hstack(tiles[:2]),np.hstack(tiles[2:])]))
