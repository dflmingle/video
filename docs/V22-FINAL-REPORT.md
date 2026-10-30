# V22 综合返工交付记录

日期：2026-10-29

## 问题、根因、修改位置、验收

| 问题 | 根因 | 修改位置 | 当前验收 |
|---|---|---|---|
| 蓝方像整齐方块 | 旧版直接写入槽位终点，缺少逐人弹簧积分和转向状态 | `tools/archers_v22.py`, `src/archer-pose-v22.js`, `src/main-v22.js` | 252 名射手逐人位置/速度/相位；最小间距 0.615；到位 1.60–2.817 s；释放相位误差 0 |
| 释放不同步但动作同步 | 渲染使用全局时钟，没有消费逐人控制相位 | `src/main-v22.js` | 每次释放均为 state 5、phase 0.64、真实 eventId；浏览器 capture ABI 检查通过 |
| 中央小队无火力 | 两翼 AIMING 长期占用目标 | `tools/archers_v22.py` 公平 lease 调度 | V22-C 中央小队出现 draw/release；当前正式模拟共 112 支箭 |
| 局部前压/受击反馈不真实 | 反馈偏移未接入唯一位置积分，且正式剧情没有蓝方受击源 | `tools/combat_response_v22.py`, `tools/motion_v22.py` | 59 次真实命中回放；最大实际局部位移约 0.194；蓝方退缩仅诊断场景 |
| 镜头过远 | 旧版交战倍率不足 | `src/camera-v22.js`, `tools/timeline_v22.py` | A/B 共用绝对推近时序；B 交战倍率 2.5625，相对 A 约 +25% |
| 箭雨窗口短 | 射程、箭速、冲锋速度和安全剪辑共同形成上限 | `tools/timeline_v22.py` | 实测 V21 0.433 s；V22-C 约 0.567 s；pre-aim 理论对照约 0.631 s；未宣称达到 1 s |
| 正式场景来源不明 | V21 使用混合适配环境 | `src/environment-native-v22.js`, `public/native-scenes/*` | 原生 Unity 导出可加载；NewScene/CastleExterior/ArenaScene 均有静态预览和二进制 bounds 校验 |

## 当前正式产物

- [V22-C-B-formal-native-recapture.mp4](../output/V22-C-B-formal-native-recapture.mp4)：当前 V22-C、B 镜头、Unity 原生 `NewScene` 导出。
- [V22-C-B-final-recapture.mp4](../output/V22-C-B-final-recapture.mp4)：同一模拟的兼容环境对照，不作为正式场景来源证明。
- [V22-C-A-camera-A-full.mp4](../output/V22-C-A-camera-A-full.mp4) 与 [V22-camera-A-B-current.mp4](../output/V22-camera-A-B-current.mp4)：当前 A/B 镜头全片及同时间对照。
- [V21-A-baseline-current.mp4](../output/V21-A-baseline-current.mp4) 与 [V21-V22-current-same-real-time.mp4](../output/V21-V22-current-same-real-time.mp4)：当前 V21 基线及 V21/V22 同时间对照。
- [V22-C-A-final-recapture-A-probe](../output/captures/V22-C-A-final-recapture-A-probe)：A 镜头探针。
- [V22-C-B-left-blue-closeup-probe](../output/captures/V22-C-B-left-blue-closeup-probe)：蓝方局部近景探针。
- [V22-C-B-formal-native-recapture-probe](../output/captures/V22-C-B-formal-native-recapture-probe)：正式场景探针。
- [V22-blue-advance-real-impact-replay.mp4](../output/V22-blue-advance-real-impact-replay.mp4)：真实命中局部前压诊断。
- [V22-blue-retreat-SYNTHETIC-diagnostic.mp4](../output/V22-blue-retreat-SYNTHETIC-diagnostic.mp4)：明确标记的蓝方受击退缩诊断。
- [V21-V22-same-real-time.mp4](../output/V21-V22-same-real-time.mp4)：V21/V22 同时对照（来源文件保留在 output）。

## V22-C 实测数据

- 252 蓝方、972 红方（红/橙/黄为 324/432/216）。
- 112 支箭，4 次屏内真实击杀；死亡保留，不重排活人。
- 最小表面净距 4.265，要求 4.0；无身体接触事件。
- 逐人站位偏差来自实际世界位置积分，非渲染后偏移；蓝方最小个人间距 0.615。
- 当前安全剪辑为 3.3 s / 199 帧，箭矢释放和命中均绑定具体射手与目标。

## 原始资源映射

正式原生环境来自 `public/native-scenes`，由 Unity 6000.0.54f1 原生求值导出：

- `NewScene`：`Assets/New Scene.unity`，包含 CastleExterior、ArenaScene 等打包布局，77 个 active mesh 对象。
- `CastleExterior-scene/prefab`：`Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity` / `_Grp.prefab`，34 个对象。
- `ArenaScene-scene/prefab`：对应原始 Unity scene/prefab，35 个对象。
- 地面、城墙、城门、树木、围栏/旗帜和装饰物均来自 manifest 指向的原始 FBX、材质和贴图；浏览器只消费 Unity 导出的 JSON+binary，不再重建程序地面。

`tools/native-export-v22/validate_native_export.py` 已修正为对 Arena/NewScene 使用通用 bounds 检查，对 CastleExterior 追加 TreeB/地面来源检查；当前全部导出目录通过，最大 bounds 误差约 3.7e-5。

## 未通过或未能诚实宣称的项目

1. 资源包没有证据证明某一个场景就是用户截图的唯一目标；`NewScene-castle` 是最接近的原生布局，但仍存在树材质和旗帜差异，不能称“完全匹配”。
2. 正式剧情没有蓝方受击事件源，因此蓝方退缩只在 synthetic diagnostic 中验证。
3. 交战窗口从 0.433 s 改善到约 0.567 s（pre-aim 对照约 0.631 s），仍未达到约 1 s；继续扩大需要放宽射程、箭速、冲锋速度、安全边界或场景长度中的至少一项。
4. `watch-video` CLI 在当前 Windows 环境不可用；因此 MP4 已完成全帧解码和连续探针检查，但未把工具输出冒充为完整人工正常速度观看结论。当前工程检查通过，最终视觉认可仍需用户观看确认。

