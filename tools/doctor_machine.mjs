import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {chromium} from 'playwright';
import {projectRoot,pythonCommand,browserOptions} from './machine-runtime.mjs';
process.chdir(projectRoot);
let failures=0;const checks=[];
function check(name,passed,detail=''){checks.push({name,passed,detail});console.log(`${passed?'OK':'FAIL'} ${name}${detail?' — '+detail:''}`);if(!passed)failures++}
const [major,minor]=process.versions.node.split('.').map(Number);
check('Node.js',major>=20&&!(major===20&&minor<19)&&!(major===22&&minor<12),process.versions.node);
const lfs=spawnSync('git',['lfs','version'],{encoding:'utf8',windowsHide:true});check('Git LFS',lfs.status===0,lfs.stdout?.trim());
const files=['assets/runtime/manifest.json','public/native-scenes/CastleExterior-scene/manifest.json','variants/V22R-C1/simulation.json','variants/V22R-C1-checkpoint/continuation-checkpoint.pkl','variants/V22R-C1-melee/simulation.json','source-materials/PVE混剪.unitypackage'];
for(const p of files)check(p,fs.existsSync(p)&&fs.statSync(p).size>1024);
const py=String.raw`
import sys,json,pickle,importlib.metadata as md
from pathlib import Path
sys.path.insert(0,str(Path('tools').resolve()))
assert sys.version_info[:2]==(3,12), 'Use Python 3.12 for the saved C1 checkpoint'
versions={p:md.version(p) for p in ['numpy','scipy','osqp','Pillow','opencv-python','imageio-ffmpeg']}
with open('variants/V22R-C1-checkpoint/continuation-checkpoint.pkl','rb') as f:ck=pickle.load(f)
assert ck['frame']==159 and ck['motion'].n==972 and ck['archers'].n==252
print(json.dumps(dict(python=sys.version.split()[0],packages=versions,checkpointFrame=ck['frame'])))
`;
const r=spawnSync(pythonCommand(),['-X','utf8','-c',py],{encoding:'utf8',windowsHide:true});
check('Python dependencies and C1 checkpoint',r.status===0,(r.stdout||r.stderr||r.error?.message||'').trim().slice(-2200));
let browser;
try{
 browser=await chromium.launch(browserOptions());const page=await browser.newPage();await page.setContent('<canvas id="view"></canvas>');
 const webgl=await page.evaluate(()=>!!document.querySelector('canvas').getContext('webgl2'));
 check('Google Chrome / WebGL2',webgl,await browser.version());
}catch(e){check('Google Chrome / WebGL2',false,'Install current stable Google Chrome, or set VIDEO_CHROME. '+e.message.slice(0,600))}
finally{if(browser)await browser.close()}
console.log(`\n${checks.length-failures}/${checks.length} passed. ${failures?'Run npm run setup after resolving the failed items.':'Ready for npm start.'}`);
process.exitCode=failures?1:0;
