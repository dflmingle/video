"""Copy original WFL dependency closure into an isolated Unity export project."""
import collections,hashlib,json,re,shutil,subprocess
from pathlib import Path

R=Path(__file__).resolve().parents[1];O=R/'docs/scene-requirements-r2'
SOURCE=Path('C:/Users/89trillion/Desktop/WFL/LockstepGameEngineV1_5')
TARGET=Path('C:/Users/89trillion/PveMontageShot01V22R-SceneAudit')
GUID=re.compile(r'guid: ([a-f0-9]{32})')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 guids={}
 indexed=subprocess.check_output(['rg','--no-heading','--with-filename','--glob','*.meta','^guid: [a-f0-9]{32}',str(SOURCE/'Assets')],text=True,encoding='utf8')
 for line in indexed.splitlines():
  meta,_,guid=line.rpartition(':guid: ')
  if len(guid.strip())==32:guids[guid.strip()]=Path(meta[:-5])
 prefab=SOURCE/'Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior_Grp.prefab'
 scene=prefab.with_name('CastleExterior.unity');queue=[prefab];seen=set();missing={};references={}
 modelRoot=SOURCE/'Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle'
 for name in ['CastleExterior_Flag','CastleExterior_Fence_01','CastleExterior_Fence_02','CastleExterior_Castle']:
  queue.append(modelRoot/(name+'.fbx'))
 while queue:
  p=queue.pop()
  if p in seen:continue
  seen.add(p);refs=set();meta=Path(str(p)+'.meta')
  if p.suffix.lower() in {'.prefab','.mat','.asset','.shader','.shadergraph','.shadersubgraph'}:refs.update(GUID.findall(p.read_text(encoding='utf8',errors='replace')))
  if meta.exists():refs.update(GUID.findall(meta.read_text(encoding='utf8',errors='replace')))
  references[str(p.relative_to(SOURCE))]={g:str(guids[g].relative_to(SOURCE)) if g in guids else None for g in refs}
  for g in refs:
   if g in guids and guids[g].suffix.lower() not in {'.cs','.dll'}:queue.append(guids[g])
   elif g not in guids:missing[g]=str(p.relative_to(SOURCE))
 seen.add(scene)
 files=[]
 for p in sorted(seen):
  if not p.is_file():continue
  dst=TARGET/p.relative_to(SOURCE);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
  meta=Path(str(p)+'.meta')
  if meta.exists():shutil.copy2(meta,Path(str(dst)+'.meta'))
  files.append(dict(source=str(p),copy=str(dst),sha256=digest(p),bytes=p.stat().st_size,copyMatches=digest(p)==digest(dst)))
 (TARGET/'Packages').mkdir(parents=True,exist_ok=True);(TARGET/'Packages/manifest.json').write_text('{"dependencies":{}}',encoding='utf8')
 (TARGET/'ProjectSettings').mkdir(exist_ok=True);(TARGET/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.0.54f1\n',encoding='utf8')
 original=(R/'tools/native-export-v22/NativeSceneExport.cs').read_text(encoding='utf8')
 s=original.replace('class NativeSceneExport','class OriginalSceneExportR2').replace('output/native-scenes/','output/native-scenes-original-r2/')
 a=s.index(' public static void Run() {');b=s.index(' static void ExportScene',a)
 s=s[:a]+''' public static void Run() {
  const string prefab="Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior_Grp.prefab";
  var loaded=PrefabUtility.LoadPrefabContents(prefab);
  try { Export(new[]{loaded},prefab,"OriginalCastle-prefab"); } finally {PrefabUtility.UnloadPrefabContents(loaded);}
  var opened=EditorSceneManager.OpenScene("Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity",OpenSceneMode.Single);
  var roots=opened.GetRootGameObjects();
  var candidates=new List<GameObject>();
  foreach(var root in roots)if(root.name.Contains("CastleExterior"))candidates.Add(root);
  Export(candidates.ToArray(),"Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity","OriginalCastle-scene");
  var cameras=new List<CameraInfo>();
  foreach(var root in roots)foreach(var camera in root.GetComponentsInChildren<Camera>(true))cameras.Add(new CameraInfo{path=Hier(camera.transform),position=camera.transform.position,rotation=camera.transform.eulerAngles,orthographic=camera.orthographic,fieldOfView=camera.fieldOfView,orthographicSize=camera.orthographicSize,enabled=camera.enabled,active=camera.gameObject.activeInHierarchy});
  var hierarchy=new List<NodeInfo>();
  foreach(var root in candidates)foreach(var t in root.GetComponentsInChildren<Transform>(true))hierarchy.Add(new NodeInfo{path=Hier(t),position=t.position,localPosition=t.localPosition,eulerAngles=t.eulerAngles,localScale=t.localScale,matrix=Matrix(t.localToWorldMatrix),active=t.gameObject.activeInHierarchy});
  Directory.CreateDirectory("output/native-scenes-original-r2");
  File.WriteAllText("output/native-scenes-original-r2/source-cameras-hierarchy.json",JsonUtility.ToJson(new SourceInfo{cameras=cameras,hierarchy=hierarchy},true));
  foreach(var modelName in new[]{"CastleExterior_Flag","CastleExterior_Fence_01","CastleExterior_Fence_02","CastleExterior_Castle"}) {
   var asset=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/"+modelName+".fbx");
   var instance=(GameObject)PrefabUtility.InstantiatePrefab(asset);
   try {Export(new[]{instance},AssetDatabase.GetAssetPath(asset),modelName+"-asset-only");} finally {UnityEngine.Object.DestroyImmediate(instance);}
  }
  Debug.Log("ORIGINAL_R2_EXPORT_COMPLETE roots="+candidates.Count+" cameras="+cameras.Count);
 }
 [Serializable] public class CameraInfo {public string path;public Vector3 position,rotation;public bool orthographic,enabled,active;public float fieldOfView,orthographicSize;}
 [Serializable] public class NodeInfo {public string path;public Vector3 position,localPosition,eulerAngles,localScale;public float[] matrix;public bool active;}
 [Serializable] public class SourceInfo {public List<CameraInfo> cameras;public List<NodeInfo> hierarchy;}
'''+s[b:]
 code=TARGET/'Assets/Editor/OriginalSceneExportR2.cs';code.parent.mkdir(exist_ok=True);code.write_text(s,encoding='utf8');(R/'tools/native-export-v22/OriginalSceneExportR2.cs').write_text(s,encoding='utf8')
 result=dict(sourceRoot=str(SOURCE),isolatedProject=str(TARGET),prefab=str(prefab),scene=str(scene),copiedFiles=files,types=dict(collections.Counter(Path(x['source']).suffix for x in files)),references=references,missingGuids=missing,policy='No original edited. Scene runtime scripts intentionally absent; only original CastleExterior root exported, plus serialized camera and original hierarchy.')
 (O/'original-scene-copy-provenance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(dict(copied=len(files),bytes=sum(x['bytes'] for x in files),types=result['types'],missing=len(missing),copyMatches=all(x['copyMatches'] for x in files)),ensure_ascii=False))
if __name__=='__main__':main()
