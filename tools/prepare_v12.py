from pathlib import Path
import json, hashlib
P=Path(__file__).resolve().parents[1]
B=P.parent/'PveMontageShot01V11'
protected=list((B/'src').glob('*'))+list((B/'variants/CAMERA-B').glob('*.*'))+[B/'output/camera-revision/PVE-Shot01-U-Archers-v11-close.mp4']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
(P/'output/protected-v11.json').write_text(json.dumps(hashes,indent=2))
p=P/'variants/FINAL/params.json';c=json.loads(p.read_text())
c.update(duration=3.05,redSpeed=17.4,runStride=3.565,runLean=.22,
         hitStaggerSeconds=.12,hitRecoverySeconds=.20,hitWoundSpeed=.82,
         hitSeriousSpeed=.60,hitPoseSeconds=.24,flashSeconds=.04,
         version='V12',speedMultiplier=1.5)
p.write_text(json.dumps(c,indent=2))
p=P/'tools/build_simulation_v11.py';s=p.read_text()
s=s.replace("factor=.12 if damage==1 else .03", "factor=.55 if damage==1 else .35")
s=s.replace("factor=.12+(woundFactor-.12)*(a2*a2*(3-2*a2))", "low=.55 if damage==1 else .35;factor=low+(woundFactor-low)*(a2*a2*(3-2*a2))")
# Earlier persistent passing routes, before a following runner reaches a wounded body.
s=s.replace('rp+[0,2.2],3.5','rp+[0,3.2],4.7').replace("<5.5", "<7.0").replace("dz<5.0", "dz<7.0")
s=s.replace("/dv<.85", "/dv<1.15").replace(".22,.85", ".22,1.15")
s=s.replace("*3,-1.2,1.2", "*3,-2.1,2.1").replace("-1.8,1.8", "-2.7,2.7")
s=s.replace("version='V11'", "version='V12'")
p.write_text(s)
p=P/'src/assets-v11.js';s=p.read_text()
s=s.replace('attribute float hit; attribute float poseBlend;', 'attribute float hit; attribute float response; attribute float poseBlend;')
s=s.replace('vHit=hit;', 'float upper=smoothstep(.55,1.0,transformed.y); transformed.z-=response*.13*upper; transformed.y-=response*.035*upper; vHit=hit;')
s=s.replace('vec3(2.4)', 'vec3(1.3)').replace("key+'v2-team-hit'", "key+'v12-locomotion-hit'")
s=s.replace("geo.setAttribute('hit',hit);", "const response=new T.InstancedBufferAttribute(new Float32Array(1024),1);geo.setAttribute('response',response);geo.setAttribute('hit',hit);")
s=s.replace('{mesh,hit,blend,moveWeight,n:0}', '{mesh,hit,response,blend,moveWeight,n:0}')
p.write_text(s)
p=P/'src/main-camera.js';s=p.read_text()
start=s.index(";if(hitAge>=0&&hitAge<C.hitStaggerSeconds")
end=s.index('  const clip=a.clips[action]',start)
s=s[:start]+";}\n  // Hit response affects upper body only; distance-driven running legs continue.\n"+s[end:]
s=s.replace("hitAge>=0&&hitAge<C.hitPoseSeconds?.22*Math.sin(hitAge/C.hitPoseSeconds*Math.PI)*(i%2?1:-1):0", "0")
s=s.replace('b.hit.setX(b.n++,', "b.response.setX(b.n,action!=='death'&&i>=nb&&hitAge>=0&&hitAge<C.hitPoseSeconds?Math.sin(Math.PI*hitAge/C.hitPoseSeconds):0);b.hit.setX(b.n++,")
s=s.replace('?.7*(1-hitAge/C.flashSeconds)', '?.25*(1-hitAge/C.flashSeconds)')
s=s.replace('b.hit.needsUpdate=true;', 'b.hit.needsUpdate=true;b.response.needsUpdate=true;')
s=s.replace("version:'V11'", "version:'V12'")
s=s.replace('(1-age/.2)*.8', '(1-age/.2)*.48')
p.write_text(s)
p=P/'tools/capture_camera.mjs';s=p.read_text().replace(':5251/',':5252/')
s=s.replace('[0,.5,1.3,1.8,2.2,2.6,3.0,3.8,C.duration-1/C.fps]', '[0,.5,1.3,1.8,2.2,2.4,2.6,2.8,C.duration-1/C.fps]')
p.write_text(s)
print('V12 prepared. Protected V11 files:',len(hashes))
