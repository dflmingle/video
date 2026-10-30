from pathlib import Path
import json,hashlib,subprocess,re
import imageio_ffmpeg
P=Path(__file__).resolve().parents[1];O=P/'output';D=P/'variants/FINAL'
M=json.loads((O/'V13-media-validation.json').read_text());B=json.loads((O/'V13-individual-behavior-validation.json').read_text());M.append(B['video'])
for m in M:
 path=O/m['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==m['sha256']
 s=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(path)],capture_output=True,text=True).stderr
 assert 'Video: h264' in s and 'yuv420p' in s
 m['codec']='h264';m['pixelFormat']='yuv420p';m['audioPresent']='Audio:' in s
(O/'V13-media-validation.json').write_text(json.dumps(M,indent=2))
engineering=json.loads((O/'V13-engineering-validation.json').read_text());engineering['visualStatus']='PARTIAL_ENCODED_FRAMES_REVIEWED';engineering['reviewScope']='10 full-shot samples, 3 x 18 consecutive-frame windows, targeted hit/runner continuity and 4 encoded local-behavior samples; no claim of normal-speed full playback.'
(O/'V13-engineering-validation.json').write_text(json.dumps(engineering,indent=2))
for p,h in json.loads((O/'protected-v12.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
F=['PVE-Shot01-U-Archers-v13.mp4','V13-individual-behavior-validation.mp4','V12-V13-realtime-comparison.mp4','V13-REVIEW.md','V13-blue-individual-schedule.json','V13-individual-behavior-frames.csv','V13-arrow-events.csv','V13-member-tracks.csv','V13-hit-fallbehind-continuous.jpg','V13-member-motion-and-release.png']
(O/'DELIVERY-V13.json').write_text(json.dumps(dict(version='V13',files=[dict(path=str(O/f),bytes=(O/f).stat().st_size,sha256=hashlib.sha256((O/f).read_bytes()).hexdigest()) for f in F],engineeringStatus='PASS',visualStatus='PARTIAL',viewer='http://127.0.0.1:5253/camera.html?variant=FINAL',entry=str(P/'RENDER-V13.md')),indent=2))
print(json.dumps(dict(media=M,protectedV12=True,visual='PARTIAL'),indent=2))
