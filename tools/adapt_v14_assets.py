from pathlib import Path
P=Path(__file__).resolve().parents[1];p=P/'src/assets-v11.js';s=p.read_text(encoding='utf-8')
s=s.replace('attribute float gaitScale;', 'attribute float gaitScale; attribute float armSwing; attribute vec3 armDelta; attribute vec3 nextArmDelta;')
s=s.replace('float lower=1.0-smoothstep', 'transformed+=mix(armDelta,nextArmDelta,poseBlend)*armSwing; float lower=1.0-smoothstep')
s=s.replace("key+'v12-locomotion-hit'", "key+'v14-dynamic-rig'")
# Sample a small additional shoulder rotation on the imported skeleton. The
# resulting vertex delta also follows actual attached weapons, no proxy arms.
anchor="    const geo=mergeGeometries(geometries,false);"
insert="""    if(action==='move'&&key!=='archer'){
     const cycle=f/phases*Math.PI*2;
     for(const [name,angle]of [['Bip001_L_UpperArm',.18*Math.sin(cycle)],['Bip001_R_UpperArm',-.18*Math.sin(cycle)]]){
      const bone=root.getObjectByName(name),parent=bone.parent.getWorldQuaternion(new T.Quaternion()),q=new T.Quaternion().setFromAxisAngle(new T.Vector3(1,0,0),angle);bone.quaternion.premultiply(parent.clone().invert().multiply(q).multiply(parent));root.updateMatrixWorld(true);
     }
     let mi=0;root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.skeleton?.update();const source=mesh.geometry.attributes.position,v=new T.Vector3(),arr=new Float32Array(source.count*3);for(let i=0;i<source.count;i++){v.fromBufferAttribute(source,i);if(mesh.isSkinnedMesh)mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);arr.set([(v.x-anchor.x)*scale,(v.y-floor)*scale,(v.z-anchor.z)*scale],i*3)}const alt=mesh.geometry.clone();alt.setAttribute('position',new T.BufferAttribute(arr,3));const final=alt.index?alt.toNonIndexed():alt,base=geometries[mi],delta=new Float32Array(base.attributes.position.count*3);for(let i=0;i<delta.length;i++)delta[i]=final.attributes.position.array[i]-base.attributes.position.array[i];base.setAttribute('armDelta',new T.BufferAttribute(delta,3));mi++;});
    }else{for(const g of geometries)g.setAttribute('armDelta',new T.BufferAttribute(new Float32Array(g.attributes.position.count*3),3));}
"""
assert anchor in s;s=s.replace(anchor,insert+anchor)
s=s.replace("geo.setAttribute('gaitScale',gaitScale);", "const armSwing=new T.InstancedBufferAttribute(new Float32Array(1024),1);geo.setAttribute('armSwing',armSwing);geo.setAttribute('gaitScale',gaitScale);")
s=s.replace('{mesh,hit,response,posture,gaitScale,blend,moveWeight,n:0}', '{mesh,hit,response,posture,gaitScale,armSwing,blend,moveWeight,n:0}')
s=s.replace("a.mesh.geometry.setAttribute('nextPosition',next.mesh.geometry.attributes.position);", "a.mesh.geometry.setAttribute('nextPosition',next.mesh.geometry.attributes.position);a.mesh.geometry.setAttribute('nextArmDelta',next.mesh.geometry.attributes.armDelta);")
p.write_text(s,encoding='utf-8')
p=P/'src/main-camera.js';s=p.read_text(encoding='utf-8').replace("version:'V13'","version:'V14'");p.write_text(s,encoding='utf-8')
p=P/'tools/capture_camera.mjs';s=p.read_text().replace(':5253/',':5254/').replace("'tools/capture_v11.mjs'", "'tools/capture_camera.mjs',`${dir}/red-control.f32`,`${dir}/gait-cycles.f32`")
a=s.index('const behaviorIds=await page.evaluate(');b=s.index(';const tracked=',a)
s=s[:a]+"const behaviorIds=[...Array.from({length:16},(_,i)=>i),...JSON.parse(fs.readFileSync('output/tracked-v14.json','utf8')).indices]"+s[b:]
p.write_text(s)
print('V14 renderer wired to dynamic controls')
