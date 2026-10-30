import * as T from 'three';import {FBXLoader} from 'three/addons/loaders/FBXLoader.js';
export async function addEnvironment(scene){
 const root='/assets/imported/Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/',manager=new T.LoadingManager();manager.setURLModifier(u=>/\.fbx$/i.test(u)?u:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==');
 const loader=new FBXLoader(manager),texture=await new T.TextureLoader().loadAsync(root+'Texture/CastleExterior_Tree_C.png');texture.colorSpace=T.SRGBColorSpace;const source=await loader.loadAsync(root+'Modle/CastleExterior_Tree_04.fbx'),box=new T.Box3().setFromObject(source),size=box.getSize(new T.Vector3()),scale=4.5/size.y;source.scale.multiplyScalar(scale);source.position.y-=box.min.y*scale;
 source.traverse(o=>{if(o.isMesh)o.material=new T.MeshStandardMaterial({map:texture,roughness:1})});
 for(let i=0;i<18;i++){const group=new T.Group(),tree=source.clone(true);group.add(tree);group.position.set((i%2?1:-1)*(30.5+(i%3)*1.2),0,-48+Math.floor(i/2)*11);group.rotation.y=i*2.4;group.scale.setScalar(.65+(i%4)*.13);scene.add(group)}
 return{model:root+'Modle/CastleExterior_Tree_04.fbx',texture:root+'Texture/CastleExterior_Tree_C.png',purpose:'Package original edge vegetation; battlefield floor is authored procedural sand',instances:18};
}
