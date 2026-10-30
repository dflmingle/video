# V22 integrated recorded-data review

Date: 2026-10-29. This snapshot reads actual V22-B and V22-C after the 1.0-second red hold and native-hand origin metadata fix. It is not the prospective timeline solver. Production files are read-only.

## Reproduce

```powershell
python tools/analyze_v22_integrated.py --source-root C:/Users/89trillion/PveMontageShot01V22
```

Outputs: result.json; quarter-second-arrow-counts.csv; each variant first20-events.csv and release-events.csv under output/v22-integrated-review. Source hashes and timestamps are recorded.

## Baseline identity

Actual V21 baseline is variants/V21, version V21-INTEGRATED: 98 arrows, 55 resolved impacts, 140 frames. The script explicitly checks that fingerprint. V20-B is a separate V20-DIAGNOSTIC-B auxiliary diagnostic (133 arrows, 59 nominal endpoints, zero resolved damage); it is never labelled V21. Its missing walking states also make locomotion phase comparisons invalid.

## Actual event timeline

| Variant | First AIMING | First DRAWING | First release | First resolved hit | Safe end | Post-hit window | Arrows / resolved hits |
|---|---:|---:|---:|---:|---:|---:|---:|
| V21 | 1.3333 | 1.4000 | 1.5833 | 1.8833 | 2.3167 | 0.4333 | 98 / 55 |
| V22-B | 1.7833 | 2.4500 | 2.6667 | 2.9667 | 3.5500 | 0.5833 | 82 / 48 |
| V22-C | 1.7833 | 2.3333 | 2.5500 | 2.8667 | 3.5833 | 0.7167 | 93 / 61 |

B waits for range-valid aiming; C can aim before entering range but cannot draw/release at an invalid target. In C, the first target assignment moves from AIMING to DRAWING within the same fixed step, so first sampled AIMING-with-target (2.9 s) is not its first acquisition (2.3333 s). The script records these independently. Event aimStart is reconstructed from drawStart minus individual aim duration and must not be treated as a state-entry timestamp.

The simulation safe end and last encoded renderer sample differ by 1/60 s because renderAt clamps t to duration - 1/fps. Encoded-boundary counts are separately output; no last-frame event is silently declared visible.

## Quarter-second arrow activity

| Time interval | B releases / hits | C releases / hits |
|---|---:|---:|
| 2.25-2.500 | 0 / 0 | 0 / 0 |
| 2.50-2.750 | 5 / 0 | 10 / 0 |
| 2.75-3.000 | 16 / 2 | 25 / 6 |
| 3.00-3.250 | 27 / 19 | 19 / 19 |
| 3.25-3.500 | 28 / 22 | 27 / 24 |
| 3.50-3.583 | 6 / 5 | 12 / 12 |

After first release there is no quarter-second empty release bin. Maximum individual inter-release gap: B .0667 s, C .0500 s. This does not prove visually sufficient density.

## Independence and real position offsets

Within squad 0, pairwise equality of native attack clip frame among pairs both drawing/releasing/recovering: V21 4.47%, B 3.78%, C 3.61%. V20 diagnostic 51.38% is recorded only as a different auxiliary baseline. V22 walking pair equality is 2.97%. Common AIMING/idle states are legitimate and not automatically synchronization failures.

Squad 0 actual standing position offset from nominal defense slot: B/C median .1875 world units, p90 about .226, maximum about .385. These are measured integrated world positions, not initialization parameters or rendered-only offsets. Detailed first-entry distributions are in JSON; first 20 archers are written to CSV, including state, target, independent phase, world position and actual slot error.

## Central firing failure: target reservation starvation

All 252 V22 archers eventually become ready and geometrically in range, but B has only 66 unique firing archers and C 69. Group 3 has zero draw entries and zero releases; it is not honest to explain that as never entering range. Earliest central ready+range is 3.05 s in both variants. Remaining time has B median .3833/max .5000 s and C median .4083/max .5333 s, enough for some individual aim+draw durations.

Read-only replay of production update_fire, using recorded movement rows, diagnoses:

| Central group 3 | B | C |
|---|---:|---:|
| Ready/in-range member-frames | 857 | 906 |
| All geometric targets reserved | 569 (66.4%) | 342 (37.7%) |
| Remaining targets all claimed | 288 (33.6%) | 564 (62.3%) |
| Calls with any available target | 0 | 0 |
| Draw entries | 0 | 0 |

Replay reproduces all central state/target samples. Across all squads there are 2 B / 3 C boundary sample mismatches from float32 trajectory reconstruction; JSON gives exact examples. Do not present that diagnostic as a bit-identical full re-simulation. No movement was replayed or modified.

