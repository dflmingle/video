"""Refresh native bow origins after a metadata-only hand/facing correction.

No trajectories, release frames, impacts, targets or damage are changed.
"""
import json, math, sys
from pathlib import Path
import numpy as np
root = Path(__file__).resolve().parents[1]
for name in sys.argv[1:] or ['V22-B', 'V22-C']:
    d = root / 'variants' / name
    s = json.loads((d / 'simulation.json').read_text(encoding='utf8'))
    p = np.load(d / 'trajectories.npy')
    b = np.load(d / 'blue-control.npy')
    a = json.loads((d / 'asset-render-audit.json').read_text(encoding='utf8'))
    local = a['models']['archer']['bowReleaseLocal']
    maximum = 0.
    for e in s['events']:
        x, z = p[e['releaseFrame'], e['shooter']]
        yaw = float(b[e['releaseFrame'], e['shooter'], 8])
        origin = [float(x + local[0]*math.cos(yaw)+local[2]*math.sin(yaw)),
                  float(local[1]+.015),
                  float(z-local[0]*math.sin(yaw)+local[2]*math.cos(yaw))]
        maximum = max(maximum, float(np.linalg.norm(np.array(origin)-e['origin'])))
        e.update(origin=origin, releaseYaw=yaw,
                 originMapping='sampled native left-hand at release phase 0.64, rotated by actual per-member facingYaw')
    (d / 'simulation.json').write_text(json.dumps(s, separators=(',', ':')), encoding='utf8')
    print(name, 'maximum corrected world origin delta', maximum)
