import * as T from 'three';import {loadArmies} from './assets.js';import {addEnvironment} from './environment.js';
const C=await fetch('/params.json').then(r=>r.json()),S=await fetch('/output/simulation.json').then(r=>r.json()),pos=new Float32Array(await fetch('/output/trajectories.f32').then(r=>r.arrayBuffer())),hitTimes=new Float32Array(await fetch('/output/hit-times.f32').then(r=>r.arrayBuffer()));
const capture=new URLSearchParams(location.search).has('capture');document.body.classList.toggle('capture',capture);
const canvas=document.querySelector('#view'),renderer=new T.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});renderer.setSize(C.width,C.height);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.18;
const scene=new T.Scene();scene.background=new T.Color(0xceb378);scene.add(new T.HemisphereLight(0xffedd0,0x687357,2.5));const sun=new T.DirectionalLight(0xfff2dc,3);sun.position.set(-20,65,35);scene.add(sun);
const camera=new T.OrthographicCamera(-34,34,45.333,-45.333,.1,300);camera.position.set(0,105,71);camera.lookAt(0,0,-5);
const ground=new T.Mesh(new T.PlaneGeometry(180,180),new T.MeshStandardMaterial({color:0xd1ac69,roughness:1}));ground.rotation.x=-Math.PI/2;ground.position.y=-.06;scene.add(ground);
// Original procedural sandy floor; package props are loaded separately.
let seed=C.seed;function rand(){seed=(seed*1664525+1013904223)>>>0;return seed/4294967296}
const gc=document.createElement('canvas');gc.width=gc.height=1024;const ctx=gc.getContext('2d');ctx.fillStyle='#d9b57b';ctx.fillRect(0,0,1024,1024);
for(let i=0;i<14000;i++){const x=rand()*1024,y=rand()*1024;ctx.fillStyle=rand()>.5?'rgba(130,110,70,.055)':'rgba(255,230,165,.12)';ctx.fillRect(x,y,rand()*7+1,rand()*4+1)}
for(let i=0;i<60;i++){ctx.fillStyle='rgba(171,139,88,.09)';ctx.beginPath();ctx.ellipse(rand()*1024,rand()*1024,rand()*80+10,rand()*40+5,rand()*6,0,7);ctx.fill()}
for(let y=0;y<1024;y+=32)for(let x=0;x<1024;x+=32){ctx.fillStyle=(x/32+y/32)%2?'rgba(255,232,167,.028)':'rgba(139,106,51,.025)';ctx.fillRect(x,y,32,32)}
const gtex=new T.CanvasTexture(gc);gtex.colorSpace=T.SRGBColorSpace;ground.material.map=gtex;
const decor=new T.Group();scene.add(decor);
for(let i=0;i<100;i++){const x=(rand()>.5?1:-1)*(27+rand()*18),z=-55+rand()*100;const rock=new T.Mesh(new T.DodecahedronGeometry(.3+rand()*.65,0),new T.MeshStandardMaterial({color:rand()>.5?0x9c8963:0x77805b,roughness:1}));rock.position.set(x,.06,z);rock.scale.y=.5;decor.add(rock)}
window.environmentAudit=await addEnvironment(scene);const armies=await loadArmies(scene);window.assetAudit=armies.audit;const nb=S.blueCount,n=S.units.length,dummy=new T.Object3D();
const shadowGeo=new T.CircleGeometry(.36,8),shadow=new T.InstancedMesh(shadowGeo,new T.MeshBasicMaterial({color:0x4b402b,transparent:true,opacity:.19,depthWrite:false}),n);shadow.rotation.x=-Math.PI/2;shadow.frustumCulled=false;scene.add(shadow);
const arrowMesh=new T.InstancedMesh(new T.CylinderGeometry(.035,.035,.95,4),new T.MeshBasicMaterial({color:0xf3edc6}),2048);arrowMesh.frustumCulled=false;scene.add(arrowMesh);
const arrowHeads=new T.InstancedMesh(new T.ConeGeometry(.11,.24,4),new T.MeshBasicMaterial({color:0x454a4c}),2048);arrowHeads.frustumCulled=false;scene.add(arrowHeads);
const trails=new T.InstancedMesh(new T.CylinderGeometry(.018,.018,1,4),new T.MeshBasicMaterial({color:0xf4e6ad,transparent:true,opacity:.32,depthWrite:false}),2048);trails.frustumCulled=false;scene.add(trails);
const sparks=new T.InstancedMesh(new T.OctahedronGeometry(.17),new T.MeshBasicMaterial({color:0xfff2bc}),2048);sparks.frustumCulled=false;scene.add(sparks);
const diag=new T.Group();scene.add(diag);const lines=[];
for(let j=0;j<nb;j++){const u=S.units[j];lines.push(new T.Vector3(u.start[0]-.14,.04,u.start[1]-C.blueAdvance),new T.Vector3(u.start[0]+.14,.04,u.start[1]-C.blueAdvance))}
const endline=new T.LineSegments(new T.BufferGeometry().setFromPoints(lines),new T.LineBasicMaterial({color:0x1b9ef8}));diag.add(endline);
const safe=new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(-25,.05,C.redStopZ),new T.Vector3(25,.05,C.redStopZ)]),new T.LineDashedMaterial({color:0xc85235,dashSize:.4,gapSize:.4}));safe.computeLineDistances();diag.add(safe);
const yAxis=new T.Vector3(0,1,0);const vectors=[new T.Vector3(),new T.Vector3(),new T.Vector3()];
function row(t,i){const f=Math.min(S.frames-1,Math.max(0,t*C.simulationFps)),a=Math.floor(f),b=Math.min(S.frames-1,a+1),w=f-a;return[pos[(a*n+i)*2]*(1-w)+pos[(b*n+i)*2]*w,pos[(a*n+i)*2+1]*(1-w)+pos[(b*n+i)*2+1]*w]}
function arrowPoint(e,t){const f=T.MathUtils.clamp((t-e.release)/(e.impact-e.release),0,1);return new T.Vector3(e.origin[0]*(1-f)+e.destination[0]*f,e.origin[1]*(1-f)+e.destination[1]*f+4*e.arc*f*(1-f),e.origin[2]*(1-f)+e.destination[2]*f)}
function segment(mesh,i,a,b,width=1){const d=b.clone().sub(a);dummy.position.copy(a).add(b).multiplyScalar(.5);dummy.quaternion.setFromUnitVectors(yAxis,d.clone().normalize());dummy.scale.set(width,d.length(),width);dummy.updateMatrix();mesh.setMatrixAt(i,dummy.matrix)}
function renderAt(t,{diagnostics=false}={}){
 t=T.MathUtils.clamp(t,0,C.duration-1/C.fps);diag.visible=diagnostics;for(const b of armies.batches.values())b.n=0;let sn=0,flashes=0;
 const frame=Math.min(S.frames-1,Math.round(t*C.simulationFps));
 for(let i=0;i<n;i++){
  const u=S.units[i],p=row(t,i),before=row(Math.max(0,t-.05),i),vel=[p[0]-before[0],p[1]-before[1]];let action='idle',clock=t+u.phase,yaw=0;
  if(i<nb){
   yaw=Math.PI;const moving=t>u.delay&&t<u.delay+C.blueMoveSeconds;
   if(moving){action='move';clock=(t-u.delay)*1.15}
   else if(t>2.35){const idx=S.shooterEvents[i];let e=null;for(const k of idx){const a=S.events[k];if(t>=a.drawStart&&t<a.release+.35){e=a;break}}
    if(e){action='attack';clock=T.MathUtils.clamp((t-e.drawStart)/(C.drawSeconds+.35),0,.999)*armies.audit.archer.clips.attack.duration;yaw=Math.atan2(e.destination[0]-p[0],e.destination[2]-p[1])}
   }
  }else{
   const dead=u.deathTime!==null&&t>=u.deathTime;
   if(dead){action='death';clock=Math.min(armies.audit[u.model].clips.death.duration-.001,(t-u.deathTime)/C.deathSeconds*armies.audit[u.model].clips.death.duration)}
   else if(Math.hypot(...vel)>.001){action='move';clock=t*u.speed*.50+u.phase;yaw=Math.atan2(vel[0],vel[1])}
  }
  const clip=armies.audit[u.model].clips[action],phase=action==='death'?Math.min(clip.phases-1,Math.floor(clock/clip.duration*clip.phases)):Math.floor((clock%clip.duration)/clip.duration*clip.phases),b=armies.batches.get(`${u.model}/${action}/${phase}`);
  dummy.position.set(p[0],.0,p[1]);dummy.rotation.set(0,yaw,0);dummy.scale.setScalar(1);dummy.updateMatrix();b.mesh.setMatrixAt(b.n,dummy.matrix);const h=i<nb?-10:t-hitTimes[frame*S.redCount+i-nb];b.hit.setX(b.n++,h>=0&&h<.08?1-h/.08:0);
  dummy.position.set(p[0],-p[1],.015);dummy.rotation.set(0,0,0);dummy.scale.set(1,1,1);dummy.updateMatrix();shadow.setMatrixAt(sn++,dummy.matrix);
 }
 for(const b of armies.batches.values()){b.mesh.count=b.n;b.mesh.instanceMatrix.needsUpdate=true;b.hit.needsUpdate=true}shadow.count=sn;shadow.instanceMatrix.needsUpdate=true;
 let an=0,tn=0;
 for(const e of S.events){
  if(t>=e.release&&t<e.impact){const p=arrowPoint(e,t),q=arrowPoint(e,Math.min(e.impact,t+.02)),d=q.clone().sub(p).normalize(),a=p.clone().addScaledVector(d,-.85);segment(arrowMesh,an,a,p);dummy.position.copy(p);dummy.quaternion.setFromUnitVectors(yAxis,d);dummy.scale.setScalar(1);dummy.updateMatrix();arrowHeads.setMatrixAt(an++,dummy.matrix);const prev=arrowPoint(e,Math.max(e.release,t-C.arrowTailSeconds));segment(trails,tn++,prev,a,.8)}
  const age=t-e.impact;if(age>=0&&age<.16){for(let k=0;k<3;k++){dummy.position.set(e.destination[0]+Math.sin(k*2.4)*age*2,.8+age*1.5,e.destination[2]+Math.cos(k*2.4)*age*2);dummy.rotation.set(age*5,k,0);dummy.scale.setScalar((1-age/.16)*.8);dummy.updateMatrix();sparks.setMatrixAt(flashes++,dummy.matrix)}}
 }
 for(const [mesh,count]of[[arrowMesh,an],[arrowHeads,an],[trails,tn],[sparks,flashes]]){mesh.count=count;mesh.instanceMatrix.needsUpdate=true}
 camera.zoom=1+.025*Math.sin(Math.min(1,t/C.duration)*Math.PI/2);camera.updateProjectionMatrix();renderer.render(scene,camera);
 const state={time:t,arrows:an,impactParticles:flashes,aliveRed:S.units.slice(nb).filter(u=>u.deathTime===null||u.deathTime>t).length};window.lastState=state;return state;
}
window.renderAt=renderAt;window.sceneRuntime={renderer,scene,camera,armies,row,arrowPoint,simulation:S,config:C};window.ready=true;renderAt(0,{diagnostics:!capture});document.querySelector('#status').textContent=`324 弓箭手 / 972 敌军 · 14 秒`;
let playing=!capture,start=performance.now(),offset=0;document.querySelector('#play').onclick=()=>{if(playing)offset=(performance.now()-start)/1000;else start=performance.now()-offset*1000;playing=!playing};document.querySelector('#reset').onclick=()=>{offset=0;start=performance.now();playing=true};document.querySelector('#time').oninput=e=>{playing=false;offset=+e.target.value;renderAt(offset,{diagnostics:document.querySelector('#diag').checked})};document.querySelector('#diag').onchange=()=>renderAt(offset,{diagnostics:document.querySelector('#diag').checked});
function tick(now){if(playing){offset=(now-start)/1000;if(offset>=C.duration){offset=C.duration-1/C.fps;playing=false}renderAt(offset,{diagnostics:document.querySelector('#diag').checked});document.querySelector('#time').value=offset}requestAnimationFrame(tick)}if(!capture)requestAnimationFrame(tick);
