import * as T from 'three';
import {FBXLoader} from 'three/addons/loaders/FBXLoader.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
export async function loadArmies(scene){
 const manifest=await fetch('/assets/runtime/manifest.json').then(r=>r.json()),batches=new Map(),audit={};
 const manager=new T.LoadingManager();manager.setURLModifier(u=>/\.fbx(?:\?|$)/i.test(u)?u:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==');
 const loader=new FBXLoader(manager),textures=new T.TextureLoader();
 for(const [key,entry]of Object.entries(manifest)){
  const prior=T.Object3D.prototype.add;T.Object3D.prototype.add=function(...o){return prior.apply(this,o.filter(x=>x!==this))};let root;try{root=await loader.loadAsync(entry.file)}finally{T.Object3D.prototype.add=prior}
  const source=root.animations[0],mixer=new T.AnimationMixer(root),clips={},hip=root.getObjectByName('Bip001'),head=root.getObjectByName('Bip001_HeadNub')||root.getObjectByName('Bip001_Head');
  const native=action=>entry.clips.find(c=>action==='death'?/^(die|death)$/.test(c.name):c.name===action);
  const ic=native('idle'),idle=T.AnimationUtils.subclip(source,'calibrate',ic.start,ic.end,30);mixer.clipAction(idle).play();mixer.update(0);root.updateMatrixWorld(true);
  const raw=[];root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.skeleton?.update();const p=mesh.geometry.attributes.position,v=new T.Vector3();for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i);if(mesh.isSkinnedMesh)mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);raw.push(v.clone())}});
  const floor=Math.min(...raw.map(v=>v.y)),hy=head.getWorldPosition(new T.Vector3()).y,targetHeight=key==='archer'?1.25:1.38,scale=targetHeight/(hy-floor),texture=await textures.loadAsync(entry.texture);texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=4;
  const color={archer:0x1879e8,sword:0xf76b09,flail:0xd92326,samurai:0xf3c229}[key];
  const mat=new T.MeshStandardMaterial({map:texture,roughness:.85,color:0xffffff});
  mat.onBeforeCompile=s=>{s.uniforms.teamColor={value:new T.Color(color)};s.vertexShader='attribute float hit; varying float vHit;\n'+s.vertexShader;s.vertexShader=s.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvHit=hit;');s.fragmentShader='uniform vec3 teamColor; varying float vHit;\n'+s.fragmentShader;s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
   float blue=max(0.0,diffuseColor.b-max(diffuseColor.r,diffuseColor.g)*.78);float sat=max(diffuseColor.r,max(diffuseColor.g,diffuseColor.b))-min(diffuseColor.r,min(diffuseColor.g,diffuseColor.b));float mask=max(smoothstep(.025,.19,blue),smoothstep(.09,.3,sat)*.85);
   diffuseColor.rgb=mix(diffuseColor.rgb,teamColor*(.7+max(diffuseColor.b,max(diffuseColor.r,diffuseColor.g))*.35),mask);
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(2.4),vHit);`);};mat.customProgramCacheKey=()=>key+'v2-team-hit';
  let radius=0,vertices=0;const actionAnatomy={},poseAnchors={};
  for(const action of ['idle','move','attack','death','walk']){
   const c=native(action)||native('move'),clip=T.AnimationUtils.subclip(source,action,c.start,c.end,30),animation=mixer.clipAction(clip);mixer.stopAllAction();animation.reset().play();
   const phases=action==='idle'?6:action==='attack'?28:action==='death'?24:32;clips[action]={duration:clip.duration,phases,nativeClip:c};actionAnatomy[action]=[];poseAnchors[action]=[];
   for(let f=0;f<phases;f++){
    animation.time=clip.duration*(action==='death'?f/(phases-1):f/phases);mixer.update(0);root.updateMatrixWorld(true);
    // Adapt the supplied skeletal move clip for a long-stride charge. World-axis
    // rotations preserve the imported hierarchy, meshes and weapon attachments.
    if(action==='move'&&key!=='archer'){
     const rotate=(name,angle)=>{const b=root.getObjectByName(name);if(!b)return;const pq=b.parent.getWorldQuaternion(new T.Quaternion()),q=new T.Quaternion().setFromAxisAngle(new T.Vector3(1,0,0),angle);b.quaternion.premultiply(pq.clone().invert().multiply(q).multiply(pq));root.updateMatrixWorld(true)};
     const hz=hip.getWorldPosition(new T.Vector3()).z,lz=(root.getObjectByName('Bip001_L_Foot').getWorldPosition(new T.Vector3()).z-hz)*scale,rz=(root.getObjectByName('Bip001_R_Foot').getWorldPosition(new T.Vector3()).z-hz)*scale;
     rotate('Bip001_L_Thigh',-lz*2.9);rotate('Bip001_R_Thigh',-rz*2.9);
     rotate('Bip001_L_Calf',-.2*Math.max(0,-lz)/.3);rotate('Bip001_R_Calf',-.2*Math.max(0,-rz)/.3);
     rotate('Bip001_L_UpperArm',lz*.7);rotate('Bip001_R_UpperArm',rz*.7);
    }
    const anchor=hip.getWorldPosition(new T.Vector3()),geometries=[];
    const bp=name=>{const v=root.getObjectByName(name)?.getWorldPosition(new T.Vector3())||anchor.clone();return[(v.x-anchor.x)*scale,(v.y-floor)*scale,(v.z-anchor.z)*scale]};
    poseAnchors[action].push({leftHand:bp('Bip001_L_Hand'),rightHand:bp('Bip001_R_Hand')});actionAnatomy[action].push({hip:anchor.toArray(),leftFoot:bp('Bip001_L_Foot'),rightFoot:bp('Bip001_R_Foot')});
    root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.skeleton?.update();const geo=mesh.geometry.clone(),p=geo.attributes.position,arr=new Float32Array(p.count*3),v=new T.Vector3();for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i);if(mesh.isSkinnedMesh)mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);arr.set([(v.x-anchor.x)*scale,(v.y-floor)*scale,(v.z-anchor.z)*scale],i*3)}geo.setAttribute('position',new T.BufferAttribute(arr,3));for(const name of Object.keys(geo.attributes))if(!['position','uv'].includes(name))geo.deleteAttribute(name);geometries.push(geo.index?geo.toNonIndexed():geo)});
    const geo=mergeGeometries(geometries,false);geo.computeVertexNormals();geo.computeBoundingBox();const bb=geo.boundingBox;radius=Math.max(radius,Math.hypot(Math.max(Math.abs(bb.min.x),Math.abs(bb.max.x)),Math.max(Math.abs(bb.min.z),Math.abs(bb.max.z)))+.35);vertices=geo.attributes.position.count;
    const hit=new T.InstancedBufferAttribute(new Float32Array(1024),1);geo.setAttribute('hit',hit);const mesh=new T.InstancedMesh(geo,mat,1024);mesh.count=0;mesh.frustumCulled=false;mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);batches.set(`${key}/${action}/${f}`,{mesh,hit,n:0});
   }
  }
  audit[key]={source:entry.source,sourceSHA256:entry.sourceSHA256,texture:entry.textureSource,clips,horizontalEnvelope:radius,verticesPerPose:vertices,calibration:{targetHeadHeight:targetHeight,scale,bindFloor:floor,method:'idle head/foot normalization, per-pose skeletal hip anchor; no bounding-box recenter'},runAdaptation:key==='archer'?'native move':'native move plus continuous thigh/calf/upper-arm long-stride overlay; weapon skeletal attachments retained',colorAdaptation:color.toString(16),poseAnchors,actionAnatomy,bowReleaseLocal:poseAnchors.attack[Math.floor(.64*clips.attack.phases)].leftHand};
 }
 return{batches,audit,manifest};
}
