"""Isolated repeatable V22 blue tests. Never writes production variants."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
import numpy as np
from scipy.spatial import cKDTree
from archers_v22 import Archers, NAMES, CONTROL_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def run(units, config, preaim=False, response=False):
    C = dict(config, preAim=preaim)
    a = Archers(copy.deepcopy(units), C)
    dt = 1 / 60
    red = np.array([[x, z] for z in np.linspace(-4, 1, 12)
                    for x in np.linspace(-25, 25, 42)], dtype=float)
    hp = np.ones(len(red)) * 100
    positions, controls, shots, timelines = [], [], [], []
    phase_error = 0.
    min_space, max_step = 1e9, 0.
    for f in range(361):
        t = f * dt
        target_red = red + [0., -100.] if preaim and t < 2.8 else red
        a.redPositions = target_red
        if response:
            a.responseOffsets[:] = 0
            # This is an input target owned by the response system, not an
            # additive world-position correction after the movement update.
            w = max(0., math.sin(math.pi * (t - 3.) / .9)) if 3 < t < 3.9 else 0.
            a.responseOffsets[:12, 0] = .18 * w
        old = a.position.copy()
        old_phase = a.walkPhase.copy()
        a.move(t, dt)
        step = np.linalg.norm(a.position - old, axis=1)
        predicted = (old_phase + step / C['blueStride']) % 1
        phase_error = max(phase_error, float(np.max(np.abs(predicted - a.walkPhase))))
        max_step = max(max_step, float(np.max(step)))
        min_space = min(min_space, float(cKDTree(a.position).query(a.position, k=2)[0][:, 1].min()))

        def spawn(j, target, release, draw_start):
            event = dict(id=f'A{len(shots):05}', shooter=j, target=target,
                         release=release, drawStart=draw_start,
                         distance=float(np.linalg.norm(target_red[target] - a.position[j])))
            shots.append(event)
            return event

        a.update_fire(t, dt, target_red, hp, np.zeros(len(red), bool), spawn)
        ctrl = a.control()
        assert ctrl.shape == (len(units), 12)
        for e in shots:
            if abs(e['release'] - t) < 1e-9:
                j = e['shooter']
                assert int(ctrl[j, 0]) == 5
                assert abs(ctrl[j, 6] - .64) < 1e-10
                assert int(ctrl[j, 11]) == int(e['id'][1:])
                assert e['distance'] <= C['archerRange'] + 1e-9
                assert release_after_draw(a, j, e)
        positions.append(a.position.copy())
        controls.append(ctrl.copy())
    pos, ctrl = np.array(positions), np.array(controls)
    digest = hashlib.sha256(pos.tobytes() + ctrl.tobytes()).hexdigest()
    for j in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 108, 109, 110, 216, 217, 218]:
        transitions = [e for e in a.transitions if e['id'] == units[j]['id']]
        timelines.append(dict(id=units[j]['id'], transitions=transitions))
    report = dict(preAim=preaim, response=response, hash=digest,
                  firstShot=min([e['release'] for e in shots], default=None),
                  shotCount=len(shots), phaseMaxError=phase_error,
                  minimumSpacing=min_space, maximumFrameStep=max_step,
                  stateIdsObserved=np.unique(ctrl[:, :, 0]).astype(int).tolist(),
                  averageArrival=float(np.nanmean(a.arrivedAt)),
                  actualArrivals=[float(np.nanmin(a.arrivedAt)), float(np.nanmax(a.arrivedAt))],
                  endpointErrorP50P95=np.percentile(np.linalg.norm(
                      pos[-1] - a.defenseSlots - a.shootingOffsets, axis=1), [50, 95]).tolist(),
                  individualTimelines=timelines,
                  maxIdleOffset=float(np.max(np.linalg.norm(a.slotOffsets, axis=1))),
                  maxShootingOffset=float(np.max(np.linalg.norm(a.shootingOffsets, axis=1))))
    assert min_space >= .615 - 2e-4, min_space
    assert phase_error < 1e-10, phase_error
    assert max_step < .16, max_step
    assert len(shots) > 50
    assert 7 in report['stateIdsObserved'], 'TURNING missing'
    assert report['actualArrivals'][1] - report['actualArrivals'][0] > .15
    assert report['endpointErrorP50P95'][1] < .09
    assert np.array_equal(pos[0], a.starts), 'authored initial positions changed'
    if preaim:
        # No arrow may spawn while every target is out of actual range.
        assert report['firstShot'] >= 2.8
        assert np.max(ctrl[120:160, :, 6][ctrl[120:160, :, 0] == 3]) > .10
    return report, pos, ctrl


def release_after_draw(a, j, e):
    return e['release'] - e['drawStart'] + 1e-8 >= a.units[j]['drawSeconds']


def native_pose_test():
    script = """
import assert from 'node:assert/strict';
import {resolveArcherPose} from './src/archer-pose-v22.js';
let checks=0;
for(let state=0;state<=7;state++)for(const p of [0,.1,.5,.9,1]){
 const bc=[state,p*.14,0,1.8,.37,.5,state===5?.64:(state===4?.12+.52*p:p),2.3,3.08,3.1,p,7];
 const a=resolveArcherPose({bc,speed:2.3,unit:{phase:.13,walkSpeed:5,aimSeconds:.14},time:2});
 const b=resolveArcherPose({bc,speed:2.3,unit:{phase:.13,walkSpeed:5,aimSeconds:.14},time:500});
 assert.equal(a.phaseFraction,b.phaseFraction,'global clock reset member phase');
 assert.ok(Math.abs(Object.values(a.transitionWeights).reduce((a,b)=>a+b,0)-1)<1e-9);
 if(state===1) assert.ok(Math.abs(a.phaseFraction-.37)<1e-9);
 if(state===5){assert.equal(a.phaseFraction,.64);assert.equal(a.releaseEventId,7);}
 if(state===7){assert.equal(a.action,'idle');assert.equal(a.yaw,3.08);}
 checks++;
}
console.log(JSON.stringify({checks,releasePhase:.64,independentClock:true,weightsSumToOne:true}));
"""
    r = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='output/v22-blue-tests')
    parser.add_argument('--config', default='variants/V22-C/params.json')
    args = parser.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    source = json.loads((ROOT / 'baseline/V5-simulation.json').read_text(encoding='utf8'))
    C = json.loads((ROOT / args.config).read_text(encoding='utf8'))
    units = source['units'][:source['blueCount']]
    normal, pos, ctrl = run(units, C)
    replay, _, _ = run(units, C)
    assert normal['hash'] == replay['hash'], 'non-deterministic replay'
    response, _, _ = run(units, C, response=True)
    preaim, _, _ = run(units, C, preaim=True)
    pose = native_pose_test()
    np.save(out / 'normal-positions.npy', pos)
    np.save(out / 'normal-controls.npy', ctrl)
    report = dict(status='PASS', controlColumns=CONTROL_COLUMNS,
                  normal=normal, response=response, testCPreAim=preaim,
                  deterministicReplay=True, renderingHelper=pose,
                  visualAcceptance='NOT_RUN: root renders encoded clip after integration')
    (out / 'tests.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps({k: normal[k] for k in ['firstShot', 'shotCount', 'phaseMaxError',
                                            'minimumSpacing', 'actualArrivals',
                                            'endpointErrorP50P95']}, indent=2))
    print(json.dumps(pose))
