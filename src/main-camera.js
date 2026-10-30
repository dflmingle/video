import {createBattleCamera as createBattleCameraV19} from './camera-v19.js';
import {createBattleCamera as createBattleCameraV22} from './camera-v22.js';
import * as T from 'three';import {loadArmies} from './assets-v17.js';
const variant=new URLSearchParams(location.search).get('variant')||'A',base='/variants/'+variant+'/',isV22=variant.startsWith('V22');
const {addEnvironment}=await import((variant.startsWith('V21')||isV22)?'./environment-v21.js':'./environment-v11.js');
const C=await fetch(base+'params.json').then(r=>r.json()),S=await fetch(base+'simulation.json').then(r=>r.json());
const load=async p=>new Float32Array(await fetch(base+p).then(r=>r.arrayBuffer()));
const [pos,hitTimes,gait]=await Promise.all([load('trajectories.f32'),load('hit-times.f32'),load('gait-distance.f32')]);
const blueControl=await load('blue-control.f32');
const BLUE_CONTROL_STRIDE=Math.max(4,Math.round(blueControl.length/(S.frames*S.blueCount)));
const [redControl,gaitCycles]=await Promise.all([load('red-control.f32'),load('gait-cycles.f32')]);
function controlAt(t,j){const f=T.MathUtils.clamp(t*C.simulationFps,0,S.frames-1),a=Math.floor(f),b=Math.min(S.frames-1,a+1),w=f-a;return Array.from({length:10},(_,k)=>redControl[(a*S.redCount+j)*10+k]*(1-w)+redControl[(b*S.redCount+j)*10+k]*w)}
const query=new URLSearchParams(location.search);let motionData=null;if(query.has('motionOnly')){const [mp,mg]=await Promise.all([load('motion-trajectories.f32'),load('motion-gait-distance.f32')]);motionData={pos:mp,gait:mg};}
const capture=query.has('capture');document.body.classList.toggle('capture',capture);
const renderer=new T.WebGLRenderer({canvas:document.querySelector('#view'),antialias:true,preserveDrawingBuffer:true});renderer.setSize(C.width,C.height);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
const scene=new T.Scene();scene.background=new T.Color(0xd1c3a8);scene.add(new T.HemisphereLight(0xfff3de,0x596b56,1.7));const sun=new T.DirectionalLight(0xffecd0,2.4);sun.position.set(-25,60,25);scene.add(sun);
const camera=new T.PerspectiveCamera(C.cameraFov,C.width/C.height,.1,600);camera.position.fromArray(C.cameraPosition);camera.lookAt(...C.cameraTarget);camera.updateMatrixWorld(true);
// Build a camera schedule from current occupied bounds; preserve all armies
// and the U. Use deterministic low-pass values, never wall-clock accumulation.
const battleCamera=(isV22?createBattleCameraV22:createBattleCameraV19)(S,C,pos),cameraSchedule=battleCamera.centers;
function setCamera(t){window.cameraState=battleCamera.apply(camera,t)}
window.environmentAudit=await addEnvironment(scene);const armies=await loadArmies(scene,C);window.assetAudit=armies.audit;const nb=S.blueCount,n=S.units.length,dummy=new T.Object3D();
const shadows=new T.InstancedMesh(new T.CircleGeometry(.38,10),new T.MeshBasicMaterial({color:0x293c24,transparent:true,opacity:.23,depthWrite:false}),n);shadows.rotation.x=-Math.PI/2;shadows.frustumCulled=false;scene.add(shadows);
const arrowMesh=new T.InstancedMesh(new T.CylinderGeometry(.052,.052,1,6),new T.MeshBasicMaterial({color:0x493321}),2048),heads=new T.InstancedMesh(new T.ConeGeometry(.10,.27,4),new T.MeshBasicMaterial({color:0x303a3e}),2048),trails=new T.InstancedMesh(new T.CylinderGeometry(.040,.040,1,4),new T.MeshBasicMaterial({color:0xf7e8c8,transparent:true,opacity:.20,depthWrite:false}),6144),sparks=new T.InstancedMesh(new T.OctahedronGeometry(.13),new T.MeshBasicMaterial({color:0xffecd0}),4096);
const feathers=new T.InstancedMesh(new T.ConeGeometry(.16,.27,3,1,true),new T.MeshBasicMaterial({color:0xf5ecd7,side:T.DoubleSide}),2048);feathers.frustumCulled=false;scene.add(feathers);
for(const mesh of [arrowMesh,heads,trails,sparks]){mesh.frustumCulled=false;scene.add(mesh)}
const diag=new T.Group();scene.add(diag);const lines=[];for(let j=0;j<nb;j++){const u=S.units[j];lines.push(new T.Vector3(u.start[0]-.14,.04,u.start[1]-C.blueAdvance),new T.Vector3(u.start[0]+.14,.04,u.start[1]-C.blueAdvance))}
diag.add(new T.LineSegments(new T.BufferGeometry().setFromPoints(lines),new T.LineBasicMaterial({color:0x42c6ff})));
const sl=new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(-25,.04,5),new T.Vector3(25,.04,5)]),new T.LineDashedMaterial({color:0xcb5635,dashSize:.4,gapSize:.4}));sl.computeLineDistances();diag.add(sl);
function sample(t,i,arr,dim=2){const f=T.MathUtils.clamp(t*C.simulationFps,0,S.frames-1),a=Math.floor(f),b=Math.min(S.frames-1,a+1),w=f-a;if(dim===1)return arr[a*n+i]*(1-w)+arr[b*n+i]*w;return[arr[(a*n+i)*2]*(1-w)+arr[(b*n+i)*2]*w,arr[(a*n+i)*2+1]*(1-w)+arr[(b*n+i)*2+1]*w]}
const row=(t,i)=>sample(t,i,motionData?.pos||pos),yAxis=new T.Vector3(0,1,0);
function arrowPoint(e,t){const f=T.MathUtils.clamp((t-e.release)/(e.impact-e.release),0,1);return new T.Vector3(e.origin[0]*(1-f)+e.destination[0]*f,e.origin[1]*(1-f)+e.destination[1]*f+4*e.arc*f*(1-f),e.origin[2]*(1-f)+e.destination[2]*f)}
function segment(mesh,i,a,b,width=1){const d=b.clone().sub(a);dummy.position.copy(a).add(b).multiplyScalar(.5);dummy.quaternion.setFromUnitVectors(yAxis,d.clone().normalize());dummy.scale.set(width,d.length(),width);dummy.updateMatrix();mesh.setMatrixAt(i,dummy.matrix)}
function renderAt(t,{diagnostics=false}={}){
 t=T.MathUtils.clamp(t,0,C.duration-1/C.fps);setCamera(t);const combat=!C.previewOnly&&!(new URLSearchParams(location.search).has('motionOnly'));const motionPos=motionData?.pos||pos;diag.visible=diagnostics;for(const b of armies.batches.values())b.n=0;let sn=0,an=0,hn=0,tn=0,flashes=0,nocked=0;
 const frame=Math.min(S.frames-1,Math.round(t*C.simulationFps));const behavior=[];
 for(let i=0;i<n;i++){
  const u=S.units[i],p=row(t,i),before=row(Math.max(0,t-.035),i),vel=[(p[0]-before[0])/.035,(p[1]-before[1])/.035],speed=Math.hypot(...vel),distance=sample(t,i,motionData?.gait||gait,1),a=armies.audit[u.model];let action='idle',clock=t+u.phase,yaw=i<nb?Math.PI:0,lean=0,phaseFraction=null;
  const hitAge=i<nb||!combat?10:t-hitTimes[frame*S.redCount+i-nb],ctrl=i>=nb?controlAt(t,i-nb):null;
  let memberState='WAIT',currentEvent=null,bluePhase=null,blueWalkPhase=null,blueFacing=null,blueTargetYaw=null,blueProgress=null,blueReleaseId=null;
  if(i<nb){
   const bc=Array.from({length:BLUE_CONTROL_STRIDE},(_,k)=>blueControl[(frame*nb+i)*BLUE_CONTROL_STRIDE+k]),state=Math.round(bc[0]),timer=bc[1],target=Math.round(bc[2]);
   memberState=['WAITING','MOVING','ARRIVING','AIMING','DRAWING','RELEASING','RECOVERING','TURNING'][state]||'WAIT'; bluePhase=Number.isFinite(bc[6])?bc[6]:null; blueWalkPhase=Number.isFinite(bc[4])?bc[4]:null; blueFacing=Number.isFinite(bc[8])?bc[8]:null; blueTargetYaw=Number.isFinite(bc[9])?bc[9]:null; blueProgress=Number.isFinite(bc[10])?Math.min(1,Math.max(0,bc[10])):null; blueReleaseId=Number.isFinite(bc[11])?Math.round(bc[11]):null;
   if(state===1||state===2){const arrivalProgress=state===2?T.MathUtils.clamp(timer/.16,0,1):0;action='move';clock=(((bc[4]??(distance/C.blueStride+u.phase))%1)+arrivalProgress*.035)*a.clips.move.duration;lean=.045*Math.min(1,speed/4)*(1-arrivalProgress*.85)} else if(state===7){action='move';clock=(.08+(blueProgress??0)*.04)*a.clips.move.duration;lean=0;yaw=blueFacing??Math.PI}
   else if(state>=3){
    if(Number.isFinite(blueTargetYaw)){yaw=blueTargetYaw}else if(target>=0){const goal=row(t,nb+target);yaw=Math.atan2(goal[0]-p[0],goal[1]-p[1])}
    let e=null;for(const k of S.shooterEvents[i]){const v=S.events[k];if(t>=v.aimStart&&t<v.release+u.recoverSeconds+.04)e=v}
    if(e){currentEvent=e.id;yaw=Math.atan2(e.destination[0]-p[0],e.destination[2]-p[1])}
    action='attack';phaseFraction=Number.isFinite(bc[6])?Math.min(.999,Math.max(0,bc[6])):(state===3?.10+.03*(blueProgress??0):state===4?.12+.52*(blueProgress??Math.min(1,timer/u.drawSeconds)):state===5?.64:.64+.359*(blueProgress??Math.min(1,timer/u.recoverSeconds)));
    if(state===4){const ix=Math.min(a.clips.attack.phases-1,Math.floor(phaseFraction*a.clips.attack.phases)),loc=a.poseAnchors.attack[ix].leftHand;const h=new T.Vector3(p[0]+loc[0]*Math.cos(yaw)+loc[2]*Math.sin(yaw),loc[1],p[1]-loc[0]*Math.sin(yaw)+loc[2]*Math.cos(yaw)),d=new T.Vector3(Math.sin(yaw),.03,Math.cos(yaw));segment(arrowMesh,an++,h.clone().addScaledVector(d,-.4),h.clone().addScaledVector(d,.6));nocked++}
   }
  }else if(combat&&u.deathTime!==null&&t>=u.deathTime){action='death';memberState='DEAD';clock=Math.min(a.clips.death.duration-.001,(t-u.deathTime)/C.deathSeconds*a.clips.death.duration)}
  else if(speed>.02){action='move';memberState=hitAge>=0&&hitAge<C.hitPoseSeconds?'STAGGER':hitAge>=0&&hitAge<10?'WOUNDED':t<u.delay+u.accelerationSeconds?'ACCELERATE':Math.round(ctrl[9])===3?'YIELD':Math.round(ctrl[9])===2?'PASS':ctrl[2]>.55?'PUSH':ctrl[2]<-.55?'SETTLE':'CHARGE';clock=(sample(t,i,gaitCycles,1)+u.phase)*a.clips.move.duration;yaw=ctrl[7];lean=C.runLean*Math.min(1,speed/8);}
  else if(i>=nb&&t>=u.delay){memberState='YIELD';yaw=ctrl[7];}
  // Hit response affects upper body only; distance-driven running legs continue.
  const clip=a.clips[action];let phase=phaseFraction!==null?Math.floor(phaseFraction*clip.phases):action==='death'?Math.floor(clock/clip.duration*clip.phases):Math.floor(((clock%clip.duration+clip.duration)%clip.duration)/clip.duration*clip.phases);phase=Math.min(clip.phases-1,phase);
  const phaseFloat=phaseFraction!==null?phaseFraction*clip.phases:action==='death'?clock/clip.duration*clip.phases:((clock%clip.duration+clip.duration)%clip.duration)/clip.duration*clip.phases;const b=armies.batches.get(`${u.model}/${action}/${phase}`);b.moveWeight.setX(b.n,i>=nb&&action==='move'?T.MathUtils.smoothstep(speed,0,4):1);b.blend.setX(b.n,Math.min(1,Math.max(0,phaseFloat-phase)));const runningLift=i>=nb&&action==='move'?.025*Math.pow(Math.sin(clock/a.clips.move.duration*Math.PI*2),2):0;dummy.position.set(p[0],.015+runningLift,p[1]);dummy.rotation.set(lean,yaw,0,'YXZ');dummy.scale.setScalar(1);dummy.updateMatrix();b.mesh.setMatrixAt(b.n,dummy.matrix);b.memberPose.setXYZW(b.n,action!=='death'&&i>=nb&&hitAge>=0&&hitAge<C.hitPoseSeconds?Math.sin(Math.PI*hitAge/C.hitPoseSeconds):0,i>=nb&&action==='move'?ctrl[5]:0,i>=nb&&action==='move'?ctrl[3]/C.runStride:1,i>=nb&&action==='move'?ctrl[6]:0);b.hit.setX(b.n++,hitAge>=0&&hitAge<C.flashSeconds?.25*(1-hitAge/C.flashSeconds):0);
  behavior.push({id:u.id,index:i,state:memberState,action,phase,phaseFloat,archerPhase:bluePhase,archerWalkPhase:blueWalkPhase,archerFacing:blueFacing,archerTargetYaw:blueTargetYaw,archerProgress:blueProgress,releaseEventId:blueReleaseId,speed,x:p[0],z:p[1],event:currentEvent,hitAge:i>=nb?hitAge:null,targetSpeed:ctrl?.[0]??null,acceleration:ctrl?.[2]??null,stride:ctrl?.[3]??null,cadence:ctrl?.[4]??null,posture:ctrl?.[5]??null,armSwing:ctrl?.[6]??null,turn:ctrl?.[7]??null,effort:ctrl?.[8]??null,reason:ctrl?Math.round(ctrl[9]):null,gaitCycles:i>=nb?sample(t,i,gaitCycles,1):null});
  dummy.position.set(p[0],-p[1],.01);dummy.rotation.set(0,0,0);dummy.scale.set(1,1,1);dummy.updateMatrix();shadows.setMatrixAt(sn++,dummy.matrix);
 }
 window.lastBehavior=behavior;
 for(const b of armies.batches.values()){b.mesh.count=b.n;b.mesh.instanceMatrix.needsUpdate=true;b.hit.needsUpdate=true;b.response.needsUpdate=true;b.posture.needsUpdate=true;b.gaitScale.needsUpdate=true;b.memberPose.needsUpdate=true;b.blend.needsUpdate=true;b.moveWeight.needsUpdate=true}shadows.count=sn;shadows.instanceMatrix.needsUpdate=true;
 for(const e of (combat?S.events:[])){
  if(t>=e.release&&t<e.impact){const p=arrowPoint(e,t),q=arrowPoint(e,Math.min(e.impact,t+.012)),d=q.clone().sub(p).normalize(),a=p.clone().addScaledVector(d,-1);segment(arrowMesh,an++,a,p);dummy.position.copy(p);dummy.quaternion.setFromUnitVectors(yAxis,d);dummy.scale.setScalar(1);dummy.updateMatrix();heads.setMatrixAt(hn,dummy.matrix);dummy.position.copy(p).addScaledVector(d,-.85);dummy.updateMatrix();feathers.setMatrixAt(hn++,dummy.matrix);const from=Math.max(e.release,t-C.arrowTailSeconds),to=Math.max(from,t-.016);for(let k=0;k<3;k++){const ta=from+(to-from)*k/3,tb=from+(to-from)*(k+1)/3;segment(trails,tn++,arrowPoint(e,ta),arrowPoint(e,tb),1-k*.15)}}
  const age=t-e.impact;if(age>=0&&age<.2){const p=row(t,e.target);for(let k=0;k<4;k++){dummy.position.set(p[0]+Math.sin(k*2.4)*age*2,.8+age*1.2,p[1]+Math.cos(k*2.4)*age*2);dummy.rotation.set(age*5,k,0);dummy.scale.setScalar((1-age/.2)*.48);dummy.updateMatrix();sparks.setMatrixAt(flashes++,dummy.matrix)}}
 }
 if(an>2048||tn>6144||flashes>4096)throw new Error('VFX instance capacity exceeded');
 for(const [mesh,count]of[[arrowMesh,an],[heads,hn],[feathers,hn],[trails,tn],[sparks,flashes]]){mesh.count=count;mesh.instanceMatrix.needsUpdate=true}
 // Keep real motion readable: locked camera, no shake or motion blur.
 renderer.render(scene,camera);
 const state={version:isV22?'V22-CAMERA':'V19-CAMERA',time:t,cameraPosition:camera.position.toArray(),cameraQuaternion:camera.quaternion.toArray(),cameraProjection:camera.projectionMatrix.toArray(),cameraZoom:camera.zoom,battleCamera:window.cameraState,arrows:an-nocked,nocked,impactParticles:flashes,aliveRed:!combat?S.redCount:S.units.slice(nb).filter(u=>u.deathTime===null||u.deathTime>t).length};window.lastState=state;return state;
}
window.renderAt=renderAt;window.sceneRuntime={renderer,scene,camera,armies,row,arrowPoint,simulation:S,config:C,cameraSchedule,setCamera};window.ready=true;renderAt(0,{diagnostics:!capture});document.querySelector('#status').textContent=`${isV22?'V22':variant.startsWith('V21')?'V21':'V19'} | ${nb} archers / ${S.redCount} enemies | ${C.duration}s`;document.querySelector('#time').max=C.duration-1/C.fps;
let playing=!capture,start=performance.now(),offset=0;document.querySelector('#play').onclick=()=>{if(playing)offset=(performance.now()-start)/1000;else start=performance.now()-offset*1000;playing=!playing};document.querySelector('#reset').onclick=()=>{offset=0;start=performance.now();playing=true};document.querySelector('#time').oninput=e=>{playing=false;offset=+e.target.value;renderAt(offset,{diagnostics:document.querySelector('#diag').checked})};document.querySelector('#diag').onchange=()=>renderAt(offset,{diagnostics:document.querySelector('#diag').checked});
function tick(now){if(playing){offset=(now-start)/1000;if(offset>=C.duration){offset=C.duration-1/C.fps;playing=false}renderAt(offset,{diagnostics:document.querySelector('#diag').checked});document.querySelector('#time').value=offset}requestAnimationFrame(tick)}if(!capture)requestAnimationFrame(tick);








