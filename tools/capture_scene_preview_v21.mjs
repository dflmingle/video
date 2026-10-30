import fs from 'node:fs';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
  const page=await browser.newPage({viewport:{width:1440,height:2160}});
  await page.goto('http://127.0.0.1:5261/camera.html?capture=1&variant=V21');
  await page.waitForFunction(()=>window.ready,null,{timeout:240000});
  await page.evaluate(()=>{
    for(const b of window.sceneRuntime.armies.batches.values()) b.mesh.visible=false;
    window.sceneRuntime.scene.traverse(o=>{if(o.isInstancedMesh) o.visible=false;});
    window.renderAt(0);
  });
  fs.mkdirSync('output/V21-scene-preview',{recursive:true});
  await page.locator('#view').screenshot({path:'output/V21-scene-preview/formal-scene.png'});
} finally { await browser.close(); }
