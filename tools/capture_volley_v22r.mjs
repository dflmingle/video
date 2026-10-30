import fs from 'node:fs';import {chromium} from 'playwright';
const arg=(name,fallback)=>{const k=process.argv.indexOf(name);return k<0?fallback:process.argv[k+1]};
const probe=process.argv.includes('--probe'),variant=arg('--variant','V22R-volley'),out=arg('--out',`output/v22r-volley/${probe?'probe':'preview'}`);fs.mkdirSync(out+'/frames',{recursive:true});
const width=720,height=1080,fps=60,c=JSON.parse(fs.readFileSync(`variants/${variant}/params.json`));
const times=probe?[0,.15,.4,40/60,1,1.5,2,2.5,3,3.5,239/60].filter(t=>t<c.duration):Array.from({length:Math.floor(c.duration*fps)},(_,f)=>f/fps);
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[],consoleErrors=[],frames=[];
try{
 const p=await browser.newPage({viewport:{width,height}});p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text().slice(0,1600));});
 await p.route('**/favicon.ico',route=>route.fulfill({status:204,body:''}));
 await p.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=${variant}&presentation=approved-castle`);await p.waitForFunction(()=>window.ready,null,{timeout:240000});
 await p.evaluate(({width,height})=>window.sceneRuntime.renderer.setSize(width,height),{width,height});
 const setup=await p.evaluate(()=>({environmentSource:window.environmentAudit.manifest.source,grid:window.environmentAudit.root.children.filter(m=>/(^|\/)Gird$/.test(m.name)).map(m=>({path:m.name,visible:m.visible})),environmentMatrix:window.environmentAudit.root.matrix.toArray(),locomotion:window.assetAudit.archer.locomotionLayer}));
 for(let i=0;i<times.length;i++){
  const audit=await p.evaluate(async({t,width,height})=>{
   window.renderAt(t);const r=window.sceneRuntime,c=r.camera,T=await import('/node_modules/three/build/three.module.js');r.renderer.getContext().finish();
   const rows=window.lastBehavior.map(b=>{const p=new T.Vector3(b.x,0,b.z).project(c);return {id:b.id,team:r.simulation.units[b.index].team,color:r.simulation.units[b.index].color,group:r.simulation.units[b.index].group,action:b.action,state:b.state,releaseEvent:b.releaseEventId,speed:b.speed,visible:Math.abs(p.x)<=1&&Math.abs(p.y)<=1,x:b.x,z:b.z,screen:[(p.x+1)*width/2,(1-p.y)*height/2]};});
   const blue=rows.slice(0,r.simulation.blueCount),red=rows.slice(r.simulation.blueCount);
   return {time:t,camera:{position:c.position.toArray(),quaternion:c.quaternion.toArray(),projection:c.projectionMatrix.toArray(),fov:c.fov,zoom:c.zoom},blueVisible:blue.filter(b=>b.visible).length,redVisible:red.filter(b=>b.visible).length,redMoving:red.filter(b=>b.speed>.02).length,blueMoving:blue.filter(b=>b.speed>.02).length,blueStates:Object.fromEntries([...new Set(blue.map(b=>b.state))].map(s=>[s,blue.filter(b=>b.state===s).length])),arrows:window.lastState.arrows,aliveRed:window.lastState.aliveRed,rows};
  },{t:times[i],width,height});frames.push(audit);await p.locator('#view').screenshot({path:`${out}/frames/F${String(i).padStart(4,'0')}.png`});if(i%40===0)console.log(probe?'PROBE':'PREVIEW',i,'/',times.length);
 }
 const signature=q=>JSON.stringify(q.camera),constant=frames.every(q=>signature(q)===signature(frames[0]));
 fs.writeFileSync(out+'/audit.json',JSON.stringify({variant,width,height,fps,times,setup,frames,constant,errors,consoleErrors},null,2));
 if(errors.length||consoleErrors.length||!constant)throw Error(JSON.stringify({errors,consoleErrors,constant}));console.log(JSON.stringify({out,frames:frames.length,constant,blueVisibleMin:Math.min(...frames.map(f=>f.blueVisible)),redVisibleMin:Math.min(...frames.map(f=>f.redVisible))}));
}finally{await browser.close()}
