import fs from 'node:fs';import {chromium} from 'playwright';
const C=JSON.parse(fs.readFileSync('variants/FINAL/params.json','utf8')),N=Math.round(C.duration*60),browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:960,height:960}});await page.goto('http://127.0.0.1:5253/camera.html?capture=1&variant=FINAL');await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 const groups=await page.evaluate(()=>{const s=window.sceneRuntime.simulation;return {blue:Array.from({length:16},(_,i)=>i),red:s.units.map((u,i)=>({u,i})).filter(x=>x.i>=s.blueCount&&x.u.army===2&&x.u.platoon===24).slice(0,16).map(x=>x.i)}});
 for(const [team,ids]of Object.entries(groups)){
  if(ids.length!==16)throw new Error('Need same-squad 16 members');const dir=`variants/FINAL/behavior-${team}`;fs.mkdirSync(dir,{recursive:true});const records=[];
  for(let f=0;f<N;f++){
   const state=await page.evaluate(async({t,ids})=>{const {T}=await import('/src/probe-helper.js');window.renderAt(t);const r=window.sceneRuntime,pts=ids.map(i=>r.row(t,i)),x=pts.reduce((s,p)=>s+p[0],0)/pts.length,z=pts.reduce((s,p)=>s+p[1],0)/pts.length;
    r.renderer.setSize(960,960);r.camera.aspect=1;r.camera.fov=42;r.camera.zoom=1.25;r.camera.position.set(x,19,z+8);r.camera.lookAt(x,0,z);r.camera.updateMatrixWorld(true);r.camera.updateProjectionMatrix();r.renderer.render(r.scene,r.camera);
    return ids.map(i=>{const a=window.lastBehavior[i],v=new T.Vector3(a.x,.7,a.z).project(r.camera);return {...a,screenX:(v.x+1)*480,screenY:(1-v.y)*480}});
   },{t:f/60,ids});records.push(state);await page.locator('#view').screenshot({path:`${dir}/F${String(f).padStart(4,'0')}.png`});if(f%60===0)console.log(team,f);
  }
  fs.writeFileSync(`${dir}/states.json`,JSON.stringify({team,indices:ids,frames:records}));
 }
}finally{await browser.close()}
