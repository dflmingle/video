using UnityEngine;

/// <summary>
/// 抛物线追踪/非追踪箭矢脚本
/// 支持标准抛物线弹道、目标索敌跟随、范围伤害(AoE)、命中特效与箭矢插中效果。
/// </summary>
public class HomingArrow : MonoBehaviour
{
    [Header("飞行参数")]
    [Tooltip("箭矢在空中的飞行速度（米/秒）")]
    public float 飞行速度 = 15f;

    [Tooltip("抛物线弹道在飞行中点达到的最高弧度高度（相对于两点连线基准的高度）")]
    public float 最高点高度 = 4f;

    [Tooltip("目标落点的坐标偏移，用于校准命中位置（例如命中敌人胸口或头部，避免射向脚底）")]
    public Vector3 落点偏移位置 = new Vector3(0f, 1.2f, 0f);

    [Tooltip("箭矢到达抛物线最高点时的缩放倍数增量。在俯视角/正交视角下放大尺寸，可增强飞向高空的立体感与视觉冲击力（0为不缩放）")]
    public float 最高点放大倍数 = 0.5f;

    [Header("弹道与索敌机制")]
    [Tooltip("是否开启追踪模式。开启后，即使目标移动，箭矢落点也会实时更新跟随目标；关闭时只射向发射时的预判落点，并使用命中判定半径；开启追踪时不使用该半径，因此隐藏黄色线框")]
    public bool 是否追踪目标 = true;

    [Tooltip("非追踪模式命中半径（世界单位）。选中箭矢且关闭追踪时显示黄色线框球；球心为目标当前位置加落点偏移，表示箭矢落点允许的三维误差。无目标时在箭矢原点预览。")]
    public float 命中判定半径 = 1.5f;

    [Header("范围伤害 (AoE) 设置")]
    [Tooltip("是否开启范围爆炸伤害。开启时会对落点周围的所有敌人造成伤害")]
    public bool 是否范围伤害 = false;

    [Tooltip("范围伤害球形检测半径（世界单位）。选中箭矢且开启范围伤害时显示橙色线框球；以目标当前位置加落点偏移为中心，与伤害检测一致。无目标时在箭矢原点预览。")]
    public float 范围伤害半径 = 3.0f;

    [Header("命中表现设置")]
    [Tooltip("命中后是否立即销毁箭矢（为 true 则不保留插箭效果）")]
    public bool 命中后立即销毁 = false;

    [Tooltip("未立即销毁时，箭矢插在目标或地面上的残留停留时间（秒）")]
    public float 插箭停留时间 = 3.0f;

    // ================= 内部运行私有变量 =================
    private Transform 目标;                     // 锁定的目标 Transform
    private GameObject[] 命中特效数组;          // 命中时随机播放的粒子/特效 Prefab 数组
    private float 特效销毁时间;                 // 命中特效生成后的自动销毁倒计时
    private int 伤害数值 = 1;                  // 本次攻击附带的伤害值
    private Vector3 起始位置;                  // 箭矢发射时的世界坐标
    private float 总飞行距离;                  // 发射时计算的直线距离，作为飞行进度的基准
    private float 飞行进度 = 0f;                // 弹道完成百分比 (0 到 1)
    private bool 是否已命中 = false;            // 标记是否已经触发命中判定，防止重复触发
    private Vector3 目标落点位置;              // 当前计算的目标世界坐标（包含落点偏移）
    private Vector3 初始缩放;                  // 箭矢生成时的原始尺寸，用于最高点缩放还原

