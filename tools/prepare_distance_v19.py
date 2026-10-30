from pathlib import Path
import json,shutil,sys
P=Path(__file__).resolve().parents[1]; src=P/'variants/FINAL';
for name,frac in [('DIST_A',0.0),('DIST_B',0.15),('DIST_C',0.25)]:
 d=P/'variants'/name
 if d.exists(): shutil.rmtree(d)
 d.mkdir(parents=True)
 for f in ['params.json']:
  c=json.loads((src/f).read_text()); c['variant']=name; c['blueDistanceShiftZ']=-float(c['blueAdvance']*0 + (64.60862*frac)); c['version']='V19-DIST'; (d/f).write_text(json.dumps(c,indent=2))
 for f in ['simulation.json','trajectories.f32','red-control.f32','gait-cycles.f32','hit-times.f32','gait-distance.f32','velocities.f32','blue-control.f32','movement-reasons.npy','slow-causes.npy','member-states.npy','avoidance-causes.npy','hit-responses.json','safety-and-causality.json','simulation-performance.json','member-trajectories.csv']:
  if (src/f).exists(): shutil.copy2(src/f,d/f)
