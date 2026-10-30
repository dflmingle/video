"""Explicit synthetic-blue-damage / real-impact response diagnostics.

Read-only production input. Writes only --out. Uses the ACTUAL Archers.move
spring/collision integrator and an identical no-response counterfactual twin.
"""
import argparse
import copy
import csv
import json
import math
from pathlib import Path
import sys
import numpy as np
from scipy.spatial import cKDTree


def nearest_distance(positions):
    return float(cKDTree(positions).query(positions, k=2)[0][:, 1].min())


def diagnose(root, variant, out):
    sys.path.insert(0, str(root / 'tools'))
    from archers_v22 import Archers
    from combat_response_v22 import CombatResponseV22
    src = root / 'variants' / variant
    data = json.loads((src / 'simulation.json').read_text(encoding='utf8'))
    config = json.loads((src / 'params.json').read_text(encoding='utf8'))
    out.mkdir(parents=True, exist_ok=True)
    blue_count = data['blueCount']
    units = copy.deepcopy(data['units'][:blue_count])
    actual = [e for e in data['events'] if (e.get('damage') or 0) > 0
              and e.get('resolution') == 'IMPACT_IN_SHOT']
    if not actual:
        raise AssertionError('No real impact available to replay')
    source_event = actual[0]
    real_shooter = int(source_event['shooter'])
    red_index = int(source_event['target']) - blue_count
    original_paths = np.load(src / 'trajectories.npy', mmap_mode='r')
    source_frame = int(source_event['impactFrame'])
    red_positions = np.asarray(original_paths[source_frame, blue_count:], float)
    dt = 1 / config['simulationFps']
    archers = Archers(units, config)
    archers.redPositions = red_positions
    # Settle genuine deployment rather than manually placing units at slots.
    for k in range(round(4.0 / dt)):
        archers.move(k * dt, dt)
    if np.any(archers.state < 3):
        raise AssertionError('Deployment not settled for isolated response test')
    cases, summaries = [], []
    csv_rows = []
    for synthetic in [True, False]:
        case = 'synthetic-blue-damage' if synthetic else 'real-impact-isolated-replay'
        peers = [i for i, u in enumerate(units) if u['group'] == units[real_shooter]['group']]
        shooter = max(peers, key=lambda i: archers.position[i, 1]) if synthetic else real_shooter
        reference = archers.position[shooter].copy()
        ids = np.argsort(np.linalg.norm(archers.position - reference, axis=1),
                         kind='stable')[:18].tolist()
        response = CombatResponseV22(copy.deepcopy(units), config=config)
        active, control = copy.deepcopy(archers), copy.deepcopy(archers)
        frames, event_rows = [], []
        minimum_spacing = math.inf
        minimum_red_gap = math.inf
        peak, peak_target = 0., 0.
        participant_union = set()
        last_event = None
        # Real replay deliberately includes a same-shooter follow-up within
        # cooldown to verify non-accumulation, then a legal post-cooldown event.
        event_times = [1.] if synthetic else [1., 1.20, 1.62]
        activated_count = 0
        for k in range(round(3.2 / dt)):
            t = k * dt
            for time in event_times:
                if abs(t - time) < dt / 2:
                    if synthetic:
                        response.record_damage(shooter, 1, t, diagnostic=True)
                    else:
                        response.record_impact(shooter, red_index,
                                               source_event['damage'],
                                               source_event['killed'], t)
                    last_event = response.events[-1]
            offset = response.offsets(t, active.position, dt, red_positions)
            active.responseOffsets = offset
            active.move(4. + t, dt)
            control.move(4. + t, dt)
            for e in response.events:
                if e['participants'] is not None:
                    participant_union.update(e['participants'])
            if last_event is not None and last_event['participants'] is not None:
                if activated_count < len(response.audit):
                    event_rows.append(dict(time=t, participants=last_event['participants'],
                                           synthetic=synthetic,
                                           cooldownUntil={str(i): float(response.cooldown[i])
                                                          for i in participant_union}))
                    activated_count = len(response.audit)
            differential = active.position - control.position
            minimum_spacing = min(minimum_spacing, nearest_distance(active.position))
            minimum_red_gap = min(minimum_red_gap, float(cKDTree(red_positions).query(active.position)[0].min()))
            peak = max(peak, float(np.linalg.norm(differential[shooter])))
            peak_target = max(peak_target, float(np.linalg.norm(offset[shooter])))
            snapshot = dict(t=t, position=active.position[ids].tolist(),
                            baseline=control.position[ids].tolist(),
                            target=offset[ids].tolist(),
                            delta=differential[ids].tolist(),
                            speed=active.moveSpeed[ids].tolist(),
                            controls=active.control()[ids].tolist())
            frames.append(snapshot)
            for j in ids:
                csv_rows.append(dict(case=case, synthetic=synthetic, t=t,
                                     id=units[j]['id'], index=j,
                                     x=float(active.position[j, 0]), z=float(active.position[j, 1]),
                                     targetX=float(offset[j, 0]), targetZ=float(offset[j, 1]),
                                     responseDeltaX=float(differential[j, 0]),
                                     responseDeltaZ=float(differential[j, 1]),
                                     speed=float(active.moveSpeed[j]),
                                     cooldownRemaining=max(0., float(response.cooldown[j] - t))))
        nonparticipants = sorted(set(range(blue_count)) - participant_union)
        unchanged = float(np.linalg.norm(active.position[nonparticipants] - control.position[nonparticipants], axis=1).max())
        midpoint = frames[round(1.42 / dt)]
        shooter_local = ids.index(shooter)
        observed = np.array(midpoint['delta'][shooter_local])
        expected = np.array([0., 1.]) if synthetic else red_positions[red_index] - reference
        expected /= np.linalg.norm(expected)
        assert observed @ expected > .07, (case, observed)
        assert minimum_spacing >= archers.personalSpace - 1e-5
        assert peak <= .235 + .002
        assert peak_target <= .235 + 1e-12
        assert unchanged < 1e-8
        if not synthetic:
            assert len(event_rows[1]['participants']) == 0, 'Cooldown ignored'
        summaries.append(dict(case=case, synthetic=synthetic, minimumSpacing=minimum_spacing,
                              minimumRedGapAtFrozenSourceFrame=minimum_red_gap,
                              peakActualResponseDelta=peak, peakTargetOffset=peak_target,
                              actualDeltaAt1_42=observed.tolist(),
                              neighborDeltaAt1_42={str(i): midpoint['delta'][ids.index(i)]
                                                  for i in participant_union if i != shooter and i in ids},
                              participants=sorted(participant_union),
                              nonparticipantFinalDeltaMax=unchanged,
                              events=event_rows, diagnosticEventCount=response.diagnostic_event_count,
                              holdSeconds=.20, attackSeconds=.12, tailTimeConstant=.40,
                              cooldownSeconds=.42, positionIntegrator='archers_v22.Archers.move'))
        cases.append(dict(case=case, synthetic=synthetic, frames=frames,
                          ids=ids, shooter=shooter, reference=reference.tolist(),
                          units=[units[i] for i in ids],
                          events=event_rows, summary=summaries[-1]))
    production_targets = np.load(src / 'response-targets.npy', mmap_mode='r')
    production_peaks = np.linalg.norm(production_targets, axis=2)
    # Freeze ONLY the recorded action/impact schedule, not position. Both twins
    # run the actual spring/contact integration. This separates response-root
    # motion from deployment, personal stance offsets and shooting poses.
    production_control = np.load(src / 'blue-control.npy', mmap_mode='r')
    twin = Archers(copy.deepcopy(units), config)
    null_twin = Archers(copy.deepcopy(units), config)
    real_response = CombatResponseV22(copy.deepcopy(units), config=config)
    responses_by_frame = {}
    for e in actual:
        responses_by_frame.setdefault(int(e['impactFrame']), []).append(e)
    production_delta = np.zeros((len(original_paths), blue_count, 2), np.float32)
    replay_error = 0.
    production_rows = []
    for f in range(len(original_paths)):
        t = f * dt
        red_before = np.asarray(original_paths[max(0, f - 1), blue_count:], float)
        if f:
            bc = production_control[f - 1]
            for instance in [twin, null_twin]:
                instance.state[:] = bc[:, 0].astype(np.uint8)
                instance.timer[:] = bc[:, 1]
                instance.target[:] = bc[:, 2].astype(int)
                instance.lastRelease[:] = bc[:, 3]
                instance.releaseEventId[:] = bc[:, 11].astype(int)
        for e in responses_by_frame.get(f, []):
            real_response.record_impact(e['shooter'], e['target'] - blue_count,
                                        e['damage'], e['killed'], t)
        twin.responseOffsets = real_response.offsets(t, twin.position, dt, red_before)
        twin.redPositions = null_twin.redPositions = red_before
        twin.move(t, dt)
        null_twin.move(t, dt)
        delta = twin.position - null_twin.position
        production_delta[f] = delta
        replay_error = max(replay_error, float(np.max(np.linalg.norm(
            twin.position - original_paths[f, :blue_count], axis=1))))
        for j in np.where((np.linalg.norm(delta, axis=1) > 1e-6) |
                          (np.linalg.norm(twin.responseOffsets, axis=1) > 1e-6))[0]:
            production_rows.append(dict(t=t, id=units[j]['id'], index=int(j), synthetic=False,
                responseDeltaX=float(delta[j, 0]), responseDeltaZ=float(delta[j, 1]),
                targetX=float(twin.responseOffsets[j, 0]), targetZ=float(twin.responseOffsets[j, 1])))
    replay_ok = replay_error < 1e-4
    assert replay_ok, f'Production spring replay mismatch: {replay_error}'
    np.save(out / 'production-response-delta.npy', production_delta)
    with (out / 'production-response-causality.csv').open('w', newline='', encoding='utf8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(production_rows[0]))
        writer.writeheader()
        writer.writerows(production_rows)
    window_stats = []
    for f in range(0, len(original_paths), round(.25 / dt)):
        end = min(len(original_paths), f + round(.25 / dt))
        window_stats.append(dict(start=f * dt, end=end * dt,
                                 realImpacts=sum(f * dt <= e['impact'] < end * dt for e in actual),
                                 respondingArchersMax=int(np.max((production_peaks[f:end] > .001).sum(axis=1))),
                                 maxResponseTarget=float(production_peaks[f:end].max())))
    result = dict(status='PASS', source=str(src), syntheticProductionEvents=0,
                  realProductionImpactCount=len(actual), sourceEvent=source_event,
                  productionMaxResponseTarget=float(production_peaks.max()),
                  productionActualResponseDeltaMax=float(np.linalg.norm(production_delta, axis=2).max()),
                  productionActualFrontStepMax=float(max(0., -production_delta[:, :, 1].min())),
                  productionArchersWithFrontStepOver01=int(np.sum(np.min(production_delta[:, :, 1], axis=0) < -.01)),
                  productionReplayPositionErrorMax=replay_error,
                  productionResponseTwinMethod='Recorded fire states and real impact log; both roots independently integrated; no response target on null twin.',
                  productionMinBlueSpacing=min(nearest_distance(p[:blue_count]) for p in original_paths),
                  productionTimeline=window_stats, cases=summaries,
                  limitations=['Synthetic retreat tests response/integration only; no production blue damage source.',
                               'Isolated impact replay uses a frozen real impact target position and shifted diagnostic time.',
                               'No claim of final battle visual approval or red-blue safety from isolated frozen setup.'])
    out.mkdir(parents=True, exist_ok=True)
    (out / 'response-diagnostics.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    (out / 'response-animation-data.json').write_text(json.dumps(dict(config=config, cases=cases)), encoding='utf8')
    with (out / 'response-trajectories.csv').open('w', newline='', encoding='utf8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--variant', default='V22-C')
    parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parents[1] / 'output/response-v22')
    args = parser.parse_args()
    result = diagnose(args.root, args.variant, args.out)
    print(json.dumps({k: v for k, v in result.items() if k not in ('productionTimeline', 'sourceEvent')}, indent=2))
