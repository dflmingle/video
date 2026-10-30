// Direct output of the user-approved scene/view and retained safe battle data.
// No trajectory changes, retiming, position fitting, or invented combat events.
import fs from 'node:fs';import crypto from 'node:crypto';import {chromium} from 'playwright';
const variant=process.argv[2]||'V22R-overlap',out=process.argv[3]||'output/V22R-final';fs.mkdirSync(out+'/frames',{recursive:true});
const params=JSON.parse(fs.readFileSync(`variants/${variant}/params.json`));
const fps=60,total=Math.round(params.duration*fps);
const hashes=Object.fromEntries(['params.json','simulation.json','trajectories.f32','blue-control.f32','red-control.f32'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(`variants/${variant}/${n}`)).digest('hex')]));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[],frames=[];
try{
 const page=await browser.newPage({viewport:{width:1440,height:2160}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=${variant}&camera=B&environment=CastleExterior&grid=0`);await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 const setup=await page.evaluate(async()=>{
  const {approvedCastle:a}=await import('/src/castle-approved-v22r.js');const r=window.sceneRuntime,e=window.environmentAudit;
  e.root.scale.set(1,1,-1);e.root.updateMatrixWorld(true);
  const c=r.camera;c.position.fromArray(a.camera.position);c.lookAt(...a.camera.target);c.fov=a.camera.fov;c.zoom=a.camera.zoom;c.updateMatrixWorld(true);c.updateProjectionMatrix();
  window.finalCastleCamera={position:c.position.clone(),quaternion:c.quaternion.clone(),fov:c.fov,zoom:c.zoom,projection:c.projectionMatrix.clone()};
  return {source:e.manifest.source,sceneObjectCount:e.root.children.length,grid:e.root.children.filter(m=>/(^|\/)Gird$/.test(m.name)).map(m=>({path:m.name,visible:m.visible})),sceneMatrix:e.root.matrix.toArray(),camera:a.camera,width:a.width,height:a.height,models:window.assetAudit,renderPipeline:'Existing Three.js renderer with native Unity-evaluated scene geometry/matrices and original asset textures; not a Unity shader/shadow-equivalent capture.'};
 });
 if(setup.grid.length!==1||setup.grid[0].visible)throw Error('Gird was not disabled');
 for(let f=0;f<total;f++){
  const state=await page.evaluate(({f,fps})=>{
   const t=f/fps;window.renderAt(t);const r=window.sceneRuntime,c=r.camera,a=window.finalCastleCamera;c.position.copy(a.position);c.quaternion.copy(a.quaternion);c.fov=a.fov;c.zoom=a.zoom;c.projectionMatrix.copy(a.projection);c.projectionMatrixInverse.copy(c.projectionMatrix).invert();c.updateMatrixWorld(true);r.renderer.render(r.scene,c);r.renderer.getContext().finish();
   const b=window.lastBehavior,nb=r.simulation.blueCount;
   return {frame:f,time:t,position:c.position.toArray(),quaternion:c.quaternion.toArray(),projection:c.projectionMatrix.toArray(),fov:c.fov,zoom:c.zoom,redMoving:b.slice(nb).filter(x=>x.speed>.02).length,blueMoving:b.slice(0,nb).filter(x=>x.speed>.02).length,realReleases:r.simulation.events.filter(e=>e.release<=t).length,realImpacts:r.simulation.events.filter(e=>e.resolution==='IMPACT_IN_SHOT'&&e.impact<=t).length,arrows:window.lastState.arrows,aliveRed:window.lastState.aliveRed};
  },{f,fps});frames.push(state);await page.locator('#view').screenshot({path:`${out}/frames/F${String(f).padStart(4,'0')}.png`});if(f%30===0)console.log('FINAL_FRAME',f,'/',total);
 }
 const sig=s=>JSON.stringify([s.position,s.quaternion,s.projection,s.fov,s.zoom]);
 const report={variant,fps,width:1440,height:2160,totalFrames:total,duration:total/fps,sourceHashes:hashes,setup,frames,cameraConstant:frames.every(f=>sig(f)===sig(frames[0])),errors,limitations:['Current safe trajectory ends at 2.20 seconds; 2.8–3.2-second combat requirement is not met.','No real impact occurs before this safe cut; arrows are not retimed and impacts are not fabricated.','Accepted close view crops rear red troops at opening; native wall crosses the original red approach. This is the retained approved-view output, not a passed battle-space integration.'],scope:'User requested direct final video output after scene/view confirmation. Battle simulation, initial positions, speeds, animation phases, event bindings, and safe cutoff remain unchanged.'};
 fs.writeFileSync(out+'/render-audit.json',JSON.stringify(report,null,2));if(errors.length||!report.cameraConstant)throw Error('Render audit failed');console.log(JSON.stringify({out,frames:total,cameraConstant:report.cameraConstant,errors}));
}finally{await browser.close()}
