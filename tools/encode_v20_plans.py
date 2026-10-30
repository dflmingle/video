from pathlib import Path
import subprocess, json, cv2, imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output'; OUT.mkdir(exist_ok=True)
clips=[]
for plan in ['A','B','C']:
    frames=ROOT/'output'/'captures'/f'V20-{plan}-B'/'frames'
    files=sorted(frames.glob('F*.png')); assert files, frames
    path=OUT/f'V20-plan-{plan}-camera-B.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-framerate','60','-i',str(frames/'F%04d.png'),'-frames:v',str(len(files)),'-an','-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
    cap=cv2.VideoCapture(str(path)); n=0; black=0; last=None; repeats=0
    while True:
        ok,im=cap.read()
        if not ok: break
        n+=1; black += int(float(im.mean()) < 1); h=hash(im.tobytes())
        if h==last: repeats+=1
        last=h
    cap.release(); assert n==len(files) and black==0
    clips.append(path)
montage=OUT/'V20-plans-A-B-C-same-time.mp4'; ff=imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff,'-hide_banner','-loglevel','error','-y','-i',str(clips[0]),'-i',str(clips[1]),'-i',str(clips[2]),'-filter_complex','[0:v][1:v][2:v]hstack=inputs=3:shortest=1,format=yuv420p[v]','-map','[v]','-an','-c:v','libx264','-crf','18','-preset','medium','-movflags','+faststart',str(montage)],check=True)
print(json.dumps({'clips':[str(p) for p in clips],'montage':str(montage)}))
