import fs from 'node:fs';import crypto from 'node:crypto';import {chromium} from 'playwright';
const variant=process.argv[2]||'FAST125',mode=process.argv[3]||'FIXED',probe=process.argv.includes('--probe'),preview=process.argv.includes('--preview'),D=`variants/${variant}`,C=JSON.parse(fs.readFileSync(`${D}/params.json`,'utf8')),fps=preview?30:C.fps,N=Math.ceil(C.duration*fps),tag=`${variant}-${mode}${probe?'-probe':preview?'-preview':''}`,out=`output/captures/${tag}`;
const names=['src/main-camera.js','src/camera-v16.js','src/assets-v11.js','src/environment-v11.js','tools/motion_v16.py','tools/build_simulation_v16.py','tools/capture_v16.mjs',`${D}/params.json`,`${D}/simulation.json`,`${D}/trajectories.f32`,`${D}/red-control.f32`,`${D}/gait-cycles.f32`,`${D}/hit-times.f32`];
const inputs=Object.fromEntries(names.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')]));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:C.width,height:C.height}}),errors=[],loads=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&/Shader Error|WebGLProgram|GL_INVALID/.test(m.text()))errors.push(m.text().slice(0,600))});page.on('response',r=>{if(/runtime\/(archer|sword|flail|samurai)\.(fbx|png)/.test(r.url()))loads.push({url:r.url(),status:r.status()})});
 await page.goto(`http://127.0.0.1:5256/camera.html?capture=1&variant=${variant}&camera=${mode}`);await page.waitForFunction(()=>window.ready,null,{timeout:240000});fs.mkdirSync(`${out}/frames`,{recursive:true});
 const frames=[],states=[],costs=[],samples=probe?[0,.5,1.,1.5,Math.min(2,C.duration-1/60),C.duration-1/60]:Array.from({length:N},(_,i)=>Math.min(C.duration-1/60,i/fps));
 for(let f=0;f<samples.length;f++){
  const start=performance.now(),data=await page.evaluate(async t=>{
   const begin=performance.now(),state=window.renderAt(t),r=window.sceneRuntime,{T}=await import('/src/probe-helper.js');r.renderer.getContext().finish();
   const rows=window.lastBehavior.map(a=>{const p=new T.Vector3(a.x,.7,a.z).project(r.camera),q=new T.Vector3(a.x,1.4,a.z).project(r.camera);return{...a,screenX:(p.x+1)*r.config.width/2,screenY:(1-p.y)*r.config.height/2,visible:Math.abs(p.x)<.98&&Math.abs(p.y)<.97&&Math.abs(p.z)<1,heightPixels:Math.abs(q.y-p.y)*r.config.height/2}});
   const live=rows.filter(a=>a.index>=r.simulation.blueCount&&r.simulation.units[a.index].army===2&&a.state!=='DEAD').sort((a,b)=>b.z-a.z),front=live.slice(0,Math.max(18,Math.ceil(live.length*.20))),blue=rows.slice(0,r.simulation.blueCount);
   return{state,rows,renderMs:performance.now()-begin,frontVisible:front.filter(a=>a.visible).length/front.length,blueVisible:blue.filter(a=>a.visible).length/blue.length,frontHeight:front.reduce((s,a)=>s+a.heightPixels,0)/front.length};
  },samples[f]);states.push({...data.state,frontVisible:data.frontVisible,blueVisible:data.blueVisible,frontHeightPixels:data.frontHeight});frames.push(data.rows);costs.push(data.renderMs);
  await page.locator('#view').screenshot({path:`${out}/frames/F${String(f).padStart(4,'0')}.png`});if(f%60===0)console.log(tag,f,samples[f].toFixed(3),'front',data.frontVisible.toFixed(2),'blue',data.blueVisible.toFixed(2));
 }
 const seeks=[];if(!probe){for(const f of[N-1,Math.min(33,N-1),Math.floor(N*.65)]){await page.evaluate(t=>window.renderAt(t),samples[f]);const png=await page.locator('#view').screenshot();seeks.push({frame:f,identical:png.equals(fs.readFileSync(`${out}/frames/F${String(f).padStart(4,'0')}.png`))})}}
 fs.writeFileSync(`${out}/render-checks.json`,JSON.stringify({version:'V16',variant,mode,tag,fps,sampleTimes:samples,inputs,states,frames,errors,loads,seeks,renderMs:costs}));fs.writeFileSync(`${out}/asset-render-audit.json`,JSON.stringify({models:await page.evaluate(()=>window.assetAudit),requests:loads,errors}));if(errors.length||seeks.some(s=>!s.identical))throw new Error(JSON.stringify({errors,seeks}));
 console.log(JSON.stringify({tag,minFrontVisible:Math.min(...states.map(s=>s.frontVisible)),minBlueVisible:Math.min(...states.map(s=>s.blueVisible)),frontHeightRange:[Math.min(...states.map(s=>s.frontHeightPixels)),Math.max(...states.map(s=>s.frontHeightPixels))]}));
}finally{await browser.close()}
