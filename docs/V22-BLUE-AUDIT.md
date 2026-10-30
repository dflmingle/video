# V22 blue behavior and rendering interface audit

Scope: blue archers only. Worktree `PveMontageShot01V22-blue`, branch
`v22-blue`. No camera, builder, red movement, response-controller, terrain or
model files changed. Tests only write `output/v22-blue-tests`.

## Confirmed V18–V21 causes

- `archers_v18.py::move`: the integration variable `step` is normalized path
  progress, but `walkPhase += step / blueStride` treats it as world distance.
  For the 7.5-unit deployment this underplays gait by about the path length.
- `archers_v18.py::move`: `position = _path(progress)` owns movement until a
  `progress >= .999` branch assigns the endpoint exactly. The final direct
  assignment bypasses acceleration and settling; it is not spring motion.
- The previous turn phase does not produce a dedicated state transition.
  `facingYaw = pi` replaces rotation each update. The renderer has a state-7
  branch, but the controller never generates it.
- `archers_v21.py`: stable slot offsets are at most .0694 world units (less
  than one screen pixel in the old composition). They only alter endpoints;
  they provide no elastic response state and no meaningful attacking stance.

## Replacement

`tools/archers_v22.py::move` is the only position integrator. Every member has
its own position, velocity, braking, yaw, action timer and target. Braking uses
remaining distance; acceleration follows a bounded damped velocity error.
No normal frame assigns a path point or endpoint directly to position.

The authored U and first-frame coordinates are unchanged. The moving goal is
the original defense slot plus a deterministic personal offset. Idle offset
is .075–.1 times original spacing; attacking offset is .20–.245 times spacing.
The attacking weight ramps over .333 seconds. These are stable member targets,
not per-frame random noise. The damped integrator also consumes external
`responseOffsets`, bounded to .38 spacing. Response is therefore not a second
world-position writer.

`_safe_velocity` queries local pairs using a cKDTree and projects predicted
next-step separation constraints into velocity before the one position
integration. It includes waiting and settled members as occupied neighbors.
Minimum personal separation is .615 world units. This is local pair constraint
projection, not a claim of full ORCA or general navigation.

States remain ABI-compatible: 0 WAITING, 1 MOVING, 2 ARRIVING, 3 AIMING,
4 DRAWING, 5 RELEASING, 6 RECOVERING, 7 TURNING. Real arrival enters TURNING;
bounded yaw and independent settling time gate AIMING. Target lock, completed
draw and actual range gate RELEASING. That state and arrow spawn occur in the
same fixed tick at native attack phase .64. `releaseEventId` uses the actual
event ID, not a separately inferred animation event.

## Builder and response integration contract

Import `Archers` from `archers_v22`; use existing constructor `(units, C)`.
Before `move(t, dt)`, set `archers.redPositions` to current red positions and
copy B's target offset array into `archers.responseOffsets`. Both arrays use
world X/Z coordinates. Call `update_fire` after movement as before. No builder
should add response offsets to emitted positions again.

All blue times are absolute simulation times. There is no hardcoded lead-in
or red hold. Root builder owns any hold before red charge. `C.preAim` defaults
false; only test C should enable it. It allows aiming preparation outside range
but never generates an arrow until a real valid target enters range.

The first 12 control columns are unchanged:

| Index | Field | V22 meaning |
|---|---|---|
| 0 | state | IDs above |
| 1 | timer | member state elapsed seconds |
| 2 | target | red local index or -1 |
| 3 | lastRelease | actual absolute release time |
| 4 | walkPhase | integrated actual distance / stride, modulo one |
| 5 | turnPhase | bounded settling/turn progress |
| 6 | actionPhase | native attack sample fraction, release .64 |
| 7 | moveSpeed | actual world distance per second, corrected from normalized units |
| 8 | facingYaw | integrated yaw |
| 9 | targetYaw | actual target/threat yaw |
| 10 | stateProgress | independent member progress |
| 11 | releaseEventId | actual event ordinal, -1 before release |

`record_combat` is a compatibility no-op: B owns combat-response interpretation.

## Rendering helper

`src/archer-pose-v22.js::resolveArcherPose` reads the member row and returns
`action`, independent `phaseFraction`, `moveWeight`, integrated `yaw`, and
`transitionWeights` for native idle/move/attack snapshots. Moving weight uses
actual world speed. TURNING plants an idle pose, and AIMING progressively blends
native attack into it. Root must crossfade baked snapshots using those weights;
the helper alone does not change the renderer. Passing global time 2 or 500
with the same member row produces identical animation phase.

## Executed validation

Command: `python tools/test_archers_v22.py`.

- 252 original blue members, all original first-frame coordinates exact.
- Four six-second fixed-step runs: normal twice, response targets, test-C preaim.
- Identical seed/input replays produce identical position/control SHA256.
- Gait phase increment equals actual integrated displacement/stride exactly;
  maximum error 0.0. First 20 members retain 20 distinct gait phases.
- Minimum pair separation .615 in normal and response runs.
- Peak frame displacement below .16; maximum recorded speed 7.010 world units/s.
- Real deployment arrivals 1.600–2.817 seconds; no endpoint assignment.
- Same-squad first-20 speed std at 1 second .316 world units/s.
- Stationary-target six-second diagnostic: 1,318 actual release events;
  first release 2.117 seconds. This is a diagnostic target field, not a claim
  about final battle arrow count or final battle timing.
- Every release event occurs in state 5 with phase .64 and matching event ID,
  after individual draw time and within effective range.
- State 7 appears in recorded state timelines.
- Shooting slot settling error P50/P95 approximately 0/.0372 world units.
- 40 JavaScript pose-helper checks: phase independent of global clock,
  transition weights sum to one, member gait and yaw preserved, release .64.

The original short battle cannot show all blue members' multiple firing cycles:
the latest member arrives at 2.817 seconds before turn/aim/draw. Root must assess
the externally controlled lead-in/hold and safety cut together. This module does
not solve that by increasing walk speed or faking out-of-range hits.

## Remaining acceptance

Native snapshot crossfade still requires root integration and encoded-video
viewing. No MP4 or normal-speed visual acceptance was performed in this worktree.
The tests establish behavior, dimensions, spacing and release causality; they
do not establish final close-up leg/arm visual quality or formal camera quality.
