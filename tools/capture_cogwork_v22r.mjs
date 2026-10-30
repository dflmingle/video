import fs from 'node:fs';import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:1440,height:1600}});
 // Request substitution ONLY in this inspection page. Production module unchanged.
 await page.route('**/native-scenes/ArenaScene-scene/manifest.json',route=>route.fulfill({path:'public/native-scenes/CogworkWastes/manifest.json',contentType:'application/json'}));
 await page.route('**/native-scenes/ArenaScene-scene/mesh-*.bin',route=>route.fulfill({path:`public/native-scenes/CogworkWastes/${route.request().url().split('/').pop()}`,contentType:'application/octet-stream'}));
 await page.goto('http://127.0.0.1:5267/scene-native-v22.html?environment=ArenaScene&source=scene&view=combat');
 await page.waitForFunction(()=>window.ready||window.previewError,null,{timeout:120000});
 const state=await page.evaluate(()=>({source:window.nativePreview?.manifest.source,error:window.previewError}));
 if(state.error||!state.source.includes('CogworkWastes'))throw Error(JSON.stringify(state));
 await page.locator('#view').screenshot({path:'output/v22r-scenes/CogworkWastes-inspection.png'});console.log(state);
}finally{await browser.close()}
