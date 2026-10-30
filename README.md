# V22-R / C1 箭雨战斗与后续近战

本仓库整理本次视频需求涉及的工程、原始资产、模拟数据、对照视频与验证资料。

**已确认基线：C1，原提交 `7c20b43a44f9c9dc6b8c2653646103e45fb72bbd`，0–2.65 秒。** 本轮新增近战是工作快照，尚未获得用户视觉确认，不应把模拟或测试通过视为正式成片通过。

## 当前需求

- 锁定 C1 的红橙黄冲锋、蓝方紧凑 U 型集结、第一波箭雨、个人射击周期、箭路、命中与死亡；公共时间区间保持原轨迹与事件。
- 保留已确认的 CastleExterior 原生 3D 场景，关闭 `Gird`，固定近景，一镜到底；场景、灯光、模型、镜头与军团初始位置不重排。
- 从原安全截止点之后继续模拟，允许实际近战，取消旧“武器包络表面净距低于 4.0 即全局结束”的规则；双方身体碰撞继续生效。
- 红兵攻击附近存活目标，攻击相位产生伤害；被近身的蓝兵中断不合理射箭，未被近身者继续原周期。
- 不预设胜负，直到一方失去战斗能力。先交付前段同步对照、2.3 秒起续战、完整低成本预览，再决定正式渲染。
- 原版城墙穿越与开场部分军团出画是独立遗留问题，本轮没有通过移动军团来掩盖。

## 文件位置

| 目录或文件 | 内容 |
|---|---|
| `src/`、`tools/` | 当前工作源码、模拟、原生资产导出、捕获、编码与核查工具 |
| `assets/runtime/` | 四种兵种实际使用的 FBX、PNG 与来源映射 |
| `assets/imported/` | 已提取的 Unity 原始资源，保留原目录与 GUID |
| `public/native-scenes/` | 原生场景几何、材质贴图导出，以及历史候选对照 |
| `unity-source/` | Unity 6000.0.54f1 项目副本，包含 `Assets/V22R/ApprovedCastle-NoGrid.unity` |
| `source-materials/` | 原始需求 PDF 与用户指定的 `PVE混剪.unitypackage` |
| `scenes/v22r/` | 已确认场景的 `.unity` 副本 |
| `variants/V22R-C1/` | 已确认 C1 参数、轨迹、个人控制、事件与检查数据 |
| `variants/V22R-C1-checkpoint/` | C1 F159 的完整内部检查点及参数，供续接使用 |
| `variants/V22R-C1-melee/` | 本轮续战模拟工作快照，**不是用户批准的正式成片** |
| `variants/V22R-C2/`、`variants/V22R-fast-A/`、`variants/V22-C/` | 已有候选与 V22 对照数据 |
| `output/v22r-burst/` | C1、C2 正常速度预览和 A/C1/C2 同时间对照 |
| `output/historical-comparison/` | 指定的 V22/V23 同时间正常速度对照，仅作历史失败对照 |
| `output/V22R-final/` | **历史**已输出版本，不能当作本轮新增近战正式版 |
| `output/v22r-melee/` | 本次快照时已完成的前段对照与检查资料；未完成的预览不冒充已交付 |
| `docs/v22r-melee/` | 本轮方案、审阅、每 0.1 秒统计和因果检查 |
| `docs/scene-requirements-r2/` | 场景需求溯源、原始参考图、资源对应和用户场景确认 |
| `reference/` | 原仓库历史 bundle、相对 C1 的补丁、PNG 帧序列压缩包 |
| `DELIVERY-MANIFEST.json` | 实际入库文件的字节数、SHA-256 和快照状态 |

旧报告保留其版本背景；以本轮工作快照和 `docs/v22r-melee/` 的有效记录为准。打包时主会话仍在制作续战视频，仓库不会把旧预览或未完成文件标记成最新成片。

## 下载和运行

```powershell
git clone https://github.com/dflmingle/video.git
cd video
git lfs pull
npm ci
python -m pip install -r requirements.txt
npx vite --host 127.0.0.1 --port 5267 --strictPort
```

C1 基线：<http://127.0.0.1:5267/v22.html?variant=V22R-C1&presentation=approved-castle>

续战工作快照：<http://127.0.0.1:5267/v22.html?variant=V22R-C1-melee&presentation=approved-castle>

Unity 原生场景可用 Unity Hub 打开 `unity-source/` 后选择 `Assets/V22R/ApprovedCastle-NoGrid.unity`。它提供真实场景和资源；浏览器端续战系统并非 Unity 编辑器里的可玩战斗系统。

## 重建与核查

脚本保持原工程路径结构。捕获脚本当前使用 Windows Chrome 路径和端口 5267；换机器时需相应调整。源资料中的绝对路径用于溯源，不代表目标机器也有这些目录。

```powershell
# 恢复逐帧基线和无损压缩日志（完整像素对照需要）
python restore_evidence.py

# 从已有可信 C1 检查点重算续战
python tools/build_melee_continuation_v22r.py
python tools/audit_melee_v22r.py

# 先核对公共时间区间，再捕获低成本完整预览
node tools/compare_melee_prefix_v22r.mjs
node tools/capture_melee_v22r.mjs --out output/v22r-melee/preview
python tools/encode_melee_v22r.py
```

捕获采用正常速度时间基准；脚本存在不表示最新视频已完成视觉验收。运行重建会更新本地生成数据，建议先保留仓库快照。

原历史与差异可独立查看：

```powershell
git bundle verify reference/source-history.bundle
git clone reference/source-history.bundle ../video-source-history
```

## 本次归档边界

保留原始需求、模型、贴图、原生场景和已有视频；未上传 `node_modules`、`dist`、Unity 缓存、求解器中间恢复文件与明确失败的临时帧。原始大 UnityPackage 使用 Git LFS；PNG 基线帧采用 ZIP，无损日志采用 gzip。

原素材版权和使用许可继续归原提供方；本次整理不构成对第三方素材的重新授权。
