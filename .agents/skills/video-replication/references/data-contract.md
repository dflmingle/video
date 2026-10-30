# 数据契约 1.0

模板见 `assets/project-template.json`。`analyze` 生成可执行子集；复杂工程可拆 JSONL/二进制缓存，但语义与来源字段保持一致。大缓存流式处理，不为审查把整文件塞进工具输出。

## 两条独立来源轴

- `evidence.grade`: OBSERVED（帧中直接可见的形状/光斑）、INFERRED（关联/插值/归属推断）、SYNTHETIC（显示槽位或生成动作）、UNKNOWN。
- `evidence.method`: AUTOMATIC、CODEX_VISUAL、HUMAN_EDIT、RULE_GENERATED。
- `refs`: 源文件/截图哈希、帧号、时间、标注记录或父证据 ID。非 UNKNOWN 数据需要来源。`confidence`: 可为 null；未经校准的主观值不能称概率。`validation`: UNREVIEWED/PASS/PARTIAL/FAIL/UNKNOWN，注明验证版本。

人工改过不自动变真值；观测位置可 OBSERVED，而跨帧身份通常 INFERRED。生成事件不能标为 OBSERVED。授权增强事件另存 `authorization_ref`；忠实模式的显示动作分配也是 SYNTHETIC，并指向原片事件证据与既有复刻授权。

## 实体及层级

| 字段 | 语义 |
| --- | --- |
| `source` | 路径、SHA256、帧数、fps、PTS/时基状态、实际解码范围、音频检查范围 |
| `analysis` | 时间范围、分析画幅、源到分析坐标矩阵、相机补偿状态、配置哈希 |
| `objects[]` | 稳定 ID、对象类型/候选类型、物理身份状态、source_count 与 render_count 分离 |
| `observations[]` | 源帧/绝对时间、中心/轮廓/bbox/占据密度/主轴及可靠性、坐标空间、独立来源 |
| `groups[]` | 群体身份、拓扑/共享区域、邻接/接触、拆分/合并事件；不以组件一对一硬套 |
| `memberships[]` | member_id/group_id/start/end/evidence；区间左闭右开，同成员不能同时属于冲突群体 |
| `layers[]` | 最终状态候选层：id/priority/start/end/position/inputs_hash。运行时状态记录实际 writer |
| `states[]` | 绝对时刻、生命周期状态、固定命中点/死亡点和证据；不删 ID |
| `events[]` | 稳定事件 ID、绝对时间、kind、actor_id/target_id（未知为 null）、位置、持续、组成、证据、授权引用 |
| `effect_observations[]` | 原片可见光斑/线/烟场及区域时序，和程序 FIRE/HIT 粒子实例分离 |
| `asset_map[]` | 源对象/职责→素材/适配参数/哈希/限制；不内嵌大量二进制 |
| `validation[]` | 区域/窗口/版本/样本分母、指标、目视范围、决定、回滚引用 |

坐标显式命名：`source_px`、`analysis_px`、`registered_px`、`scene_world`、`asset_local`；矩阵明确方向。像素 y 向下与世界 up 轴不可混淆。PCA 轴为模 π 的排列轴，不是角色朝向。

时间使用源绝对时间；CFR 时第 n 帧在 n/fps，N 帧媒体覆盖 [0,N/fps)，末帧时间为 (N−1)/fps。VFR 必须保留 PTS 映射；脚本遇可变/不可验证 PTS 会拒绝主要处理，不能偷偷按平均 fps 重排。

新显示成员另账：origin/parent/source_identity/first_source_visible/first_render_visible/count_basis。首次渲染晚于原片首现须说明；不能把补漏成员说成增援。无法看到全体时，不补猜完整数量。

## 有效数据与缓存

显式记录最终优先级，推荐由项目实际层级决定：基础布局 < 局部空间修正 < 群体/成员变形 < 专项路径 < 绝对成员轨迹；生命周期最后控制存活/固定死亡位置。不是强制所有项目创建这些层。

绝对缓存记录来源哈希、生成器版本、种子、时间步长、素材适配影响和有效窗口。输入变化后重建受影响缓存；`inputs_hash` 必须由实际生成器核验，`check` 不会猜项目任意缓存依赖。通过改前后 final state、writer 和渲染对照证明生效。

`check` 只是结构/采样路径和适用生命周期的检查器，不是完整 JSON Schema 认证、碰撞系统或原片身份验证器。项目适配器需补成员守恒、重叠归属、映射可逆性及其特定状态规则。
