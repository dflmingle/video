"""Generate an isolated exporter from the existing native geometry exporter."""
from pathlib import Path
R=Path(__file__).resolve().parents[1]
TARGET=Path('C:/Users/89trillion/PveMontageShot01V22R-PackageSceneAudit')
s=(R/'tools/native-export-v22/NativeSceneExport.cs').read_text(encoding='utf8')
s=s.replace('class NativeSceneExport','class PackageSceneExportR2').replace('output/native-scenes/','output/package-scenes-r2/')
a=s.index(' public static void Run() {');b=s.index(' static void ExportScene',a)
s=s[:a]+''' public static void Run() {
  foreach(var name in new[]{"CastleExterior","ArenaScene","CogworkWastes"}) {
   var path="Assets/ArtOfWar-II_Art/Environment/Feature/"+name+"/"+name+".unity";
   var opened=EditorSceneManager.OpenScene(path,OpenSceneMode.Single);var roots=new List<GameObject>();
   foreach(var root in opened.GetRootGameObjects())if(root.name.Contains(name))roots.Add(root);
   Export(roots.ToArray(),path,name+"-scene");
  }
  ExportScene("Assets/New Scene.unity","NewScene");
  foreach(var modelName in new[]{"CastleExterior_Building","CastleExterior_Tree_04","CastleExterior_Tree_05","CastleExterior_Stakes_01","CastleExterior_Stakes_02"}) {
   var asset=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/"+modelName+".fbx");
   var instance=(GameObject)PrefabUtility.InstantiatePrefab(asset);
   try{Export(new[]{instance},AssetDatabase.GetAssetPath(asset),modelName+"-asset-only");}finally{UnityEngine.Object.DestroyImmediate(instance);}
  }
  Debug.Log("PACKAGE_R2_EXPORT_COMPLETE");
 }
'''+s[b:]
(R/'tools/native-export-v22/PackageSceneExportR2.cs').write_text(s,encoding='utf8')
(TARGET/'Assets/Editor/PackageSceneExportR2.cs').write_text(s,encoding='utf8')
print('Generated package-only native exporter')
