// 0–1.5s motion diagnostic only. The native scene is explicitly unconfirmed.
import fs from 'node:fs';import {chromium} from 'playwright';
const out='output/v22r-opening';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
let fixed;
try{
 for(const variant of ['V22-C','V22R-overlap']){
  const page=await browser.newPage({viewport:{width:1440,height:2160}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=${variant}&camera=B&environment=NewScene`);
  await page.waitForFunction(()=>window.ready,null,{timeout:180000});
  if(!fixed)fixed=await page.evaluate(async()=>{
   const T=await import('/node_modules/three/build/three.module.js');const r=window.sceneRuntime,c=r.camera;
   const xy=r.simulation.units.map(u=>u.start);const xs=xy.map(p=>p[0]),zs=xy.map(p=>p[1]);
   const bounds={minX:Math.min(...xs)-1,maxX:Math.max(...xs)+1,minZ:Math.min(...zs)-1,maxZ:Math.max(...zs)+1};
   const h=Math.max(...Object.values(r.armies.audit).map(a=>a.calibration.targetHeadHeight))+1;
   const fit=center=>{c.position.set(0,240,center+100);c.lookAt(0,0,center);c.fov=42;c.zoom=1;c.updateProjectionMatrix();c.updateMatrixWorld(true);let z=100;
    for(const x of [bounds.minX,bounds.maxX])for(const y of [0,h])for(const d of [bounds.minZ,bounds.maxZ]){const p=new T.Vector3(x,y,d).project(c);z=Math.min(z,.94/Math.max(Math.abs(p.x),Math.abs(p.y)));}return z;};
   let a=-80,b=0;for(let i=0;i<45;i++){const p=a+(b-a)/3,q=b-(b-a)/3;if(fit(p)<fit(q))a=p;else b=q;}
   const center=(a+b)/2,zoom=fit(center);return {position:[0,240,center+100],target:[0,0,center],fov:42,zoom,bounds,marginNdc:.94,method:'Fixed perspective fit of unchanged opening formation + model height; no runtime refit.'};
  });
  fs.mkdirSync(`${out}/${variant}`,{recursive:true});const states=[];
  for(let f=0;f<90;f++){
   const audit=await page.evaluate(async({t,fixed})=>{
    window.renderAt(t);const r=window.sceneRuntime,c=r.camera;c.position.fromArray(fixed.position);c.lookAt(...fixed.target);c.fov=fixed.fov;c.zoom=fixed.zoom;c.updateMatrixWorld(true);c.updateProjectionMatrix();r.renderer.render(r.scene,c);r.renderer.getContext().finish();
    const b=window.lastBehavior;return {time:t,position:c.position.toArray(),quaternion:c.quaternion.toArray(),fov:c.fov,zoom:c.zoom,projection:c.projectionMatrix.toArray(),redMoving:b.slice(r.simulation.blueCount).filter(u=>u.speed>.02).length,blueMoving:b.slice(0,r.simulation.blueCount).filter(u=>u.speed>.02).length};
   },{t:f/60,fixed});states.push(audit);
   await page.locator('#view').screenshot({path:`${out}/${variant}/F${String(f).padStart(4,'0')}.png`});
  }
  const sig=x=>JSON.stringify([x.position,x.quaternion,x.fov,x.zoom,x.projection]);const constant=states.every(s=>sig(s)===sig(states[0]));
  fs.writeFileSync(`${out}/${variant}-camera.json`,JSON.stringify({variant,fixed,frames:states,constant,errors,nativeScene:'NewScene, UNCONFIRMED and visually mismatched; movement diagnostic only',visualWholeVideoWatched:false},null,2));
  if(!constant||errors.length)throw Error('Capture check failed');console.log(variant,'90 frames, fixed camera',fixed.zoom);await page.close();
 }
 fs.writeFileSync(`${out}/fixed-camera.json`,JSON.stringify(fixed,null,2));
}finally{await browser.close()}
