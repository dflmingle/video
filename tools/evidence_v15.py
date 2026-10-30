from pathlib import Path
import json,hashlib,csv,difflib,subprocess,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from media_v11 import ff
P=Path(__file__).resolve().parents[1];O=P/'output';B=P.parent/'PveMontageShot01V14'
summaries={}
for variant in ['LOCAL','HEALTHY','FINAL']:
 D=P/'variants'/variant;R=json.loads((D/'render-checks.json').read_text());S=json.loads((D/'simulation.json').read_text());C=S['config'];nb=S['blueCount'];K=np.load(D/'red-control.npy');Y=np.load(D/'gait-cycles.npy');A=np.load(D/'trajectories.npy')
 assert not R['errors'] and all(s['identical'] for s in R['seeks'])
 for p,h in R['inputs'].items():assert hashlib.sha256((P/p).read_bytes()).hexdigest()==h,p
 for f,rows in enumerate(R['frames']):
  for a in rows[nb:]:
   j=a['index']-nb;assert abs(a['stride']-K[f,j,3])<1e-4 and abs(a['gaitCycles']-Y[f,a['index']])<1e-4
   if a['action']=='move':assert abs(a['phaseFloat']-((Y[f,a['index']]+S['units'][a['index']]['phase'])%1)*32)<.001
 if variant=='FINAL':
  oldR=json.loads((B/'variants/FINAL/render-checks.json').read_text())
  for f,state in enumerate(R['states']):
   for key in ['cameraPosition','cameraQuaternion','cameraProjection','cameraZoom']:assert state[key]==oldR['states'][f][key],key
 manifest=json.loads((P/'assets/runtime/manifest.json').read_text())
 for key,entry in manifest.items():
  for ext,tag in [('fbx','sourceSHA256'),('png','textureSHA256')]:assert hashlib.sha256((P/f'assets/runtime/{key}.{ext}').read_bytes()).hexdigest()==entry[tag]
 summaries[variant]=dict(renderInputsCurrent=True,independentIntegratedPhaseUsed=True,perMemberStrideUsed=True,shaderErrors=R['errors'],seeks=R['seeks'],renderMsP50P95=np.percentile(R['renderMs'][1:],[50,95]).tolist(),captureMsP50P95=np.percentile(R['frameCaptureMs'][1:],[50,95]).tolist(),specifiedAssetsUnchanged=True)
 # All raw event data includes future flights labelled as such.
 if variant=='FINAL':
  events=S['events']
  with (O/'V15-arrow-events.csv').open('w',newline='',encoding='utf-8-sig') as stream:
   fields=['id','shooterID','targetID','release','impact','resolution','damage','remainingHP','killed'];w=csv.DictWriter(stream,fields,extrasaction='ignore');w.writeheader();w.writerows(events)
  V=np.diff(A[:,nb:],axis=0)*60;acc=np.diff(V,axis=0)*60
  summaries[variant]['contactSafetyAccelerationP99Max']=np.percentile(np.abs(acc[:,:,1]),[99,100]).tolist()
  summaries[variant]['cameraEveryFrameMatchesV14']=True
for p,h in json.loads((O/'protected-v14.json').read_text()).items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
T=P/'variants/LOCAL';A=np.load(T/'trajectories.npy');K=np.load(T/'red-control.npy');Y=np.load(T/'gait-cycles.npy');t=np.arange(len(A))/60
fig,axes=plt.subplots(4,1,figsize=(13,11),sharex=True)
for i in range(20):
 line,=axes[0].plot(t,K[:,i,1],lw=.8);axes[1].plot(t,K[:,i,4],color=line.get_color(),lw=.8);axes[2].plot(t,(Y[:,i]+json.loads((T/'simulation.json').read_text())['units'][i]['phase'])%1,color=line.get_color(),lw=.7);axes[3].plot(t,A[:,i,1]-A[:,:20,1].mean(axis=1),color=line.get_color(),lw=.8)
for ax,label in zip(axes,['Actual forward speed','Cycles/sec','Individual phase (cycles)','Relative forward position']):
 ax.set_ylabel(label);ax.grid(alpha=.2);ax.axvline(1.5,color='k',ls='--',lw=.6);ax.axvline(1.8,color='r',ls='--',lw=.6)
axes[0].set_title('20 members of same platoon / real time / controlled obstacle fixture at 1.5, 1.8s');axes[-1].set_xlabel('Seconds');fig.tight_layout();fig.savefig(O/'V15-individual-motion-5s.png',dpi=140);plt.close(fig)
H=P/'variants/HEALTHY';AH=np.load(H/'trajectories.npy');KH=np.load(H/'red-control.npy');fig,axes=plt.subplots(3,1,figsize=(12,9),sharex=True)
for i in range(20):
 axes[0].plot(t,KH[:,i,1],lw=.8);axes[1].plot(t,KH[:,i,4],lw=.8);axes[2].plot(t,AH[:,i,1]-AH[:,:20,1].mean(axis=1),lw=.8)
for ax,label in zip(axes,['Actual forward speed','Cycles/sec','Relative forward position']):ax.set_ylabel(label);ax.grid(alpha=.2)
axes[0].set_title('Same squad 20 unhit members / 5 real seconds / production motion controller');axes[-1].set_xlabel('Seconds');fig.tight_layout();fig.savefig(O/'V15-healthy-motion-5s.png',dpi=140);plt.close(fig)
diff=''
for name in ['src/main-camera.js']:
 diff+=''.join(difflib.unified_diff((B/name).read_text(encoding='utf-8').splitlines(True),(P/name).read_text(encoding='utf-8').splitlines(True),fromfile='V14/'+name,tofile='V15/'+name))
diff+=''.join(difflib.unified_diff((B/'tools/build_simulation_v11.py').read_text(encoding='utf-8').splitlines(True),(P/'tools/build_simulation_v15.py').read_text(encoding='utf-8').splitlines(True),fromfile='V14/tools/build_simulation_v11.py',tofile='V15/tools/build_simulation_v15.py'))
diff+=''.join(difflib.unified_diff([],(P/'tools/motion_v15.py').read_text(encoding='utf-8').splitlines(True),fromfile='/dev/null',tofile='V15/tools/motion_v15.py'));(O/'V14-V15-code.diff').write_text(diff,encoding='utf-8')
media=[]
for name in ['PVE-Shot01-U-Archers-v15.mp4','V15-50-members-5s-validation.mp4','V15-50-members-5s-healthy-charge.mp4']:
 p=O/name;r=subprocess.run([ff,'-hide_banner','-i',str(p)],capture_output=True,text=True,encoding='utf-8',errors='replace');stream=next(l.strip() for l in r.stderr.splitlines() if 'Video:' in l);assert 'h264' in stream;media.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),stream=stream))
out=dict(status='PASS',renderVerification=summaries,media=media,V14Unchanged=True,visualStatus='PENDING_ENCODED_FRAME_REVIEW');(O/'V15-render-validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
