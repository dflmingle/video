from pathlib import Path
P=Path(__file__).resolve().parents[1];p=P/'src/main-camera.js';s=p.read_text(encoding='utf-8')
s="import {createBattleCamera} from './camera-v16.js';\n"+s
a=s.index('const cameraSchedule=[];');b=s.index('window.environmentAudit=',a)
s=s[:a]+'''const battleCamera=createBattleCamera(S,C,pos),cameraSchedule=battleCamera.centers;
function setCamera(t){window.cameraState=battleCamera.apply(camera,t)}
'''+s[b:]
s=s.replace("version:'V15'","version:'V16'")
s=s.replace('cameraZoom:camera.zoom,arrows:', 'cameraZoom:camera.zoom,battleCamera:window.cameraState,arrows:')
p.write_text(s,encoding='utf-8')
