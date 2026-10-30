# 2026-10-30 用户确认：CastleExterior / 关闭 Gird / 固定参考视角

本记录覆盖本目录旧报告中的「场景待选」「需要恢复 PDF 的绿色树冠、骷髅牌」结论。旧报告保留调查背景，不再作为当前场景验收标准。

## 用户最新确认

用户指着 `PACKAGE-VS-DOCUMENT.jpg` 明确说：「是这个场景，需要把上面的格子关掉」，并给出 Unity 层级 `CastleExterior_Grp/Gird` 和无格子参考视角。此确认授权使用**包内现有 CastleExterior 版本**，不继续寻找或拼装另一套树木、城门、围栏、牌子。

## 本轮实施

- 原生来源：`PVE混剪.unitypackage` 内 `Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity`。
- 只关闭 `CastleExterior_Grp/Gird`，保留 `CastleExterior_Land` 及其原贴图。浏览器 loader 的 `grid=0` 现在可同时用于场景页和战斗预览；其他旧入口默认行为保持原样。
- 新增 `preset=castle-approved`：1440×2160，固定俯视相机。Unity 世界相机 `(0,98,-65)`，看向 `(0,0,-5)`，俯角约 58.523°，FOV 42°。浏览器采用已有文档声明的 Z 手性转换，环境和场景检查相机一致转换。
- 没有推拉、跟随、动态包围盒适配或相机时间线。192 个时间样本的场景相机参数相同；这是场景预览检查，不冒充完成 3 秒战斗验收。
- 真正 Unity 场景副本已保存：`C:/Users/89trillion/PveMontageShot01V22R-PackageSceneAudit/Assets/V22R/ApprovedCastle-NoGrid.unity`。在原生加载后复制环境根及全部原物体相对变换到新场景，关闭一个 Gird，新增固定相机。原场景、Prefab、模型、材质和贴图均未覆盖。
- 仓库副本在 `scenes/v22r/ApprovedCastle-NoGrid.unity`，其 GUID 引用依赖指定原包。直接可打开的完整隔离 Unity 工程仍是上述 PackageSceneAudit。
- 确认场景静帧：`output/v22r-approved-castle/scene-grid-off.png`。格子开关对照 `scene-grid-on.png`。实际加载、可见性、矩阵与相机日志 `checks.json`。

## 当前边界

用户给的第 3 张图带有 Unity 的光照与投影；本轮浏览器静帧采用原几何、贴图和现有材质预览，没有声称 Unity Shader、阴影逐像素一致。场景来源和 Gird 关闭已经落实。

按相同近景机位叠加原 V22R-overlap 士兵坐标，开场红军位于原城墙后侧，部分后军出画。`battle-0.000.png` 是这一问题的诊断证据，**不能作为正式战斗构图**。没有擅自平移军队、缩放模型、移动个别建筑或拖慢冲锋。

地面 Z 方向原始宽度约 183.016，城墙前的主要可用纵深约 121–127；红军最后排到蓝军后排初始跨度约 143.734（−102.384 到 41.35），还未计人物边界。原坐标轴向和近景构图都需要在后续进行独立空间核算；本次不会把该问题转嫁成重新更换场景。

约 3 秒目标、开场双方同时运动、真实箭雨、轻微受击和 ≥4.0 净距要求继续保留。本轮未修改模拟缓存、双方起始位置、速度、射击状态机或受击流程，未制作完整视频。

## 复核入口

场景页：`http://127.0.0.1:5267/scene-native-v22.html?preset=castle-approved&capture=1`。

复核工具：`node tools/capture_approved_castle_v22r.mjs`。原生场景创建工具：`tools/native-export-v22/ApprovedCastleSceneV22R.cs`。首次创建工具曾错误调用仅 Play Mode 可用的 DontDestroyOnLoad；已移除，随后 Unity 执行成功，日志 `output/approved-castle-v22r-unity.log` 以退出码 0 结束，不采用失败运行作为保存证据。
