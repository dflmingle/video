import fs from 'node:fs';
import {chromium} from 'playwright';
const variant='FINAL', port=5258, D=`variants/${variant}`;
const C=JSON.parse(fs.readFileSync(`${D}/params.json`,'utf8'));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
  const page=await browser.newPage({viewport:{width:960,height:960}});
  await page.goto(`http://127.0.0.1:${port}/camera.html?capture=1&variant=${variant}&camera=FIXED`);
  await page.waitForFunction(()=>window.ready,null,{timeout:240000});
  const groups=await page.evaluate(()=>{const s=window.sceneRuntime.simulation; const m=new Map(); for(let i=0;i<s.blueCount;i++){const g=s.units[i].group; if(!m.has(g))m.set(g,[]);m.get(g).push(i);} return [...m].map(([group,ids])=>({group,ids}));});
  const chosen=[groups[0],groups[Math.floor(groups.length/2)],groups[groups.length-1]];
  fs.mkdirSync('output/archer-diagnostics',{recursive:true});
  const manifest=[];
  for(const item of chosen){
    const tag=item.group===chosen[0].group?'left':item.group===chosen[1].group?'center':'right';
    const dir=`output/archer-diagnostics/${tag}`;fs.mkdirSync(`${dir}/frames`,{recursive:true});
    for(let f=0;f<Math.ceil(C.duration*30);f++){
      const t=Math.min(C.duration-1/C.fps,f/30);
      const data=await page.evaluate(({t,ids})=>{
        const r=window.sceneRuntime; window.renderAt(t); const {T}=window;
        const pts=ids.map(i=>r.row(t,i)); const cx=pts.reduce((s,p)=>s+p[0],0)/pts.length, cz=pts.reduce((s,p)=>s+p[1],0)/pts.length;
        r.renderer.setSize(960,960);r.camera.aspect=1;r.camera.fov=42;r.camera.position.set(cx,48,cz+23);r.camera.lookAt(cx,0,cz);r.camera.zoom=5.8;r.camera.updateMatrixWorld(true);r.camera.updateProjectionMatrix();r.renderer.render(r.scene,r.camera);
        return {time:t,center:[cx,cz],rows:ids.map(i=>window.lastBehavior[i])};
      },{t,ids:item.ids});
      await page.locator('#view').screenshot({path:`${dir}/frames/F${String(f).padStart(4,'0')}.png`});
      manifest.push({tag,frame:f,...data});
    }
  }
  fs.writeFileSync('output/archer-diagnostics/state-timeline.json',JSON.stringify({chosen,manifest},null,2));
  console.log(JSON.stringify({chosen,frames:Math.ceil(C.duration*30)}));
} finally {await browser.close()}
