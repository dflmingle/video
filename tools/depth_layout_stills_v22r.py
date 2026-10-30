"""One-frame render copies; never overwrite any simulation seed/checkpoint."""
from pathlib import Path
import json,shutil,sys
P=Path(__file__).resolve().parents[1];group=sys.argv[sys.argv.index('--group')+1] if '--group' in sys.argv else 'depth';setup=json.loads((P/('docs/v22r-'+group)/'setup.json').read_text())
for case in setup['candidates']:
 src=P/'variants'/case['seed'];out=P/'variants'/(case['variant']+'-opening');out.mkdir(exist_ok=True)
 for f in src.glob('*.f32'):shutil.copyfile(f,out/f.name)
 c=json.loads((src/'params.json').read_text());c.update(duration=1/60,meleeContinuation=False)
 s=json.loads((src/'simulation.json').read_text());s['config']=c
 (out/'params.json').write_text(json.dumps(c),encoding='utf8');(out/'simulation.json').write_text(json.dumps(s),encoding='utf8')
