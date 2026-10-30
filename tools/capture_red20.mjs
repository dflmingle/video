import fs from 'node:fs';import crypto from 'node:crypto';import {chromium} from 'playwright';
const C=JSON.parse(fs.readFileSync('variants/FINAL/params.json','utf8')),N=Math.round(C.duration*60),tracked=JSON.parse(fs.readFileSync('output/tracked-v14.json','utf8')),ids=tracked.indices;
const inputs=Object.fromEntries(['src/main-camera.js','src/assets-v11.js','variants/FINAL/simulation.json','variants/FINAL/red-control.f32','variants/FINAL/gait-cycles.f32','variants/FINAL/trajectories.f32','tools/capture_red20.mjs'].map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:1000,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader Error|WebGLProgram/.test(m.text()))errors.push(m.text().slice(0,400))});
 await page.goto('http://127.0.0.1:5254/camera.html?capture=1&variant=FINAL');await page.waitForFunction(()=>window.ready,null,{timeout:240000});const dir='variants/FINAL/red20-frames';fs.mkdirSync(dir,{recursive:true});const frames=[];
 for(let f=0;f<N;f++){
  frames.push(await page.evaluate(async({t,ids})=>{const{T}=await import('/src/probe-helper.js');window.renderAt(t);const r=window.sceneRuntime,pts=ids.map(i=>r.row(t,i)),x=pts.reduce((s,p)=>s+p[0],0)/pts.length,z=pts.reduce((s,p)=>s+p[1],0)/pts.length;
   r.renderer.setSize(1000,1000);r.camera.aspect=1;r.camera.fov=42;r.camera.zoom=1.08;r.camera.position.set(x,19,z+8);r.camera.lookAt(x,0,z);r.camera.updateMatrixWorld(true);r.camera.updateProjectionMatrix();r.renderer.render(r.scene,r.camera);
   return ids.map(i=>{const a=window.lastBehavior[i],v=new T.Vector3(a.x,.7,a.z).project(r.camera);return{...a,screenX:(v.x+1)*500,screenY:(1-v.y)*500}});
  },{t:f/60,ids}));await page.locator('#view').screenshot({path:`${dir}/F${String(f).padStart(4,'0')}.png`});if(f%60===0)console.log('red20',f);
 }
 fs.writeFileSync('variants/FINAL/red20-states.json',JSON.stringify({inputs,indices:ids,platoon:tracked.platoon,frames,errors}));if(errors.length)throw new Error(errors.join('\n'));
}finally{await browser.close()}
