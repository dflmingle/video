from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'tools/native-export-v22/NativeSceneExport.cs').read_text(encoding='utf8')
s=s.replace('class NativeSceneExport','class NativeSceneAuditV22R').replace('output/native-scenes/','output/native-scenes-v22r/')
a=s.index(' public static void Run() {');b=s.index(' static void ExportScene',a)
s=s[:a]+''' public static void Run() {
  ExportScene("Assets/ArtOfWar-II_Art/Environment/Feature/CogworkWastes/CogworkWastes.unity","CogworkWastes");
  Debug.Log("V22R_NATIVE_AUDIT_COMPLETE");
 }
'''+s[b:]
(root/'tools/native-export-v22/NativeSceneAuditV22R.cs').write_text(s,encoding='utf8')
Path('C:/Users/89trillion/PveMontageShot01V22-UnityExport/Assets/Editor/NativeSceneAuditV22R.cs').write_text(s,encoding='utf8')
