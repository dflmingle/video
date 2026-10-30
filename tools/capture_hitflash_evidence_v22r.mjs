import fs from 'node:fs';import {chromium} from 'playwright';
const arg=(n,d)=>{const k=process.argv.indexOf(n);return k<0?d:process.argv[k+1]};
const variant=arg('--variant','V22R-frontfield'),out=arg('--out','output/v22r-frontfield/evidence');
const s=JSON.parse(fs.readFileSync(`variants/${variant}/simulation.json`));
const arrow=s.events.find(e=>e.damage>0&&e.release>=0),melee=s.meleeEvents.find(e=>e.damage>0);
const targets=[{type:'arrow',id:arrow.id,index:arrow.target,time:arrow.impact},{type:'melee',id:melee.id,index:melee.target,time:melee.time}];
fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[],rows=[];
try{
 const p=await browser.newPage({viewport:{width:720,height:1080}});p.on('pageerror',e=>errors.push(e.message));
 await p.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=${variant}&presentation=approved-castle`);await p.waitForFunction(()=>window.ready,null,{timeout:240000});
 await p.evaluate(()=>window.sceneRuntime.renderer.setSize(720,1080));
 const opening=await p.evaluate(async()=>{window.renderAt(0);const r=window.sceneRuntime,T=await import('/node_modules/three/build/three.module.js');return window.lastBehavior.map(b=>{const v=new T.Vector3(b.x,0,b.z).project(r.camera);return {id:b.id,x:b.x,z:b.z,screen:[(v.x+1)*360,(1-v.y)*540],visible:Math.abs(v.x)<1&&Math.abs(v.y)<1};});});
 await p.locator('#view').screenshot({path:out+'/opening.png'});
 const firstWave=s.events.filter(e=>e.release<=arrow.impact+.2).length;
 await p.evaluate(t=>window.renderAt(t),arrow.impact);await p.locator('#view').screenshot({path:out+'/first-volley.png'});
 for(const event of targets){
  for(const k of [-1,0,1,2,3,5,7,9]){
   const time=event.time+k/60;
   const data=await p.evaluate(async({time,event})=>{
    window.renderAt(time);const r=window.sceneRuntime,T=await import('/node_modules/three/build/three.module.js');r.renderer.getContext().finish();const b=window.lastBehavior[event.index],v=new T.Vector3(b.x,.7,b.z).project(r.camera);
    return {id:b.id,hitAge:b.hitAge,hitFlash:b.hitFlash,screen:[(v.x+1)*360,(1-v.y)*540],activeFlashIds:window.lastBehavior.filter(x=>x.hitFlash>0).map(x=>x.id)};
   },{time,event});
   const file=`${out}/${event.type}-${k<0?'before':String(k).padStart(2,'0')}.png`;
   await p.locator('#view').screenshot({path:file});rows.push({event,...data,time,frameOffset:k,file});
  }
 }
 fs.writeFileSync(out+'/evidence.json',JSON.stringify({variant,opening,targets,rows,firstWaveReleases:firstWave,errors}));
 console.log(JSON.stringify({variant,targets,openingVisible:opening.filter(x=>x.visible).length,total:opening.length,errors}));
}finally{await browser.close()}
