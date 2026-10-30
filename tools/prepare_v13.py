from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[1];B=P.parent/'PveMontageShot01V12';O=P/'output'
protected=list((B/'src').glob('*'))+list((B/'variants/FINAL').glob('*.*'))+[B/'output/PVE-Shot01-U-Archers-v12.mp4']
(O/'protected-v12.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()},indent=2))
c=json.loads((P/'variants/FINAL/params.json').read_text())
c.update(version='V13',duration=2.9,blueAdvance=7.5,blueMoveSeconds=1.48,blueStartSpread=.32,
         archerCycle=.96,archerRange=38.,cameraZoom=2.95,cameraTarget=[0,0,-5],cameraPosition=[0,240,95])
(P/'variants/FINAL/params.json').write_text(json.dumps(c,indent=2))
p=P/'tools/build_simulation_v11.py';s=p.read_text(encoding='utf-8')
marker="for u in blue:u['cycle']=C['archerCycle']*(u['cycle']/baseline['config']['archerCycle'])"
s=s.replace(marker,"""for j,u in enumerate(blue):
 # Stable ID-derived individual parameters, never per-frame random noise.
 q=((j+1)*.61803398875)%1; r=((j+1)*.41421356237)%1
 u['delay']=.035+.032*(u['group']%4)+.15*q
 u['moveSeconds']=C['blueMoveSeconds']*(.91+.18*r)
 u['arrival']=u['delay']+u['moveSeconds']
 u['drawSeconds']=.25+.10*q;u['aimSeconds']=.055+.045*r
 u['recoverSeconds']=.19+.09*(1-q);u['turnSeconds']=.07+.07*r
 u['cycle']=C['archerCycle']*(.86+.27*r)
 u['readyAt']=u['arrival']+u['turnSeconds']+u['drawSeconds']+u['aimSeconds']+.16*q
 u['shootYaw']=math.pi
""")
s=s.replace(".035+.060*u['phase']", ".035+.125*u['phase']")
s=s.replace("u['gaitStride']=C['runStride']", "u['gaitStride']=C['runStride'];u['personalPosture']=.06*math.sin(int(u['id'][1:])*1.319)")
s=s.replace("arrival=max(u['delay']+C['blueMoveSeconds'] for u in blue);firstDraw=arrival+.14", "arrival=max(u['arrival'] for u in blue);firstDraw=min(u['arrival'] for u in blue)")
s=s.replace("nextFire=np.array([firstDraw+u['phase']*.26+.055*(u['group']%3)+C['drawSeconds'] for u in blue])", "nextFire=np.array([u['readyAt'] for u in blue])")
s=s.replace("(t-u['delay'])/C['blueMoveSeconds']", "(t-u['delay'])/u['moveSeconds']")
# Range is checked against live world coordinates at the actual release tick.
a=s.index("   if len(eligible):\n    sector=")
b=s.index("   flight=float",a)
s=s[:a]+"""   if len(eligible):
    p=positions[f,j];ds=np.linalg.norm(rp[eligible]-p,axis=1)
    eligible=eligible[ds<=C['archerRange']]
   if len(eligible):
    sector=(u['group']+int(max(0,t-u['readyAt'])/u['cycle']))%3
    preferred=[k for k in eligible if red[k]['squadCol']==sector and ((int(red[k]['id'][1:])*.61803398875)%1)<.65]
    if preferred:eligible=np.array(preferred)
   if not len(eligible):continue
   p=positions[f,j];ds=np.linalg.norm(rp[eligible]-p,axis=1);close=eligible[np.argsort(ds)[:C['targetFrontCount']]]
   wounded=close[hp[close]<C['redHitPoints']];pool=wounded if len(wounded) and j%3==0 else close
   target=int(rng.choice(pool));dist=float(np.linalg.norm(rp[target]-p))
"""+s[b:]
s=s.replace("drawStart=t-C['drawSeconds'],aimStart=t-C['aimSeconds']", "drawStart=t-u['aimSeconds']-u['drawSeconds'],aimStart=t-u['aimSeconds']")
s=s.replace("drawStart=release-C['drawSeconds'],aimStart=release-C['aimSeconds']", "drawStart=release-u['aimSeconds']-u['drawSeconds'],aimStart=release-u['aimSeconds']")
# The post-cut arrow pass must obey the same range and personal timing rules.
s=s.replace("candidates=[k for k in survivors if death[k]>C['duration']]", "candidates=[k for k in survivors if death[k]>C['duration'] and np.linalg.norm(positions[rf,nb+k]-p)<=C['archerRange']]\n   if not candidates:break")
s=s.replace("version='V12'", "version='V13'")
p.write_text(s,encoding='utf-8')
p=P/'src/assets-v11.js';s=p.read_text(encoding='utf-8')
s=s.replace('attribute float response;', 'attribute float response; attribute float posture;')
s=s.replace('transformed.z-=response*.13*upper;', 'transformed.z+=posture*max(0.0,transformed.y-.55)*upper; transformed.z-=response*.13*upper;')
s=s.replace("geo.setAttribute('response',response);", "const posture=new T.InstancedBufferAttribute(new Float32Array(1024),1);geo.setAttribute('posture',posture);geo.setAttribute('response',response);")
s=s.replace('{mesh,hit,response,blend,moveWeight,n:0}', '{mesh,hit,response,posture,blend,moveWeight,n:0}')
p.write_text(s,encoding='utf-8')
p=P/'tools/capture_camera.mjs';s=p.read_text().replace(':5252/',':5253/')
s=s.replace('[0,.5,1.3,1.8,2.2,2.4,2.6,2.8,C.duration-1/C.fps]', '[0,.4,.8,1.2,1.5,1.8,2.0,2.2,2.5,C.duration-1/C.fps]')
p.write_text(s)
print('V13 prepared')
