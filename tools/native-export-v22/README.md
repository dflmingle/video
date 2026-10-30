# Unity 原生场景导出

隔离项目：`C:/Users/89trillion/PveMontageShot01V22-UnityExport`。只复制 V22 `assets/imported/Assets/ArtOfWar-II_Art/Environment` 及原 shaders，保留原 meta GUID；未启动或修改 `My project`。Unity 6000.0.54f1 batchmode 无图形运行，不安装 Pipeline/URP，不修改原始资源。

`NativeSceneExport.Run` 分别使用 `PrefabUtility.LoadPrefabContents` 与 `EditorSceneManager.OpenScene` 加载原 `CastleExterior_Grp.prefab` 和 `CastleExterior.unity`。Unity 解析实际 nested prefab、FBX 导入单位、父子覆写和完整世界矩阵，不手工重建层级或地形。只导出 activeInHierarchy 且 renderer.enabled 的 MeshRenderer+MeshFilter。

产物：`output/native-scenes/CastleExterior-{prefab,scene}/manifest.json` 与 `mesh-N.bin`（路径相对隔离项目）。每份均 34 对象、10 unique mesh、7 材质，0 导出 warning。

## 数据格式

- `meshes`: `vertexCount`，`normalCount`，`uvCount`；`positionOffset`/`normalOffset`/`uvOffset` 为各自 binary 文件中的**字节**位置。position/normal 为 Float32 xyz，uv 为 Float32 xy，小端。
- `submeshes`: `offset` 字节位置，`count` 个 Int32 indices；`topology=0` 表示 Unity triangles。保留每个子网格，不拼造几何。
- `objects`: `mesh` 是 meshes 索引，`materials` 是各 submesh 的材质索引；`matrix` 是完整 `renderer.localToWorldMatrix` 的 **column-major** 数组，可直接 `THREE.Matrix4.fromArray`。不再叠加原 prefab transform 或 FBX scale，否则会重复缩放。
- 输出保留 Unity 世界坐标（+Y up、+Z forward），不在导出器隐藏翻转轴。若浏览器既有渲染坐标系统有 Z 反射，请在外层统一转换并正确处理手性/绕序，不能同时把变换烘进 vertices 又再乘一次 matrix。
- `boundsCenter`/`boundsSize` 是 Unity 原生 Renderer.bounds，供消费端回归。
- 材质保留全部非空 saved texture property/path/scale/offset；TreeB/DecShadow 优先 `_MainTexture`，其余优先实际非空 `_BaseMap`，再 `_MainTexture`/`_MainTex`。
- `shader` 为此 minimal project 实际解析 shader；部分自定义 shader 缺 URP/依赖而成为 `Hidden/InternalErrorShader`，**不表示原资源使用 error shader**。`authoredShaderGuid`/`authoredShaderPath` 另保留源材质引用。这里只原生求值网格与变换，未声称 Unity 原生 shader 外观在 Three.js 等价。

关键原生尺寸：`CastleExterior_Land` 世界中心 (1.6,-0.18,0)，size=(137.2198,0,183.0155)。此前巨大地形是手工 YAML 子节点 scale 与 FBX 单位重复/错误组合所致；消费此原生输出不应再次应用 scale1831。

## 重跑

把 C# 复制到隔离项目 Assets/Editor，运行：

```powershell
& 'C:/Program Files/Unity/Hub/Editor/6000.0.54f1/Editor/Unity.exe' -batchmode -nographics -quit -projectPath 'C:/Users/89trillion/PveMontageShot01V22-UnityExport' -executeMethod NativeSceneExport.Run -logFile 'C:/Users/89trillion/PveMontageShot01V22-UnityExport/native-export.log'
python tools/native-export-v22/validate_native_export.py
```

日志必须包含两次 NATIVE_EXPORT 和 NATIVE_EXPORT_COMPLETE，Unity exit0。验证脚本检验所有 binary index 范围、finite 顶点、完整矩阵变换后 AABB 与原生 Renderer.bounds 一致、土地尺度、TreeB 贴图。产物尚未在浏览器渲染，最终外观由父任务接入后验收。

NewScene output is also produced: 77 active objects, 31 meshes, 19 materials. It contains the authored CastleExterior at x=-165.57, ArenaScene at x=6.825 and CogworkWastes. The `NewScene-scene-castle` preview is the closest native layout to the user screenshot, but remains a failed exact match because the source TreeB material uses the orange `CastleExterior_TreeB_C.png` and the source layout has no left flag. SampleScene and CrossRiverScene exported zero active meshes.
