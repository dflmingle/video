from pathlib import Path
P=Path(__file__).resolve().parents[1]
s=(P/'tools/capture_v16.mjs').read_text(encoding='utf-8').replace("||'FAST125'","||'FINAL'").replace('5256','5257').replace('camera-v16.js','camera-v17.js').replace('assets-v11.js','assets-v17.js').replace('motion_v16.py','motion_v17.py').replace('build_simulation_v16.py','build_simulation_v17.py').replace('capture_v16.mjs','capture_v17.mjs').replace("version:'V16'","version:'V17'").replace("`${D}/hit-times.f32`","`${D}/hit-times.f32`,`${D}/blue-control.f32`,'tools/archers_v17.py'")
(P/'tools/capture_v17.mjs').write_text(s,encoding='utf-8')
s=(P/'tools/media_v16.py').read_text(encoding='utf-8').replace("f'V16-","f'V17-")
(P/'tools/media_v17.py').write_text(s,encoding='utf-8')
