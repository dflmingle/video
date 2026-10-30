import {spawnSync} from 'node:child_process';
import {pythonCommand,projectRoot} from './machine-runtime.mjs';
const result=spawnSync(pythonCommand(),['-X','utf8',...process.argv.slice(2)],{cwd:projectRoot,stdio:'inherit',windowsHide:true});
if(result.error){console.error(result.error.message);process.exit(1)}
process.exit(result.status??1);
