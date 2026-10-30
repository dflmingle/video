import * as T from 'three';import {FBXLoader} from 'three/addons/loaders/FBXLoader.js';
import {addEnvironment as addTrees} from './environment.js';
export async function addEnvironment(scene){
 const base='/assets/imported/Assets/ArtOfWar-II_Art/Environment/Common/ArenaScene/',manager=new T.LoadingManager();manager.setURLModifier(u=>/\.fbx$/i.test(u)?u:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==');
 const model=base+'Model/ArenaScene_Land.fbx',texture=base+'Texture/ArenaScene_Land_C.png';const root=await new FBXLoader(manager).loadAsync(model),map=await new T.TextureLoader().loadAsync(texture);map.colorSpace=T.SRGBColorSpace;map.anisotropy=8;
 root.traverse(o=>{if(!o.isMesh)return;const g=o.geometry.clone(),a=g.attributes.position;for(let i=0;i<a.count;i++)a.setY(i,0);a.needsUpdate=true;g.computeVertexNormals();o.geometry=g;o.material=new T.MeshStandardMaterial({map,roughness:1,onBeforeCompile:s=>{s.fragmentShader=s.fragmentShader.replace('#include <map_fragment>', '#include <map_fragment>\n diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.63,.53,.34),.58);');}});o.receiveShadow=true;});
 root.scale.set(.065,.065,.078);root.position.set(0,-.035,-12);root.updateMatrixWorld(true);scene.add(root);
 return{ground:{model,texture,adaptation:'Original package mesh topology/UV and original texture; low-relief Y flattened for cinematic collision plane',scale:root.scale.toArray()},trees:await addTrees(scene)};
}
