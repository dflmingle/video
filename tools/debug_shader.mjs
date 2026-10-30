import {chromium} from 'playwright';
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{const p=await browser.newPage();p.on('console',m=>{if(m.type()==='error')console.log(m.text().slice(0,4000))});await p.goto('http://127.0.0.1:5254/camera.html?capture=1&variant=FINAL');await p.waitForFunction(()=>window.ready,null,{timeout:240000});await p.evaluate(()=>window.renderAt(1.4));}finally{await browser.close()}
