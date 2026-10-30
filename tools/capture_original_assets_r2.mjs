import fs from 'node:fs';import path from 'node:path';import {chromium} from 'playwright';
const root='C:/Users/89trillion/PveMontageShot01V22R-SceneAudit',out='output/scene-requirements-r2';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{for(const name of ['CastleExterior_Flag','CastleExterior_Fence_01','CastleExterior_Fence_02','CastleExterior_Castle']){
 const base=`${root}/output/native-scenes-original-r2/${name}-asset-only`;
 const page=await browser.newPage({viewport:{width:720,height:720}});
 await page.route('**/native-scenes/CastleExterior-scene/**',route=>route.fulfill({path:base+'/'+path.basename(new URL(route.request().url()).pathname),contentType:route.request().url().endsWith('.json')?'application/json':'application/octet-stream'}));
 await page.route('**/assets/imported/**',async route=>{const file=root+'/'+decodeURIComponent(new URL(route.request().url()).pathname).replace('/assets/imported/','');if(fs.existsSync(file))await route.fulfill({path:file});else await route.continue();});
 await page.goto('http://127.0.0.1:5267/scene-native-v22.html?environment=CastleExterior&source=scene&view=combat');await page.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
 const audit=await page.evaluate(async()=>{
  const T=await import('/node_modules/three/build/three.module.js'),r=window.nativePreview;if(!r)throw Error(window.previewError);
  r.root.scale.set(1,1,-1);r.root.updateMatrixWorld(true);const box=new T.Box3().setFromObject(r.root),center=box.getCenter(new T.Vector3()),size=box.getSize(new T.Vector3());
  const dim=Math.max(size.x,size.y,size.z),c=r.camera;c.aspect=1;c.fov=38;c.zoom=1;c.near=Math.min(.001,dim*.001);c.position.copy(center).add(new T.Vector3(dim*.20,dim*.65,-dim*1.5));c.lookAt(center);c.updateProjectionMatrix();c.updateMatrixWorld(true);r.renderer.setSize(720,720);r.scene.background=new T.Color(0x30383f);r.renderer.render(r.scene,c);r.renderer.getContext().finish();
  return {source:r.manifest.source,bounds:{center:center.toArray(),size:size.toArray()},objects:r.manifest.objects.length,materials:r.manifest.materials.map(m=>({path:m.path,texture:m.texturePath})),note:'Asset-only inspection; no scene assembly or object rearrangement.'};
 });await page.locator('#view').screenshot({path:`${out}/${name}-asset-only.png`});fs.writeFileSync(`${out}/${name}-asset-only.json`,JSON.stringify(audit,null,2));console.log(name,audit.objects);await page.close();
}}finally{await browser.close()}
