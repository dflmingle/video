"""Bounded deterministic timing experiments. No source asset or start edit."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1];base=json.loads((R/'variants/V22-C/params.json').read_text())
cases={'V22R-extended':dict(duration=4.2,redChargeStart=1.),'V22R-immediate':dict(duration=4.2,redChargeStart=0.),'V22R-overlap':dict(duration=4.2,redChargeStart=0.,openingRedStartWindow=.04,openingBlueStartWindow=.09)}
for name,override in cases.items():
    d=R/'variants'/name;d.mkdir(exist_ok=True);(d/'params.json').write_text(json.dumps(dict(base,**override),indent=2),encoding='utf8')
print('Prepared',list(cases),'-- simulations auto-cut; no 4-second promise')
