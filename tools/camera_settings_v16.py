from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
for name in ['BASE100','FAST125','FAST150']:
 p=P/f'variants/{name}/params.json';c=json.loads(p.read_text());c.update(cameraZoom=2.7,cameraFixedCenterZ=-4.,cameraFollowMaxSpeed=2.);p.write_text(json.dumps(c,indent=2))
