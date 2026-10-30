from pathlib import Path
import json, csv, hashlib
import numpy as np
P=Path(__file__).resolve().parents[1];D=P/'variants/FINAL';O=P/'output';B=P.parent/'PveMontageShot01V11/variants/CAMERA-B'
S=json.loads((D/'simulation.json').read_text());Q=json.loads((B/'simulation.json').read_text());C=S['config'];U=S['units'];nb=S['blueCount']
A=np.load(D/'trajectories.npy');A0=np.load(B/'trajectories.npy');V=np.diff(A,axis=0,prepend=A[:1])*60;V0=np.diff(A0,axis=0,prepend=A0[:1])*60
E=[e for e in S['events'] if e['resolution']=='IMPACT_IN_SHOT'];E0=[e for e in Q['events'] if e['resolution']=='IMPACT_IN_SHOT']
first={};first0={}
for e in sorted(E,key=lambda e:e['impact']):first.setdefault(e['target'],e['impact'])
for e in sorted(E0,key=lambda e:e['impact']):first0.setdefault(e['target'],e['impact'])
assert np.array_equal(A[0],A0[0])
cameraKeys=['cameraPosition','cameraTarget','cameraFov','cameraZoom','cameraShiftX','cameraShiftY','cameraTravelZ','width','height','fps']
baselineCamera=json.loads((B/'params.json').read_text())
assert all(C[k]==baselineCamera[k] for k in cameraKeys)
ratios=[U[i]['speed']/Q['units'][i]['speed'] for i in range(nb,len(U))];assert np.allclose(ratios,1.5)
assert np.diff(A[:,nb:,1],axis=0).min()>=-1e-5
perSecond=[]
for start,end in [(0,1),(1,2),(2,3),(3,3.033333333333333)]:
 a,b=round(start*60),round(end*60)
 ids=[i for i in range(nb,len(U)) if U[i]['army']==2 and first.get(i,99)>end and first0.get(i,99)>end]
 d=A[b,ids,1]-A[a,ids,1];d0=A0[b,ids,1]-A0[a,ids,1]
 perSecond.append(dict(start=start,end=end,sameNeverHitMembers=len(ids),v11AdvanceMedian=float(np.median(d0)),v12AdvanceMedian=float(np.median(d)),actualRatioMedian=float(np.median(d/d0)),v11SpeedMedian=float(np.median(d0/(end-start))),v12SpeedMedian=float(np.median(d/(end-start)))))
samples=[]
for t in [1,2,2.2,2.4,2.6,2.8,3.0]:
 k=round(t*60);ids=[i for i in range(nb,len(U)) if first.get(i,99)>t]
 samples.append(dict(time=t,unhitCount=len(ids),forwardSpeedP10P50P90=np.percentile(V[k,ids,1],[10,50,90]).tolist(),belowHalfNominal=sum(V[k,i,1]<U[i]['speed']*.5 for i in ids),reversed=sum(V[k,i,1]<-1e-5 for i in ids)))
for p,digest in json.loads((O/'protected-v11.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
validation=json.loads((O/'V11-engineering-validation.json').read_text());validation['scope']=f'All {len(A)} simulation states, continuous conservative clearance bound; no reverse root motion; encoded visuals reviewed separately.'
(O/'V12-engineering-validation.json').write_text(json.dumps(validation,indent=2))
report=dict(initialExact=True,cameraExact=True,nominalPerMemberSpeedRatio=[min(ratios),max(ratios)],yellowSameMemberPerSecond=perSecond,unhitMotion=samples,
 rootReverseSteps=int((np.diff(A[:,nb:,1],axis=0)<-1e-5).sum()),duration=C['duration'],endReason='Cut before contact while unhit members continue running; no end-of-shot braking.',
 gait=dict(v11Stride=Q['config']['runStride'],v12Stride=C['runStride'],nominalStrideRatio=C['runStride']/Q['config']['runStride'],nominalCadenceRatio=1.5/(C['runStride']/Q['config']['runStride']),v11CyclesPerSecond=11.6/3.1,v12CyclesPerSecond=17.4/C['runStride'],leanRadians=C['runLean'],method='Actual cumulative world path / personal stride. Source FBX skeleton with adapted IK run, not an original native sprint clip.'),
 hitResponse=dict(staggerSeconds=C['hitStaggerSeconds'],recoverSeconds=C['hitRecoverySeconds'],lightInitialSpeedFactor=.55,lightRecoveredSpeedFactor=C['hitWoundSpeed'],seriousInitialSpeedFactor=.35,seriousRecoveredSpeedFactor=C['hitSeriousSpeed'],upperBodyPoseSeconds=C['hitPoseSeconds'],worldImpulse=False,groupBroadcast=False),protectedV11Files=len(json.loads((O/'protected-v11.json').read_text())))
(O/'V12-speed-direction-audit.json').write_text(json.dumps(report,indent=2,default=lambda x:x.item()));print(json.dumps(report,indent=2,default=lambda x:x.item()))
