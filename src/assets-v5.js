import * as T from 'three';
import {FBXLoader} from 'three/addons/loaders/FBXLoader.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
export async function loadArmies(scene,config){
 const manifest=await fetch('/assets/runtime/manifest.json').then(r=>r.json()),batches=new Map(),audit={};
 const manager=new T.LoadingManager();manager.setURLModifier(u=>/\.fbx(?:\?|$)/i.test(u)?u:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==');
 const loader=new FBXLoader(manager),textures=new T.TextureLoader();
 for(const [key,entry]of Object.entries(manifest)){
  const prior=T.Object3D.prototype.add;T.Object3D.prototype.add=function(...o){return prior.apply(this,o.filter(x=>x!==this))};let root;try{root=await loader.loadAsync(entry.file)}finally{T.Object3D.prototype.add=prior}
  const source=root.animations[0],mixer=new T.AnimationMixer(root),clips={},hip=root.getObjectByName('Bip001'),head=root.getObjectByName('Bip001_HeadNub')||root.getObjectByName('Bip001_Head');
  const native=action=>entry.clips.find(c=>action==='death'?/^(die|death)$/.test(c.name):c.name===action);
  const ic=native('idle'),idle=T.AnimationUtils.subclip(source,'calibrate',ic.start,ic.end,30);mixer.clipAction(idle).play();mixer.update(0);root.updateMatrixWorld(true);
  const nativeBones=[];root.traverse(o=>{if(o.isBone)nativeBones.push({bone:o,position:o.position.clone(),quaternion:o.quaternion.clone(),scale:o.scale.clone()})});
  const raw=[];root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.skeleton?.update();const p=mesh.geometry.attributes.position,v=new T.Vector3();for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i);if(mesh.isSkinnedMesh)mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);raw.push(v.clone())}});
  const floor=Math.min(...raw.map(v=>v.y)),hy=head.getWorldPosition(new T.Vector3()).y,targetHeight=key==='archer'?1.25:1.38,scale=targetHeight/(hy-floor),texture=await textures.loadAsync(entry.texture);texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=4;
  for(const side of ['L','R']){const foot=root.getObjectByName(`Bip001_${side}_Foot`);foot.userData.idleHeight=(foot.getWorldPosition(new T.Vector3()).y-floor)*scale;foot.userData.idleQuaternion=foot.getWorldQuaternion(new T.Quaternion());}
  const color={archer:0x1879e8,sword:0xf76b09,flail:0xd92326,samurai:0xf3c229}[key];
  const mat=new T.MeshStandardMaterial({map:texture,roughness:.85,color:0xffffff});
  mat.onBeforeCompile=s=>{s.uniforms.teamColor={value:new T.Color(color)};s.vertexShader='attribute float hit; attribute float poseBlend; attribute vec3 nextPosition; varying float vHit;\n'+s.vertexShader;s.vertexShader=s.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\ntransformed=mix(position,nextPosition,poseBlend); vHit=hit;');s.fragmentShader='uniform vec3 teamColor; varying float vHit;\n'+s.fragmentShader;s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
   float blue=max(0.0,diffuseColor.b-max(diffuseColor.r,diffuseColor.g)*.78);float sat=max(diffuseColor.r,max(diffuseColor.g,diffuseColor.b))-min(diffuseColor.r,min(diffuseColor.g,diffuseColor.b));float mask=max(smoothstep(.025,.19,blue),smoothstep(.09,.3,sat)*.85);
   diffuseColor.rgb=mix(diffuseColor.rgb,teamColor*(.7+max(diffuseColor.b,max(diffuseColor.r,diffuseColor.g))*.35),mask);
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(2.4),vHit);`);};mat.customProgramCacheKey=()=>key+'v2-team-hit';
  let radius=0,vertices=0;const actionAnatomy={},poseAnchors={};
  for(const action of ['idle','move','attack','death','walk']){
   const c=native(action)||native('move'),clip=T.AnimationUtils.subclip(source,action,c.start,c.end,30),animation=mixer.clipAction(clip);mixer.stopAllAction();animation.reset().play();
   const phases=action==='idle'?6:action==='attack'?28:action==='death'?24:32;clips[action]={duration:clip.duration,phases,nativeClip:c};actionAnatomy[action]=[];poseAnchors[action]=[];
   // First sample all untouched native poses, then adapt snapshots. This avoids
   // AnimationMixer's unchanged-property cache retaining last sample's IK edits.
   const nativePoses=[];
   for(const b of nativeBones){b.bone.position.copy(b.position);b.bone.quaternion.copy(b.quaternion);b.bone.scale.copy(b.scale)}
   for(let f=0;f<phases;f++){
    animation.time=clip.duration*(action==='death'?f/(phases-1):f/phases);mixer.update(0);root.updateMatrixWorld(true);
    nativePoses.push(nativeBones.map(b=>({p:b.bone.position.clone(),q:b.bone.quaternion.clone(),s:b.bone.scale.clone()})));
   }
   for(let f=0;f<phases;f++){
    nativeBones.forEach((b,j)=>{const v=nativePoses[f][j];b.bone.position.copy(v.p);b.bone.quaternion.copy(v.q);b.bone.scale.copy(v.s)});root.updateMatrixWorld(true);
    // Adapt the supplied skeletal move clip for a long-stride charge. World-axis
    // rotations preserve the imported hierarchy, meshes and weapon attachments.
    let legDiagnostics=[];
    if(action==='move'&&key!=='archer'&&config.runMode==='grounded'){
     // Analytical two-bone solve: retain original skeleton lengths, never scale legs.
     // Each frame starts at the native animation pose, not the previous IK result.
     const wp=o=>o.getWorldPosition(new T.Vector3()),rotateTo=(bone,from,to)=>{
      const q=new T.Quaternion().setFromUnitVectors(from.clone().normalize(),to.clone().normalize()),parent=bone.parent.getWorldQuaternion(new T.Quaternion());
      bone.quaternion.premultiply(parent.clone().invert().multiply(q).multiply(parent));root.updateMatrixWorld(true);
     };
     const lean=.22;
     const idleFoot=(root.getObjectByName('Bip001_L_Foot').userData.idleHeight??.10);
     const th=root.getObjectByName('Bip001_L_Thigh'),ca=root.getObjectByName('Bip001_L_Calf'),fo=root.getObjectByName('Bip001_L_Foot');
     const legLength=(wp(th).distanceTo(wp(ca))+wp(ca).distanceTo(wp(fo)))*scale;
     const hw=wp(hip);hw.y=floor+(idleFoot+legLength*.80+.018*Math.sin(f/phases*Math.PI*4))/scale;
     hip.position.copy(hip.parent.worldToLocal(hw));root.updateMatrixWorld(true);
     const base=wp(hip);
     for(const [side,offset]of [['L',0],['R',.5]]){
      const thigh=root.getObjectByName(`Bip001_${side}_Thigh`),calf=root.getObjectByName(`Bip001_${side}_Calf`),foot=root.getObjectByName(`Bip001_${side}_Foot`);
      const h=wp(thigh),k=wp(calf),ft=wp(foot),l1=h.distanceTo(k),l2=k.distanceTo(ft),fq=foot.getWorldQuaternion(new T.Quaternion());
      const q=(f/phases+offset)%1,stance=config.runStance??.18,u=q<stance?q/stance:(q-stance)/(1-stance),reach=config.runStride*stance/2;
      const zz=q<stance?reach-config.runStride*q:-reach+2*reach*u*u*(3-2*u);
      const ground=idleFoot+.015+(q<stance?0:.17*Math.sin(Math.PI*u));
      const y=(ground+Math.sin(lean)*zz)/Math.cos(lean);
      const target=new T.Vector3(h.x,floor+y/scale,base.z+zz/scale),direction=target.clone().sub(h),wanted=direction.length();
      const dist=T.MathUtils.clamp(wanted,Math.abs(l1-l2)+.001,l1+l2-.001);direction.normalize();
      const bend=new T.Vector3(0,0,1).addScaledVector(direction,-direction.z).normalize();
      const along=(l1*l1-l2*l2+dist*dist)/(2*dist),height=Math.sqrt(Math.max(0,l1*l1-along*along));
      const knee=h.clone().addScaledVector(direction,along).addScaledVector(bend,height),goal=h.clone().addScaledVector(direction,dist);
      rotateTo(thigh,k.clone().sub(h),knee.clone().sub(h));
      const nk=wp(calf);rotateTo(calf,wp(foot).sub(nk),goal.clone().sub(nk));
      const footWorld=foot.userData.idleQuaternion.clone();if(q>=stance)footWorld.slerp(fq,.5*Math.sin(Math.PI*u));foot.quaternion.copy(foot.parent.getWorldQuaternion(new T.Quaternion()).invert().multiply(footWorld));root.updateMatrixWorld(true);
      legDiagnostics.push({side,phase:q,stance:q<stance,boneLength:(l1+l2)*scale,target:target.toArray().map((v,i)=>(v-(i===1?floor:i===2?base.z:base.x))*scale),reachError:wp(foot).distanceTo(target)*scale});
     }
    }
    const anchor=hip.getWorldPosition(new T.Vector3()),geometries=[];
    const bp=name=>{const v=root.getObjectByName(name)?.getWorldPosition(new T.Vector3())||anchor.clone();return[(v.x-anchor.x)*scale,(v.y-floor)*scale,(v.z-anchor.z)*scale]};
    poseAnchors[action].push({leftHand:bp('Bip001_L_Hand'),rightHand:bp('Bip001_R_Hand')});actionAnatomy[action].push({legDiagnostics,hip:anchor.toArray(),leftFoot:bp('Bip001_L_Foot'),rightFoot:bp('Bip001_R_Foot')});
    root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.skeleton?.update();const geo=mesh.geometry.clone(),p=geo.attributes.position,arr=new Float32Array(p.count*3),v=new T.Vector3();for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i);if(mesh.isSkinnedMesh)mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);arr.set([(v.x-anchor.x)*scale,(v.y-floor)*scale,(v.z-anchor.z)*scale],i*3)}geo.setAttribute('position',new T.BufferAttribute(arr,3));for(const name of Object.keys(geo.attributes))if(!['position','uv'].includes(name))geo.deleteAttribute(name);geometries.push(geo.index?geo.toNonIndexed():geo)});
    const geo=mergeGeometries(geometries,false);geo.computeVertexNormals();geo.computeBoundingBox();const bb=geo.boundingBox;actionAnatomy[action][f].geometryMinY=bb.min.y;actionAnatomy[action][f].geometryMaxY=bb.max.y;radius=Math.max(radius,Math.hypot(Math.max(Math.abs(bb.min.x),Math.abs(bb.max.x)),Math.max(Math.abs(bb.min.z),Math.abs(bb.max.z)))+.35);vertices=geo.attributes.position.count;
    const hit=new T.InstancedBufferAttribute(new Float32Array(1024),1),blend=new T.InstancedBufferAttribute(new Float32Array(1024),1);geo.setAttribute('hit',hit);geo.setAttribute('poseBlend',blend);const mesh=new T.InstancedMesh(geo,mat,1024);mesh.count=0;mesh.frustumCulled=false;mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);batches.set(`${key}/${action}/${f}`,{mesh,hit,blend,n:0});
   }
   for(let f=0;f<phases;f++){const a=batches.get(`${key}/${action}/${f}`),next=batches.get(`${key}/${action}/${action==='death'?Math.min(phases-1,f+1):(f+1)%phases}`);a.mesh.geometry.setAttribute('nextPosition',next.mesh.geometry.attributes.position);}
  }
  audit[key]={source:entry.source,sourceSHA256:entry.sourceSHA256,texture:entry.textureSource,clips,horizontalEnvelope:radius,verticesPerPose:vertices,calibration:{targetHeadHeight:targetHeight,scale,bindFloor:floor,method:'idle head/foot normalization, per-pose skeletal hip anchor; no bounding-box recenter'},runAdaptation:key==='archer'?'native move':'native pose reset each sample; analytical length-constrained two-bone legs, native arms and weapon attachments retained',colorAdaptation:color.toString(16),poseAnchors,actionAnatomy,bowReleaseLocal:poseAnchors.attack[Math.floor(.64*clips.attack.phases)].leftHand};
 }
 return{batches,audit,manifest};
}
