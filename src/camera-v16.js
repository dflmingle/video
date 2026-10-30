import * as T from 'three';
// Schedule at fixed 60 Hz; sampling it is independent of playback/seek order.
// No bounds fit, auto zoom, red-centroid tracking or wall-clock accumulation.
export function createBattleCamera(S,C,positions){
 const n=S.units.length,nb=S.blueCount,mode=new URLSearchParams(location.search).get('camera')||C.cameraMode;
 const fronts=[],defenses=[],desired=[],centers=[],velocities=[],dt=1/60;
 const smoothTime=C.cameraFollowSmoothTime||.8,maxSpeed=C.cameraFollowMaxSpeed||6;
 function frontAt(f){
  const t=f/60,ids=S.units.map((u,i)=>({u,i})).filter(({u,i})=>i>=nb&&u.army===2&&(u.deathTime===null||u.deathTime>t));
  ids.sort((a,b)=>positions[(f*n+b.i)*2+1]-positions[(f*n+a.i)*2+1]);
  const top=ids.slice(0,Math.max(18,Math.ceil(ids.length*.20)));return new T.Vector2(top.reduce((s,{i})=>s+positions[(f*n+i)*2],0)/top.length,top.reduce((s,{i})=>s+positions[(f*n+i)*2+1],0)/top.length);
 }
 const fixed=new T.Vector2(0,C.cameraFixedCenterZ??-6),velocity=new T.Vector2();let current=fixed.clone();
 for(let f=0;f<S.frames;f++){
  const front=frontAt(f),blue=new T.Vector2();for(let i=0;i<nb;i++){blue.x+=positions[(f*n+i)*2];blue.y+=positions[(f*n+i)*2+1]}blue.multiplyScalar(1/Math.max(1,nb));
  const target=front.clone().lerp(blue,.35);target.x=T.MathUtils.clamp(target.x,-1.2,1.2);target.y=T.MathUtils.clamp(target.y,-5,-2);
  if(mode==='FOLLOW'&&f){
   // Critically damped spring; limit desired displacement and final speed.
   const omega=2/smoothTime,exp=Math.exp(-omega*dt),change=current.clone().sub(target);change.clampLength(0,maxSpeed*smoothTime);
   const adjusted=current.clone().sub(change),temp=velocity.clone().addScaledVector(change,omega).multiplyScalar(dt);
   const next=adjusted.clone().add(change.add(temp).multiplyScalar(exp));velocity.sub(temp.multiplyScalar(omega)).multiplyScalar(exp).clampLength(0,maxSpeed);
   const move=next.clone().sub(current).clampLength(0,maxSpeed*dt);current.add(move);
  }else if(mode!=='FOLLOW'){current=fixed.clone();velocity.set(0,0)}
  fronts.push(front.toArray());defenses.push(blue.toArray());desired.push(target.toArray());centers.push(current.toArray());velocities.push(velocity.toArray());
 }
 function sample(t,list){const x=T.MathUtils.clamp(t*60,0,S.frames-1),a=Math.floor(x),b=Math.min(S.frames-1,a+1),w=x-a;return list[a].map((v,i)=>v*(1-w)+list[b][i]*w)}
 function apply(camera,t){
  const center=sample(t,centers),offset=new T.Vector3(0,C.cameraPosition[1]-C.cameraTarget[1],C.cameraPosition[2]-C.cameraTarget[2]);
  camera.position.set(center[0]+offset.x,offset.y,center[1]+offset.z);camera.lookAt(center[0],0,center[1]);camera.fov=C.cameraFov;camera.zoom=C.cameraZoom;camera.updateMatrixWorld(true);camera.updateProjectionMatrix();
  camera.projectionMatrix.elements[8]=C.cameraShiftX;camera.projectionMatrix.elements[9]=C.cameraShiftY;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
  return{mode,center,zoom:camera.zoom,front:sample(t,fronts),blue:sample(t,defenses),desired:sample(t,desired)};
 }
 return{apply,mode,centers,fronts,defenses,desired,velocities};
}
