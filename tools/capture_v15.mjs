import fs from 'node:fs';import crypto from 'node:crypto';import {chromium} from 'playwright';
const variant=process.argv[2]||'LOCAL',local=variant==='LOCAL',D=`variants/${variant}`,C=JSON.parse(fs.readFileSync(`${D}/params.json`,'utf8')),N=Math.round(C.duration*C.fps),width=local?1100:C.width,height=local?1100:C.height;
const names=['src/main-camera.js','src/assets-v11.js','src/environment-v11.js','tools/motion_v15.py','tools/build_simulation_v15.py','tools/capture_v15.mjs',`${D}/params.json`,`${D}/simulation.json`,`${D}/trajectories.f32`,`${D}/red-control.f32`,`${D}/gait-cycles.f32`,`${D}/hit-times.f32`];
const inputs=Object.fromEntries(names.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width,height}}),errors=[],loads=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader Error|WebGLProgram|GL_INVALID/.test(m.text()))errors.push(m.text().slice(0,600))});page.on('response',r=>{if(/runtime\/(archer|sword|flail|samurai)\.(fbx|png)/.test(r.url()))loads.push({url:r.url(),status:r.status()})});
 await page.goto(`http://127.0.0.1:5255/camera.html?capture=1&variant=${variant}`);await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 fs.mkdirSync(`${D}/frames`,{recursive:true});const frames=[],states=[],costs=[],renderCosts=[];
 async function draw(f){return await page.evaluate(async({t,local,width,height})=>{
  const begin=performance.now();const state=window.renderAt(t),r=window.sceneRuntime;let pts=[];
  if(local){const {T}=await import('/src/probe-helper.js');const alive=r.simulation.units.map((u,i)=>({u,i})).filter(({u})=>u.deathTime===null||u.deathTime>t),points=alive.map(({i})=>r.row(t,i)),x=points.reduce((s,p)=>s+p[0],0)/points.length,z=points.reduce((s,p)=>s+p[1],0)/points.length;r.renderer.setSize(width,height);r.camera.aspect=1;r.camera.fov=42;r.camera.zoom=1.03;r.camera.position.set(x,23,z+7);r.camera.lookAt(x,0,z);r.camera.updateMatrixWorld(true);r.camera.updateProjectionMatrix();r.renderer.render(r.scene,r.camera);pts=window.lastBehavior.map(a=>{const v=new T.Vector3(a.x,.7,a.z).project(r.camera);return{...a,screenX:(v.x+1)*width/2,screenY:(1-v.y)*height/2}})}
  r.renderer.getContext().finish();return{state,behavior:local?pts:window.lastBehavior,renderMs:performance.now()-begin,info:{calls:r.renderer.info.render.calls,triangles:r.renderer.info.render.triangles}}
 },{t:f/C.fps,local,width,height})}
 for(let f=0;f<N;f++){const start=performance.now(),data=await draw(f);states.push(data.state);frames.push(data.behavior);renderCosts.push(data.renderMs);await page.locator('#view').screenshot({path:`${D}/frames/F${String(f).padStart(4,'0')}.png`});costs.push(performance.now()-start);if(f%60===0)console.log(variant,f,'arrows',data.state.arrows,'renderMs',data.renderMs.toFixed(1),'calls',data.info.calls)}
 const seeks=[];for(const f of[N-1,35,Math.floor(N*.65)]){await draw(f);const png=await page.locator('#view').screenshot();seeks.push({frame:f,identical:png.equals(fs.readFileSync(`${D}/frames/F${String(f).padStart(4,'0')}.png`))})}
 fs.writeFileSync(`${D}/render-checks.json`,JSON.stringify({version:'V15',variant,inputs,states,frames,errors,loads,seeks,frameCaptureMs:costs,renderMs:renderCosts}));fs.writeFileSync(`${D}/asset-render-audit.json`,JSON.stringify({models:await page.evaluate(()=>window.assetAudit),requests:loads,errors}));
 if(errors.length||seeks.some(s=>!s.identical))throw new Error(JSON.stringify({errors,seeks}));
}finally{await browser.close()}
