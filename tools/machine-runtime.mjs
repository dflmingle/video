// Shared by portable capture/check tools. No machine-specific Chrome path.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
export const projectRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export function pythonCommand(){
 const local=path.join(projectRoot,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 return fs.existsSync(local)?local:process.env.VIDEO_PYTHON||(process.platform==='win32'?'python':'python3');
}
export function browserOptions(executablePath=process.env.VIDEO_CHROME){
 return {headless:true,...(executablePath?{executablePath}:{channel:process.env.VIDEO_BROWSER||'chrome'}),args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']};
}
export const battleURL=()=>process.env.VIDEO_URL||'http://127.0.0.1:5267';
