// Static diagnostic only. Never changes actor arrays, camera rules or source assets.
import fs from 'node:fs';
import {chromium} from 'playwright';
const out='output/v22r-scenes';fs.mkdirSync(out,{recursive:true});
const sim=JSON.parse(fs.readFileSync('variants/V22-C/simulation.json'));
const times=[0,1.3,Math.min(...sim.events.map(e=>e.release)),Math.min(...sim.events.map(e=>e.impact))];
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const results=[];
try{
 for(const environment of ['NewScene','CastleExterior','ArenaScene']){
  const page=await browser.newPage({viewport:{width:1440,height:2160}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=V22-C&camera=B&environment=${environment}`);
  await page.waitForFunction(()=>window.ready,null,{timeout:180000});
  for(let i=0;i<times.length;i++){
   const audit=await page.evaluate(t=>{window.renderAt(t);const r=window.sceneRuntime;r.renderer.getContext().finish();return {time:t,camera:window.lastState,environment:window.environmentAudit.audit,positions:r.simulation.units.map((u,j)=>r.row(t,j))};},times[i]);
   const name=`${environment}-${i}`;
   await page.locator('#view').screenshot({path:`${out}/${name}.png`});
   fs.writeFileSync(`${out}/${name}.json`,JSON.stringify(audit));
   results.push({environment,index:i,time:times[i],camera:JSON.stringify([audit.camera.cameraPosition,audit.camera.cameraQuaternion,audit.camera.cameraProjection]),positions:JSON.stringify(audit.positions),errors});
  }
  await page.close();console.log(environment,'4 static frames');
 }
 for(const environment of ['CastleExterior','ArenaScene','NewScene']){
  const page=await browser.newPage({viewport:{width:1440,height:1600}});
  await page.goto(`http://127.0.0.1:5267/scene-native-v22.html?source=scene&view=${environment==='NewScene'?'castle':'combat'}&environment=${environment}`);
  await page.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
  const info=await page.evaluate(()=>({error:window.previewError,camera:window.nativePreview?.camera.position.toArray(),target:'inspection camera only'}));
  if(info.error)throw Error(info.error);
  await page.locator('#view').screenshot({path:`${out}/${environment}-inspection.png`});
  fs.writeFileSync(`${out}/${environment}-inspection.json`,JSON.stringify(info));await page.close();
 }
 const checks={sameActorPositions:times.every((_,i)=>new Set(results.filter(x=>x.index===i).map(x=>x.positions)).size===1),sameCamera:times.every((_,i)=>new Set(results.filter(x=>x.index===i).map(x=>x.camera)).size===1),noPageErrors:results.every(x=>x.errors.length===0)};
 fs.writeFileSync(`${out}/checks.json`,JSON.stringify({times,checks,notes:'V22 dynamic B camera retained for IDENTICAL baseline comparison. Not a fixed-camera acceptance or final scene replacement.'},null,2));
 if(!Object.values(checks).every(Boolean))throw Error(JSON.stringify(checks));console.log(checks);
}finally{await browser.close()}
