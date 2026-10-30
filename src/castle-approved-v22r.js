// User confirmation: 2026-10-30, CastleExterior; hide Gird; fixed high view.
// Unity coordinates are preserved. Reflection below is a documented basis
// conversion in the scene-only inspection page, never an actor relocation.
export const approvedCastle = Object.freeze({
  environment: 'CastleExterior',
  source: 'scene',
  showGrid: false,
  width: 1440,
  height: 2160,
  camera: Object.freeze({ position: [0, 98, 65], target: [0, 0, 5], fov: 42, zoom: 1 }),
  nativeToPreview: Object.freeze([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1]),
});
