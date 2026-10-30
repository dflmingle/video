using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

public static class ApprovedCastleSceneV22R {
 [Serializable] public class Audit {public string source,output;public bool gridActive;public int disabledGridCount;public Vector3 cameraPosition,cameraEuler;public float fov;public string scope;}
 public static void Run(){
  const string source="Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity";
  var scene=EditorSceneManager.OpenScene(source,OpenSceneMode.Single);GameObject environment=null;
  foreach(var root in scene.GetRootGameObjects())if(root.name=="CastleExterior_Grp")environment=root;
  if(!environment)throw new Exception("Original CastleExterior root not found");
  var copy=UnityEngine.Object.Instantiate(environment);copy.name="CastleExterior_Grp";
  // Move to a new empty scene; no original scene or asset is saved over.
  var target=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);
  SceneManager.MoveGameObjectToScene(copy,target);int count=0;
  foreach(var t in copy.GetComponentsInChildren<Transform>(true))if(t.name=="Gird"){t.gameObject.SetActive(false);count++;}
  if(count!=1)throw new Exception("Expected one Gird, found "+count);
  var camObject=new GameObject("V22R_FixedReferenceCamera");SceneManager.MoveGameObjectToScene(camObject,target);
  var cam=camObject.AddComponent<Camera>();cam.transform.position=new Vector3(0,98,-65);cam.transform.LookAt(new Vector3(0,0,-5));cam.fieldOfView=42;cam.aspect=2f/3f;cam.nearClipPlane=.1f;cam.farClipPlane=600;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.82f,.76f,.66f);cam.tag="MainCamera";
  Directory.CreateDirectory("Assets/V22R");const string output="Assets/V22R/ApprovedCastle-NoGrid.unity";
  if(!EditorSceneManager.SaveScene(target,output))throw new Exception("Candidate save failed");
  Directory.CreateDirectory("output/approved-castle-v22r");
  File.WriteAllText("output/approved-castle-v22r/scene-save-audit.json",JsonUtility.ToJson(new Audit{source=source,output=output,disabledGridCount=count,gridActive=false,cameraPosition=cam.transform.position,cameraEuler=cam.transform.eulerAngles,fov=cam.fieldOfView,scope="Approved environment-only scene copy. No actor placement, speed, asset geometry, or source scene edits. Camera is fixed; battle framing remains separate."},true));
  Debug.Log("APPROVED_CASTLE_SCENE_SAVED "+output+" disabledGrid="+count);
 }
}
