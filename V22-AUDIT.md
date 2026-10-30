# V22 根因审计与实施记录

状态：专项修复与对照中。不是完整 V22 验收报告。2026-10-29。

| 问题 | 已找到的根因 | 修改位置/归属 | 直接验收 |
|---|---|---|---|
| 蓝方仍机械 | V21 插值部署路径直接赋位置；不是实际弹簧阻尼运动 | Agent A `tools/archers_v22.py` | 实际积分、逐人到位/转向日志、连续近景 |
| 步态与位移脱节 | V21 行走相位漏乘路径世界长度 | Agent A 同上、`src/archer-pose-v22.js`；主 Agent `src/assets-v22.js`、`src/main-v22.js` | 累计实际步长/stride 与相位逐帧一致，实例属性独立 |
| 只有放箭错峰 | 需要确认状态、相位及姿态权重最终进入实例缓冲 | 同上 | 生产 JS helper 读取实际 control；渲染逐人 state/phase/release 对照；不是全局时钟 |
| 中央长期不开火 | 两翼首先占有 AIMING claim，中央可射目标被 claim/reservation 饥饿 | Agent A `tools/archers_v22.py` | 按队首次拉弓/释放与目标分配回放；不可仅检查总箭数 |
| 局部反应不明显 | 目标偏移与实际根位置未分开验收；位移可能小于正式画面可读尺度 | Agent B `tools/combat_response_v22.py` | 同积分器无响应孪生轨迹差，真实事件与 synthetic 诊断分别输出 |
| 红方绕行限制失效 | V21 `min(1,limit/.20)` 恒为 1；伤害减速叠加两次 | Agent B `tools/motion_v22.py` | 健康前向/侧向速度、最低间距、独立步态、尸体固定 |
| 镜头过远/基准误读 | FIXED 参数静默回退旧 A；人物像素测量口径不一致 | Agent C `src/camera-v22.js` | 相同模拟的 A/B，实际透视投影，注明输出分辨率与 head-height 定义 |
| 首次命中过晚 | 部署、瞄准、拉弓、射程内可用距离共同限制；不能只改射程 | Agent C `tools/timeline_v22.py`；主 Agent `tools/build_simulation_v22.py` | 实测 B/C 时间表；假设性上限另列，不当作实际视频 |
| 箭从位置不完全对齐 | 箭 origin 使用预测目标方向，模型使用实际 facingYaw | 主 Agent builder + `tools/update_arrow_origins_v22.py` | 释放帧 native left-hand 经实际实例朝向变换后误差为零 |
| 正式场景来源不实 | V21 用原模型但压平土地、重摆城墙、替换统一材质，不是原场景结构 | Agent D/C `tools/native-export-v22/`、`src/environment-native-v22.js` | Unity 原生 OpenScene/LoadPrefabContents 求值，原世界矩阵/UV/绑定；无士兵预览与用户截图核对 |
| 手工转换失败 | 子 FBX target override 被误套根节点、shader 实际纹理字段不匹配 | 已弃用手工转换原型 | 无效旧图标记在 output/scenes，禁止作验收证据 |

## 不变量

原始 V5/V21 初始单位坐标、人数（红324/橙432/黄216/蓝252）、模型尺寸、27个红方小方阵、蓝方 U 型、地形防御方向不因行为修复改变。真实推进基准 redSpeed=21.75、chargeMultiplier=1.25。C 中 redChargeStart=1.0 是**冲锋前可见准备时间**；启动后不靠突然刹车延长片长。射程仍34，最低表面安全净距4。局部后撤 synthetic 事件不进入正式模拟。

## 文件隔离

三个 worker worktree 分别为 `PveMontageShot01V22-blue`、`-response`、`-camera`；原生 Unity 导出另用 `PveMontageShot01V22-UnityExport`。根目录负责 builder、renderer 接线、捕获和集成。资源审计先于原生导出；四个职责按并发槽位分波执行，未让多 Agent 同时编辑同一生产文件。合并使用逐个 cherry-pick，原 V21 工程不覆盖。

## 场景目标更新

用户 2026-10-29 提供 `企业微信截图_17931917146262.png`：暖黄棋盘、橙色边缘、紫色墙/右侧门、绿色树与旗帜。CastleExterior 初次原生预览与该图有明显差异，**不能宣称匹配**。正在核查包内其他场景与源 Prefab。原生网格导出正确不等于场景选择正确。按用户第八节要求，匹配预览确认前不接入正式战斗。

## 视觉验收口径

自动数据、浏览器截图、编码视频分别记录。没有完成正常速度完整观看就必须写未完成；不得以解码全部帧或生成 MP4 替代。当前仍是离线确定性模拟/演出，不宣称完全自主战斗 AI。
