import * as T from 'three';

// Perspective-camera A/B only. No actor, projectile or live-bounds ownership.
// FIXED is an explicit alias for actual V21 A, never a silent preset fallback.
export function createBattleCamera(S, C, positions) {
  const requested = new URLSearchParams(location.search).get('camera') || 'A';
  const mode = requested === 'FIXED' ? 'A' : requested;
  if (!['A', 'B'].includes(mode)) throw new Error(`V22 camera must be A/B; received ${requested}`);
  const hold = Math.max(0, C.redChargeStart ?? C.redChargeStartTime ?? 0);
  const presets = {
    A: { openingZoom: 1.35, combatZoom: 2.05, openingZ: -20, combatZ: -4 },
    B: { openingZoom: 1.35, combatZoom: 2.5625, openingZ: -20, combatZ: -4 },
  };
  const P = presets[mode];
  const fps = C.simulationFps || 60;
  // Both A and B use the same absolute push schedule. A is the V21 baseline
  // camera; B changes only the combat zoom so its subject scale is a stable
  // 25% increase instead of changing the comparison timing when a red hold is
  // enabled in the V22 timeline.
  const start = .72;
  const finish = Math.max(start + .18, C.duration - .16);
  const span = finish - start;
  const centers = [], fronts = [], defenses = [], desired = [], velocities = [];
  const blueCount = S.blueCount;
  const yellow = S.units.map((u, i) => u.team === 'red' && u.color === 'yellow' ? i : -1).filter(i => i >= 0);
  const blend = t => T.MathUtils.smootherstep(t, start, finish);
  // Quintic curve has zero velocity and acceleration at both boundaries.
  const derivative = t => {
    const u = T.MathUtils.clamp((t - start) / span, 0, 1);
    return 30 * u * u * (1 - u) * (1 - u) / span;
  };
  const at = (f, i) => {
    const offset = (f * S.units.length + i) * 2;
    return [positions[offset], positions[offset + 1]];
  };
  for (let f = 0; f < S.frames; f++) {
    const t = f / fps, k = blend(t);
    const z = T.MathUtils.lerp(P.openingZ, P.combatZ, k);
    centers.push([0, z]); velocities.push([0, (P.combatZ - P.openingZ) * derivative(t)]);
    const front = yellow.map(i => at(f, i)).filter(p => p.every(Number.isFinite)).sort((a, b) => b[1] - a[1]).slice(0, 24);
    const blue = Array.from({ length: blueCount }, (_, i) => at(f, i)).filter(p => p.every(Number.isFinite)).sort((a, b) => a[1] - b[1]).slice(0, 72);
    const mean = a => a.length ? a.reduce((s, p) => [s[0] + p[0] / a.length, s[1] + p[1] / a.length], [0, 0]) : [0, 0];
    const redFront = mean(front), defense = mean(blue);
    fronts.push(redFront); defenses.push(defense);
    desired.push([redFront[0] * .6 + defense[0] * .4, redFront[1] * .6 + defense[1] * .4]);
  }
  function apply(camera, t) {
    const k = blend(t);
    const center = [0, T.MathUtils.lerp(P.openingZ, P.combatZ, k)];
    const zoom = T.MathUtils.lerp(P.openingZoom, P.combatZoom, k);
    const offsetZ = C.cameraPosition[2] - C.cameraTarget[2];
    camera.position.set(center[0] + C.cameraTarget[0], C.cameraPosition[1], center[1] + offsetZ);
    camera.lookAt(center[0] + C.cameraTarget[0], 0, center[1]);
    camera.fov = C.cameraFov; camera.zoom = zoom;
    camera.updateMatrixWorld(true); camera.updateProjectionMatrix();
    camera.projectionMatrix.elements[8] = C.cameraShiftX || 0;
    camera.projectionMatrix.elements[9] = C.cameraShiftY || 0;
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    return { mode, requested, center, zoom, projection: 'perspective', redChargeStart: hold };
  }
  return {
    apply, mode, centers, fronts, defenses, desired, velocities, preset: P,
    motionBounds: {
      maxCenterSpeed: 1.875 * Math.abs(P.combatZ - P.openingZ) / span,
      maxCenterAcceleration: (10 / Math.sqrt(3)) * Math.abs(P.combatZ - P.openingZ) / (span * span),
      maxZoomSpeed: 1.875 * Math.abs(P.combatZoom - P.openingZoom) / span,
      maxZoomAcceleration: (10 / Math.sqrt(3)) * Math.abs(P.combatZoom - P.openingZoom) / (span * span),
    },
  };
}
