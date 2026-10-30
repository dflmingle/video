# V3 可调参数与重建要求

修改 `params.json` 后运行 `python -X utf8 tools/render_v3.py`，不要只刷新浏览器读取旧轨迹。重新生成后仍需查看成片，不能沿用本版视觉评价。

| 参数 | 本版 | 作用与约束 |
| --- | --- | --- |
| duration / fps | 6.6 / 30 | 自然演出时长与输出帧率；增加时长必须重新检查安全间距，不能添加全军刹车 |
| redFrontZ | -51 | 黄色前军起点最前沿；其他军按自身纵深和间距向后排布 |
| redSpeed / accelerationSeconds | 9.4 / 0.8 | 冲锋基速与加速时间；实际速度含逐人固定差异 |
| redSpeedVariation / redStartSpread | 0.055 / 0.22 | 速度及启动差，另有前中后排延迟；不可逐帧重抽随机数 |
| armyMemberRows | [6,8,4] | 各小队行数，红方六列固定、每军 3×3 小队，得 324/432/216；groupSide 仅控制蓝方 |
| redMemberSpacingX / Z | 0.9 / 0.82 | 小队成员间距；需同时检查实际网格遮挡 |
| redSquadPitchX / redSquadGapZ | 7.2 / 2.5 | 小队横向中心距与纵向净空；纵向中心距按实际小队深度计算 |
| redArmyGap | 7.9 | 大军之间初始净间距；改变前后规模时仍保留三军边界 |
| chargeSpread | 0.7 | 连续横向展开的幅度，不能将不同兵种打散混合 |
| blueGroups / groupSide | 7 / 6 | U 型七队，每队 6×6；七队来源为策划图 |
| uHalfWidth / uDepth / uArmsStartZ | 16 / 20 / 30 | U 型几何，开口朝负 Z；半圆参数计算队中心 |
| blueSpacing | 0.95 | 蓝方队内间距 |
| blueAdvance | 6 | 沿负 Z 前进距离，**暂定值，未获策划明确终点确认** |
| blueMoveSeconds / blueStartSpread | 1.6 / 0.2 | 每人移动时间与启动差，使用连续起停曲线 |
| archerCycle / drawSeconds | 1.35 / 0.43 | 射击周期和拉弓时长，个体错峰 |
| arrowSpeed / arrowArcHeight | 62 / 5 | 世界距离决定飞行时间；重力弧线为程序化演出 |
| arrowTailSeconds | 0.014 | 短尾迹对应的时间跨度；不以长漂浮线代替箭矢 |
| redHitPoints / targetFrontCount | 2 / 260 | 目标生命和前沿候选范围；死亡只能来自实际绑定命中 |
| runStride / blueStride | 2.5 / 1.5 | 累计路程驱动动作相位；红军跨步需与骨骼约束共同调整 |
| minimumEnemyClearance | 4 | 阵营表面净间距的最低要求，含帧间运动下界 |
| weaponEnvelopeRadius | 3.1 | 含武器和倒地的保守单体水平包络；不得缩小它来伪造安全 |
| seed | 71423 | 固定成员差异及事件，保证可重复 |

`redRows/redColumns/redSquadPitchZ/redArmyPitch` 是旧版兼容字段，V3 实际编组由 `armyMemberRows`、3×3 层级及对应间距决定。`redStopZ` 仅用于诊断线，不驱动运动或刹车；`redSlowDistance=0` 不是末段减速开关。勿通过这些旧字段推断当前实际轨迹。

相机、箭杆/箭头尺寸、骨骼姿态适配及地面颜色在 `src/`。改动后必须重新录制并更新所有相关对照。安全验证包括无伤亡版本；增加伤亡不能成为避免接触的唯一手段。
