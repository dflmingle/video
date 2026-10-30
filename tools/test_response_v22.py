"""Run: python tools/test_response_v22.py [--baseline SIMULATION.json]."""
import argparse
import copy
import json
import time
from pathlib import Path
import numpy as np
from combat_response_v22 import CombatResponseV22
from motion_v22 import Crowd
from motion_v17 import DT


def run(baseline=None):
    root = Path(__file__).resolve().parents[1]
    source = Path(baseline) if baseline else root / 'baseline/V5-simulation.json'
    data = json.loads(source.read_text(encoding='utf8'))
    config = json.loads((root / 'variants/V21/params.json').read_text(encoding='utf8'))
    nb = data['blueCount']
    blue = data['units'][:nb]
    blue_pos = np.array([u['start'] for u in blue], float)
    red_pos = np.array([u['start'] for u in data['units'][nb:]], float)
    impacts = [e for e in data.get('events', []) if (e.get('damage') or 0) > 0
               and e.get('resolution') == 'IMPACT_IN_SHOT']
    # A true encoded V21 bound impact is preferred over a fixture.
    event = impacts[0] if impacts else dict(shooter=4, target=nb, damage=1,
                                           killed=False, impact=.1)
    response = CombatResponseV22(blue)
    t0 = float(event['impact'])
    j = int(event['shooter'])
    target = int(event['target']) - nb
    response.record_impact(j, target, event['damage'], event['killed'], t0)
    assert not np.any(response.offsets(t0 - DT, blue_pos, DT, red_pos))
    peak = 0.
    for k in range(1, 30):
        offset = response.offsets(t0 + k * DT, blue_pos, DT, red_pos)
        peak = max(peak, float(np.linalg.norm(offset[j])))
        assert np.linalg.norm(offset, axis=1).max() <= .235 + 1e-12
    participants = response.events[0]['participants']
    assert j in participants and len(participants) <= 3
    other = np.ones(nb, bool)
    other[participants] = False
    assert np.all(offset[other] == 0), 'Nonparticipants moved'
    direction = red_pos[target] - blue_pos[j]
    direction /= np.linalg.norm(direction)
    assert float(offset[j] @ direction) > .07 and peak > .10
    before = offset[j].copy()
    response.record_impact(j, target, 1, False, t0 + .5)
    for k in range(31, 140):
        offset = response.offsets(t0 + k * DT, blue_pos, DT, red_pos)
    assert np.linalg.norm(offset[j]) < .008, 'Intent did not decay'
    assert response.diagnostic_event_count == 0

    diagnostic = CombatResponseV22(blue)
    try:
        diagnostic.record_damage(j, 1, 0)
        raise AssertionError('Unmarked fake damage accepted')
    except ValueError:
        pass
    diagnostic.record_damage(j, 1, 0, diagnostic=True)
    for k in range(30):
        retreat = diagnostic.offsets(k * DT, blue_pos, DT, red_pos)
    assert retreat[j, 1] > .08
    assert diagnostic.audit[0]['diagnostic']

    # A compact authored squad retains independent, deterministic movement.
    red = copy.deepcopy(data['units'][nb:nb + 24])
    for u in red:
        u['delay'] = 0.
    c = Crowd(copy.deepcopy(red), config)
    d = Crowd(copy.deepcopy(red), config)
    c.bluePositions = d.bluePositions = blue_pos
    c.position[0, 0] += .32
    d.position[0, 0] += .32
    c.position[1, 1] += 1.0
    d.position[1, 1] += 1.0
    history, started = [], time.perf_counter()
    for k in range(70):
        t = k * DT
        c.step(t)
        d.step(t)
        history.append(c.velocity.copy())
        assert np.all(c.velocity[:, 1] >= 0)
        delta = c.position[:, None] - c.position[None, :]
        pair_distance = np.linalg.norm(delta, axis=2) + np.eye(c.n) * 100
        assert pair_distance.min() >= .615 - 1e-4
    assert np.array_equal(c.position, d.position)
    assert np.ptp(c.cycles + c.phase) > .1
    assert np.std(np.array(history)[-1, :, 1]) > .01
    assert np.all(c.position[:, 1] > c.initial[:, 1] + 10)
    assert np.any(abs(c.formationAcceleration) > .01)
    assert np.linalg.norm(c.formationAcceleration, axis=1).max() <= 6.47
    c.apply_hit(0, config['redHitPoints'], 70 * DT)
    death = c.position[0].copy()
    healthy_multipliers = [c.get_hit_speed_multiplier(i, 71 * DT)
                           for i in range(1, c.n)]
    assert set(healthy_multipliers) == {1.}
    for k in range(70, 80):
        c.step(k * DT)
    assert np.array_equal(c.position[0], death)
    # This exercises the formerly no-op ratio clamp at low forward speed.
    c.velocity[2, 1] = 1.
    c.route[2] = 0
    c.routeSide[2] = -1
    avoid = c.compute_local_avoidance(2, np.array([0]), 1.4)
    assert abs(avoid) <= .30 + 1e-12
    probe = Crowd(copy.deepcopy(red), config)
    probe.position[1, 1] += 2.0
    untouched = probe.position.copy()
    probe.compute_soft_formation_correction(1)
    far_force = probe.formationAcceleration[1].copy()
    probe.pressure[1] = 1.
    probe.compute_soft_formation_correction(1)
    near_force = probe.formationAcceleration[1].copy()
    assert far_force[1] < near_force[1] <= 0
    assert np.array_equal(probe.position, untouched), 'Spring wrote root position'
    return dict(status='PASS', trueImpactReplay=bool(impacts), baseline=str(source),
                responseParticipants=participants, responsePeak=peak,
                forwardOffsetAtHold=before.tolist(), nonparticipantsExactlyZero=True,
                diagnosticSeparated=True, deterministic=True,
                minBodyDistance=.615, deadFixed=True, noReverse=True,
                healthyWoundMultiplier=1., independentGait=True,
                speedStd=float(np.std(np.array(history)[-1, :, 1])),
                farFormationAcceleration=far_force.tolist(),
                nearFormationAcceleration=near_force.tolist(),
                testSeconds=time.perf_counter() - started,
                note='Tests desired offset. Actual blue spring/collision is caller-owned.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline')
    args = parser.parse_args()
    print(json.dumps(run(args.baseline), indent=2))
