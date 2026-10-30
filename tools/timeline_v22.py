"""Read-only prospective V22 timing solver; never rewrites simulation data.

Uses recorded V21 paths with red(t)=V21.red(max(0,t-hold)) and absolute blue
deployment. Hypothetical first shots are optimistic single-target feasibility
bounds, not a new combat simulation (reservation, damage and congestion differ).
"""
from pathlib import Path
import argparse
import json
import math
import numpy as np
from scipy.spatial import cKDTree


def sample(a, t, fps):
    f = min(max(t * fps, 0.0), len(a) - 1.0)
    lo = int(f)
    return a[lo] * (1 - (f - lo)) + a[min(lo + 1, len(a) - 1)] * (f - lo)


def camera_probe(s, paths, hold):
    """Exact perspective projection for this camera pose; no ortho shortcut."""
    c = s['config']; fps = c['simulationFps']; nb = s['blueCount']
    end = (len(paths)-1)/fps + hold
    height = c['cameraPosition'][1]
    depth_offset = c['cameraPosition'][2]-c['cameraTarget'][2]
    norm = math.hypot(height, depth_offset)
    tan_half = math.tan(math.radians(c['cameraFov']/2))
    aspect = c['width']/c['height']
    colors = np.array([u.get('color', 'blue') for u in s['units']])
    result = {}
    for mode, combat_zoom in [('A', 2.05), ('B', 2.5625)]:
        # A is the actual V21 baseline and B differs only by combat zoom.
        # Keep the same absolute push schedule for a like-for-like A/B test.
        start = .72
        finish = max(start+.18, end-.16); span = finish-start
        keys = {}; min_yellow = 1.; min_blue = 1.
        for frame in range(round(end*fps)+1):
            t = frame/fps; u = min(1., max(0., (t-start)/span))
            k = u*u*u*(u*(u*6-15)+10)
            center = -20+16*k; zoom = 1.35+(combat_zoom-1.35)*k
            pts = np.concatenate([sample(paths[:, :nb], t, fps), sample(paths[:, nb:], max(0, t-hold), fps)]).astype(np.float64)
            def project(y):
                depth = (height*(height-y)+depth_offset*(center+depth_offset-pts[:, 1]))/norm
                x = pts[:, 0]/depth/tan_half/aspect*zoom-c.get('cameraShiftX', 0)
                py = (depth_offset*y-height*(pts[:, 1]-center))/norm/depth/tan_half*zoom-c.get('cameraShiftY', 0)
                return x, py
            x, y = project(.75); visible = (np.abs(x)<.98)&(np.abs(y)<.98)
            min_yellow = min(min_yellow, float(visible[colors=='yellow'].mean()))
            min_blue = min(min_blue, float(visible[:nb].mean()))
            labels = {0: 'opening', round(end*fps/2): 'middle', round((hold+1.8833333333)*fps): 'oldHitTime', round(end*fps): 'end'}
            if frame in labels:
                _, floor_y = project(0); _, head_y = project(1.5)
                pixel = np.abs(head_y-floor_y)*c['height']/2
                keys[labels[frame]] = dict(time=t, zoom=zoom, centerZ=center,
                    teams={color: dict(visibleFraction=float(visible[colors==color].mean()),
                                       heightPixelsMean=float(pixel[colors==color].mean()))
                           for color in ['red', 'orange', 'yellow', 'blue']})
        result[mode] = dict(keyframes=keys, yellowMinimumVisibleFraction=min_yellow,
                           blueMinimumVisibleFraction=min_blue,
                           maxCenterSpeed=1.875*16/span,
                           maxZoomSpeed=1.875*(combat_zoom-1.35)/span)
    return result


