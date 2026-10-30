# V21 综合修复报告

## 已完成并验证

- 蓝方射手使用独立软槽位偏差和小队/个体错峰；初始 U 型坐标保持，最大稳定偏差 `0.0694`，首轮释放时间 `1.40–2.30s`，释放标准差 `0.2596s`。
- 红方继续使用 V17 个体运动与 1.25× 世界速度；新增 `motion_v21.py` 将近期命中压力接入单兵速度衰减和有限避让，未受击士兵保持正向推进。
- V21 数据构建生成 `252` 名蓝方、`972` 名红方、`140` 帧（2.3167s）。
- 箭矢仍由射手实际释放事件生成；98 次释放、55 次画内命中，首发 `1.583s`，首命中 `1.883s`，最大释放间隔 `0.0667s`。
- 最小中心距离 `11.274`，武器包络后的表面净距 `5.074`，要求 `4.0`；接触帧和不安全帧均为 0。
- 正式 UnityPackage 资源已映射到 Three.js：ArenaScene 地面、远景墙体/旗帜、CastleExterior 建筑与树木。Unity 场景本身不能由浏览器直接加载，因此使用同包 FBX/PNG 的选择性兼容转换。
- 编码后 MP4 已读取检查：139 帧、1440×2160、60fps，渲染回读无黑帧；关键帧 seek 与原始截图一致。

## 交付文件

- `output/PVE-Shot01-U-Archers-v21.mp4`
- `output/V20-V21-same-time.mp4`
- `output/V21-archer-and-arrow-diagnostic.mp4`
- `output/V21-local-response-diagnostic.mp4`
- `output/V21-scene-preview/formal-scene.png`
- `output/V21-validation/V21-audit.json`
- `output/V21-validation/V20-B-vs-V21.json`
- `V21-SCAN.md`

## 关键代码

- `tools/archers_v21.py`：稳定软槽位与分层射击启动。
- `tools/motion_v21.py`：命中压力接入红方单兵速度/避让。
- `tools/local_response_v21.py`：滑动窗口、半衰期、滞回与冷却。
- `src/environment-v21.js`：正式 UnityPackage 场景资源的浏览器兼容加载。
- `src/main-camera.js`：V21 变体选择正式场景模块。

## 未通过或尚未可被当前场景证明的项目

1. 当前剧情只有蓝方向红方射击，没有红方反击蓝方的伤害事件，因此“蓝方受击后的局部后撤”和“命中/击杀后的局部前压”没有真实事件源，不能声称已在正式战斗中验收。V21 只完成了蓝方部署/射击错峰，以及红方受箭后的单兵响应。
2. V20 的首次命中后窗口仍约 `0.433s`；本轮保留交战时序约束，没有伪造延长。
3. 正常速度整片已完成编码回读和关键帧检查；本环境未进行人工逐秒播放，因此视觉验收结论以截图、连续帧和渲染回读为证据，不能等同于人工完整观看通过。

## 回归命令

```powershell
python tools/test_archers_v21.py
python tools/test_local_response_v21.py
python tools/validate_v21.py --variant V21 --old V20-B --new V21
npm run build
```
