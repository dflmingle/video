"""Portable I/O and media helpers. No project paths or install side effects."""
import hashlib
import json
from pathlib import Path
import subprocess
import cv2
import numpy as np

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def fresh_dir(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=False)
    return p

def imread(path):
    im = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if im is None:
        raise ValueError(f'Cannot decode image: {path}')
    return im

def imwrite(path, im):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        raise FileExistsError(p)
    ok, buf = cv2.imencode(p.suffix, im)
    if not ok:
        raise ValueError(f'Cannot encode image: {path}')
    buf.tofile(p)

def capture(path):
    c = cv2.VideoCapture(str(path))
    if not c.isOpened():
        raise ValueError(f'Cannot open video: {path}')
    return c

def frame(c, n):
    c.set(cv2.CAP_PROP_POS_FRAMES, int(n))
    ok, im = c.read()
    if not ok:
        raise ValueError(f'Cannot decode frame {n}')
    return im

def probe(path, decode=False):
    c = capture(path)
    fps = c.get(cv2.CAP_PROP_FPS)
    count = int(c.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or count <= 0:
        c.release()
        raise ValueError('Invalid media time base')
    d = dict(path=str(Path(path).resolve()), sha256=sha(path), fps=fps,
             frames_reported=count, width=int(c.get(3)), height=int(c.get(4)),
             duration_cfr_estimate=count/fps, time_basis='CFR_ASSUMED_VERIFY_PTS',
             audio_status='NOT_ANALYZED', pts_check='NOT_RUN')
    if decode:
        n, previous_pts, deltas = 0, None, []
        while True:
            ok, _ = c.read()
            if not ok:
                break
            pts = c.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if previous_pts is not None:
                deltas.append(pts - previous_pts)
            previous_pts = pts
            n += 1
        d['decoded_frames'] = n
        d['decode_status'] = 'PASS' if n == count else 'FAIL'
        varying = bool(deltas and np.max(np.abs(np.array(deltas) - 1/fps)) > .002)
        d['pts_check'] = 'VARIABLE_OR_UNAVAILABLE' if varying else 'CFR_CONSISTENT_OPENCV'
        d['time_basis'] = 'UNSUPPORTED_VFR_OR_BAD_PTS' if varying else 'CFR_VERIFIED_OPENCV'
    c.release()
    return d

def panel(a, b, label, width=960):
    if a.shape != b.shape:
        raise ValueError('Panel requires explicitly aligned equal image sizes')
    both = np.hstack([a, b])
    s = min(1., width/both.shape[1])
    both = cv2.resize(both, None, fx=s, fy=s)
    board = cv2.copyMakeBorder(both, 28, 0, 0, 0, cv2.BORDER_CONSTANT, value=(25,25,25))
    cv2.putText(board, label, (8,19), 0, .43, (255,255,255), 1, cv2.LINE_AA)
    return board

class Encoder:
    def __init__(self, path, width, height, fps):
        import imageio_ffmpeg
        if Path(path).exists():
            raise FileExistsError(path)
        self.size = (width, height)
        self.p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-n',
            '-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}', '-r',str(fps),
            '-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','fast',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(path)], stdin=subprocess.PIPE)

    def send(self, im):
        if im.shape[:2] != self.size[::-1]:
            raise ValueError('Encoder frame dimensions changed')
        self.p.stdin.write(np.ascontiguousarray(im).tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError('ffmpeg encoding failed')

def evidence(method, grade, refs=None, confidence=None):
    return dict(grade=grade, method=method, refs=refs or [], confidence=confidence,
                validation='UNREVIEWED')
