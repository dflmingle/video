"""Encode captured actual frames at their recorded real-time FPS; decode audit.

Usage: python tools/encode_v22.py frames-dir output.mp4 --fps 30
"""
import argparse, json, subprocess
from pathlib import Path
import cv2
import imageio_ffmpeg

def encode(frames, output, fps):
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner','-loglevel','error','-y',
         '-framerate',str(fps),'-i',str(frames/'F%04d.png'),'-c:v','libx264',
         '-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    subprocess.run(cmd,check=True)
    cap=cv2.VideoCapture(str(output)); count=0; samples=[]
    total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); actual_fps=cap.get(cv2.CAP_PROP_FPS)
    while True:
        ok,frame=cap.read()
        if not ok: break
        if count in [0,total//2,total-1]:
            p=output.with_name(output.stem+f'-decoded-{count:04}.png');cv2.imwrite(str(p),frame);samples.append(str(p))
        count+=1
    cap.release()
    assert count==total and count>0
    result=dict(path=str(output),frames=count,width=width,height=height,fps=actual_fps,
                duration=count/actual_fps,allFramesDecoded=True,decodedSamples=samples,
                normalSpeedWholeVideoWatched=False)
    output.with_suffix('.decode.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('frames',type=Path);p.add_argument('output',type=Path);p.add_argument('--fps',type=float,default=60);a=p.parse_args();encode(a.frames,a.output,a.fps)
