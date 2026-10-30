using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class NativeSceneExport {
 [Serializable] public class Manifest { public string source, unityVersion, matrixLayout="column-major, Unity world coordinates; use Matrix4.fromArray"; public List<Obj> objects=new List<Obj>(); public List<Mat> materials=new List<Mat>(); public List<MeshData> meshes=new List<MeshData>(); public List<string> warnings=new List<string>(); }
 [Serializable] public class Obj { public string path; public int mesh; public float[] matrix; public int[] materials; public Vector3 boundsCenter,boundsSize; }
 [Serializable] public class MeshData { public string name,asset,file; public int vertexCount,normalCount,uvCount; public long positionOffset,normalOffset,uvOffset; public List<Sub> submeshes=new List<Sub>(); }
 [Serializable] public class Sub { public long offset; public int count,topology; }
 [Serializable] public class Tex { public string property,path; public Vector2 scale,offset; }
 [Serializable] public class Scalar { public string property; public float value; }
 [Serializable] public class Tint { public string property; public Color value; }
 [Serializable] public class Mat { public string name,path,shader,authoredShaderGuid,authoredShaderPath,textureProperty,texturePath; public Color color; public int renderQueue; public List<Tex> textures=new List<Tex>(); public List<Scalar> floats=new List<Scalar>(); public List<Tint> colors=new List<Tint>(); }
 static string Hier(Transform t) { return t.parent==null?t.name:Hier(t.parent)+"/"+t.name; }
 static float[] Matrix(Matrix4x4 m) { var a=new float[16];for(int col=0;col<4;col++)for(int row=0;row<4;row++)a[col*4+row]=m[row,col];return a; }
 static void Vec(BinaryWriter b, Vector3[] a) {foreach(var v in a){b.Write(v.x);b.Write(v.y);b.Write(v.z);}}
 static void Export(GameObject[] roots,string source,string tag) {
  string dir=Path.GetFullPath("output/native-scenes/"+tag);Directory.CreateDirectory(dir);
  var manifest=new Manifest{source=source,unityVersion=Application.unityVersion};var meshIds=new Dictionary<Mesh,int>();var materialIds=new Dictionary<Material,int>();
  foreach(var root in roots)foreach(var renderer in root.GetComponentsInChildren<MeshRenderer>(false)) {
   if(!renderer.enabled || !renderer.gameObject.activeInHierarchy)continue;
   var filter=renderer.GetComponent<MeshFilter>();if(filter==null||filter.sharedMesh==null)continue;var mesh=filter.sharedMesh;
   int meshId;
   if(!meshIds.TryGetValue(mesh,out meshId)) {
    meshId=manifest.meshes.Count;meshIds[mesh]=meshId;
    try {
     var d=new MeshData{name=mesh.name,asset=AssetDatabase.GetAssetPath(mesh),file="mesh-"+meshId+".bin",vertexCount=mesh.vertexCount,normalCount=mesh.normals.Length,uvCount=mesh.uv.Length};
     using(var w=new BinaryWriter(File.Create(Path.Combine(dir,d.file)))) {
      d.positionOffset=w.BaseStream.Position;Vec(w,mesh.vertices);
      d.normalOffset=w.BaseStream.Position;Vec(w,mesh.normals);
      d.uvOffset=w.BaseStream.Position;foreach(var uv in mesh.uv){w.Write(uv.x);w.Write(uv.y);}
      for(int sm=0;sm<mesh.subMeshCount;sm++){var ix=mesh.GetIndices(sm);var sub=new Sub{offset=w.BaseStream.Position,count=ix.Length,topology=(int)mesh.GetTopology(sm)};foreach(var i in ix)w.Write(i);d.submeshes.Add(sub);}
     }
     manifest.meshes.Add(d);
    } catch(Exception e){manifest.warnings.Add("Mesh failure "+mesh.name+": "+e.Message);meshIds.Remove(mesh);continue;}
   }
   var mats=new List<int>();
   foreach(var material in renderer.sharedMaterials) {
    if(material==null){mats.Add(-1);continue;}int id;
    if(!materialIds.TryGetValue(material,out id)) {
     id=manifest.materials.Count;materialIds[material]=id;
     var m=new Mat{name=material.name,path=AssetDatabase.GetAssetPath(material),shader=material.shader?material.shader.name:"",color=Color.white,renderQueue=material.renderQueue};
     var shaderMatch=System.Text.RegularExpressions.Regex.Match(File.ReadAllText(m.path),@"m_Shader:.*guid: ([a-f0-9]+)");
     if(shaderMatch.Success){m.authoredShaderGuid=shaderMatch.Groups[1].Value;m.authoredShaderPath=AssetDatabase.GUIDToAssetPath(m.authoredShaderGuid);}
     // Saved texture properties retain bindings even if the original custom
     // shader has missing dependencies in this minimal export-only project.
     var so=new SerializedObject(material);var saved=so.FindProperty("m_SavedProperties.m_TexEnvs");
     if(saved!=null)for(int i=0;i<saved.arraySize;i++) {
      var pair=saved.GetArrayElementAtIndex(i);var key=pair.FindPropertyRelative("first").stringValue;var val=pair.FindPropertyRelative("second");var tx=val.FindPropertyRelative("m_Texture").objectReferenceValue;
      if(tx!=null)m.textures.Add(new Tex{property=key,path=AssetDatabase.GetAssetPath(tx),scale=val.FindPropertyRelative("m_Scale").vector2Value,offset=val.FindPropertyRelative("m_Offset").vector2Value});
     }
     var fs=so.FindProperty("m_SavedProperties.m_Floats");if(fs!=null)for(int i=0;i<fs.arraySize;i++){var pair=fs.GetArrayElementAtIndex(i);m.floats.Add(new Scalar{property=pair.FindPropertyRelative("first").stringValue,value=pair.FindPropertyRelative("second").floatValue});}
     var cs=so.FindProperty("m_SavedProperties.m_Colors");if(cs!=null)for(int i=0;i<cs.arraySize;i++){var pair=cs.GetArrayElementAtIndex(i);m.colors.Add(new Tint{property=pair.FindPropertyRelative("first").stringValue,value=pair.FindPropertyRelative("second").colorValue});}
     var prefer=m.shader.IndexOf("DecShadow",StringComparison.OrdinalIgnoreCase)>=0||m.name.Contains("TreeB")?new[]{"_MainTexture","_BaseMap","_MainTex"}:new[]{"_BaseMap","_MainTexture","_MainTex"};
     foreach(var property in prefer){var tx=m.textures.Find(x=>x.property==property);if(tx!=null){m.textureProperty=property;m.texturePath=tx.path;break;}}
     if(material.HasProperty("_BaseColor"))m.color=material.GetColor("_BaseColor");else if(material.HasProperty("_Color"))m.color=material.GetColor("_Color");
     manifest.materials.Add(m);
    }
    mats.Add(id);
   }
   manifest.objects.Add(new Obj{path=Hier(renderer.transform),mesh=meshId,matrix=Matrix(renderer.localToWorldMatrix),materials=mats.ToArray(),boundsCenter=renderer.bounds.center,boundsSize=renderer.bounds.size});
  }
  File.WriteAllText(Path.Combine(dir,"manifest.json"),JsonUtility.ToJson(manifest,true));
  Debug.Log("NATIVE_EXPORT "+tag+" objects="+manifest.objects.Count+" meshes="+manifest.meshes.Count+" materials="+manifest.materials.Count+" warnings="+manifest.warnings.Count);
 }
 public static void Run() {
  const string prefab="Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior_Grp.prefab";
  var loaded=PrefabUtility.LoadPrefabContents(prefab);try{Export(new[]{loaded},prefab,"CastleExterior-prefab");}finally{PrefabUtility.UnloadPrefabContents(loaded);}
  const string scene="Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity";
  var opened=EditorSceneManager.OpenScene(scene,OpenSceneMode.Single);Export(opened.GetRootGameObjects(),scene,"CastleExterior-scene");
  const string arenaPrefab="Assets/ArtOfWar-II_Art/Environment/Feature/ArenaScene/ArenaScene_Grp.prefab";
  loaded=PrefabUtility.LoadPrefabContents(arenaPrefab);try{Export(new[]{loaded},arenaPrefab,"ArenaScene-prefab");}finally{PrefabUtility.UnloadPrefabContents(loaded);}
  const string arenaScene="Assets/ArtOfWar-II_Art/Environment/Feature/ArenaScene/ArenaScene.unity";
  opened=EditorSceneManager.OpenScene(arenaScene,OpenSceneMode.Single);Export(opened.GetRootGameObjects(),arenaScene,"ArenaScene-scene");
  ExportScene("Assets/New Scene.unity","NewScene");
  ExportScene("Assets/Scenes/SampleScene.unity","SampleScene");
  ExportScene("Assets/20261019-跨河强渡战役/20261019-跨河强渡战役.unity","CrossRiverScene");
  Debug.Log("NATIVE_EXPORT_COMPLETE");
 }
 static void ExportScene(string scene,string tag) {
  if(!File.Exists(scene)){Debug.LogWarning("NATIVE_EXPORT_MISSING "+scene);return;}
  try { var opened=EditorSceneManager.OpenScene(scene,OpenSceneMode.Single); Export(opened.GetRootGameObjects(),scene,tag); }
  catch(Exception e){Debug.LogWarning("NATIVE_EXPORT_SCENE_FAILED "+scene+" "+e.Message); }
 }
}
