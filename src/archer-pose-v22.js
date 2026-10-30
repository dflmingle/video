// No global clock drives walking or firing. Every sample comes from the
// authoritative member control row; native snapshot interpolation stays intact.
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = x => {const q = clamp(x);return q * q * (3 - 2 * q);};
export function resolveArcherPose({bc, speed = 0, unit = {}, time = 0,
                                   attackDuration = 1, moveDuration = 1}) {
  const state = Math.round(bc[0]), timer = Math.max(0, bc[1] || 0);
  const gaitPhase = ((bc[4] || 0) % 1 + 1) % 1;
  const phase = clamp(Number.isFinite(bc[6]) ? bc[6] : 0, 0, .999999);
  const progress = clamp(bc[10] || 0);
  const yaw = Number.isFinite(bc[8]) ? bc[8] : Math.PI;
  let action = 'idle', phaseFraction = (unit.phase || 0) % 1;
  let idle = 1, move = 0, attack = 0;
  const walkAmount = smooth(speed / Math.max(unit.walkSpeed || 5, .1));
  if (state === 1 || state === 2) {
    action = 'move';phaseFraction = gaitPhase;
    move = walkAmount;idle = 1 - move;
  } else if (state === 7) {
    // Stop/turn uses a still planted idle pose. The upcoming aiming state
    // blends in the native attack clip instead of jumping from a walk frame.
    phaseFraction = (unit.phase || 0) % 1;
  } else if (state >= 3 && state <= 6) {
    action = 'attack';phaseFraction = state === 5 ? .64 : phase;
    attack = state === 3 ? smooth(timer / Math.max(.07, unit.aimSeconds || .1)) : 1;
    idle = 1 - attack;
  }
  return {
    action, phaseFraction, yaw,
    moveWeight: action === 'move' ? move : 1,
    gaitPhase, state, stateProgress: progress,
    // Root renderer crossfades baked idle/move/attack snapshots with these
    // weights; it must not replace the independent native pose fraction.
    transitionWeights: {idle, move, attack},
    idleWeight: idle, walkWeight: move, attackWeight: attack,
    idlePhaseFraction: (unit.phase || 0) % 1,
    movePhaseFraction: gaitPhase,
    attackPhaseFraction: state === 5 ? .64 : phase,
    clock: action === 'move' ? gaitPhase * moveDuration : phaseFraction * attackDuration,
    releaseEventId: Math.round(bc[11] ?? -1),
    releaseTime: bc[3] ?? -10,
    // Exposed for diagnostics; time is not an animation phase source.
    sampleTime: time,
  };
}
