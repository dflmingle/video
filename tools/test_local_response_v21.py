from pathlib import Path
import json, numpy as np, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from local_response_v21 import LocalResponseV21
P=Path(__file__).resolve().parents[1]; D=P/'variants/FINAL'; S=json.loads((D/'simulation.json').read_text(encoding='utf8')); units=S['units'][S['blueCount']:]; C=S['config']; n=len(units)
R=LocalResponseV21(units,C); pos=np.array([u['start'] for u in units],float); hp=np.full(n,C['redHitPoints']); alive=hp>0
# Baseline: no hit keeps a positive forward intent and zero response pressure.
a=R.update(0.,pos,hp=hp,alive=alive); assert np.all(a['forwardIntent'][alive]>0.0); assert float(a['hitPressure'].max())==0.0
# One local hit should not propagate a speed multiplier to healthy neighbors.
R.record_hit(0,1,.5,False); hp[0]-=1; alive[0]=True; b=R.update(.55,pos,hp=hp,alive=alive); assert b['speedMultiplier'][0] < 1.0; assert np.all(b['speedMultiplier'][1:]==1.0)
# Decay after the finite window.
c=R.update(2.0,pos,hp=hp,alive=alive); assert float(c['hitPressure'].max()) < float(b['hitPressure'].max())
# Stable avoidance side and cooldown.
s1=R.choose_avoidance_side(0,.55,1.2,.8,True); s2=R.choose_avoidance_side(0,.60,.4,1.5,False); assert s1==s2
# No reverse command is ever emitted.
assert np.all(b['forwardIntent']>=0.88)
out={'status':'PASS','squads':len(R.squad_members),'hitPressureAtHit':b['hitPressure'].tolist(),'hitPressureAfterDecay':c['hitPressure'].tolist(),'healthySpeedMultiplierUnique':sorted(set(b['speedMultiplier'][1:].tolist()))[:10],'stableAvoidSide':int(s1),'forwardIntentMin':float(b['forwardIntent'].min())}
(P/'output/V21-local-response-tests.json').write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps(out,indent=2))
