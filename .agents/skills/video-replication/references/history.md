# 审计溯源与失败边界

这是通用方法的来源说明，不是运行依赖。依据 2026-10-26 完成的 `r1-r21-technical-audit/` 六份文件：R1-R21_TECHNICAL_AUDIT.md、TECHNIQUE_INVENTORY.csv、CV_AND_EARLY_HISTORY.md、MEMBERS_AND_MOTION.md、COMBAT_EFFECTS.md、RENDER_VALIDATION_AND_SKILL.md。源审计位于原 RiverBattle 项目的 `output/reports/`；通用工具运行不需要该项目。

| 历史实证 | 实现入口（相对源项目） | 新 Skill 如何继承 |
| --- | --- | --- |
| 掩膜/轮廓/连通域/代理误差 | tools/video-analysis/replication_common.py::team_masks/binary_metrics；replication_detection.py::proposals | vision.py 提炼参数化候选和 IoU/Chamfer/密度；移除阵营阈值和 HUD 假设 |
| 特征配准、留出与失败拒绝 | replication_registration.py；R21 r21-map-towers/prepare-assets.py | register 提供两帧 SIFT+RANSAC 与留出门禁，不宣称三维恢复或跨风格稳健 |
| LK 与候选关联 | track-opening.py；R8 track.py::step；R21 edge-entry.py | flow 前后向门控，associate 速度预测/Hungarian；身份 UNKNOWN 不自动判死/增援 |
| 小范围修正、留出回滚 | R12 refine-data.py、INTEGRATION_CHANGELOG.md | 验证流程区分 proposal/保留结果；一项退化不能因均值改善留用 |
| 非矩形稳定成员布局 | candidate-frontline-reconstruction-r16/parallel/spatial/shared-red.py | reconstruction.stable_mask_layout 重写为无路径/阵营依赖的最远点+Hungarian，不复制项目脚本 |
| 有界约束拟合 | 同版 parallel/spatial/optimize.py::residual | fit_path 提供精简二维有界最小二乘；完整邻队/群体约束需按项目扩展 |
| CDF/绝对轨迹/覆盖层 | R21 candidate/member-distribution.js、member-distribution-occupation.js；integrated.js::sampleBase | occupation_quantiles、resolve 与最终 writer/缓存检查；不包装成全片自动求解 |
| 六状态死亡与绝对时间 | R18/R21 death-lifecycle.js、combat-state.js | 复用项目控制器的规则，不复制战斗专用运行时进通用 Skill；check 可查适用状态门禁 |
| 编码后区域验证 | R21 record.mjs、visual/metrics 工具与对照产物 | common.Encoder、probe、compare，实际解码和查看范围分开 |

这些是根据实证重写的少量通用原语，不是动态 import 旧工程，也不是复制旧脚本后改目录。新脚本单点维护，旧生产 Skill 不变。

## 保留失败链

1. **模板最高分→当可靠兵种→全未知仍硬解释**：历史自动模板分类未成功。新片先有负类/留出语义验证，否则只候选；没有已打包神经检测能力。
2. **低图像损失→假定还原成功**：早期代理改善很大，注册/身份仍拒绝。看关键局部和全部失败分母，不能只看均值。
3. **运行引擎继承→后段已经复刻**：全时长中心位移保留了错误内部形状/失证 hold。按每窗补具体成员和事件，不复制前段参数。
4. **PCA轴翻转/每秒形状→整队转圈/呼吸**：分离布局轴与瞄准，低置信稳定形状；有真实形变证据时再局部重建。
5. **改布局无画面变化→继续加参数**：高优先级绝对成员缓存覆盖修改。查最终 writer 和输入哈希，更新该层再渲染。
6. **补漏体→误称新增援军**：开场漏映射与后进入分开；新增显示成员另账，不声称真实人数。
7. **后段平淡→盲目调粒子上限**：历史主要是合法攻击事件稀疏；后续新增大量用户授权合成事件，加上外观/烟形/反馈修正改善观感。不能把增强反写为已恢复真实射击。
8. **安全运动→一定更像原片**：安全 DP 某候选无新增穿透但 IoU 退化被拒；此 Skill 提供连续最小距原语，没有打包完整 DP。
9. **换图配准成功→路径也兼容**：同底图注册仅证明二维位置可转移，旧路径可能穿新河岸；素材适配必须重验空间。

审计区分 A（已实现且局部有效）、B（实现但效果/覆盖不充分）、C（失败/弃用）、D（无实现证据）。R21 用户当前认可与历史完整冲锋/后段几何 PARTIAL/FAIL 并存；本 Skill 继承混合重建闭环，不声称 R21 已证明端到端通用准确复刻。SSIM、SLAM、完整遮挡重识别等不列为历史已验证能力。
