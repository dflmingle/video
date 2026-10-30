import fs from 'node:fs';import {chromium} from 'playwright';
import {browserOptions,battleURL,projectRoot} from './machine-runtime.mjs';
process.chdir(projectRoot);
const arg=(n,d)=>{const k=process.argv.indexOf(n);return k<0?d:process.argv[k+1]};
const variant=arg('--variant','V22R-C1-melee'),out=arg('--out','output/v22r-melee/preview');
const width=+arg('--width','480'),height=width*1.5,fps=60,probe=process.argv.includes('--probe');
const c=JSON.parse(fs.readFileSync(`variants/${variant}/params.json`));
const times=probe?[0,2.3,2.65,3,3.5,4,5,6,8,10,12,15,20,25,c.duration-1/60].filter(t=>t<c.duration):Array.from({length:Math.round(c.duration*fps)},(_,f)=>f/fps);
fs.mkdirSync(out+'/frames',{recursive:true});
const browser=await chromium.launch(browserOptions(arg('--chrome',process.env.VIDEO_CHROME)));
const errors=[],frames=[];
try{
 const p=await browser.newPage({viewport:{width,height}});p.on('pageerror',e=>errors.push(e.message));
 await p.route('**/favicon.ico',r=>r.fulfill({status:204,body:''}));
 await p.goto(`${battleURL()}/v22.html?capture=1&variant=${encodeURIComponent(variant)}&presentation=approved-castle`);
 await p.waitForFunction(()=>window.ready,null,{timeout:240000});
 await p.evaluate(({width,height})=>window.sceneRuntime.renderer.setSize(width,height),{width,height});
 for(let i=0;i<times.length;i++){
  const state=await p.evaluate(t=>{window.renderAt(t);window.sceneRuntime.renderer.getContext().finish();return {...window.lastState,blueDead:window.lastBehavior.filter(b=>b.index<252&&b.state==='DEAD').length,melee:window.lastBehavior.filter(b=>b.action==='attack'&&b.index>=252).length}},times[i]);
  frames.push(state);await p.locator('#view').screenshot({path:`${out}/frames/F${String(i).padStart(4,'0')}.png`});
  if(i%120===0)console.log('CAPTURE',i,'/',times.length);
 }
 const key=f=>JSON.stringify([f.cameraPosition,f.cameraQuaternion,f.cameraProjection,f.cameraZoom]);
 const constant=frames.every(f=>key(f)===key(frames[0]));
 fs.writeFileSync(out+'/audit.json',JSON.stringify({variant,width,height,fps,times,constant,errors,frames}));
 if(errors.length||!constant)throw Error(JSON.stringify({errors,constant}));
 console.log(JSON.stringify({out,frames:frames.length,constant,errors}));
}finally{await browser.close()}
