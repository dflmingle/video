from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]; TL=ROOT/'variants'/'V20-TIMELINE'; OUT=ROOT/'V20-ENGAGEMENT-WINDOW.md'
s=json.loads((TL/'timeline-summary.json').read_text(encoding='utf8')); b=s['baseline']; plans=s['plans']; th=s['theoretical']
def row(p):
    return f"| {p['plan']} | {p['range']:.1f} | {p.get('firstAim', 0):.3f} | {p.get('firstDraw', 0):.3f} | {p['firstRelease']:.3f} | {p['firstHit']:.3f} | {p['safeEnd']:.3f} | {p['postHitWindow']:.3f} | {p['releases']} | {p['impacts']} |"
md=f'''# V20 交战窗口根因诊断

本阶段冻结 V19-B 镜头，未制作正式 V20 整片。所有 A/B/C 诊断使用 `variants/FINAL` 的同一红方、蓝方轨迹（60 fps、1.25 倍红方真实速度、252 蓝方 / 972 红方），只改变射手调度诊断模型。

## 真实事件时间线（V19 基线）

| 事件 | 时间（s） | 证据 |
|---|---:|---|
| 红方冲锋开始 | 0.000 | `trajectories.npy` 第 0 帧 |
| 元数据最早到位 | {b['firstArrival']:.3f} | `simulation.json.units[].arrival` |
| 元数据最早 readyAt | {b['firstReady']:.3f} | `simulation.json.units[].readyAt` |
| 实际最早进入 AIMING | {b['actualFirstAiming']:.3f} | `blue-control.f32` state=3 |
| 实际最早进入 DRAWING | {b['actualFirstDrawing']:.3f} | `blue-control.f32` state=4 |
| 实际首个释放状态 | {b['actualFirstReleaseState']:.3f} | `blue-control.f32` state=5 |
| 首次实际放箭 | {b['firstRelease']:.3f} | `simulation.json.events[]` |
| 首次实际命中 | {b['firstHit']:.3f} | 可见 `IMPACT_IN_SHOT` 事件 |
| 最晚安全结束 | {b['safeEnd']:.3f} | surface clearance >= 4 |

首发箭的飞行时间约为 0.283–0.317 s（首批样本），所以首次命中被推迟到约 1.883 s。首发后可见窗口只有 **{b['postHitWindow']:.3f} s**。

## 延迟归因

- **A 部署/到位控制：主因。** 元数据 readyAt 最早约 {b['firstReady']:.3f} s，但实际控制数据直到 {b['actualFirstAiming']:.3f} s 才进入 AIMING；这是约 0.22 s 的实际状态延迟，来自弧线路径积分到位与 ARRIVING/转向阶段，而不是全军统一时钟。
- **B 射击状态机额外等待：次因，但不是首要瓶颈。** 实际 AIMING → DRAWING → RELEASE 的首批转换为 {b['actualFirstAiming']:.3f} → {b['actualFirstDrawing']:.3f} → {b['actualFirstReleaseState']:.3f}，约 0.05 s + 0.20 s，基本符合逐人瞄准/拉弓时长。
- **C 射程/目标选择：贡献有限。** 最早进入有效射程约 {b['firstInRange']:.3f} s，早于实际 AIMING；因此首发并非单纯被射程挡住。把射程从 34 提到 38 的 B 方案没有提前首发。
- **D 箭矢飞行：明确压缩窗口。** 首发后还需约 0.30 s 才命中。
- **E 安全边界：明确压缩窗口。** 当前轨迹在 {b['safeEnd']:.3f} s 达到最后安全帧，不能继续向前推进而保持最低 4 的表面净距。

## 理论上限

在不改变红方速度、初始阵型、人数和安全净距的条件下，以实际 AIMING 起点和现有瞄准/拉弓时长计算，最早合规释放约 **{th['earliestEligibleRelease']:.3f} s**；按当前最快可见拦截样本估算，最早命中约 **{th['earliestInterceptedHit']:.3f} s**，理论最大首命中后窗口约 **{th['upperBoundPostHit']:.3f} s**。因此仅优化射手调度无法达到 1.0–1.5 s 的目标窗口。

## A/B/C 因果对照

| 方案 | 射程 | 首次 AIMING | 首次 DRAWING | 首次放箭 | 首次命中 | 安全结束 | 首次命中后 | 放箭数 | 可见命中 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V19 基线 | 34.0 | {b['actualFirstAiming']:.3f} | {b['actualFirstDrawing']:.3f} | {b['firstRelease']:.3f} | {b['firstHit']:.3f} | {b['safeEnd']:.3f} | {b['postHitWindow']:.3f} | {b['allReleases']} | {b['visibleArrows']} |
{chr(10).join(row(p) for p in plans)}

方案 A 只去掉目标占用抖动，首发仍为 {plans[0]['firstRelease']:.3f} s；方案 B 只把有效射程诊断值提高到 38，首发仍为 {plans[1]['firstRelease']:.3f} s；方案 C 联合两者也未改变首发时刻。三者都不能把箭雨窗口推到 1 s 以上，说明需要调整部署/转向时序或战场几何，而不是继续堆射击随机数。

## 0.25 s 箭雨分布

基线放箭桶：`{b['releaseHistogram']}`

基线命中桶：`{b['impactHistogram']}`

连续性检查：基线首发前为空窗（首发 {b['firstRelease']:.3f} s），首发后的相邻放箭最大间隔约 `{b.get('gapStats',{}).get('maxGapAll', 0):.3f} s`；可见命中相邻间隔约 `{b.get('gapStats',{}).get('impact',{}).get('maxGapAll', 0):.3f} s`。因此当前“空档”主要是首发太晚与飞行时间造成，而不是首发后调度出现长时间断火。

A/B/C 的完整桶数据保存在 `variants/V20-TIMELINE/timeline-summary.json`；三种方案均无“首发前大量命中”的伪造事件，箭矢仍使用真实释放到拦截的飞行时间。

## 最小可行几何/时序放宽方案

1. **放宽蓝方部署路径/转向时长（推荐先测）**：保持红方轨迹和安全净距，允许最靠近交战区的 1–2 个小队提前约 0.20–0.30 s 进入 AIMING；代价是需要重新验证 U 型队形的到位顺序，不能把全军同步提前。
2. **放宽箭矢飞行距离或提高箭速（需策划确认）**：保持释放时刻，减少约 0.10–0.15 s 飞行时间；代价是必须重新标定弹道与屏幕可读性，不能瞬移命中。
3. **放宽红蓝初始主轴距离或安全结束距离（二选一）**：给出至少 0.6–1.0 s 额外推进空间；代价是改变初始构图/安全边界，不能在未确认前直接并入正式 V20。

## 交付与限制

- 诊断短片：`output/V20-plan-A-camera-B.mp4`、`output/V20-plan-B-camera-B.mp4`、`output/V20-plan-C-camera-B.mp4`、同时间拼接 `output/V20-plans-A-B-C-same-time.mp4`。
- 源码：`tools/diagnose_timeline_v20.py`、`tools/prepare_v20_plan_variants.py`、`tools/encode_v20_plans.py`。
- 当前尚未修改正式 V20 战斗，也未声称完成完整片视觉验收；下一阶段应先选择上述时序/几何放宽方向，再重求镜头和整片时长。
'''
OUT.write_text(md,encoding='utf8'); print(OUT)
