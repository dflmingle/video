import * as T from 'three';
// V18 camera: authored framing, never fitted to live bounds.
export function createBattleCamera(S,C,positions){
 const mode=new URLSearchParams(location.search).get('camera')||'A';
 const centers=[],fronts=[],defenses=[],desired=[],velocities=[];
 const smooth=(t,a,b)=>T.MathUtils.smootherstep(t,a,Math.max(a+.01,b));
 for(let f=0;f<S.frames;f++){
  const t=f/60,k=smooth(t,.72,Math.max(.9,C.duration-.16));
  const push=mode==='B'||mode==='PUSH';
  const z=push?T.MathUtils.lerp(-20,-4,k):-20;
  centers.push([0,z]);fronts.push([0,z]);defenses.push([0,25]);desired.push([0,z]);velocities.push([0,0]);
 }
 function apply(camera,t){
  const idx=Math.min(S.frames-1,Math.max(0,Math.round(t*60))),center=centers[idx];
  const push=mode==='B'||mode==='PUSH',k=push?smooth(t,.72,Math.max(.9,C.duration-.16)):0;
  const zoom=push?T.MathUtils.lerp(1.35,2.05,k):1.35;
  const offsetZ=C.cameraPosition[2]-C.cameraTarget[2];
  camera.position.set(center[0]+C.cameraTarget[0],C.cameraPosition[1],center[1]+offsetZ);camera.lookAt(center[0]+C.cameraTarget[0],0,center[1]);camera.fov=C.cameraFov;camera.zoom=zoom;
  camera.updateMatrixWorld(true);camera.updateProjectionMatrix();camera.projectionMatrix.elements[8]=C.cameraShiftX;camera.projectionMatrix.elements[9]=C.cameraShiftY;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  return{mode,center,zoom};
 }
 return{apply,mode,centers,fronts,defenses,desired,velocities};
}
