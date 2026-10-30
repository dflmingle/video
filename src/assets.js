import * as T from 'three';
import {FBXLoader} from 'three/addons/loaders/FBXLoader.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
export async function loadArmies(scene){
 const manifest=await fetch('/assets/runtime/manifest.json').then(r=>r.json()),batches=new Map(),audit={};
 const manager=new T.LoadingManager();manager.setURLModifier(u=>/\.fbx(?:\?|$)/i.test(u)?u:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==');
 const loader=new FBXLoader(manager),textures=new T.TextureLoader();
 for(const [key,entry]of Object.entries(manifest)){
  const prior=T.Object3D.prototype.add;T.Object3D.prototype.add=function(...o){return prior.apply(this,o.filter(x=>x!==this))};let root;try{root=await loader.loadAsync(entry.file)}finally{T.Object3D.prototype.add=prior}
  const source=root.animations[0],box=new T.Box3().setFromObject(root),size=box.getSize(new T.Vector3()),scale=entry.height/size.y,outer=new T.Group();outer.add(root);root.scale.multiplyScalar(scale);root.position.y-=box.min.y*scale;outer.updateMatrixWorld(true);
  const texture=await textures.loadAsync(entry.texture);texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=4;
  const color={archer:0x3088f1,sword:0xf68527,flail:0xe3403f,samurai:0xf3c83c}[key];
  const mat=new T.MeshStandardMaterial({map:texture,roughness:.85,metalness:0,color:0xffffff});
  mat.onBeforeCompile=s=>{s.uniforms.teamColor={value:new T.Color(color)};s.vertexShader='attribute float hit; varying float vHit;\n'+s.vertexShader;s.vertexShader=s.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvHit=hit;');s.fragmentShader='uniform vec3 teamColor; varying float vHit;\n'+s.fragmentShader;s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
   float blue=max(0.0,diffuseColor.b-max(diffuseColor.r,diffuseColor.g)*.78);float saturation=max(diffuseColor.r,max(diffuseColor.g,diffuseColor.b))-min(diffuseColor.r,min(diffuseColor.g,diffuseColor.b));float mask=max(smoothstep(.025,.19,blue),smoothstep(.09,.3,saturation)*.85);
   diffuseColor.rgb=mix(diffuseColor.rgb,teamColor*(.58+max(diffuseColor.b,max(diffuseColor.r,diffuseColor.g))*.48),mask);
   diffuseColor.rgb=mix(diffuseColor.rgb,vec3(1.9),vHit);`);};mat.customProgramCacheKey=()=>key+'-team-hit';
  const mixer=new T.AnimationMixer(root),clips={};let radius=0,vertices=0;
  for(const action of ['idle','move','attack','death']){
   const candidates=entry.clips.filter(c=>action==='death'?/^(die|death)$/.test(c.name):action==='idle'?/^idle$/.test(c.name):c.name===action);const c=candidates[0]||{start:action==='idle'?10:action==='move'?40:action==='attack'?80:220,end:action==='idle'?34:action==='move'?56:action==='attack'?95:260};
   const clip=T.AnimationUtils.subclip(source,action,c.start,c.end,30),animation=mixer.clipAction(clip);mixer.stopAllAction();animation.play();const phases=action==='idle'?4:action==='attack'?18:action==='death'?16:12;clips[action]={duration:clip.duration,phases};
   for(let f=0;f<phases;f++){
    animation.time=clip.duration*(action==='death'?f/(phases-1):f/phases);mixer.update(0);outer.updateMatrixWorld(true);const geometries=[];
    root.traverse(mesh=>{if(!mesh.isMesh)return;mesh.skeleton?.update();const geo=mesh.geometry.clone(),p=geo.attributes.position,arr=new Float32Array(p.count*3),v=new T.Vector3();for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i);if(mesh.isSkinnedMesh)mesh.applyBoneTransform(i,v);v.applyMatrix4(mesh.matrixWorld);arr.set(v.toArray(),i*3)}geo.setAttribute('position',new T.BufferAttribute(arr,3));for(const name of Object.keys(geo.attributes))if(!['position','uv'].includes(name))geo.deleteAttribute(name);geometries.push(geo.index?geo.toNonIndexed():geo)});
    const geo=mergeGeometries(geometries,false);geo.computeBoundingBox();const bb=geo.boundingBox,center=bb.getCenter(new T.Vector3());geo.translate(-center.x,0,-center.z);geo.computeVertexNormals();geo.computeBoundingSphere();radius=Math.max(radius,Math.hypot(Math.max(Math.abs(bb.min.x-center.x),Math.abs(bb.max.x-center.x)),Math.max(Math.abs(bb.min.z-center.z),Math.abs(bb.max.z-center.z))));vertices=geo.attributes.position.count;
    const hit=new T.InstancedBufferAttribute(new Float32Array(1024),1);geo.setAttribute('hit',hit);const mesh=new T.InstancedMesh(geo,mat,1024);mesh.count=0;mesh.frustumCulled=false;scene.add(mesh);batches.set(`${key}/${action}/${f}`,{mesh,hit,n:0});
   }
  }
  audit[key]={source:entry.source,sourceSHA256:entry.sourceSHA256,texture:entry.textureSource,clips,horizontalEnvelope:radius,verticesPerPose:vertices,originalAnimations:root.animations.map(c=>({name:c.name,duration:c.duration})),colorAdaptation:color.toString(16)};
 }
 return{batches,audit,manifest};
}
