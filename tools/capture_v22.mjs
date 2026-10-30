import fs from 'node:fs';import {chromium} from 'playwright';
const args=process.argv.slice(2).filter(x=>!x.startsWith('--')),variant=args[0]||'V22-C',camera=args[1]||'B',detail=args[2]||'',probe=process.argv.includes('--probe');
const baseUrl=process.argv.find(x=>x.startsWith('--url='))?.split('=')[1]||'http://127.0.0.1:5262';
const dir=`variants/${variant}`,C=JSON.parse(fs.readFileSync(`${dir}/params.json`)),tag=process.argv.find(x=>x.startsWith('--tag='))?.split('=')[1]||'',out=`output/captures/${variant}-${camera}${detail?'-'+detail:''}${tag?'-'+tag:''}${probe?'-probe':''}`;
const option=(name,fallback)=>process.argv.find(x=>x.startsWith(`--${name}=`))?.split('=')[1]??fallback;
const captureFps=Number(option('fps',C.fps)),width=Number(option('width',C.width)),height=Math.round(width*C.height/C.width);
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width,height}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const environment=process.argv.find(x=>x.startsWith('--environment='))?.split('=')[1]||'';
 await page.goto(`${baseUrl}/v22.html?capture=1&variant=${variant}&camera=${camera}${environment?`&environment=${environment}`:''}`);await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 await page.evaluate(({width,height})=>{window.sceneRuntime.renderer.setSize(width,height)}, {width,height});
 const explicit=process.argv.find(x=>x.startsWith('--times='))?.split('=')[1]?.split(',').map(Number).filter(Number.isFinite);
 const times=explicit?.length?explicit:probe?[0,.7,1.5,2.4,2.733333,3.,C.duration-1/60]:Array.from({length:Math.ceil(C.duration*captureFps)},(_,i)=>i/captureFps);
 fs.mkdirSync(`${out}/frames`,{recursive:true});const states=[];
 for(let i=0;i<times.length;i++){
  const result=await page.evaluate(async({t,detail,probe,width,height})=>{
   window.renderAt(t);const r=window.sceneRuntime,{T}=await import('/src/probe-helper.js');
   if(detail){
    const g={left:0,center:3,right:6}[detail]??0,us=r.simulation.units.slice(0,r.simulation.blueCount).map((u,i)=>({...u,i})).filter(u=>u.group===g);
    const pts=us.map(u=>r.row(t,u.i)),x=pts.reduce((s,p)=>s+p[0],0)/pts.length,z=pts.reduce((s,p)=>s+p[1],0)/pts.length;
    r.camera.position.set(x,19,z+13);r.camera.lookAt(x,0,z);r.camera.zoom=1;r.camera.updateProjectionMatrix();r.camera.updateMatrixWorld(true);r.renderer.render(r.scene,r.camera);
   }
   r.renderer.getContext().finish();
   const rows=window.lastBehavior.map(a=>{const p=new T.Vector3(a.x,0,a.z).project(r.camera),q=new T.Vector3(a.x,r.armies.audit[r.simulation.units[a.index].model].calibration.targetHeadHeight,a.z).project(r.camera);return{id:a.id,index:a.index,state:a.state,phase:a.phaseFloat,release:a.releaseEventId,x:a.x,z:a.z,speed:a.speed,screenX:(p.x+1)*width/2,screenY:(1-p.y)*height/2,heightPx:Math.abs(q.y-p.y)*height/2,visible:Math.abs(p.x)<.98&&Math.abs(p.y)<.98}});
   const yellow=rows.filter(a=>a.index>=r.simulation.blueCount&&r.simulation.units[a.index].color==='yellow').sort((a,b)=>b.z-a.z).slice(0,36),blue=rows.slice(0,r.simulation.blueCount);
   return {t,camera:window.cameraState,frontVisible:yellow.filter(x=>x.visible).length/yellow.length,blueVisible:blue.filter(x=>x.visible).length/blue.length,frontHeightPx:yellow.reduce((s,x)=>s+x.heightPx,0)/yellow.length,rows:probe?rows:rows.slice(0,r.simulation.blueCount)};
  },{t:times[i],detail,probe,width,height});states.push(result);
  await page.locator('#view').screenshot({path:`${out}/frames/F${String(i).padStart(4,'0')}.png`});if(i%60===0)console.log(out,i,times[i].toFixed(3));
 }
 fs.writeFileSync(`${out}/audit.json`,JSON.stringify({variant,camera,detail,sourceDuration:C.duration,fps:captureFps,width,height,times,states,errors}));if(errors.length)throw Error(errors.join('\n'));console.log(JSON.stringify({out,frames:times.length,minFrontVisible:Math.min(...states.map(x=>x.frontVisible))}));
}finally{await browser.close()}
