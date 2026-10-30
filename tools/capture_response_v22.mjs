// Independent specialist diagnostic capture. No shared file/variant mutations.
// Run after diagnose_response_v22.py. The root browser supplies the same native
// archer batches; this browser scene is replaced by a clearly labelled test pad.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const args=process.argv.slice(2),get=(name,fallback)=>{const i=args.indexOf(name);return i<0?fallback:args[i+1]};
const root=path.resolve(get('--root','C:/Users/89trillion/PveMontageShot01V22'));
const out=path.resolve(get('--out',new URL('../output/response-v22',import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1')));
const source=JSON.parse(fs.readFileSync(path.join(out,'response-animation-data.json'),'utf8'));
const {chromium}=await import(pathToFileURL(path.join(root,'node_modules/playwright/index.mjs')));
const probe=args.includes('--probe'),fps=30;
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:960,height:720}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5262/v22.html?capture=1&variant=V22-C');
 await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 await page.evaluate(async()=>{
  const {T}=await import('/src/probe-helper.js'),{resolveArcherPose}=await import('/src/archer-pose-v22.js');
  const r=window.sceneRuntime;
  // Reuse original native model/animation/material data. Test pad is explicitly
  // separate from the production terrain; no claim this is the battle camera.
  r.scene.traverse(o=>{if(o.isMesh||o.isLine)o.visible=false});
  for(const b of r.armies.batches.values()){b.mesh.visible=true;b.mesh.count=0}
  r.scene.background=new T.Color(0x26323a);
  const ground=new T.Mesh(new T.PlaneGeometry(30,30),new T.MeshStandardMaterial({color:0x607366,roughness:1}));
  ground.rotation.x=-Math.PI/2;ground.position.y=-.025;r.scene.add(ground);
  const grid=new T.GridHelper(30,30,0xa4b2a8,0x718479);grid.position.y=-.02;r.scene.add(grid);
  const marks=new T.Group();r.scene.add(marks);
  r.renderer.setSize(960,720);r.camera.aspect=960/720;r.camera.fov=40;
  document.body.style.display='block';document.querySelector('#view').style.cssText='width:960px;height:720px;display:block';
  const label=document.createElement('div');label.id='response-label';
  label.style.cssText='position:fixed;left:0;top:0;width:100%;padding:10px 16px;box-sizing:border-box;background:#14212be8;color:white;font:16px monospace;line-height:1.45;pointer-events:none';
  document.body.appendChild(label);
  window.responseDiagnostic={T,r,resolveArcherPose,marks,ground,grid,label,dummy:new T.Object3D()};
 });
 for(const c of source.cases){
  const dir=path.join(out,'captures',c.case+(probe?'-probe':''));fs.mkdirSync(dir,{recursive:true});
  const indices=probe?[0,60,84,110,160,190]:Array.from({length:Math.floor(c.frames.length/2)},(_,i)=>i*2);
  for(let i=0;i<indices.length;i++){
   const f=c.frames[indices[i]];
   await page.evaluate(({c,f})=>{
    const {T,r,resolveArcherPose,marks,ground,grid,label,dummy}=window.responseDiagnostic;
    for(const b of r.armies.batches.values())b.n=0;
    for(const child of [...marks.children]){marks.remove(child);child.geometry?.dispose();child.material?.dispose()}
    const focus=[c.reference[0]-1.25,c.reference[1]-.7];
    ground.position.set(focus[0],-.025,focus[1]);grid.position.set(focus[0],-.02,focus[1]);
    r.camera.zoom=1;r.camera.position.set(focus[0],13.5,focus[1]+10.1);r.camera.lookAt(focus[0],.4,focus[1]);r.camera.updateProjectionMatrix();r.camera.updateMatrixWorld(true);
    for(let k=0;k<c.ids.length;k++){
     const u=c.units[k],p=f.position[k],a=r.armies.audit.archer,bc=f.controls[k];
     const pose=resolveArcherPose({bc,speed:f.speed[k],unit:u,time:f.t,attackDuration:a.clips.attack.duration,moveDuration:a.clips.move.duration});
     const clip=a.clips[pose.action],float=pose.phaseFraction*clip.phases,phase=Math.min(clip.phases-1,Math.floor(float));
     const b=r.armies.batches.get(`archer/${pose.action}/${phase}`);
     dummy.position.set(p[0],.015,p[1]);dummy.rotation.set(0,pose.yaw,0,'YXZ');dummy.scale.setScalar(1);dummy.updateMatrix();
     b.mesh.setMatrixAt(b.n,dummy.matrix);b.blend.setX(b.n,float-phase);b.moveWeight.setX(b.n,pose.action==='move'?pose.walkWeight:pose.action==='attack'?pose.attackWeight:1);b.memberPose.setXYZW(b.n,0,0,1,0);b.hit.setX(b.n++,0);
     const base=f.baseline[k],target=f.target[k],isShooter=c.ids[k]===c.shooter;
     const material=new T.MeshBasicMaterial({color:isShooter?0xffcc45:0xd1e6df,side:T.DoubleSide});
     const ring=new T.Mesh(new T.RingGeometry(.20,.225,24),material);ring.rotation.x=-Math.PI/2;ring.position.set(base[0],.03,base[1]);marks.add(ring);
     if(Math.hypot(...target)>.001){
      const line=new T.Line(new T.BufferGeometry().setFromPoints([new T.Vector3(base[0],.045,base[1]),new T.Vector3(base[0]+target[0],.045,base[1]+target[1])]),new T.LineBasicMaterial({color:0x28f7ef}));marks.add(line);
      const tip=new T.Mesh(new T.SphereGeometry(.045,8,6),new T.MeshBasicMaterial({color:0x28f7ef}));tip.position.set(base[0]+target[0],.06,base[1]+target[1]);marks.add(tip);
     }
    }
    for(const b of r.armies.batches.values()){b.mesh.count=b.n;for(const key of ['instanceMatrix','hit','response','posture','gaitScale','memberPose','blend','moveWeight']){const attr=key==='instanceMatrix'?b.mesh.instanceMatrix:b[key];if(attr)attr.needsUpdate=true}}
    const j=c.ids.indexOf(c.shooter),delta=Math.hypot(...f.delta[j]),target=Math.hypot(...f.target[j]);
    label.innerHTML=`${c.synthetic?'SYNTHETIC = TRUE | BLUE DAMAGE DIAGNOSTIC':'SYNTHETIC = FALSE | REAL IMPACT EVENT REPLAY'}<br>t=${f.t.toFixed(2)}s | ${c.units[j].id} actual delta=${delta.toFixed(3)} | target=${target.toFixed(3)}<br><small>Gold ring: no-response twin | Cyan: response target | Root: actual Archers.move<br>Native pose retained. Isolated test; no production blue damage / no battle approval.</small>`;
    r.renderer.render(r.scene,r.camera);r.renderer.getContext().finish();
   },{c:{...c,frames:undefined},f});
   await page.screenshot({path:path.join(dir,`F${String(i).padStart(4,'0')}.png`)});
   if(i%30===0)console.log(c.case,i,indices.length);
  }
 }
 fs.writeFileSync(path.join(out,'capture-response-audit.json'),JSON.stringify({source:'actual integrator traces',syntheticSeparate:true,fps,probe,errors,normalSpeedWholeVideoWatched:false},null,2));
 if(errors.length)throw Error(errors.join('\n'));
}finally{await browser.close()}
