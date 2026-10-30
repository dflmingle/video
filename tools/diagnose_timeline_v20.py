"""V20 engagement-window diagnosis and causal firing plans.

This diagnostic keeps the V19 red and blue trajectories fixed.  It does not
change the production battle or render the formal V20 shot.  Plans A/B/C only
change the archer scheduler/range so that timing effects can be separated.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "variants" / "FINAL"
OUT = ROOT / "variants" / "V20-TIMELINE"
OUT.mkdir(parents=True, exist_ok=True)

sim = json.loads((BASE / "simulation.json").read_text(encoding="utf-8"))
safe = json.loads((BASE / "safety-and-causality.json").read_text(encoding="utf-8"))
C = sim["config"]
units = sim["units"]
nb = int(sim["blueCount"])
nr = int(sim["redCount"])
fps = float(C["simulationFps"])
dt = 1.0 / fps
T = np.load(BASE / "trajectories.npy", mmap_mode="r")
assert T.shape[1] == nb + nr


def frame_at(t: float) -> int:
    return max(0, min(T.shape[0] - 1, int(round(t * fps))))


def pos(t: float, idx: int) -> np.ndarray:
    f = frame_at(t)
    return np.asarray(T[f, idx], dtype=np.float64)


blue = units[:nb]
red = units[nb:]
blue_pos = np.asarray(T[:, :nb, :], dtype=np.float64)
red_pos = np.asarray(T[:, nb:, :], dtype=np.float64)
red_vel = np.gradient(red_pos, dt, axis=0)
baseline_blue_control = np.fromfile(BASE / 'blue-control.f32', dtype=np.float32).reshape(T.shape[0], nb, -1)
actual_aim_start = np.full(nb, np.nan)
actual_draw_start = np.full(nb, np.nan)
actual_release_start = np.full(nb, np.nan)
for j in range(nb):
    for state, out in [(3, actual_aim_start), (4, actual_draw_start), (5, actual_release_start)]:
        ix = np.where(np.rint(baseline_blue_control[:, j, 0]).astype(int) == state)[0]
        if len(ix): out[j] = float(ix[0]) * dt
actual_ready = np.where(np.isfinite(actual_aim_start), actual_aim_start, np.array([float(u['readyAt']) for u in blue]))


def flight_seconds(shooter: int, target: int, f: int, arrow_speed: float) -> float:
    """Solve the same constant-velocity intercept equation as the builder."""
    rel = red_pos[f, target] - blue_pos[f, shooter]
    v = red_vel[f, target]
    qa = float(v @ v - arrow_speed * arrow_speed)
    qb = float(2.0 * (rel @ v))
    qc = float(rel @ rel)
    if abs(qa) < 1e-8:
        roots = [-qc / qb] if abs(qb) > 1e-8 else []
    else:
        disc = max(0.0, qb * qb - 4.0 * qa * qc)
        sq = math.sqrt(disc)
        roots = [(-qb + sq) / (2.0 * qa), (-qb - sq) / (2.0 * qa)]
    roots = [x for x in roots if x > 0]
    return max(0.18, min(roots)) if roots else max(0.18, float(np.linalg.norm(rel)) / arrow_speed)


def nearest_distance(t: float) -> float:
    f = frame_at(t)
    # cKDTree is unnecessary at this small diagnostic size; this is only a few
    # dozen sampled times and keeps the script dependency-free.
    d = np.linalg.norm(blue_pos[f, :, None, :] - red_pos[f, None, :, :], axis=2)
    return float(d.min())


def event_hist(events, key, end):
    edges = np.arange(0.0, end + 0.250001, 0.25)
    hist, _ = np.histogram([float(e[key]) for e in events if e.get(key) is not None], bins=edges)
    return {f"{edges[i]:.2f}-{edges[i+1]:.2f}": int(v) for i, v in enumerate(hist)}


def baseline_metrics():
    events = [e for e in sim["events"] if e.get("release") is not None]
    visible = [e for e in events if e.get("resolution") == "IMPACT_IN_SHOT"]
    first_release = min((float(e["release"]) for e in events), default=None)
    first_hit = min((float(e["impact"]) for e in visible), default=None)
    end = float(sim["frames"] - 1) * dt
    ready = [float(u["readyAt"]) for u in blue]
    arrivals = [float(u["arrival"]) for u in blue]
    first_in_range = []
    first_in_range_after_actual_ready = []
    for j, u in enumerate(blue):
        start = frame_at(float(u["readyAt"]))
        found = None
        for f in range(start, T.shape[0]):
            d = np.linalg.norm(red_pos[f] - blue_pos[f, j], axis=1)
            if np.any(d <= float(C["archerRange"])):
                found = f * dt
                break
        first_in_range.append(found)
        start2 = frame_at(float(actual_ready[j]))
        found2 = None
        for f in range(start2, T.shape[0]):
            d = np.linalg.norm(red_pos[f] - blue_pos[f, j], axis=1)
            if np.any(d <= float(C["archerRange"])):
                found2 = f * dt
                break
        first_in_range_after_actual_ready.append(found2)
    earliest_theoretical = [
        (first_in_range_after_actual_ready[j] + float(u.get("aimSeconds", C.get("aimSeconds", 0.1))) + float(u.get("drawSeconds", C.get("drawSeconds", 0.38))))
        if first_in_range_after_actual_ready[j] is not None else None
        for j, u in enumerate(blue)
    ]
    first_eligible = min((x for x in earliest_theoretical if x is not None), default=None)
    safe_dist = np.asarray(safe["distanceByFrame"], dtype=np.float64)
    surface = safe_dist - 2.0 * float(safe["envelopeRadiusPerUnit"])
    safe_frames = np.where(surface >= float(safe["requiredSurfaceClearance"]))[0]
    safe_end = float(safe_frames[-1]) * dt if len(safe_frames) else end
    return {
        "firstArrival": min(arrivals), "lastArrival": max(arrivals),
        "firstReady": min(ready), "lastReady": max(ready),
        "actualFirstAiming": float(np.nanmin(actual_aim_start)), "actualLastAiming": float(np.nanmax(actual_aim_start)),
        "actualFirstDrawing": float(np.nanmin(actual_draw_start)), "actualFirstReleaseState": float(np.nanmin(actual_release_start)),
        "firstInRange": min(x for x in first_in_range if x is not None),
        "firstEligibleRelease": first_eligible,
        "firstRelease": first_release, "firstHit": first_hit,
        "safeEnd": safe_end, "duration": end,
        "postHitWindow": None if first_hit is None else safe_end - first_hit,
        "visibleArrows": len(visible), "allReleases": len(events),
        "releaseHistogram": event_hist(events, "release", end),
        "impactHistogram": event_hist(visible, "impact", end),
        "flightSamples": [float(e["impact"] - e["release"]) for e in visible[:32]],
        "firstInRangeByArcher": first_in_range,
        "firstInRangeAfterActualReadyByArcher": first_in_range_after_actual_ready,
        "earliestEligibleByArcher": earliest_theoretical,
    }


def choose_target(j, f, valid, mode):
    if len(valid) == 0:
        return None
    # Stable spatial choice.  Plan A/C remove the avoidable target reservation
    # churn by taking the nearest free target with a deterministic tie-break.
    d = np.linalg.norm(red_pos[f, valid] - blue_pos[f, j], axis=1)
    order = np.lexsort((valid, d))
    if mode == "B":
        # Keep a mild squad stagger in B so the range change is isolated from
        # the scheduler improvement in A/C.
        k = (j + (f // 2)) % min(4, len(order))
        return int(valid[order[k]])
    return int(valid[order[0]])


def run_plan(name: str, range_value: float, relaxed_scheduler: bool):
    end = float(sim["frames"] - 1) * dt
    states = np.zeros(nb, dtype=np.uint8)  # 3 AIMING, 4 DRAWING, 6 RECOVERING
    timers = np.zeros(nb, dtype=np.float64)
    targets = np.full(nb, -1, dtype=np.int32)
    next_allowed = np.zeros(nr, dtype=np.float64)
    pending = defaultdict(list)
    events = []
    controls = np.zeros((T.shape[0], nb, 12), dtype=np.float32)
    first_aim = None
    first_draw = None
    first_release = None
    first_hit = None
    for f in range(T.shape[0]):
        t = f * dt
        # release events are the only new projectile causes; impacts are
        # recorded after their physical flight time.
        for j, u in enumerate(blue):
            # Hold deployment and turning exactly to the V19 control timeline;
            # plans A/B/C only alter firing eligibility after the real AIMING
            # state begins.
            if t < float(actual_ready[j]):
                states[j] = 0; timers[j] = 0; targets[j] = -1
                continue
            if states[j] == 0:
                states[j] = 3; timers[j] = 0
                if first_aim is None: first_aim = t
            # recover -> aim; one shooter owns its state, no global clock.
            if states[j] == 6:
                timers[j] += dt
                if timers[j] < float(u["recoverSeconds"]):
                    continue
                states[j] = 3; timers[j] = 0; targets[j] = -1
                if first_aim is None: first_aim = t
            if states[j] == 3:
                timers[j] += dt
                # Targets with a pending impact/cooldown are excluded.  In A/C
                # this is the only reservation; no transient claimed map.
                reserved = np.zeros(nr, dtype=bool)
                for target, untils in pending.items():
                    if any(t < x for x in untils): reserved[target] = True
                alive = np.ones(nr, dtype=bool)
                valid = np.where((~reserved) & alive & (np.linalg.norm(red_pos[f] - blue_pos[f, j], axis=1) <= range_value))[0]
                if targets[j] < 0 or targets[j] in np.where(reserved)[0] or targets[j] not in valid:
                    picked = choose_target(j, f, valid, name)
                    targets[j] = -1 if picked is None else picked
                    if picked is None:
                        # Keep waiting in AIMING; a later frame may enter the
                        # range without inventing a teleport or global timer.
                        timers[j] = min(timers[j], float(u["aimSeconds"]))
                    else:
                        timers[j] = 0
                if targets[j] >= 0 and (relaxed_scheduler or timers[j] >= float(u["aimSeconds"])):
                    if relaxed_scheduler:
                        # Preserve the actual aim duration, but start counting
                        # from the first valid target rather than after target
                        # reservation churn.
                        pass
                    if timers[j] >= float(u["aimSeconds"]):
                        states[j] = 4; timers[j] = 0
                        first_draw = t if first_draw is None else first_draw
            elif states[j] == 4:
                timers[j] += dt
                target = int(targets[j])
                valid = target >= 0 and np.linalg.norm(red_pos[f, target] - blue_pos[f, j]) <= range_value
                if not valid:
                    states[j] = 3; timers[j] = 0; targets[j] = -1
                elif timers[j] >= float(u["drawSeconds"]):
                    flight = flight_seconds(j, target, f, float(C["arrowSpeed"]))
                    impact = t + flight
                    e = {"id": f"{name}-{len(events):05d}", "shooter": j, "shooterID": u["id"], "target": target, "targetID": red[target]["id"], "release": t, "impact": impact, "releaseDistance": float(np.linalg.norm(red_pos[f, target] - blue_pos[f, j])), "aimStart": t - float(u["drawSeconds"]) - float(u["aimSeconds"]), "drawStart": t - float(u["drawSeconds"]), "resolution": "IMPACT_IN_SHOT" if impact <= end else "IN_FLIGHT_AT_CUT"}
                    events.append(e); pending[target].append(impact + float(C["minHitInterval"])); next_allowed[target] = impact + float(C["minHitInterval"])
                    states[j] = 6; timers[j] = 0; targets[j] = -1
                    first_release = t if first_release is None else first_release
                    if first_hit is None and impact <= end: first_hit = impact
        for j, u in enumerate(blue):
            controls[f, j] = [states[j], timers[j], targets[j], -1, 0, 0, .64 if states[j] >= 4 else .10, 0, math.pi, math.pi, 1, len(events)]
    visible = [e for e in events if e["resolution"] == "IMPACT_IN_SHOT"]
    return {
        "plan": name, "range": range_value, "relaxedScheduler": relaxed_scheduler,
        "firstReady": float(np.nanmin(actual_ready)),
        "firstAim": first_aim, "firstDraw": first_draw, "firstRelease": first_release,
        "firstHit": first_hit, "safeEnd": end,
        "postHitWindow": None if first_hit is None else end - first_hit,
        "releases": len(events), "impacts": len(visible),
        "releaseHistogram": event_hist(events, "release", end),
        "impactHistogram": event_hist(visible, "impact", end),
        "releaseTimes": [e["release"] for e in events], "impactTimes": [e["impact"] for e in visible],
        "events": events, "controls": controls,
    }


base = baseline_metrics()
plans = [
    run_plan("A", float(C["archerRange"]), True),
    run_plan("B", float(C["archerRange"]) + 4.0, False),
    run_plan("C", float(C["archerRange"]) + 4.0, True),
]

summary = {
    "version": "V20-TIMELINE",
    "sourceVariant": "FINAL",
    "fixedRedBlueTrajectories": True,
    "camera": "V19-B (frozen for later clips)",
    "baseline": base,
    "plans": [{k: v for k, v in p.items() if k not in ("events", "controls", "releaseTimes", "impactTimes")} for p in plans],
    "theoretical": {
        "safeEnd": base["safeEnd"],
        "earliestEligibleRelease": base["firstEligibleRelease"],
        "earliestInterceptedHit": None if base["firstEligibleRelease"] is None else base["firstEligibleRelease"] + min(base["flightSamples"] or [0.0]),
        "upperBoundPostHit": None if base["firstEligibleRelease"] is None else base["safeEnd"] - (base["firstEligibleRelease"] + min(base["flightSamples"] or [0.0])),
    },
}
(OUT / "timeline-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
for p in plans:
    d = OUT / p["plan"]; d.mkdir(exist_ok=True)
    (d / "events.json").write_text(json.dumps(p["events"], indent=2), encoding="utf-8")
    p["controls"].tofile(d / "blue-control.f32")
print(json.dumps({"baseline": {k: base[k] for k in ["firstReady", "firstInRange", "firstEligibleRelease", "firstRelease", "firstHit", "safeEnd", "postHitWindow"]}, "plans": [{k: p[k] for k in ["plan", "range", "firstAim", "firstDraw", "firstRelease", "firstHit", "safeEnd", "postHitWindow", "releases", "impacts"]} for p in plans]}, indent=2))
