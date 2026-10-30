import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {chromium} from 'playwright';
const port=5278,out='docs/repository-check';fs.mkdirSync(out,{recursive:true});
const server=spawn(process.execPath,['node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',String(port),'--strictPort'],{stdio:'pipe',windowsHide:true});
let browser;
try{
 for(let i=0;i<60;i++){
  try{const r=await fetch(`http://127.0.0.1:${port}/v22.html`);if(r.ok)break}catch{}
  await new Promise(resolve=>setTimeout(resolve,500));
 }
 browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:480,height:720}}),errors=[],failed=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&!r.url().endsWith('favicon.ico'))failed.push({url:r.url(),status:r.status()})});
 await page.goto(`http://127.0.0.1:${port}/v22.html?capture=1&variant=V22R-C1&presentation=approved-castle`);
 await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 const state=await page.evaluate(()=>{window.sceneRuntime.renderer.setSize(480,720);window.renderAt(2.3);return {...window.lastState,source:window.environmentAudit.manifest.source,units:window.sceneRuntime.simulation.units.length}});
 await page.locator('#view').screenshot({path:out+'/C1-copied-repository-2.3s.png'});
 fs.writeFileSync(out+'/runtime-check.json',JSON.stringify({checkedAt:new Date().toISOString(),port,variant:'V22R-C1',state,errors,failed,scope:'Copied repository runtime load and one actual browser screenshot; not continuation visual acceptance'},null,2));
 if(errors.length||failed.length)throw Error(JSON.stringify({errors,failed}));
 console.log(JSON.stringify({ready:true,units:state.units,source:state.source,errors,failed}));
}finally{if(browser)await browser.close();server.kill()}
