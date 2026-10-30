import fs from 'node:fs';
import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try {
 const p=await browser.newPage({viewport:{width:1440,height:2160}});
 await p.goto('http://127.0.0.1:5251/?capture=1&variant=FINAL');await p.waitForFunction(()=>window.ready,null,{timeout:240000});
 for(const [name,position] of [['high',[0,240,72]],['higher',[0,260,52]],['slightYaw',[35,250,62]]]) {
  const fit=await p.evaluate(async({position})=>{
   const {T}=await import('/src/probe-helper.js'),r=window.sceneRuntime,C=r.config;
   C.cameraPosition=position;C.cameraTarget=[0,0,-30];C.cameraZoom=1;C.cameraShiftX=0;C.cameraShiftY=0;window.renderAt(0);
   const box=new T.Box2();for(const t of [0,C.duration-1/C.fps])for(let i=0;i<r.simulation.units.length;i++) {
    const q=r.row(t,i);for(const y of[0,1.8]) {const v=new T.Vector3(q[0],y,q[1]).project(r.camera);box.expandByPoint(new T.Vector2(v.x,v.y));}
   }
   const size=box.getSize(new T.Vector2()),mid=box.getCenter(new T.Vector2());C.cameraZoom=Math.min(1.78/size.x,1.84/size.y);C.cameraShiftX=mid.x*C.cameraZoom;C.cameraShiftY=mid.y*C.cameraZoom;
   return {position,zoom:C.cameraZoom,x:C.cameraShiftX,y:C.cameraShiftY,elevation:Math.atan2(position[1],Math.hypot(position[0],position[2]+30))*180/Math.PI};
  },{position});
  fs.writeFileSync(`output/camera-${name}.json`,JSON.stringify(fit,null,2));
  for(const t of [0,2.8,4.18]){await p.evaluate(t=>window.renderAt(t),t);await p.locator('#view').screenshot({path:`output/camera-${name}-${t}.png`});}
 }
 fs.writeFileSync('output/camera-model-audit.json',JSON.stringify(await p.evaluate(()=>window.assetAudit)));
} finally {await browser.close();}