    /// <summary>
    /// 发射箭矢初始化方法
    /// </summary>
    /// <param name="敌人目标">索敌目标 Transform</param>
    /// <param name="特效数组">命中时随机触发的特效预制体数组</param>
    /// <param name="特效保留时间">生成的特效存活时间</param>
    /// <param name="造成伤害">本次箭矢携带的伤害值</param>
    public void Fire(Transform 敌人目标, GameObject[] 特效数组, float 特效保留时间, int 造成伤害)
    {
        目标 = 敌人目标;
        命中特效数组 = 特效数组;
        特效销毁时间 = 特效保留时间;
        伤害数值 = 造成伤害;
        初始缩放 = transform.localScale;

        起始位置 = transform.position;

        if (目标 != null)
        {
            目标落点位置 = 目标.position + 落点偏移位置;
            总飞行距离 = Vector3.Distance(起始位置, 目标落点位置);
        }
        else
        {
            // 若未指定目标，则沿正前方生成默认落点
            目标落点位置 = 起始位置 + transform.forward * 10f;
            总飞行距离 = 10f;
        }
    }

    void Update()
    {
        // 已触发命中后停止位移与姿态计算
        if (是否已命中) return;

        // 距离过近或异常直接销毁，避免除以零
        if (总飞行距离 <= 0.01f)
        {
            Destroy(gameObject);
            return;
        }

        // 检查目标是否有效且存活
        bool 目标是否存活 = (目标 != null && 目标.gameObject.activeInHierarchy);

        // 若目标存活且开启了追踪模式，动态刷新追踪落点坐标
        if (目标是否存活 && 是否追踪目标)
        {
            目标落点位置 = 目标.position + 落点偏移位置;
        }

        // 根据速度推进飞行进度 (0 -> 1)
        飞行进度 += (飞行速度 / 总飞行距离) * Time.deltaTime;

        if (飞行进度 >= 1f)
        {
            // 到达终点，恢复默认尺寸并执行命中结算
            transform.localScale = 初始缩放;
            触发命中(目标是否存活);
        }
        else
        {
            // 1. ================= 计算三维抛物线坐标 =================
            // 起点到终点的线性水平插值基准
            Vector3 基础插值坐标 = Vector3.Lerp(起始位置, 目标落点位置, 飞行进度);

            // 标准抛物线高度方程：y = 4 * H * t * (1 - t)
            // 在进度 t = 0 和 t = 1 时垂直偏移为 0；在进度 t = 0.5（飞行正中）高度偏移恰好为 最高点高度
            float 垂直抛物高度 = 4f * 最高点高度 * 飞行进度 * (1f - 飞行进度);

            // 叠加垂直高度偏移
            Vector3 当前帧位置 = 基础插值坐标 + Vector3.up * 垂直抛物高度;

            // 2. ================= 调整飞行姿态朝向 =================
            // 朝向下一帧切线方向，使箭矢能够自然抬头与俯冲
            Vector3 运动方向 = 当前帧位置 - transform.position;
            if (运动方向 != Vector3.zero)
            {
                transform.rotation = Quaternion.LookRotation(运动方向);
            }

            // 3. ================= 视觉欺骗缩放 =================
            // 归一化高度比例：在最高点(t = 0.5)达到最大 1.0，起终点为 0.0
            float 高度归一化比例 = 4f * 飞行进度 * (1f - 飞行进度);
            transform.localScale = 初始缩放 * (1f + 高度归一化比例 * 最高点放大倍数);

            // 应用计算得到的位置
            transform.position = 当前帧位置;
        }
    }

