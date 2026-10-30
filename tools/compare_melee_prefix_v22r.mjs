// Render the approved 159-frame C1 opening and compare decoded pixels.
// This audit records every difference. It deliberately has no visual tolerance.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {chromium} from 'playwright';
import {browserOptions,pythonCommand,battleURL} from './machine-runtime.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const arg=(name,fallback)=>{const k=process.argv.indexOf(name);return k<0?fallback:process.argv[k+1]};
const variant=arg('--variant','V22R-C1-melee');
const out=path.resolve(root,arg('--out','output/v22r-melee/prefix'));
const reference=path.resolve(root,arg('--reference','output/v22r-burst/C1-preview/frames'));
const url=arg('--url',battleURL());
const width=720,height=1080,fps=60,count=159;
const variantPath=path.join(root,'variants',variant);
for(const file of ['params.json','simulation.json'])if(!fs.existsSync(path.join(variantPath,file)))throw Error(`Missing continuation input: ${file}`);
for(let i=0;i<count;i++){
 const file=path.join(reference,`F${String(i).padStart(4,'0')}.png`);
 if(!fs.existsSync(file))throw Error(`Missing approved reference frame: ${file}`);
}
const config=JSON.parse(fs.readFileSync(path.join(variantPath,'params.json'),'utf8'));
const simulation=JSON.parse(fs.readFileSync(path.join(variantPath,'simulation.json'),'utf8'));
if(!config.meleeContinuation||!simulation.prefixEvents||!simulation.prefixShooterEvents)throw Error('Continuation prefix metadata is missing');
if(config.duration<2.65||simulation.frames<160)throw Error('Continuation does not contain the complete C1 opening');
fs.mkdirSync(path.join(out,'frames'),{recursive:true});
const errors=[],consoleErrors=[],frames=[];
const browser=await chromium.launch(browserOptions(arg('--chrome',process.env.VIDEO_CHROME)));
try{
 const page=await browser.newPage({viewport:{width,height}});
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')consoleErrors.push(m.text().slice(0,1200))});
 await page.route('**/favicon.ico',route=>route.fulfill({status:204,body:''}));
 await page.goto(`${url}/v22.html?capture=1&variant=${encodeURIComponent(variant)}&presentation=approved-castle`);
 await page.waitForFunction(()=>window.ready,null,{timeout:240000});
 await page.evaluate(({width,height})=>window.sceneRuntime.renderer.setSize(width,height),{width,height});
 const setup=await page.evaluate(()=>({environmentSource:window.environmentAudit.manifest.source,environmentMatrix:window.environmentAudit.root.matrix.toArray(),prefixCutTime:window.sceneRuntime.simulation.prefixCutTime}));
 for(let f=0;f<count;f++){
  const audit=await page.evaluate(t=>{
   window.renderAt(t);const r=window.sceneRuntime,c=r.camera;r.renderer.getContext().finish();
   return {time:t,camera:{position:c.position.toArray(),quaternion:c.quaternion.toArray(),projection:c.projectionMatrix.toArray(),fov:c.fov,zoom:c.zoom},arrows:window.lastState.arrows,aliveRed:window.lastState.aliveRed};
  },f/fps);
  frames.push(audit);
  await page.locator('#view').screenshot({path:path.join(out,'frames',`F${String(f).padStart(4,'0')}.png`)});
  if(f%30===0)console.log(`PREFIX ${f}/${count}`);
 }
 const constantCamera=frames.every(q=>JSON.stringify(q.camera)===JSON.stringify(frames[0].camera));
 fs.writeFileSync(path.join(out,'capture-audit.json'),JSON.stringify({variant,width,height,fps,count,setup,constantCamera,frames,errors,consoleErrors},null,2));
 if(errors.length||consoleErrors.length||!constantCamera)throw Error(JSON.stringify({errors,consoleErrors,constantCamera}));
}finally{await browser.close()}

// Use decoded PNG pixels, not PNG byte hashes. Independent WebGL contexts can
// exhibit isolated channel differences, but those remain reported as differences.
const python=String.raw`
import json, sys
from pathlib import Path
import cv2
import numpy as np
root, output, reference, variant = map(Path,sys.argv[1:])
rows=[]
for frame in range(159):
 name=f'F{frame:04}.png'
 a=cv2.imread(str(reference/name),cv2.IMREAD_COLOR)
 b=cv2.imread(str(output/'frames'/name),cv2.IMREAD_COLOR)
 if a is None or b is None or a.shape!=b.shape or a.shape!=(1080,720,3):
  raise RuntimeError(f'Frame input mismatch: {name}')
 d=np.abs(a.astype(np.int16)-b.astype(np.int16))
 rows.append(dict(frame=frame,time=frame/60,maximumChannelDifference=int(d.max()),meanChannelDifference=float(d.mean()),changedChannels=int(np.count_nonzero(d)),changedPixels=int(np.count_nonzero(np.any(d,axis=2)))))
arrays=[]
for name in ['trajectories','blue-control','red-control','gait-distance','gait-cycles','hit-times']:
 a=np.load(root/'variants'/'V22R-C1'/f'{name}.npy')
 candidate=variant/f'{name}.npy'
 if candidate.exists():
  b=np.load(candidate)
  exact=bool(a.shape[0]==160 and b.shape[0]>=160 and np.array_equal(a,b[:160]))
  arrays.append(dict(name=name,sourceFrames=int(a.shape[0]),exactOpening160States=exact))
 else:
  arrays.append(dict(name=name,exactOpening160States=False,error='Missing continuation npy audit input'))
report=dict(reference=str(reference),candidate=str(output/'frames'),frames=159,resolution=[720,1080],fps=60,exactPixels=all(q['changedChannels']==0 for q in rows),differentFrames=sum(q['changedChannels']>0 for q in rows),maximumChannelDifference=max(q['maximumChannelDifference'] for q in rows),meanChannelDifference=float(np.mean([q['meanChannelDifference'] for q in rows])),arrayChecks=arrays,exactData=all(q['exactOpening160States'] for q in arrays),toleranceApplied=False,scope='Pixel and authoritative array audit; event-prefix equivalence is separately required.',perFrame=rows)
(output/'pixel-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['perFrame','arrayChecks']},ensure_ascii=False))
if not report['exactData']:
 raise SystemExit('Authoritative C1 opening data changed')
`;
const result=spawnSync(arg('--python',pythonCommand()),['-X','utf8','-c',python,root,out,reference,variantPath],{cwd:root,encoding:'utf8',maxBuffer:1024*1024});
if(result.stdout)process.stdout.write(result.stdout);
if(result.stderr)process.stderr.write(result.stderr);
if(result.error)throw result.error;
if(result.status!==0)process.exitCode=result.status??1;
