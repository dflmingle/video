import * as T from 'three';
// Solve once from authored limits. No per-frame bounds fitting or tracking.
export function createBattleCamera(S,C,positions){
 const mode=new URLSearchParams(location.search).get('camera')||'FIXED';
 const centers=[],fronts=[],defenses=[],desired=[],velocities=[];
 for(let f=0;f<S.frames;f++){
  const t=f/60,k=T.MathUtils.smootherstep(t,.35,Math.max(.36,C.duration-.18));
  let center=mode==='PUSH'?[0,C.cameraFixedCenterZ+(C.cameraPushCenterZ-C.cameraFixedCenterZ)*k]:[0,C.cameraFixedCenterZ];
  if(mode==='ARCHERS')center=[17,20];
  if(mode==='REDLOCAL'){
   const f=Math.min(S.frames-1,Math.round(t*60)),ids=S.units.map((u,i)=>({u,i})).filter(({u,i})=>i>=S.blueCount&&u.army===2&&u.squadRow===0&&u.squadCol===1).slice(0,20);
   center=[ids.reduce((a,{i})=>a+positions[(f*S.units.length+i)*2],0)/ids.length,ids.reduce((a,{i})=>a+positions[(f*S.units.length+i)*2+1],0)/ids.length];
  }
  centers.push(center);fronts.push([0,0]);defenses.push([0,0]);desired.push(center);velocities.push([0,0]);
 }
 function apply(camera,t){
  const k=T.MathUtils.smootherstep(t,.35,Math.max(.36,C.duration-.18));
  const center=centers[Math.min(S.frames-1,Math.max(0,Math.round(t*60)))];
  const offset=new T.Vector3(0,C.cameraPosition[1]-C.cameraTarget[1],C.cameraPosition[2]-C.cameraTarget[2]);
  camera.position.set(center[0],offset.y,center[1]+offset.z);camera.lookAt(center[0],0,center[1]);camera.fov=C.cameraFov;
  camera.zoom=mode==='PUSH'?T.MathUtils.lerp(C.cameraZoom,C.cameraPushZoom,k):C.cameraZoom;
  if(mode==='ARCHERS'||mode==='REDLOCAL')camera.zoom=9;
  camera.updateMatrixWorld(true);camera.updateProjectionMatrix();camera.projectionMatrix.elements[8]=C.cameraShiftX;camera.projectionMatrix.elements[9]=C.cameraShiftY;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  return{mode,center,zoom:camera.zoom};
 }
 return{apply,mode,centers,fronts,defenses,desired,velocities};
}
