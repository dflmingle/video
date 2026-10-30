"""Same-ID no-hit charge regression, without writing production data.

Run from the response worktree AFTER the limiter fix. The unhit V21 controller
and V22 controller receive identical starts, seed, dt, blue samples and time.
"""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import numpy as np


def run(root, out):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from motion_v21 import Crowd as Original
    from motion_v22 import Crowd as Revised
    source = root / 'variants/V22-C'
    data = json.loads((source / 'simulation.json').read_text(encoding='utf8'))
    config = data['config']
    nb = data['blueCount']
    units = data['units'][nb:]
    trajectories = np.load(source / 'trajectories.npy', mmap_mode='r')
    dt = 1 / config['simulationFps']
    charge_frame = round(config.get('redChargeStart', 0) / dt)
    baseline, revised = Original(copy.deepcopy(units), config), Revised(copy.deepcopy(units), config)
    cumulative = [np.zeros(len(units)), np.zeros(len(units))]
    at_half = [np.full(len(units), np.nan), np.full(len(units), np.nan)]
    at_full = [np.full(len(units), np.nan), np.full(len(units), np.nan)]
    rows = []
    started = time.perf_counter()
    for frame in range(121):
        t = frame * dt
        blue = np.asarray(trajectories[min(charge_frame + frame, len(trajectories) - 1), :nb], float)
        for q, crowd in enumerate([baseline, revised]):
            crowd.bluePositions = blue
            previous = crowd.position.copy()
            crowd.step(t, dt)
            cumulative[q] += np.linalg.norm(crowd.position - previous, axis=1)
            for threshold, records in [(.5, at_half), (.9, at_full)]:
                entered = np.isnan(records[q]) & (crowd.velocity[:, 1] >= crowd.preferred * threshold)
                records[q][entered] = t
        if frame not in [36, 72, 120]:
            continue
        for color in ['red', 'orange', 'yellow']:
            ids = np.array([i for i, u in enumerate(units) if u['color'] == color])
            entry = dict(time=t, color=color, count=len(ids))
            for name, q, crowd in [('V21', 0, baseline), ('V22fixed', 1, revised)]:
                entry[name] = dict(medianForward=float(np.median(crowd.velocity[ids, 1])),
                                   meanForward=float(crowd.velocity[ids, 1].mean()),
                                   medianWorldPath=float(np.median(cumulative[q][ids])),
                                   medianForwardProgress=float(np.median((crowd.position - crowd.initial)[ids, 1])))
            entry['medianSpeedRatio'] = entry['V22fixed']['medianForward'] / entry['V21']['medianForward']
            entry['medianPathDifference'] = entry['V22fixed']['medianWorldPath'] - entry['V21']['medianWorldPath']
            assert .97 <= entry['medianSpeedRatio'] <= 1.03, entry
            assert abs(entry['medianPathDifference']) < .30, entry
            rows.append(entry)
    onset = {}
    for threshold, records in [('halfPreferred', at_half), ('ninetyPercentPreferred', at_full)]:
        difference = records[1] - records[0]
        onset[threshold] = dict(medianTimeDifference=float(np.nanmedian(difference)),
                                p95TimeDifference=float(np.nanpercentile(difference, 95)),
                                maxTimeDifference=float(np.nanmax(difference)))
        assert abs(onset[threshold]['medianTimeDifference']) <= dt + 1e-12
    # A single unobstructed soldier must inherit exactly the old acceleration.
    one = [copy.deepcopy(units[-1])]
    old_one, new_one = Original(copy.deepcopy(one), config), Revised(copy.deepcopy(one), config)
    max_free_error = 0.
    for frame in range(121):
        old_one.bluePositions = new_one.bluePositions = np.asarray(
            trajectories[min(charge_frame + frame, len(trajectories) - 1), :nb], float)
        old_one.step(frame * dt, dt)
        new_one.step(frame * dt, dt)
        max_free_error = max(max_free_error, float(np.linalg.norm(old_one.velocity - new_one.velocity)))
    assert max_free_error < 1e-10
    report = dict(status='PASS', noHitsApplied=True, sameIDs=True, sameSeed=config['seed'],
                  fixedDt=dt, rows=rows, startupOnset=onset,
                  unobstructedVelocityErrorMax=max_free_error,
                  seconds=time.perf_counter() - started,
                  limitation='No-hit motion regression only; safety/end time and rendered battle require rebuild.')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'output/response-v22/red-speed-fixed-regression.json')
    args = parser.parse_args()
    result = run(args.root, args.out)
    print(json.dumps(result, indent=2))