    /// <summary>
    /// 触发命中结算（伤害判断、特效生成、插箭表现）
    /// </summary>
    /// <param name="目标是否存活">目标当前是否激活且存活</param>
    private void 触发命中(bool 目标是否存活)
    {
        是否已命中 = true;
        bool 判定成功命中 = false;
        Vector3 特效生成位置 = transform.position;

        // 判定是否击中敌人
        if (目标是否存活)
        {
            if (是否追踪目标)
            {
                判定成功命中 = true;
            }
            else
            {
                // 非追踪模式下判断终点与目标实时位置的偏差
                float 与目标距离 = Vector3.Distance(transform.position, 目标.position + 落点偏移位置);
                if (与目标距离 <= 命中判定半径)
                {
                    判定成功命中 = true;
                }
            }
        }

        // 执行伤害与特效逻辑
        if (判定成功命中)
        {
            特效生成位置 = 目标.position + 落点偏移位置;

            if (是否范围伤害)
            {
                // AoE 范围伤害检测
                Collider[] 范围碰撞体 = Physics.OverlapSphere(特效生成位置, 范围伤害半径);
                foreach (Collider 碰撞体 in 范围碰撞体)
                {
                    SoldierHealth 敌人生命 = 碰撞体.GetComponentInParent<SoldierHealth>();
                    if (敌人生命 != null && !敌人生命.isDead)
                    {
                        Vector3 受击击退方向 = (敌人生命.transform.position - 特效生成位置);
                        受击击退方向.y = 0; // 仅保留水平击退
                        敌人生命.TakeDamage(伤害数值, 受击击退方向.normalized, source: SoldierDamageSource.Ranged);
                    }
                }
            }
            else
            {
                // 单体目标受击伤害
                SoldierHealth 目标生命 = 目标.GetComponent<SoldierHealth>();
                if (目标生命 != null && !目标生命.isDead)
                {
                    Vector3 受击击退方向 = (目标.position - transform.position);
                    受击击退方向.y = 0;
                    目标生命.TakeDamage(伤害数值, 受击击退方向.normalized, source: SoldierDamageSource.Ranged);
                }
            }

            // 播放随机命中特效
            if (命中特效数组 != null && 命中特效数组.Length > 0)
            {
                int 随机索引 = Random.Range(0, 命中特效数组.Length);
                GameObject 选定特效 = 命中特效数组[随机索引];
                if (选定特效 != null)
                {
                    GameObject 特效实例 = Instantiate(选定特效, 特效生成位置, Quaternion.identity);
                    Destroy(特效实例, 特效销毁时间);
                }
            }

            // 表现：箭矢插在目标身上随其移动
            if (!命中后立即销毁 && 目标 != null && !是否范围伤害)
            {
                SoldierHealth 目标生命 = 目标.GetComponent<SoldierHealth>();
                if (目标生命 == null || !目标生命.isDead)
                {
                    transform.SetParent(目标);
                }
            }
        }

        // 立即销毁判定
        if (命中后立即销毁 || (是否范围伤害 && 判定成功命中))
        {
            Destroy(gameObject);
            return;
        }

        // 停止拖尾发射，延时销毁实体以维持插箭残留效果
        TrailRenderer 拖尾组件 = GetComponentInChildren<TrailRenderer>();
        if (拖尾组件 != null)
        {
            拖尾组件.emitting = false;
        }

        Destroy(gameObject, 插箭停留时间);
    }
    /// <summary>
    /// 选中且启用组件时，按实际功能开关绘制世界空间半径，不受模型缩放影响。
    /// 黄色：非追踪模式的命中容差，以目标当前瞄准点为球心。
    /// 橙色：成功命中后在目标当前瞄准点执行的球形范围伤害。
    /// 尚未发射、没有目标时只在箭矢原点预览大小，不代表已经确定的落点。
    /// 此回调只绘制辅助图形，不更改飞行、命中或伤害逻辑。
    /// </summary>
    void OnDrawGizmosSelected()
    {
        if (!isActiveAndEnabled) return;
        Color previousColor = Gizmos.color;
        Vector3 center = 目标 != null ? 目标.position + 落点偏移位置 : transform.position;
        if (!是否追踪目标 && 命中判定半径 > 0f)
        {
            Gizmos.color = Color.yellow;
            Gizmos.DrawWireSphere(center, 命中判定半径);
#if UNITY_EDITOR
            UnityEditor.Handles.Label(center + Vector3.up * 命中判定半径, "命中半径（黄色）：" + 命中判定半径 + " 单位");
#endif
        }
        if (是否范围伤害 && 范围伤害半径 > 0f)
        {
            Gizmos.color = new Color(1f, 0.45f, 0f);
            Gizmos.DrawWireSphere(center, 范围伤害半径);
#if UNITY_EDITOR
            UnityEditor.Handles.Label(center + Vector3.down * 范围伤害半径, "范围伤害（橙色）：" + 范围伤害半径 + " 单位");
#endif
        }
        Gizmos.color = previousColor;
    }
}