def solve(variant, holds):
    s = json.loads((variant / 'simulation.json').read_text(encoding='utf8'))
    c = s['config']; fps = c['simulationFps']; dt = 1 / fps; nb = s['blueCount']
    p = np.load(variant / 'trajectories.npy')
    ctrl = np.load(variant / 'blue-control.npy')
    blue, red = p[:, :nb], p[:, nb:]
    yellow = np.array([i for i, u in enumerate(s['units'][nb:]) if u.get('color') == 'yellow'])
    ready = np.full(nb, np.inf)
    for j in range(nb):
        frames = np.flatnonzero(np.isin(ctrl[:, j, 0].astype(int), [3, 4, 5, 6]))
        if len(frames): ready[j] = frames[0] / fps
    minimum = c['minimumEnemyClearance']; envelope = 2 * c['weaponEnvelopeRadius']
    scenarios = []
    for hold in holds:
        times = np.arange(round((hold + (len(p)-1)/fps) * fps) + 1) / fps
        rp = [sample(red, max(0, t - hold), fps) for t in times]
        bp = [sample(blue, t, fps) for t in times]
        prev = None; safe_end = 0.0; min_safe = float('inf')
        for k, t in enumerate(times):
            gap = float(cKDTree(bp[k]).query(rp[k])[0].min())
            lower = gap - envelope
            if prev is not None:
                dr = np.linalg.norm(rp[k] - rp[k-1], axis=1).max()
                db = np.linalg.norm(bp[k] - bp[k-1], axis=1).max()
                lower = min(prev, gap) - .5 * (dr + db) - envelope
            if lower < minimum + .05: break
            safe_end = float(t); min_safe = min(min_safe, lower); prev = gap
        in_range = np.full(nb, np.inf)
        for k, t in enumerate(times):
            if t > safe_end: break
            d = np.linalg.norm(bp[k][:, None, :] - rp[k][yellow][None, :, :], axis=2).min(axis=1)
            entered = (d <= c['archerRange']) & ~np.isfinite(in_range)
            in_range[entered] = t

        def candidate(plan):
            shots = []
            for j, u in enumerate(s['units'][:nb]):
                if not np.isfinite(ready[j]) or not np.isfinite(in_range[j]): continue
                aim, draw = u['aimSeconds'], u['drawSeconds']
                if plan == 'strict': release = max(ready[j], in_range[j]) + aim + draw
                elif plan == 'preAim': release = max(ready[j] + aim, in_range[j]) + draw
                elif plan == 'preDrawBound': release = max(ready[j] + aim + draw, in_range[j])
                else: release = in_range[j]  # first-frame prepared upper bound, NOT applied
                release = math.ceil((release - 1e-9) * fps) / fps
                if release > safe_end: continue
                origin = sample(blue, release, fps)[j]
                targets = sample(red, max(0, release-hold), fps)
                distance = np.linalg.norm(targets[yellow]-origin, axis=1)
                valid = yellow[distance <= c['archerRange']]
                if not len(valid): continue
                # Test all valid targets. Pointwise interception uses the future
                # recorded trajectory; no constant-velocity/stale distance proxy.
                for target in valid:
                    toward = targets[target] - origin
                    source = origin + toward / max(np.linalg.norm(toward), 1e-9) * c.get('arrowOriginForward', .38)
                    def error(flight):
                        destination = sample(red, max(0, release+flight-hold), fps)[target]
                        horizontal = np.linalg.norm(destination-source)
                        return math.hypot(horizontal, c.get('arrowOriginHeight', .95)-.85) - c['arrowSpeed']*flight
                    horizon = safe_end-release
                    if horizon <= 0 or error(horizon) > 0: continue
                    lo, hi = 0., horizon
                    for _ in range(36):
                        mid = (lo+hi)/2
                        if error(mid) > 0: lo = mid
                        else: hi = mid
                    flight = hi
                    hit = release + flight
                    shots.append(dict(shooter=u['id'], target=s['units'][nb+int(target)]['id'],
                                      ready=float(ready[j]), rangeEntry=float(in_range[j]), release=release,
                                      hit=hit, flight=flight, releaseDistance=float(np.linalg.norm(toward)),
                                      postHitWindow=safe_end-hit))
            return min(shots, key=lambda q: q['hit']) if shots else None

        scenarios.append(dict(redChargeStart=hold, safeEnd=safe_end,
                              conservativeMinimumSurfaceGap=min_safe,
                              firstRangeEntry=float(in_range.min()),
                              strict=candidate('strict'), preAim=candidate('preAim'),
                              preDrawBound=candidate('preDrawBound'),
                              firstFramePreparedNotApplied=candidate('prepared')))
    events = s['events']; impacts = [e for e in events if e.get('resolution') == 'IMPACT_IN_SHOT']
    return dict(baseline=str(variant), baselineObserved=dict(
        firstReady=float(ready.min()), firstRelease=min(e['release'] for e in events),
        firstHit=min(e['impact'] for e in impacts), safeEnd=(len(p)-1)/fps,
        postHitWindow=(len(p)-1)/fps-min(e['impact'] for e in impacts)),
        units=dict(blue=nb, red=s['redCount']), assumptions=dict(
            range=c['archerRange'], arrowSpeed=c['arrowSpeed'], redSpeed=c['redSpeed'],
            safeGap=minimum, weaponEnvelopeRadius=c['weaponEnvelopeRadius'],
            redTransform='baseline(max(0, absoluteTime-redChargeStart))',
            blueTransform='baseline(absoluteTime); endpoint held after recorded end',
            strict='Aim and draw only after range-valid target exists.',
            preAim='Aim before range; draw only after valid range entry.',
            preDrawBound='OPTIMISTIC ONLY: draw outside effective release range; needs explicit policy approval.',
            firstFramePreparedNotApplied='NOT APPLIED: initial prepared behavior differs from requested visible deployment.',
            limits='No target reservations, injuries re-simulation, full 3D arc-speed proof, or native hand offset. Prospective bounds, not rendered evidence.'),
        scenarios=scenarios, perspectiveCameraProbe=camera_probe(s, p, .8))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--variant', default='variants/V21')
    ap.add_argument('--holds', type=float, nargs='+', default=[0, .8, 1., 1.2])
    ap.add_argument('--output', default='output/V22-timeline-prospective.json')
    args = ap.parse_args(); result = solve(Path(args.variant), args.holds)
    probe = result['perspectiveCameraProbe']
    checks = {
        'allRedArmiesInOpening': all(probe['B']['keyframes']['opening']['teams'][color]['visibleFraction'] == 1 for color in ['red', 'orange', 'yellow']),
        'yellowFrontVisibleEveryFrame': probe['B']['yellowMinimumVisibleFraction'] == 1,
        'blueSourcesVisibleEveryFrame': probe['B']['blueMinimumVisibleFraction'] == 1,
        'combatPixelIncrease25Percent': abs(probe['B']['keyframes']['end']['teams']['yellow']['heightPixelsMean'] / probe['A']['keyframes']['end']['teams']['yellow']['heightPixelsMean'] - 1.25) < 1e-9,
        'prospectiveSafety': all(q['conservativeMinimumSurfaceGap'] >= result['assumptions']['safeGap'] for q in result['scenarios']),
        'releaseRangeValid': all(q[plan] is None or q[plan]['releaseDistance'] <= result['assumptions']['range'] + 1e-6 for q in result['scenarios'] for plan in ['strict', 'preAim', 'preDrawBound']),
    }
    result['numericChecks'] = checks
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({'observed': result['baselineObserved'], 'scenarios': result['scenarios']}, indent=2))
    if not all(checks.values()): raise SystemExit('FAILED numeric checks: ' + ', '.join(k for k, v in checks.items() if not v))