Cause: the earliest ready wings acquire and reacquire exclusive AIMING claims and future hit reservations. Newly eligible squads find no unclaimed target. Minimal correction: preserve all DRAWING and in-flight commitments, but allocate AIMING leases fairly by squad and prioritize squads not yet represented, without delaying the first ready wing arrow. Do not delete pending arrows or fake central releases. This report is the pre-fairness snapshot; rerun after the separate production fix.

## Release-to-render ABI and origin correction

The audit executes the actual production JS resolveArcherPose helper on recorded rows, including every release frame. It changes only global time and verifies action, independent native phase, yaw and release ID remain stable. It checks control f32 against npy, release state=5, phase=.64, event ID and release timestamp, plus actual renderer wiring through per-instance phase/weight attributes and shader interpolation. This is stronger than merely finding a field name in source.

Original arrow origins were rotated toward predicted impact targets, while rendered archers face bc[8]. Before root metadata correction, native hand origin error was B median .059716/max .113709 and C median .055368/max .110295 world units. Facing-versus-predicted-target angle max was .220779/.214124 radians. After correction, every B/C origin exactly matches native bowReleaseLocal rotated by actual release facing (error 0); event times and trajectories remain the same.

Existing browser capture rows are checked against native phase, state and release ID only when duration and timestamps are current. A changed simulation metadata timestamp marks older captures stale; stale footage is not silently counted as fresh evidence. The script cannot certify an encoded MP4 from browser logs.

## Theoretical range/window ceiling

On the actual recorded paths, first geometric range entry is 2.3333 s for both V22 variants. An optimistic bound with instant preparation, no aim/draw delay, nearest-target availability, horizontal interception and one-frame slack yields post-hit ceilings about .928 s (B) and .965 s (C). Even zero-flight geometry-only ceilings are only 1.233/1.267 s. Therefore 1.5-2 s of post-hit action cannot be claimed under these unchanged paths/range/safe ends. These are necessary bounds, not achievable production schedules.

Observed horizontal arrow origin-to-destination distance divided by flight duration exceeds configured arrowSpeed=72 for some events (about 83-84). The bound uses the observed upper value; it does not pretend the existing curved renderer travels at constant configured speed. This remains a trajectory-speed consistency issue.

## Status and limits

Recorded-data/ABI/safety checks pass after origin correction. Conservative interframe surface gaps: V21 >=4.612, B >=4.316, C >=4.093 for required4.0. Actual unresolved product issues remain: central firing starvation, short post-hit window, and configured-versus-rendered arrow travel speed. Numeric PASS does not declare these creative requirements satisfied.

No normal-speed whole encoded MP4 visual acceptance was performed by this audit. No scene, camera, red movement, battle data or renderer was modified. Final visual review belongs to the main integration/render workflow.

## Fair scheduler correction: isolated verification

A reorder-only AIMING experiment was insufficient: central C could enter DRAWING
four times but never released before the safe cut. The first wing wave had
already committed those front targets to in-flight arrows plus .45-second
post-impact reservation. Those commitments cannot legally be stolen.

`Archers._allocate_aiming` now balances squad release-plus-draw load, keeps
individual progress and short same-squad lease priority, and preserves DRAWING
locks. `Archers._opportunity_targets` preserves at most one real target for each
as-yet unrepresented interior squad. This is a planning hold, not out-of-range
target acquisition/drawing/release. All actual range, target and native release
checks remain. The earliest wing opportunity is exempt so its first arrow is
not delayed. Existing in-flight arrows are not changed or deleted.

Run the separate isolation test:

```powershell
python tools/test_archer_fairness_v22.py --source-root C:/Users/89trillion/PveMontageShot01V22
```

It holds actual recorded red/blue paths and baseline readiness fixed, runs the
new production scheduler with bounded independent target-facing yaw, resolves
scheduled individual impacts, and repeats deterministically. This is not a full
combat re-simulation or a rendered acceptance claim.

| Isolation outcome | B | C |
|---|---:|---:|
| First release before/after | 2.666667 / 2.666667 | 2.550000 / 2.550000 |
| Central draw entries before/after | 0 / 1 | 0 / 4 |
| Central releases before/after | 0 / 1 | 0 / 1 |
| Total releases before/after | 82 / 76 | 93 / 99 |
| Squads with any release after | 7 / 7 | 7 / 7 |
| DRAWING target changes | 0 | 0 |

Remaining limitation: one central release proves removal of total starvation,
not sufficient full central firepower or a longer engagement. Root must rebuild
the full simulation, run the recorded-data analysis, and recapture actual native
animations after merging. Earlier capture files are not evidence of this change.
