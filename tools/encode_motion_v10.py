from pathlib import Path
import json,subprocess,imageio_ffmpeg
P=Path(__file__).resolve().parents[1];C=json.loads((P/'variants/FINAL/params.json').read_text());N=round(C['duration']*C['fps']);d=P/'variants/FINAL/motion-frames';assert len(list(d.glob('F*.png')))==N
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-framerate',str(C['fps']),'-i',str(d/'F%04d.png'),'-frames:v',str(N),'-an','-c:v','libx264','-crf','17','-preset','fast','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(P/'output/V10-noCombat.mp4')],check=True)
