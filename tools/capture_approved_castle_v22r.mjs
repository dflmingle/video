import fs from 'node:fs';import {chromium} from 'playwright';
const out='output/v22r-approved-castle';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const errors=[],logs=[];
try{
 const p=await browser.newPage({viewport:{width:1440,height:2160}});p.on('pageerror',e=>errors.push(e.message));
 await p.goto('http://127.0.0.1:5267/scene-native-v22.html?preset=castle-approved&capture=1');await p.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
 for(const grid of [true,false]){
  const audit=await p.evaluate(grid=>{
   const r=window.nativePreview;if(!r)throw Error(window.previewError);for(const mesh of r.root.children)if(/(^|\/)Gird$/.test(mesh.name))mesh.visible=grid;
   r.renderer.render(r.scene,r.camera);r.renderer.getContext().finish();return {grid,source:r.manifest.source,objects:r.root.children.map(m=>({name:m.name,visible:m.visible,matrix:m.matrix.toArray()})),camera:{position:r.camera.position.toArray(),quaternion:r.camera.quaternion.toArray(),projection:r.camera.projectionMatrix.toArray(),fov:r.camera.fov,zoom:r.camera.zoom},rootMatrix:r.root.matrix.toArray(),textureBindings:r.audit.textureBindings};
  },grid);logs.push(audit);await p.locator('#view').screenshot({path:`${out}/scene-grid-${grid?'on':'off'}.png`});
 }
 const fixed=await p.evaluate(()=>{const r=window.nativePreview;return {position:r.camera.position.toArray(),quaternion:r.camera.quaternion.toArray(),projection:r.camera.projectionMatrix.toArray(),zoom:r.camera.zoom,fov:r.camera.fov};});
 const cameraLog=await p.evaluate(()=>{const r=window.nativePreview,c=r.camera,a=[];for(let f=0;f<192;f++){r.renderer.render(r.scene,c);a.push({frame:f,time:f/60,position:c.position.toArray(),quaternion:c.quaternion.toArray(),projection:c.projectionMatrix.toArray(),zoom:c.zoom,fov:c.fov});}return a;});
 await p.close();
 const q=await browser.newPage({viewport:{width:1440,height:2160}});q.on('pageerror',e=>errors.push(e.message));
 await q.goto('http://127.0.0.1:5267/v22.html?capture=1&variant=V22R-overlap&camera=B&environment=CastleExterior&grid=0');await q.waitForFunction(()=>window.ready,null,{timeout:180000});
 const battle=[];
 for(const time of [0,.75,1.5,2.183333333333333]){
  const a=await q.evaluate(({time,fixed})=>{
   window.renderAt(time);const r=window.sceneRuntime,c=r.camera;
   c.position.fromArray(fixed.position);c.quaternion.fromArray(fixed.quaternion);c.fov=fixed.fov;c.zoom=fixed.zoom;c.projectionMatrix.fromArray(fixed.projection);c.projectionMatrixInverse.copy(c.projectionMatrix).invert();c.updateMatrixWorld(true);
   // Candidate-only coordinate-basis conversion, keep all mesh-local matrices.
   const e=window.environmentAudit;e.root.scale.set(1,1,-1);e.root.updateMatrixWorld(true);r.renderer.render(r.scene,c);r.renderer.getContext().finish();
   return {time,worldRows:r.simulation.units.map((_,i)=>r.row(time,i)),camera:{position:c.position.toArray(),quaternion:c.quaternion.toArray(),projection:c.projectionMatrix.toArray()},gridObjects:e.root.children.filter(m=>/(^|\/)Gird$/.test(m.name)).map(m=>({name:m.name,visible:m.visible})),note:'Composition diagnostic: unchanged actor coordinates and world speed; no approved environment-to-battle placement yet.'};
  },{time,fixed});battle.push(a);await q.locator('#view').screenshot({path:`${out}/battle-${time.toFixed(3)}.png`});
 }await q.close();
 const sig=x=>JSON.stringify([x.position,x.quaternion,x.projection,x.zoom,x.fov]);
 const report={scene:logs,fixedCameraOver192Frames:cameraLog.every(x=>sig(x)===sig(cameraLog[0])),cameraLog,battle,errors,gridOff:logs[1].objects.filter(x=>/(^|\/)Gird$/.test(x.name)).every(x=>!x.visible),geometryUnchanged:logs[0].objects.every((x,i)=>JSON.stringify(x.matrix)===JSON.stringify(logs[1].objects[i].matrix)),cameraSameGridAB:sig(logs[0].camera)===sig(logs[1].camera),note:'192-frame scene-only camera audit is not a completed battle video or 3-second combat validation.'};
 fs.writeFileSync(`${out}/checks.json`,JSON.stringify(report,null,2));if(!report.gridOff||!report.geometryUnchanged||!report.cameraSameGridAB||errors.length)throw Error('Approved scene check failed');console.log({gridOff:report.gridOff,geometryUnchanged:report.geometryUnchanged,fixedCamera:report.fixedCameraOver192Frames,errors});
}finally{await browser.close()}
