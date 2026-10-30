"""Materialize diagnostic Plan A/B/C variants for the V19 camera-B clip pass."""
from pathlib import Path
import json, shutil
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'variants' / 'FINAL'
TL = ROOT / 'variants' / 'V20-TIMELINE'
sim = json.loads((BASE/'simulation.json').read_text(encoding='utf8'))
summary = json.loads((TL/'timeline-summary.json').read_text(encoding='utf8'))
T = np.load(BASE/'trajectories.npy', mmap_mode='r')
nb, nr = int(sim['blueCount']), int(sim['redCount'])
fps = float(sim['config']['simulationFps']); dt = 1.0/fps

for plan in ['A','B','C']:
    d = ROOT/'variants'/f'V20-{plan}'
    d.mkdir(parents=True, exist_ok=True)
    for name in ['params.json','trajectories.f32','gait-distance.f32','gait-cycles.f32','red-control.f32','velocities.f32','formation-pressure.npy','movement-reasons.npy','slow-causes.npy','member-states.npy','avoidance-causes.npy','asset-render-audit.json']:
        src = BASE/name
        if src.exists(): shutil.copy2(src, d/name)
    # Keep the original V19 scene duration and fixed trajectories.
    events = json.loads((TL/plan/'events.json').read_text(encoding='utf8'))
    shooter_events = [[] for _ in range(nb)]
    hit = np.full((T.shape[0], nr), -10.0, dtype=np.float32)
    out_events=[]
    for ei,e in enumerate(events):
        j=int(e['shooter']); local=int(e['target']); rf=int(round(e['release']*fps)); hf=int(round(e['impact']*fps))
        global_target=nb+local
        origin=[float(T[rf,j,0]),0.95,float(T[rf,j,1])]
        endf=min(T.shape[0]-1,max(0,hf))
        destination=[float(T[endf,global_target,0]),0.85,float(T[endf,global_target,1])]
        ee=dict(e)
        ee.update(target=global_target,releaseFrame=rf,impactFrame=hf,arc=float(sim['config'].get('arrowArcHeight',7.0)),plannedDamage=1,damage=None,remainingHP=None,killed=False,origin=origin,destination=destination,originMapping='diagnostic fixed-trajectory origin',resolution='IMPACT_IN_SHOT' if hf<T.shape[0] else 'IN_FLIGHT_AT_CUT')
        out_events.append(ee); shooter_events[j].append(ei)
        if hf < T.shape[0]: hit[hf:,local] = float(e['impact'])
    out = dict(sim)
    out['version']='V20-DIAGNOSTIC-'+plan
    out['events']=out_events; out['shooterEvents']=shooter_events
    out['units']=[dict(u) for u in sim['units']]
    for u in out['units'][nb:]: u['deathTime']=None
    (d/'simulation.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf8')
    hit.tofile(d/'hit-times.f32'); np.save(d/'hit-times.npy',hit)
    # The diagnostic scheduler already writes the 12-column state interface.
    shutil.copy2(TL/plan/'blue-control.f32', d/'blue-control.f32')
    # Keep the input manifest self-describing.
    (d/'diagnostic-plan.json').write_text(json.dumps({'plan':plan,'source':'FINAL','camera':'V19-B','fixedTrajectories':True},indent=2),encoding='utf8')
print('prepared', ', '.join(f'V20-{x}' for x in ['A','B','C']))
