# V22 原生场景浏览器预览

## 实现与来源

预览从 Unity 6000.0.54f1 原生求值的 `CastleExterior.unity` 与 `CastleExterior_Grp.prefab` 读取实际 vertices、UV、submesh indices、材质绑定及完整 world matrix。没有手绘土地、重造城墙、重新摆放道具或再次套用 FBX 单位缩放。

- `src/environment-native-v22.js`：可集成的 `addNativeEnvironment(scene, options)`；只加载 JSON+binary，不解析 YAML 或 FBX。
- `src/scene-native-preview-v22.js` / `scene-native-v22.html`：无士兵的两种静态观察尺度。
- `tools/capture_native_scene_v22.mjs`：对 Scene/Prefab、全景/局部、正式/debug/无 Grid 对照共 12 张浏览器截图，保存审计 JSON，遇到 pageerror 或 WebGL console error 非零退出。

网格数据位于 `public/native-scenes/CastleExterior-{scene,prefab}`，从独立 Unity 导出工程复制；原始资源纹理仍引用 `assets/imported/Assets/...`。这些生成物未入 Git，主任务集成时需要复制整个 `public/native-scenes`。

## 修正了不完整导入引起的误判

初次 minimal export 中找不到 Grid/DecShadow shader，并不代表原 package 没有它们。复核 `docs/package-inventory.json` 和原 `PVE混剪.unitypackage` 后，确认并按原 GUID 补齐：

| GUID | 原包资源 | 处理 |
|---|---|---|
| 736974b9f28792b4a8cbc2a70e792395 | ArtOfWar-II_Art/Shaders/Grid.shader | 原文件/原 meta 复制到独立 Unity 工程 |
| 6e46eb022277fe44eb5eeb162a4551b4 | ArtOfWar-II_Art/Shaders/DecShadow.shader | 同上 |
| 8719d446b9efe4811abb73bbfe603609 | Effects/BattleUnit/BattleUnit_51/Low/Textures/08ce35de.png | 原遮罩绑定恢复 |
| 1f640f97f523e96458e8ee5cb6256797 | Grid 材质中的旧 TextureSample0 | 原包确实未含此 GUID；当前 Grid shader 不采样该字段 |
| 70a736fce43c8b448a4d4f5988b6bbda | Grid 材质中的旧 TillingMasj | 同上，不作为当前 Grid 可见行为 blocker |

遮罩文件名虽为 `.png`，字节实际是 DDS；浏览器 Image 无法解码。使用 PIL 无损解码得到 `public/native-scenes/textures/08ce35de-decoded.png`，保留原始样本像素，不重新生成视觉内容。

导出工具补充材质 saved floats/colors 与 authored shader GUID/path。当前 Gird 原生网格保留可见，按原 Grid.shader 的 worldXZ、Scale、Offset、屏幕导数抗锯齿、颜色混合、Mask 及 `Blend DstColor Zero` 实现。`_UseShapeControl` 未在原材质启用，使用原网格分支。Three r180 MultiplyBlending 必须设置 premultipliedAlpha=true；第一次实际截图发现白色覆盖错误后已修复并重拍，不能把早期白棋盘截图作为最终图。

## 可查看与重复执行

隔离 Vite 进程 PID 30468，端口 5265，项目为 `PveMontageShot01V22-camera`。

- `http://127.0.0.1:5265/scene-native-v22.html?source=scene&view=combat`
- `http://127.0.0.1:5265/scene-native-v22.html?source=prefab&view=overview`
- `debugMissing=1` 强制显示任何不受支持的材质对象；当前全部资源解析，debug 与正常图一致。
- `grid=0` 明确关闭原 Grid 覆盖层，仅用于诊断对照，不冒充完整场景。

```powershell
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5265 --strictPort
node tools/capture_native_scene_v22.mjs
python tools/native-export-v22/validate_native_export.py
```

输出：`output/V22-native-scene-preview/{scene,prefab}-{overview,combat}{,-debug,-no-grid}.png` 及同名审计 JSON。

## New Scene 包装场景核对

进一步用同一 Unity 原生导出器打开了 `Assets/New Scene.unity`，得到 77 个 active 网格对象、31 个 mesh、19 个材质；它确实是包装布局，包含平移到 x=-165.57 的 CastleExterior、x=6.825 的 ArenaScene 和另一套 CogworkWastes。`NewScene-scene-castle.png` 是以 Castle 根的真实世界位置为中心的最佳静态构图，地面、紫色墙、城门和橙色边缘与用户截图的空间关系最接近。ArenaScene 裸场景及 New Scene 的中心视角都是椭圆竞技场，已排除为目标画面。

但源资源本身仍存在两个可见差异：CastleExterior 的 TreeB 材质在原材质保存的 `_MainTexture` 绑定为 `CastleExterior_TreeB_C.png`（橙红块树），而用户截图是绿色松树；原 New Scene Castle 布局没有用户截图左侧旗帜。`CastleExterior_Tree_C.png` 与 Arena Flag 资源确实存在，但把 `_MainTex` 或别的 prefab 资源改接进去会是材质/布局重设计，不能宣称“原场景完全匹配”。当前报告明确把 NewScene-castle 标为**最佳原生近似、未通过目标匹配**。

同时导出 `SampleScene.unity` 与 `20261019-跨河强渡战役.unity`，均为 0 active mesh，不是目标环境。

## 实际检查结果与边界

已亲自通过 view_image 查看重新编码后的 `scene-combat.png` 和 `prefab-overview.png`，并查看过修复前后截图。最终画面土地完整且比例正常，城墙在原位置，木桩、花、橙红树来自原生模型及纹理；Grid 以轻微棋盘乘色叠加，没有白平面遮挡。两种来源各有 34 对象，所有对象可见，7 材质绑定解析，0 绑定 warning，无页面/GL错误。

原生 binary 验证重新通过：变换后本地 AABB 与 Unity Renderer.bounds 最大误差 2.86e-6，Land size 137.2198×183.0155，TreeB 使用 `_MainTexture` 对应专用树纹理，索引范围全部有效。

这证明的是**原网格/变换/纹理绑定的浏览器呈现**，不是完整 Unity 渲染管线像素等价。DecShadow 动态风、投影阴影、特殊夜间/高光尚未逐项移植，普通材质采用 MeshBasicMaterial 显示原贴图，不声称全部 Unity shader 效果一致。无士兵静态预览不覆盖战斗构图、碰撞安全和正常速度整片观看，需主任务统一集成后验收。
