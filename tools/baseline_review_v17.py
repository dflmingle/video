from pathlib import Path
import cv2,numpy as np
from media_v11 import at,fit,jpg
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V16/output'
names=['PVE-Shot01-U-Archers-v16.mp4','V15-V16-same-time.mp4','V16-camera-fixed-vs-follow.mp4','V16-world-speed-1x-125x-150x.mp4','V16-1x-longer-battle.mp4']
for time in [.7,1.8]:
 out=np.full((2*500,3*640,3),235,np.uint8)
 for j,name in enumerate(names):
  cap=cv2.VideoCapture(str(B/name));im=at(cap,time);cap.release();x=j%3*640;y=j//3*500;out[y+50:y+500,x:x+640]=fit(im,640,450)
  cv2.putText(out,name,(x+7,y+22),0,.38,(0,0,0),1);cv2.putText(out,f'{time:.2f}s encoded frame',(x+7,y+43),0,.45,(0,0,0),1)
 jpg(P/f'output/V16-input-videos-{time}.jpg',out)
