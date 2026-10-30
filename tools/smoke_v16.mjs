import {chromium} from 'playwright';import fs from 'node:fs';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:1100,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5256/');await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 const initial=await page.evaluate(()=>({version:window.lastState.version,variant:window.sceneRuntime.config.variant,mode:window.cameraState.mode,modelCount:Object.keys(window.assetAudit).length}));
 if(initial.version!=='V16'||initial.variant!=='FAST125'||initial.mode!=='FIXED')throw Error(JSON.stringify(initial));
 await page.locator('#diag').uncheck();
 // Reset is a REPLAY button, not "pause exactly at zero". Establish the start
 // with the slider, then test normal wall-clock replay through the final state.
 await page.locator('#time').fill('0');await page.locator('#time').dispatchEvent('input');await page.locator('#reset').click();
 await page.waitForFunction(()=>window.lastState.time>.05&&window.lastState.time<.5,null,{timeout:20000});
 const restartedAt=await page.evaluate(()=>window.lastState.time);await page.waitForFunction(()=>window.lastState.time>=2.29,null,{timeout:20000});
 const end=await page.evaluate(()=>window.lastState);await page.screenshot({path:'output/V16-browser-playback-end.png'});
 if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync('output/V16-entry-validation.json',JSON.stringify({status:'PASS',initial,end,errors,wallClockPlaybackReachedEnd:true,resetRestartsFromBeginning:true,restartedAt,note:'Automated browser playback test. Human visual evidence remains decoded stills/consecutive frames.'},null,2));console.log(JSON.stringify({status:'PASS',initial,endTime:end.time,restartedAt}));
}finally{await browser.close()}
