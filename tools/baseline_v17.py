from pathlib import Path
import shutil,json
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V16';D=P/'variants/BASELINE';D.mkdir(exist_ok=True)
for f in (B/'variants/FAST125').glob('*'):
 if f.is_file():shutil.copy2(f,D/f.name)
C=json.loads((D/'params.json').read_text());new=json.loads((P/'variants/FINAL/params.json').read_text())
for k in ['cameraZoom','cameraFixedCenterZ','cameraPushZoom','cameraPushCenterZ']:C[k]=new[k]
C['variant']='BASELINE';(D/'params.json').write_text(json.dumps(C,indent=2))
s=(B/'src/main-camera.js').read_text(encoding='utf-8').replace('./camera-v16.js','./camera-v17.js');(P/'src/main-v16-samecamera.js').write_text(s,encoding='utf-8')
s=(P/'camera.html').read_text(encoding='utf-8').replace('/src/main-camera.js','/src/main-v16-samecamera.js');(P/'baseline.html').write_text(s,encoding='utf-8')
p=P/'tools/capture_v17.mjs';s=p.read_text(encoding='utf-8').replace('/camera.html?capture=1',"/${variant==='BASELINE'?'baseline.html':'camera.html'}?capture=1")
s=s.replace("`${D}/blue-control.f32`,'tools/archers_v17.py'","'tools/archers_v17.py','src/main-v16-samecamera.js'")
s=s.replace("'tools/archers_v17.py','src/main-v16-samecamera.js'","'tools/archers_v17.py','src/main-v16-samecamera.js',...(variant==='BASELINE'?[]:[`${D}/blue-control.f32`])")
p.write_text(s,encoding='utf-8')
