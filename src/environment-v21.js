import * as T from 'three';
import {FBXLoader} from 'three/addons/loaders/FBXLoader.js';

// Selective Three.js conversion of the formal UnityPackage scene.  The
// original Unity scene remains the source of truth; browser rendering uses
// the exported FBX/PNG pairs with the same relative scale and colors.
const ROOT='/assets/imported/Assets/ArtOfWar-II_Art/Environment/Common/';
const ARENA=ROOT+'ArenaScene/';
const CASTLE=ROOT+'CastleExterior/';

function manager(){
  const m=new T.LoadingManager();
  m.setURLModifier(u=>/\.fbx(?:\?|$)/i.test(u)?u:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==');
  return m;
}

async function model(path, texturePath, color, scale=[.065,.065,.078], flatten=false){
  const root=await new FBXLoader(manager()).loadAsync(path);
  let map=null;
  if(texturePath){
    map=await new T.TextureLoader().loadAsync(texturePath);
    map.colorSpace=T.SRGBColorSpace; map.anisotropy=8;
  }
  root.traverse(o=>{
    if(!o.isMesh)return;
    if(flatten){
      const g=o.geometry.clone(),a=g.attributes.position;
      for(let i=0;i<a.count;i++)a.setY(i,0); a.needsUpdate=true; g.computeVertexNormals(); o.geometry=g;
    }
    o.material=new T.MeshStandardMaterial({map,color:new T.Color(color),roughness:.9,metalness:0});
    o.receiveShadow=true; o.castShadow=false;
  });
  root.scale.set(...scale); root.updateMatrixWorld(true); return root;
}

export async function addEnvironment(scene){
  const audit={source:'PVE混剪.unitypackage',scene:'New Scene.unity',formalAssets:true,objects:[]};
  const land=await model(ARENA+'Model/ArenaScene_Land.fbx',ARENA+'Texture/ArenaScene_Land_C.png',0xffffff,[.065,.065,.078],true);
  land.position.set(0,-.035,-12); scene.add(land);
  audit.objects.push({id:'ArenaScene_Land',path:'ArenaScene/Model/ArenaScene_Land.fbx',position:land.position.toArray()});

  // Keep the central engagement lane clear. Formal castle/edge pieces sit on
  // the far perimeter and never intersect the archer U or arrow trajectories.
  const castle=await model(CASTLE+'Modle/CastleExterior_Building.fbx',CASTLE+'Texture/CastleExterior_Castle_C.png',0xffffff);
  castle.position.set(0,-.03,88); castle.scale.multiplyScalar(.20); scene.add(castle);
  audit.objects.push({id:'CastleExterior_Building',path:'CastleExterior/Modle/CastleExterior_Building.fbx',position:castle.position.toArray()});

  for(const [name,x] of [['ArenaScene_HighWalls',-24],['ArenaScene_HighWalls',24]]){
    const wall=await model(ARENA+'Model/ArenaScene_HighWalls.fbx',ARENA+'Texture/ArenaScene_LowWall_C.png',0xffffff);
    wall.position.set(x*1.65,-.03,78); wall.scale.multiplyScalar(.14); scene.add(wall);
    audit.objects.push({id:name,path:'ArenaScene/Model/ArenaScene_HighWalls.fbx',position:wall.position.toArray()});
  }
  for(const [x,z] of [[-28,33],[28,33]]){
    const tree=await model(CASTLE+'Modle/CastleExterior_Tree_04.fbx',CASTLE+'Texture/CastleExterior_Tree_C.png',0xffffff);
    tree.position.set(x*1.45,-.02,80); tree.scale.multiplyScalar(.12); scene.add(tree);
    audit.objects.push({id:'CastleExterior_Tree_04',path:'CastleExterior/Modle/CastleExterior_Tree_04.fbx',position:tree.position.toArray()});
  }
  const flag=await model(ARENA+'Model/ArenaScene_Flag.fbx',ARENA+'Texture/ArenaScene_Castle_C.png',0xffffff);
  flag.position.set(0,-.03,76); flag.scale.multiplyScalar(.16); scene.add(flag);
  audit.objects.push({id:'ArenaScene_Flag',path:'ArenaScene/Model/ArenaScene_Flag.fbx',position:flag.position.toArray()});
  return audit;
}
