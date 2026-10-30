// Runs before node_modules exists; uses only Node built-ins.
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {projectRoot} from './machine-runtime.mjs';
process.chdir(projectRoot);
function run(command,args){
 console.log(`\n> ${command} ${args.join(' ')}`);
 const r=spawnSync(command,args,{stdio:'inherit',windowsHide:true});
 if(r.error||r.status!==0)throw new Error(r.error?.message||`Command failed (${r.status})`);
}
try{
 const [major,minor]=process.versions.node.split('.').map(Number);
 if(major<20||major===20&&minor<19||major===22&&minor<12)throw Error('Install Node.js 22.12+ (22 LTS recommended).');
 run('git',['lfs','install','--local']);run('git',['lfs','pull']);
 const archive=path.join(projectRoot,'source-materials','PVE混剪.unitypackage');
 if(!fs.existsSync(archive)||fs.statSync(archive).size<1000000)throw Error('UnityPackage is missing or still an LFS pointer. Check GitHub login and git lfs pull.');
 // npm provides its actual JS entry point, avoiding platform-specific npm.cmd.
 const npmCLI=process.env.npm_execpath;
 if(!npmCLI)throw Error('Run this installer using: npm run setup');
 run(process.execPath,[npmCLI,'ci','--no-audit','--no-fund']);
 let py=process.env.VIDEO_PYTHON;
 if(!py){
  for(const candidate of process.platform==='win32'?['python','python3']:['python3','python']){
   const r=spawnSync(candidate,['-c','import sys; print(sys.version_info[:2]); raise SystemExit(0 if sys.version_info[:2]==(3,12) else 1)'],{encoding:'utf8',windowsHide:true});
   if(!r.error&&r.status===0){py=candidate;break}
  }
 }
 if(!py)throw Error('Install Python 3.12, or set VIDEO_PYTHON to its executable path.');
 run(py,['-c','import sys; assert sys.version_info[:2]==(3,12), "Use Python 3.12 for the saved C1 checkpoint"']);
 const local=path.join(projectRoot,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 if(!fs.existsSync(local))run(py,['-m','venv','.venv']);
 run(local,['-m','pip','install','-r','requirements.txt']);
 // Production poses are checked in current stable Google Chrome. An older
 // bundled Chromium loaded the page but failed to draw the archer bodies.
 // Never install/replace the user's system browser from this script.
 if(process.env.VIDEO_BROWSER==='chromium'&&!process.env.VIDEO_CHROME)
  run(process.execPath,['node_modules/playwright/cli.js','install',...(process.platform==='linux'?['--with-deps']:[]),'--no-shell','chromium']);
 run(local,['-X','utf8','restore_evidence.py']);
 run(process.execPath,['tools/doctor_machine.mjs']);
 console.log('\nReady. Run npm start, then open the URLs in CONTINUE-HERE.md. No simulation was recomputed.');
}catch(error){console.error(`\nSetup stopped: ${error.message}`);process.exitCode=1}
