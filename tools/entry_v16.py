from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
for name in ['camera.html','index.html']:
 p=P/name;s=p.read_text(encoding='utf-8').replace('set("variant","FINAL")','set("variant","FAST125")').replace('<title>PVE 第一段','<title>PVE V16 第一段')
 p.write_text(s,encoding='utf-8')
p=P/'package.json';c=json.loads(p.read_text());c['scripts']['build']='vite build';p.write_text(json.dumps(c,indent=2))
