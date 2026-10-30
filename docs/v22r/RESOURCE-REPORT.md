# V22-R 原始资源映射

原包根：`PVE混剪.unitypackage`。以下路径均来自磁盘/Unity 导出清单，未修改源资产。

| 元素 | 原始模型路径 | 材质与贴图 | 当前对象/匹配状态 |
|---|---|---|---|
|地面|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/CastleExterior_Land.fbx|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Material/CastleExterior_Land_Mat.mat<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Texture/CastleExterior_Land_C.png|1 个原生对象；来源确认；参考图的布局/材质匹配待确认|
|棋盘覆盖层|Assets/ArtOfWar-II_Art/Environment/Common/SnowBridge/Mesh/SnowBridge_Gird.fbx|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Material/CastleExterior_Gird_Mat.mat|1 个原生对象；来源确认；参考图的布局/材质匹配待确认|
|城墙和城门|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/CastleExterior_Building.fbx|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Material/CastleExterior_Castle_Mat.mat<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Material/CastleExterior_Mountain_Mat.mat<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Texture/CastleExterior_Castle_C.png<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Texture/CastleExterior_Mountain_C.png|2 个原生对象；来源确认；参考图的布局/材质匹配待确认|
|树木|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/CastleExterior_Tree_04.fbx<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/CastleExterior_Tree_05.fbx|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Material/CastleExterior_TreeB_Mat.mat<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Texture/CastleExterior_TreeB_C.png|8 个原生对象；来源确认；参考图的布局/材质匹配待确认|
|木桩围栏|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/CastleExterior_Stakes_01.fbx<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Modle/CastleExterior_Stakes_02.fbx|Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Material/CastleExterior_TreeB_Mat.mat<br>Assets/ArtOfWar-II_Art/Environment/Common/CastleExterior/Texture/CastleExterior_TreeB_C.png|12 个原生对象；来源确认；参考图的布局/材质匹配待确认|
|告示牌/紫色徽记|未确认||0 个原生对象；未找到可确认对应物；ArenaScene_Flag 是旗帜候选，不能冒充告示牌|
|旗帜候选|Assets/ArtOfWar-II_Art/Environment/Common/ArenaScene/Model/ArenaScene_Flag.fbx|Assets/ArtOfWar-II_Art/Environment/Common/ArenaScene/Material/ArenaScene_Castle_Mat.mat<br>Assets/ArtOfWar-II_Art/Environment/Common/ArenaScene/Texture/ArenaScene_Castle_C.png|4 个原生对象；原包存在；参考图左侧标志的对应关系未确认|

完整对象层级和路径见 `resource-map.json`。城墙和城门在同一 Building FBX 中，没有独立 Gate 文件。树木绑定 `CastleExterior_TreeB_Mat` 的 `_MainTexture`，原 shader 确实采样 `_MainTexture`；不能为得到绿色擅自改接遗留 `_MainTex`。

## 全部候选场景与排除依据

| 候选 | 来源 | 核查结论 |
|---|---|---|
| New Scene | 原包 Assets/New Scene.unity | 原生 77 对象；包含竞技场/城堡/工厂，战斗 x≈0 对应竞技场，城堡在 x≈−165.57 |
| CastleExterior | Feature/CastleExterior/CastleExterior.unity 与原 Prefab | 34 对象；元素最接近，树色、标志、方位不一致，未通过参考匹配 |
| ArenaScene | Feature/ArenaScene/ArenaScene.unity 与原 Prefab | 35 对象；椭圆竞技场，不符合参考 |
| CogworkWastes | Feature/CogworkWastes/CogworkWastes.unity | 新 Unity 原生导出 8 对象，蓝色工厂场景，不符合参考 |
| SampleScene | 原包 Assets/Scenes/SampleScene.unity | 相机/灯光/Volume，没有目标环境 |
| 跨河强渡战役 | 原包与当前工程 | 角色资源展示，无目标城堡 |
| 当前工程其余场景 | 17 个场景逐个解析递归 GUID 依赖 | 公会战塔、双桥演出、背景图或示例；未找到 CastleExterior 原生环境依赖 |
| Pve压迫感 | 资源包与当前工程 | 场景包含“底图”及弓手，引用图片；不能作为目标 3D 环境 |

扫描范围和每个场景的递归依赖保存在 `resources-*.json` 和 `package-dependencies.json`。8 份外部包含 2 份同名公会战包；9 份内嵌包均为角色特效，没有额外 .unity 场景。Downloads/assets*.zip 等未证实与本任务有关的通用压缩包未擅自解包。

## 坐标转换提案：尚未实施

New Scene 的 Castle 根在 (−165.5697,0,6.2807)，原生建筑在 +Z，参考构图需要建筑在红军后方。若采用该城堡，需要报告并确认**整个环境根**的统一平移/旋转（可能还涉及环境尺度）；所有建筑相对位置保持。单纯将 x 平移 +165.5697 只能移到中心，不能解决前后方向、地面覆盖范围和树/标志差异。当前未实施任何转换、材质改接或建筑重摆。

## 静帧对照

同一 V22-C 轨迹、同一 V22-B 参数：0、1.3、2.416667、2.733333 秒。原生 NewScene / CastleExterior / ArenaScene 各 4 张，原始 PNG 在 `output/v22r-scenes`；A/B/C 小图 `ABC-0.jpg` 到 `ABC-3.jpg`。C 为用户参考图，只在审阅文档展示，没有放入渲染背景。

场景相同时间的士兵坐标与相机矩阵完全一致，页面无脚本错误。该对照保留 V22 原推近，目的是隔离场景变量，不能作为全程固定镜头验收。另有固定开场诊断，未作为正式场景替换。