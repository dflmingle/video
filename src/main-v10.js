import * as T from 'three';import {loadArmies} from './assets-v10.js';import {addEnvironment} from './environment-v10.js';
const variant=new URLSearchParams(location.search).get('variant')||'A',base='/variants/'+variant+'/';
const C=await fetch(base+'params.json').then(r=>r.json()),S=await fetch(base+'simulation.json').then(r=>r.json());
const load=async p=>new Float32Array(await fetch(base+p).then(r=>r.arrayBuffer()));
const [pos,hitTimes,gait]=await Promise.all([load('trajectories.f32'),load('hit-times.f32'),load('gait-distance.f32')]);
const query=new URLSearchParams(location.search);let motionData=null;if(query.has('motionOnly')){const [mp,mg]=await Promise.all([load('motion-trajectories.f32'),load('motion-gait-distance.f32')]);motionData={pos:mp,gait:mg};}
const capture=query.has('capture');document.body.classList.toggle('capture',capture);
const renderer=new T.WebGLRenderer({canvas:document.querySelector('#view'),antialias:true,preserveDrawingBuffer:true});renderer.setSize(C.width,C.height);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
const scene=new T.Scene();scene.background=new T.Color(0xd1c3a8);scene.add(new T.HemisphereLight(0xfff3de,0x596b56,1.7));const sun=new T.DirectionalLight(0xffecd0,2.4);sun.position.set(-25,60,25);scene.add(sun);
const camera=new T.PerspectiveCamera(C.cameraFov,C.width/C.height,.1,600);camera.position.fromArray(C.cameraPosition);camera.lookAt(...C.cameraTarget);camera.updateMatrixWorld(true);
// Build a camera schedule from current occupied bounds; preserve all armies
// and the U. Use deterministic low-pass values, never wall-clock accumulation.
const cameraSchedule=[];
function setCamera(t){
 // One fixed perspective and one initial fit for the entire shot. No cuts,
 // auto-reframe, dolly or zoom; advancing bodies themselves grow on screen.
 camera.position.fromArray(C.cameraPosition);camera.lookAt(...C.cameraTarget);
 camera.fov=C.cameraFov;camera.zoom=C.cameraZoom;
 camera.updateMatrixWorld(true);camera.updateProjectionMatrix();
 camera.projectionMatrix.elements[8]=C.cameraShiftX;
 camera.projectionMatrix.elements[9]=C.cameraShiftY;
 camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
}
window.environmentAudit=await addEnvironment(scene);const armies=await loadArmies(scene,C);window.assetAudit=armies.audit;const nb=S.blueCount,n=S.units.length,dummy=new T.Object3D();
const shadows=new T.InstancedMesh(new T.CircleGeometry(.38,10),new T.MeshBasicMaterial({color:0x293c24,transparent:true,opacity:.23,depthWrite:false}),n);shadows.rotation.x=-Math.PI/2;shadows.frustumCulled=false;scene.add(shadows);
const arrowMesh=new T.InstancedMesh(new T.CylinderGeometry(.038,.038,1,6),new T.MeshBasicMaterial({color:0x976e38}),2048),heads=new T.InstancedMesh(new T.ConeGeometry(.10,.27,4),new T.MeshBasicMaterial({color:0x303a3e}),2048),trails=new T.InstancedMesh(new T.CylinderGeometry(.040,.040,1,4),new T.MeshBasicMaterial({color:0xf7e8c8,transparent:true,opacity:.40,depthWrite:false}),6144),sparks=new T.InstancedMesh(new T.OctahedronGeometry(.13),new T.MeshBasicMaterial({color:0xffecd0}),4096);
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
 const frame=Math.min(S.frames-1,Math.round(t*C.simulationFps));
 for(let i=0;i<n;i++){
  const u=S.units[i],p=row(t,i),before=row(Math.max(0,t-.035),i),vel=[(p[0]-before[0])/.035,(p[1]-before[1])/.035],speed=Math.hypot(...vel),distance=sample(t,i,motionData?.gait||gait,1),a=armies.audit[u.model];let action='idle',clock=t+u.phase,yaw=i<nb?Math.PI:0,lean=0,phaseFraction=null;
  const hitAge=i<nb||!combat?10:t-hitTimes[frame*S.redCount+i-nb];
  if(i<nb){
   if(t>u.delay&&t<u.delay+C.blueMoveSeconds){action='move';clock=distance/C.blueStride*a.clips.move.duration+u.phase*a.clips.move.duration;lean=.045*Math.min(1,speed/4)}
   else{let e=null;for(const k of (combat?S.shooterEvents[i]:[])){const v=S.events[k];if(t>=v.drawStart&&t<v.release+.28){e=v;break}}
    if(e){action='attack';phaseFraction=t<e.release?.64*T.MathUtils.clamp((t-e.drawStart)/C.drawSeconds,0,1):.64+.359*Math.min(1,(t-e.release)/.28);yaw=Math.atan2(e.destination[0]-p[0],e.destination[2]-p[1]);
     if(t<e.release){const ix=Math.min(a.clips.attack.phases-1,Math.floor(phaseFraction*a.clips.attack.phases)),loc=a.poseAnchors.attack[ix].leftHand;const h=new T.Vector3(p[0]+loc[0]*Math.cos(yaw)+loc[2]*Math.sin(yaw),loc[1],p[1]-loc[0]*Math.sin(yaw)+loc[2]*Math.cos(yaw)),d=new T.Vector3(Math.sin(yaw),.03,Math.cos(yaw));segment(arrowMesh,an++,h.clone().addScaledVector(d,-.4),h.clone().addScaledVector(d,.6));nocked++}
    }
   }
  }else if(combat&&u.deathTime!==null&&t>=u.deathTime){action='death';clock=Math.min(a.clips.death.duration-.001,(t-u.deathTime)/C.deathSeconds*a.clips.death.duration)}
  else if(speed>.02){action='move';clock=distance/(u.gaitStride||C.runStride)*a.clips.move.duration+u.phase*a.clips.move.duration;yaw=Math.atan2(vel[0],Math.max(.01,vel[1]));lean=C.runLean*Math.min(1,speed/8);if(hitAge>=0&&hitAge<C.hitStaggerSeconds+C.hitRecoverySeconds){const w=Math.max(0,1-hitAge/(C.hitStaggerSeconds+C.hitRecoverySeconds));lean-=.45*Math.sin(Math.min(1,hitAge/.22)*Math.PI*.8)*w;}}
  if(i>=nb&&action!=='death'&&combat&&hitAge>=0&&hitAge<C.hitPoseSeconds){action='stagger';phaseFraction=Math.min(.999,hitAge/C.hitPoseSeconds);lean=-.22*Math.sin(Math.PI*phaseFraction)+.12*phaseFraction;}
  const clip=a.clips[action];let phase=phaseFraction!==null?Math.floor(phaseFraction*clip.phases):action==='death'?Math.floor(clock/clip.duration*clip.phases):Math.floor(((clock%clip.duration+clip.duration)%clip.duration)/clip.duration*clip.phases);phase=Math.min(clip.phases-1,phase);
  const phaseFloat=phaseFraction!==null?phaseFraction*clip.phases:action==='death'?clock/clip.duration*clip.phases:((clock%clip.duration+clip.duration)%clip.duration)/clip.duration*clip.phases;const b=armies.batches.get(`${u.model}/${action}/${phase}`);b.moveWeight.setX(b.n,i>=nb&&action==='move'?T.MathUtils.smoothstep(speed,0,4):1);b.blend.setX(b.n,Math.min(1,Math.max(0,phaseFloat-phase)));const runningLift=0;dummy.position.set(p[0],.015+runningLift,p[1]);dummy.rotation.set(lean,yaw,hitAge>=0&&hitAge<C.hitPoseSeconds?.22*Math.sin(hitAge/C.hitPoseSeconds*Math.PI)*(i%2?1:-1):0,'YXZ');dummy.scale.setScalar(1);dummy.updateMatrix();b.mesh.setMatrixAt(b.n,dummy.matrix);b.hit.setX(b.n++,hitAge>=0&&hitAge<C.flashSeconds?.7*(1-hitAge/C.flashSeconds):0);
  dummy.position.set(p[0],-p[1],.01);dummy.rotation.set(0,0,0);dummy.scale.set(1,1,1);dummy.updateMatrix();shadows.setMatrixAt(sn++,dummy.matrix);
 }
 for(const b of armies.batches.values()){b.mesh.count=b.n;b.mesh.instanceMatrix.needsUpdate=true;b.hit.needsUpdate=true;b.blend.needsUpdate=true;b.moveWeight.needsUpdate=true}shadows.count=sn;shadows.instanceMatrix.needsUpdate=true;
 for(const e of (combat?S.events:[])){
  if(t>=e.release&&t<e.impact){const p=arrowPoint(e,t),q=arrowPoint(e,Math.min(e.impact,t+.012)),d=q.clone().sub(p).normalize(),a=p.clone().addScaledVector(d,-1);segment(arrowMesh,an++,a,p);dummy.position.copy(p);dummy.quaternion.setFromUnitVectors(yAxis,d);dummy.scale.setScalar(1);dummy.updateMatrix();heads.setMatrixAt(hn,dummy.matrix);dummy.position.copy(p).addScaledVector(d,-.85);dummy.updateMatrix();feathers.setMatrixAt(hn++,dummy.matrix);const from=Math.max(e.release,t-C.arrowTailSeconds),to=Math.max(from,t-.016);for(let k=0;k<3;k++){const ta=from+(to-from)*k/3,tb=from+(to-from)*(k+1)/3;segment(trails,tn++,arrowPoint(e,ta),arrowPoint(e,tb),1-k*.15)}}
  const age=t-e.impact;if(age>=0&&age<.2){const p=row(t,e.target);for(let k=0;k<4;k++){dummy.position.set(p[0]+Math.sin(k*2.4)*age*2,.8+age*1.2,p[1]+Math.cos(k*2.4)*age*2);dummy.rotation.set(age*5,k,0);dummy.scale.setScalar((1-age/.2)*.8);dummy.updateMatrix();sparks.setMatrixAt(flashes++,dummy.matrix)}}
 }
 if(an>2048||tn>6144||flashes>4096)throw new Error('VFX instance capacity exceeded');
 for(const [mesh,count]of[[arrowMesh,an],[heads,hn],[feathers,hn],[trails,tn],[sparks,flashes]]){mesh.count=count;mesh.instanceMatrix.needsUpdate=true}
 // Keep real motion readable: locked camera, no shake or motion blur.
 renderer.render(scene,camera);
 const state={version:'V10',time:t,cameraPosition:camera.position.toArray(),cameraQuaternion:camera.quaternion.toArray(),cameraProjection:camera.projectionMatrix.toArray(),cameraZoom:camera.zoom,arrows:an-nocked,nocked,impactParticles:flashes,aliveRed:!combat?S.redCount:S.units.slice(nb).filter(u=>u.deathTime===null||u.deathTime>t).length};window.lastState=state;return state;
}
window.renderAt=renderAt;window.sceneRuntime={renderer,scene,camera,armies,row,arrowPoint,simulation:S,config:C,cameraSchedule,setCamera};window.ready=true;renderAt(0,{diagnostics:!capture});document.querySelector('#status').textContent=`V3 · ${nb} 弓箭手 / ${S.redCount} 敌军 · ${C.duration} 秒`;document.querySelector('#time').max=C.duration-1/C.fps;
let playing=!capture,start=performance.now(),offset=0;document.querySelector('#play').onclick=()=>{if(playing)offset=(performance.now()-start)/1000;else start=performance.now()-offset*1000;playing=!playing};document.querySelector('#reset').onclick=()=>{offset=0;start=performance.now();playing=true};document.querySelector('#time').oninput=e=>{playing=false;offset=+e.target.value;renderAt(offset,{diagnostics:document.querySelector('#diag').checked})};document.querySelector('#diag').onchange=()=>renderAt(offset,{diagnostics:document.querySelector('#diag').checked});
function tick(now){if(playing){offset=(now-start)/1000;if(offset>=C.duration){offset=C.duration-1/C.fps;playing=false}renderAt(offset,{diagnostics:document.querySelector('#diag').checked});document.querySelector('#time').value=offset}requestAnimationFrame(tick)}if(!capture)requestAnimationFrame(tick);
