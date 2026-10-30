import json, subprocess
from pathlib import Path
import cv2
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parents[1];out=R/'output/v22r-opening';ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
for variant in ['V22-C','V22R-overlap']:
    frames=sorted((out/variant).glob('F*.png'));assert len(frames)==90
    label=Image.new('RGBA',(1440,90),(0,0,0,220));ld=ImageDraw.Draw(label);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',29)
    ld.text((18,10),f'{variant} | OPENING MOTION DIAGNOSTIC | 60 fps / 1x',font=font,fill='white');ld.text((18,48),'Native NewScene UNCONFIRMED / scene mismatch / not final acceptance',font=font,fill='#ffd182');label.save(out/f'{variant}-label.png')
    subprocess.run([ffmpeg,'-y','-loglevel','error','-framerate','60','-i',str(out/variant/'F%04d.png'),'-i',str(out/f'{variant}-label.png'),'-filter_complex','[0:v][1:v]overlay=0:0[v]','-map','[v]','-frames:v','90','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(out/f'{variant}-opening-1.5s.mp4')],check=True)
subprocess.run([ffmpeg,'-y','-loglevel','error','-i',str(out/'V22-C-opening-1.5s.mp4'),'-i',str(out/'V22R-overlap-opening-1.5s.mp4'),'-filter_complex','[0:v]scale=640:960[a];[1:v]scale=640:960[b];[a][b]hstack=inputs=2[v]','-map','[v]','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'V22-V22R-opening-same-time-60fps.mp4')],check=True)
probes=[]
for p in out.glob('*.mp4'):
    c=cv2.VideoCapture(str(p));n=0
    while True:
        ok,frame=c.read()
        if not ok:break
        n+=1
    probes.append(dict(path=str(p),decodedFrames=n,fps=c.get(cv2.CAP_PROP_FPS),width=c.get(cv2.CAP_PROP_FRAME_WIDTH),height=c.get(cv2.CAP_PROP_FRAME_HEIGHT),normalSpeed=True,visualWholeVideoWatched=False));c.release();assert n==90
(out/'encode-check.json').write_text(json.dumps(probes,indent=2),encoding='utf8')
panel=Image.new('RGB',(1080,1120),'#191919');draw=ImageDraw.Draw(panel)
for row,f in enumerate([0,6,30,60]):
    for col,var in enumerate(['V22-C','V22R-overlap']):
        im=Image.open(out/var/f'F{f:04d}.png');im.thumbnail((360,250));panel.paste(im,(col*540,30+row*275));draw.text((col*540+175,35+row*275),f'{var}\nt={f/60:.3f}s\nFixed camera\nScene UNCONFIRMED',fill='white')
panel.save(out/'opening-temporal.jpg',quality=88)
print(json.dumps(probes,indent=2))
