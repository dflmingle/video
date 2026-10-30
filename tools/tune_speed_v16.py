from pathlib import Path
import json
P=Path(__file__).resolve().parents[1]
for name in ['BASE100','FAST125','FAST150']:
 p=P/f'variants/{name}/params.json';c=json.loads(p.read_text());m=c['chargeMultiplier'];c['runStride']=3.565*(1+.16*(m-1));c['runLean']=.22+.06*(m-1);p.write_text(json.dumps(c,indent=2))
