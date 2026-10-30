// Candidate pages only: exact designated package -> Unity-evaluated export -> framebuffer.
import fs from 'node:fs';import path from 'node:path';import {chromium} from 'playwright';
const root='C:/Users/89trillion/PveMontageShot01V22R-PackageSceneAudit';
const out='output/scene-requirements-r2';fs.mkdirSync(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const checks=[];
const fixedOnly=process.argv.includes('--fixed-only');
async function routePackage(page,tag){
 await page.route('**/native-scenes/**',async route=>{
  const url=new URL(route.request().url());if(url.pathname.includes('/textures/'))return route.continue();
  const prefix=tag||url.pathname.split('/')[2];const file=`${root}/output/package-scenes-r2/${prefix}/${path.basename(url.pathname)}`;
  if(fs.existsSync(file))return route.fulfill({path:file,contentType:file.endsWith('.json')?'application/json':'application/octet-stream'});return route.continue();
 });
 await page.route('**/assets/imported/**',async route=>{
  const file=path.resolve(root,decodeURIComponent(new URL(route.request().url()).pathname).replace('/assets/imported/',''));
  if(file.startsWith(path.resolve(root)+path.sep)&&fs.existsSync(file))await route.fulfill({path:file});else await route.continue();
 });
}
try{
 for(const environment of fixedOnly?[]:['NewScene','CastleExterior','ArenaScene']){
  const p=await browser.newPage({viewport:{width:1440,height:1600}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await routePackage(p);
  await p.goto(`http://127.0.0.1:5267/scene-native-v22.html?environment=${environment}&source=scene&view=combat`);await p.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
  const state=await p.evaluate(()=>{const r=window.nativePreview;if(!r)throw Error(window.previewError);r.root.scale.set(1,1,-1);r.root.updateMatrixWorld(true);r.camera.position.set(0,87,40);r.camera.lookAt(0,0,-14);r.camera.updateMatrixWorld(true);r.camera.updateProjectionMatrix();r.renderer.render(r.scene,r.camera);r.renderer.getContext().finish();return {source:r.manifest.source,objects:r.manifest.objects.length,audit:r.audit,camera:{position:r.camera.position.toArray(),quaternion:r.camera.quaternion.toArray(),fov:r.camera.fov},candidateTransform:r.root.matrix.toArray()};});
  await p.locator('#view').screenshot({path:`${out}/exact-package-${environment}-inspection.png`});fs.writeFileSync(`${out}/exact-package-${environment}-inspection.json`,JSON.stringify({...state,errors},null,2));checks.push({environment,mode:'inspection',errors,camera:state.camera});await p.close();console.log('inspection',environment,state.objects);
 }
 for(const environment of ['NewScene','CastleExterior']){
  const p=await browser.newPage({viewport:{width:1440,height:2160}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await routePackage(p);
  await p.goto(`http://127.0.0.1:5267/v22.html?capture=1&variant=V22-C&camera=B&environment=${environment}`);await p.waitForFunction(()=>window.ready,null,{timeout:180000});
  if(fixedOnly)await p.evaluate(()=>{window.renderAt(0);const c=window.sceneRuntime.camera;window.fixedSceneAuditCamera={position:c.position.clone(),quaternion:c.quaternion.clone(),zoom:c.zoom,fov:c.fov,projection:c.projectionMatrix.clone(),projectionInverse:c.projectionMatrixInverse.clone()};});
  for(const [label,time] of [['first',0],['assembly',1.65],['release',145/60],['hit',164/60]]){
   const state=await p.evaluate(time=>{window.renderAt(time);const r=window.sceneRuntime,c=r.camera,f=window.fixedSceneAuditCamera;if(f){c.position.copy(f.position);c.quaternion.copy(f.quaternion);c.zoom=f.zoom;c.fov=f.fov;c.projectionMatrix.copy(f.projection);c.projectionMatrixInverse.copy(f.projectionInverse);c.updateMatrixWorld(true);r.renderer.render(r.scene,c);r.renderer.getContext().finish();}return {state:window.lastState,source:window.environmentAudit.audit.source,actualScreenshotCamera:{position:c.position.toArray(),quaternion:c.quaternion.toArray(),zoom:c.zoom,fov:c.fov,projection:c.projectionMatrix.toArray()},fixedCandidateOnly:!!f,rows:r.simulation.units.map((_,i)=>r.row(time,i))};},time);
   const prefix=fixedOnly?'V22-fixed':'V22';await p.locator('#view').screenshot({path:`${out}/exact-package-${environment}-${prefix}-${label}.png`});fs.writeFileSync(`${out}/exact-package-${environment}-${prefix}-${label}.json`,JSON.stringify({...state,time,errors}));checks.push({environment,mode:'battle',label,time,errors,camera:state.actualScreenshotCamera});
  }await p.close();console.log('V22 frozen frames',environment);
 }
 for(const model of fixedOnly?[]:['CastleExterior_Building','CastleExterior_Tree_04','CastleExterior_Tree_05','CastleExterior_Stakes_01','CastleExterior_Stakes_02']){
  const p=await browser.newPage({viewport:{width:720,height:720}});await routePackage(p,model+'-asset-only');await p.goto('http://127.0.0.1:5267/scene-native-v22.html?environment=CastleExterior&view=combat');await p.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
  const state=await p.evaluate(async()=>{
   const T=await import('/node_modules/three/build/three.module.js'),r=window.nativePreview;if(!r)throw Error(window.previewError);r.root.scale.set(1,1,-1);r.root.updateMatrixWorld(true);const box=new T.Box3().setFromObject(r.root),center=box.getCenter(new T.Vector3()),size=box.getSize(new T.Vector3()),dim=Math.max(size.x,size.y,size.z),c=r.camera;
   c.aspect=1;c.fov=38;c.position.copy(center).add(new T.Vector3(dim*.2,dim*.65,-dim*1.5));c.lookAt(center);c.updateProjectionMatrix();c.updateMatrixWorld(true);r.renderer.setSize(720,720);r.scene.background=new T.Color(0x30383f);r.renderer.render(r.scene,c);r.renderer.getContext().finish();return {source:r.manifest.source,objects:r.manifest.objects.length,bounds:{center:center.toArray(),size:size.toArray()},audit:r.audit};
  });await p.locator('#view').screenshot({path:`${out}/exact-package-${model}-asset.png`});fs.writeFileSync(`${out}/exact-package-${model}-asset.json`,JSON.stringify(state,null,2));await p.close();console.log('asset',model);
 }
 fs.writeFileSync(`${out}/exact-package${fixedOnly?'-fixed':''}-browser-checks.json`,JSON.stringify({checks,noPageErrors:checks.every(x=>!x.errors.length),sameCamera:fixedOnly?new Set(checks.map(x=>JSON.stringify(x.camera))).size===1:JSON.stringify(checks[0].camera)===JSON.stringify(checks[1].camera),sourcePolicy:'All candidate geometry/material textures routed from designated package-only project; source, simulation and production renderer unchanged. Environment-inspection handedness reflection is candidate only; battle frames use identity.'},null,2));
}finally{await browser.close()}
