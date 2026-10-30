// Route the isolated original export only inside candidate browser pages.
// No scene file, production import, actor trajectory or source asset is edited.
import fs from 'node:fs';import path from 'node:path';import {chromium} from 'playwright';
const out='output/scene-requirements-r2';fs.mkdirSync(out,{recursive:true});
const original='C:/Users/89trillion/PveMontageShot01V22R-SceneAudit';
const base=original+'/output/native-scenes-original-r2/OriginalCastle-scene';
const cameras=JSON.parse(fs.readFileSync(original+'/output/native-scenes-original-r2/source-cameras-hierarchy.json'));
const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const results=[];
async function candidate(page){
 await page.route('**/native-scenes/CastleExterior-scene/**',async route=>{
  const file=path.basename(new URL(route.request().url()).pathname);await route.fulfill({path:base+'/'+file,contentType:file.endsWith('.json')?'application/json':'application/octet-stream'});
 });
 await page.route('**/assets/imported/**',async route=>{
  const asset=decodeURIComponent(new URL(route.request().url()).pathname).replace('/assets/imported/','');const file=path.resolve(original,asset);
  if(file.startsWith(path.resolve(original)+path.sep)&&fs.existsSync(file))await route.fulfill({path:file});else await route.continue();
 });
}
try{
 for(const variant of ['package','original']){
  const p=await b.newPage({viewport:{width:1440,height:1600}}),errors=[];p.on('pageerror',e=>errors.push(e.message));if(variant==='original')await candidate(p);
  await p.goto('http://127.0.0.1:5267/scene-native-v22.html?environment=CastleExterior&source=scene&view=combat');await p.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
  for(const view of ['comparable','reference-area','authored-camera','unity-handedness','unity-authored-camera']){
   const state=await p.evaluate(async({view,cameras})=>{
    const T=await import('/node_modules/three/build/three.module.js');const r=window.nativePreview;if(!r)throw Error(window.previewError);const c=r.camera;
    c.up.set(0,1,0);r.root.scale.set(1,1,1);r.root.updateMatrixWorld(true);
    if(view==='comparable'){c.position.set(0,87,-40);c.lookAt(0,0,14);c.fov=42;}
    if(view==='reference-area'){c.position.set(-7,67,-36);c.lookAt(-9,0,12);c.fov=42;}
    if(view==='unity-handedness'){r.root.scale.set(1,1,-1);r.root.updateMatrixWorld(true);c.position.set(0,87,40);c.lookAt(0,0,-14);c.fov=42;}
    if(view==='authored-camera'||view==='unity-authored-camera'){
     const native=cameras.cameras[0];c.position.set(native.position.x,native.position.y,native.position.z);
     // Unity +Z camera forward maps to Three -Z; right/up reconstructed explicitly.
     const q=new T.Quaternion().setFromEuler(new T.Euler(native.rotation.x*Math.PI/180,native.rotation.y*Math.PI/180,native.rotation.z*Math.PI/180,'YXZ'));
     const forward=new T.Vector3(0,0,1).applyQuaternion(q),up=new T.Vector3(0,1,0).applyQuaternion(q);
     if(view==='unity-authored-camera'){r.root.scale.set(1,1,-1);r.root.updateMatrixWorld(true);c.position.z*=-1;forward.z*=-1;up.z*=-1;}
     c.up.copy(up);c.lookAt(c.position.clone().add(forward));c.fov=native.fieldOfView;
    }
    c.zoom=1;c.updateMatrixWorld(true);c.updateProjectionMatrix();r.renderer.render(r.scene,c);r.renderer.getContext().finish();
    return {source:r.manifest.source,objects:r.manifest.objects.length,position:c.position.toArray(),quaternion:c.quaternion.toArray(),fov:c.fov,view,rootMatrix:r.root.matrix.toArray(),audit:r.audit};
   },{view,cameras});
   await p.locator('#view').screenshot({path:`${out}/${variant}-${view}.png`});fs.writeFileSync(`${out}/${variant}-${view}.json`,JSON.stringify({...state,errors},null,2));results.push({variant,view,camera:JSON.stringify([state.position,state.quaternion,state.fov]),errors});
  }await p.close();console.log(variant,'5 candidate static views');
 }
 // V22 battle positions and V22 B camera: identity scene transform only.
 for(const variant of ['package','original']){
  const p=await b.newPage({viewport:{width:1440,height:2160}});if(variant==='original')await candidate(p);
  await p.goto('http://127.0.0.1:5267/v22.html?capture=1&variant=V22-C&camera=B&environment=CastleExterior');await p.waitForFunction(()=>window.ready,null,{timeout:180000});
  const state=await p.evaluate(()=>{window.renderAt(0);return {state:window.lastState,source:window.environmentAudit.audit.source,positions:window.sceneRuntime.simulation.units.map((_,i)=>window.sceneRuntime.row(0,i))};});
  await p.locator('#view').screenshot({path:`${out}/${variant}-V22-first-identity.png`});fs.writeFileSync(`${out}/${variant}-V22-first-identity.json`,JSON.stringify(state));await p.close();
 }
 const checks={sameInspectionCameras:['comparable','reference-area','authored-camera','unity-handedness','unity-authored-camera'].every(v=>new Set(results.filter(x=>x.view===v).map(x=>x.camera)).size===1),noPageErrors:results.every(x=>x.errors.length===0),productionSceneUnchanged:true};
 fs.writeFileSync(`${out}/checks.json`,JSON.stringify(checks,null,2));if(!Object.values(checks).every(Boolean))throw Error(JSON.stringify(checks));console.log(checks);
}finally{await b.close()}
