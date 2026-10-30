import fs from 'node:fs';import {chromium} from 'playwright';
const gi=process.argv.indexOf('--group'),group=gi<0?'depth':process.argv[gi+1],doc=`docs/v22r-${group}`,out=`output/v22r-${group}`;
const setup=JSON.parse(fs.readFileSync(`${doc}/setup.json`));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const results=[];
try{
 for(const c of setup.candidates){
  const p=await browser.newPage({viewport:{width:720,height:1080}});
  await p.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=${c.variant}-opening&presentation=approved-castle`);await p.waitForFunction(()=>window.ready,null,{timeout:240000});
  const r=await p.evaluate(()=>{
   const e=window.environmentAudit;
   return {objects:e.root.children.map(o=>({path:o.name,matrixWorld:o.matrixWorld.toArray(),scale:o.scale.toArray(),visible:o.visible,materials:o.material.map(m=>m.name)})),source:e.audit.source,warnings:e.audit.warnings,textureBindings:e.audit.textureBindings,camera:window.cameraState};
  });results.push({label:c.label,...r});await p.close();
 }
 // Old D2 has no sceneLayout: its scene matrices must remain the original ones.
 const p=await browser.newPage({viewport:{width:720,height:1080}});
 await p.goto('http://127.0.0.1:5267/v22.html?capture=1&variant=V22R-distance-D2&presentation=approved-castle');await p.waitForFunction(()=>window.ready,null,{timeout:240000});
 const baseline=await p.evaluate(()=>({objects:window.environmentAudit.root.children.map(o=>({path:o.name,matrixWorld:o.matrixWorld.toArray()})),camera:window.cameraState}));
 await p.evaluate(()=>{window.sceneRuntime.renderer.setSize(720,1080);window.renderAt(0);window.sceneRuntime.renderer.getContext().finish()});
 await p.locator('#view').screenshot({path:`${out}/D2-current-environment-regression.png`});
 fs.writeFileSync(`${doc}/D2-environment-regression.json`,JSON.stringify(baseline,null,2));await p.close();
 fs.writeFileSync(`${doc}/environment-runtime.json`,JSON.stringify(results,null,2));
 console.log('ENVIRONMENT_RUNTIME',results.map(r=>({label:r.label,objects:r.objects.length,camera:r.camera})));
}finally{await browser.close()}
