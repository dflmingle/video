from pathlib import Path
import json,numpy as np,math
p=Path('.');d=p/'variants/FINAL';s=json.loads((d/'simulation.json').read_text());c=json.loads((d/'params.json').read_text());a=np.load(d/'trajectories.npy');g=np.load(d/'gait-distance.npy');audit=json.loads((d/'asset-render-audit.json').read_text())['models'];n=len(s['units']);nb=s['blueCount'];summ={}
for model in ['flail','sword','samurai']:
 poses=audit[model]['actionAnatomy']['move'];idle=audit[model]['actionAnatomy']['idle'][0];local=[]
 # This nominal metric checks sampled stance points after the actual lean transform.
 for side,j in [('leftFoot',0),('rightFoot',1)]:
  for k in range(31):
   if poses[k]['legDiagnostics'][j]['stance'] and poses[k+1]['legDiagnostics'][j]['stance']:
    delta=np.array(poses[k+1][side])-poses[k][side];local.append(abs(1+np.dot(delta,[0,math.sin(c['runLean']),math.cos(c['runLean'])])/(c['runStride']/32)))
 summ[model]=dict(stanceResidualSpeedFraction=float(np.mean(local)),stancePairSamples=len(local),maximumIKTargetError=max(q['reachError'] for z in poses for q in z['legDiagnostics']),nominalCyclesPerSecond=11.8/c['runStride'],scope='Full lean, nominal straight constant speed, native-length skeleton. Does not prove no visual slip under turns/startup.')
(p/'output/gait-validation.json').write_text(json.dumps(summ,indent=2));print(summ)
