import fs from 'node:fs';
import {chromium} from 'playwright';
const b=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const result={};
try{
 for(const shot of ['A','B']){
  const p=await b.newPage({viewport:{width:1080,height:1440}});
  await p.goto(`http://127.0.0.1:5250/?capture=1&variant=FINAL&shot=${shot}`);
  await p.waitForFunction(()=>window.ready,null,{timeout:240000});
  result[shot]=await p.evaluate(async()=>{
   const {T}=await import('/src/probe-helper.js'),r=window.sceneRuntime,S=r.simulation,C=r.config;
   const project=(x,y,z)=>{const q=new T.Vector3(x,y,z).project(r.camera);return[(q.x+1)*C.width/2,(1-q.y)*C.height/2]};
   return[0,.5,1.5,1.8,2.4,2.8,3.3,3.8,3.9,4.2666666667].map(t=>{
    window.renderAt(t);const out=[];
    for(let army=0;army<3;army++){
     const ids=S.units.flatMap((u,i)=>i>=S.blueCount&&u.army===army?[i]:[]);
     const centers=ids.map(i=>r.row(t,i));
     const heights=centers.map(q=>{const a=project(q[0],1.38,q[1]),b=project(q[0],0,q[1]);return Math.hypot(a[0]-b[0],a[1]-b[1])}).sort((a,b)=>a-b);
     out.push({army,nominalHeightPxMedian:heights[Math.floor(heights.length/2)],centerScreens:centers.map(q=>project(q[0],.7,q[1]))});
    }
    return{time:t,armies:out};
   });
  });
  await p.close();
 }
}finally{await b.close()}
fs.writeFileSync('output/camera-projection-measurements.json',JSON.stringify(result,null,2));
