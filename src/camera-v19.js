import * as T from 'three';
// V19 camera-only A/B/C/D comparison. Simulation and actor data are unchanged.
export function createBattleCamera(S,C,positions){
 const mode=new URLSearchParams(location.search).get('camera')||'A';
 const centers=[],fronts=[],defenses=[],desired=[],velocities=[];
 const presets={
  A:{openingZoom:1.35,combatZoom:2.05,openingZ:-20,combatZ:-4},
  B:{openingZoom:1.35,combatZoom:2.5625,openingZ:-20,combatZ:-4},
  C:{openingZoom:1.35,combatZoom:3.075,openingZ:-20,combatZ:-4},
  D:{openingZoom:1.35,combatZoom:3.5875,openingZ:-20,combatZ:-4}
 };
 const P=presets[presets[mode]?mode:'A'];
 const smooth=(t,a,b)=>T.MathUtils.smootherstep(t,a,Math.max(a+.01,b));
 for(let f=0;f<S.frames;f++){
  const t=f/60,k=smooth(t,.72,Math.max(.9,C.duration-.16));
  const z=T.MathUtils.lerp(P.openingZ,P.combatZ,k);
  centers.push([0,z]);fronts.push([0,z]);defenses.push([0,25]);desired.push([0,z]);velocities.push([0,0]);
 }
 function apply(camera,t){
  const idx=Math.min(S.frames-1,Math.max(0,Math.round(t*60))),center=centers[idx];
  const k=smooth(t,.72,Math.max(.9,C.duration-.16));
  const zoom=T.MathUtils.lerp(P.openingZoom,P.combatZoom,k);
  const offsetZ=C.cameraPosition[2]-C.cameraTarget[2];
  camera.position.set(center[0]+C.cameraTarget[0],C.cameraPosition[1],center[1]+offsetZ);camera.lookAt(center[0]+C.cameraTarget[0],0,center[1]);camera.fov=C.cameraFov;camera.zoom=zoom;
  camera.updateMatrixWorld(true);camera.updateProjectionMatrix();camera.projectionMatrix.elements[8]=C.cameraShiftX;camera.projectionMatrix.elements[9]=C.cameraShiftY;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  return{mode,center,zoom};
 }
 return{apply,mode,centers,fronts,defenses,desired,velocities,preset:P};
}
