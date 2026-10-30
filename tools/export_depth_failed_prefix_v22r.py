"""Export only completed checkpoint frames; never include failed solver step."""
from pathlib import Path
import sys,json,pickle,copy,numpy as np
P=Path(__file__).resolve().parents[1];source=P/'variants/V22R-depth-E3-seed';out=P/'variants/V22R-depth-E3'
with (out/'progress-checkpoint.pkl').open('rb') as f:k=pickle.load(f)
assert k['f']==480
S=json.loads((source/'simulation.json').read_text());C=copy.deepcopy(S['config']);C.update(meleeContinuation=True,autoCut=False,duration=(k['f']+1)/60,continuationPolicy='C1_PREFIX_LOCKED_THEN_LOCAL_MELEE',previewFailure='BODY_SOLVER_RESIDUAL_8.016667_NOT_A_COMPLETE_BATTLE')
for name,data in k['arrays'].items():
 a=np.asarray(data,dtype=np.float32);assert len(a)==k['f']+1;np.save(out/(name+'.npy'),a);a.tofile(out/(name+'.f32'))
np.asarray(k['melee'],np.float32).tofile(out/'melee-control.f32');np.asarray(k['blueHits'],np.float32).tofile(out/'blue-hit-times.f32')
units=copy.deepcopy(S['units']);nb=S['blueCount']
for j,u in enumerate(units):
 d=k['bdeath'][j] if j<nb else k['death'][j-nb];u['deathTime']=None if d>1e5 else float(d)
simulation=dict(S,config=C,units=units,frames=k['f']+1,events=k['events'],shooterEvents=k['fired'],prefixCutTime=0.,prefixEvents=S['events'],prefixShooterEvents=S['shooterEvents'],meleeEvents=k['engine'].events)
(out/'params.json').write_text(json.dumps(C,indent=2),encoding='utf8');(out/'simulation.json').write_text(json.dumps(simulation,separators=(',',':'),default=lambda v:v.item() if isinstance(v,np.generic) else v.tolist()),encoding='utf8')
e=k['engine'];report=dict(prefixArraysEqual={name:bool(np.array_equal(np.asarray(data[:1]),np.load(source/(name+'.npy')))) for name,data in k['arrays'].items() if (source/(name+'.npy')).exists()},prefixEventsFrozen=True,winner=None,wonAt=None,duration=C['duration'],aliveRed=int((k['hp']>0).sum()),aliveBlue=int((k['bhp']>0).sum()),meleeAttempts=len(e.events),meleeHits=sum(q['damage']>0 for q in e.events),meleeKills=sum(q['killed'] for q in e.events),arrowReleases=len(k['events']),arrowHits=sum(bool(q.get('damage')) for q in k['events']),arrowKills=sum(bool(q.get('killed')) for q in k['events']),minimumBodyCenter=min(q['minimumCenter'] for q in e.solverAudit),minimumSweptBodyCenter=min(q['sweptMinimum'] for q in e.solverAudit),physicalBodyDiameter=.58,meleeRules=dict(blueHP=3,redDamage=1,attackDuration=e.duration,impactPhase=e.impactPhase,reach=e.reach),termination='NUMERICAL_ABORT_SAFE_CHECKPOINT_PREFIX_ONLY',failedAt=8.016666666666666,failure='Body solver solved inaccurate residual 0.005025544127612719 exceeds existing 0.005 tolerance',lastVerifiedTime=8.,completeBattle=False)
(out/'continuation-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8');(out/'body-projection.json').write_text(json.dumps(e.solverAudit),encoding='utf8')
(P/'docs/v22r-depth/E3-failure.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
