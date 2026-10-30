using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class PackageDeepAuditR2 {
 [Serializable] public class Record { public string source,kind; public List<Node> nodes=new List<Node>(); public List<Cam> cameras=new List<Cam>(); }
 [Serializable] public class Node { public string path,mesh,meshAsset,rendererType,prefab; public bool activeSelf,activeHierarchy,rendererEnabled; public Vector3 position,rotation,scale,boundsCenter,boundsSize;public int vertices;public string[] materials; }
 [Serializable] public class Cam {public string path;public Vector3 position,rotation;public float fov,orthographicSize;public bool orthographic;}
 [Serializable] public class All { public string unityVersion; public List<Record> records=new List<Record>();public List<string> errors=new List<string>(); }
 static string Hier(Transform t){return t.parent?Hier(t.parent)+"/"+t.name:t.name;}
 static Record Inspect(GameObject[] roots,string source,string kind) {
  var r=new Record{source=source,kind=kind};
  foreach(var root in roots)foreach(var t in root.GetComponentsInChildren<Transform>(true)) {
   var rr=t.GetComponent<Renderer>();var mf=t.GetComponent<MeshFilter>();var sk=t.GetComponent<SkinnedMeshRenderer>();var mesh=mf?mf.sharedMesh:sk?sk.sharedMesh:null;
   var mats=new List<string>();if(rr)foreach(var m in rr.sharedMaterials)mats.Add(m?AssetDatabase.GetAssetPath(m):"MISSING");
   r.nodes.Add(new Node{path=Hier(t),position=t.position,rotation=t.eulerAngles,scale=t.lossyScale,activeSelf=t.gameObject.activeSelf,activeHierarchy=t.gameObject.activeInHierarchy,rendererType=rr?rr.GetType().Name:"",rendererEnabled=rr&&rr.enabled,mesh=mesh?mesh.name:"",meshAsset=mesh?AssetDatabase.GetAssetPath(mesh):"",vertices=mesh?mesh.vertexCount:0,materials=mats.ToArray(),boundsCenter=rr?rr.bounds.center:Vector3.zero,boundsSize=rr?rr.bounds.size:Vector3.zero,prefab=PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(t.gameObject)});
   var cam=t.GetComponent<Camera>();if(cam)r.cameras.Add(new Cam{path=Hier(t),position=t.position,rotation=t.eulerAngles,fov=cam.fieldOfView,orthographic=cam.orthographic,orthographicSize=cam.orthographicSize});
  }
  return r;
 }
 public static void Run() {
  var all=new All{unityVersion=Application.unityVersion};Directory.CreateDirectory("output/package-deep-r2");
  foreach(var guid in AssetDatabase.FindAssets("t:Scene")) {
   string path=AssetDatabase.GUIDToAssetPath(guid);try{var scene=EditorSceneManager.OpenScene(path,OpenSceneMode.Single);var record=Inspect(scene.GetRootGameObjects(),path,"scene");all.records.Add(record);Debug.Log("DEEP_SCENE "+path+" nodes="+record.nodes.Count);}catch(Exception e){all.errors.Add(path+": "+e);}
  }
  foreach(var guid in AssetDatabase.FindAssets("t:Prefab")) {
   string path=AssetDatabase.GUIDToAssetPath(guid);try{var p=PrefabUtility.LoadPrefabContents(path);try{all.records.Add(Inspect(new[]{p},path,"prefab"));}finally{PrefabUtility.UnloadPrefabContents(p);}}catch(Exception e){all.errors.Add(path+": "+e.Message);}
  }
  foreach(var guid in AssetDatabase.FindAssets("t:Model")) {
   string path=AssetDatabase.GUIDToAssetPath(guid);try{var p=AssetDatabase.LoadAssetAtPath<GameObject>(path);if(p)all.records.Add(Inspect(new[]{p},path,"model"));}catch(Exception e){all.errors.Add(path+": "+e.Message);}
  }
  File.WriteAllText("output/package-deep-r2/native-all-hierarchy.json",JsonUtility.ToJson(all,true));Debug.Log("PACKAGE_DEEP_COMPLETE records="+all.records.Count+" errors="+all.errors.Count);
 }
}
