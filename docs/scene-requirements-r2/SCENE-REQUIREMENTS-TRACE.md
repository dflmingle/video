# 场景需求溯源表（原始文件证据，V22-R 第二轮）

当前工作分支 `v22-reference-revision`，战斗代码提交 `109a92e`。本轮不移植 V23，不替换正式场景，不重新渲染完整视频。最新时长要求是 **2.8–3.2 秒**，覆盖之前的约 4 秒目标。

## 原始依据

主需求文件：`C:/Users/89trillion/Downloads/pve pvp真实感混剪.pdf`，16 页，SHA256 `ecb52eeaf5891655c699a30ba20ee487c81e432e012c314965fd9f6bee4561a0`。

- 第 7 页「分镜所需的对战阵型 / 阵型1」明确列出场景链接。
- 第 14 页「场景 / 对应小兵」重复同一个链接，并嵌入本轮提取的完整场景参考图。图片 xref 64，798×1807，SHA256 `7305f7565141032fc5623e8a27f4f6885a378021a37d842beea06c06129f0ffb`。
- 两页链接均为 `https://drive.89trillion.com:5001/d/f/18LIFiPBiOMRrSB1jDWQ4YgHVNy7uKwo`。网页返回公开分享壳、错误码 1002，没有文件名信息；不能据此断言链接文件叫 CastleExterior。用户最新补充指定 `PVE混剪.unitypackage`，本轮按这份包优先核查。
- 原 PDF **没有直接写 Unity 场景名、Prefab 名或 Assets 路径**。CastleExterior 是实际资产与画面的候选匹配结果，不是文档原文指定名称。

下表来源「主 PDF」均指上面的完整文件路径；其他来源逐行写明。图片观察不冒充文字原文。

| 编号 | 需求原文或图像证据 | 来源及位置 | 参考图片 | 性质 | 对应实际资源 | 匹配状态 / 差异 |
|---|---|---|---|---|---|---|
| DOC-01 | 「所有大方阵均由3*3小方阵构成」 | 主 PDF，第 7 页，分镜所需的对战阵型 | 第 7 页阵型1示意图 | 必须 | V22 军团、小队模拟数据 | 保留；不是场景背景图内的士兵证据 |
| DOC-02 | 「蓝方为u型阵，缓慢往前边攻击边前进；」 | 主 PDF，第 7 页，阵型1内容 | 第 7 页阵型1示意图 | 必须 | V22 蓝方 U 型与前进集结轨迹 | 保留；原文没有要求蓝方原地冻结 |
| DOC-03 | 「红方为整齐的方阵往前冲。」 | 主 PDF，第 7 页，阵型1内容 | 第 7 页阵型1示意图 | 必须 | V22 红橙黄军团轨迹 | 保留；不采用 V23 等待与大幅击退 |
| SCN-01 | 「场景：」及上述原始分享链接 | 主 PDF，第 7 页，阵型1所需 | 对应第 14 页同链接图 | 必须；文件名不明确 | 包内 `Assets/ArtOfWar-II_Art/Environment/Feature/CastleExterior/CastleExterior.unity` | 候选；无法证明原链接确实对应本包这一版本 |
| SCN-02 | 「场景」「对应小兵」，同一场景链接旁嵌入完整城堡地面图 | 主 PDF，第 14 页，资源表第一行 | `document-scene-reference.png`，xref 64 | 必须参考的图像证据 | CastleExterior 场景、同目录 Grp Prefab | 部分匹配；有真实模型版本差异，不能仅凭颜色宣布完成 |
| VIS-01 | 图像可见：暖黄色棋盘格地面（无逐字文字规定） | 主 PDF，第 14 页图片 | xref 64 | 图像要求 | `Common/CastleExterior/Modle/CastleExterior_Land.fbx`；Land/Gird 材质；`Common/SnowBridge/Mesh/SnowBridge_Gird.fbx` | 部分匹配；地面是真实几何及原贴图/网格 Shader，比例待确认 |
| VIS-02 | 图像可见：紫色城墙、明显的塔和垛口 | 主 PDF，第 14 页图片 | xref 64 上部 | 图像要求 | `Common/CastleExterior/Modle/CastleExterior_Building.fbx` | 部分匹配；包内中央开口与双小塔轮廓不同 |
| VIS-03 | 图像可见：墙右侧深蓝绿色有分格的城门 | 主 PDF，第 14 页图片 | xref 64 上部右侧 | 图像要求 | Building.fbx 两个子网格 | 不完全匹配；原生模型检查未发现另一套隐藏门体 |
| VIS-04 | 图像可见：左侧绿色、蓝绿色完整树冠 | 主 PDF，第 14 页图片 | xref 64 左上 | 图像要求 | `Common/CastleExterior/Modle/CastleExterior_Tree_04.fbx`、`CastleExterior_Tree_05.fbx` | 不匹配；本包实例为橙色块状树形；不能只改颜色认定树冠还原 |
| VIS-05 | 图像可见：左侧尖头木桩与横向连接木栏 | 主 PDF，第 14 页图片 | xref 64 左侧 | 图像要求 | `Common/CastleExterior/Modle/CastleExterior_Stakes_01.fbx`、`CastleExterior_Stakes_02.fbx` | 部分匹配；只有木桩对应，未证实横栏几何存在 |
| VIS-06 | 图像可见：左侧紫色骷髅图案告示牌 | 主 PDF，第 14 页图片 | xref 64 左侧 | 图像要求 | 本包 DecD 贴图和材质存在；没有找到可确认的对应模型/实例 | 未找到；不能用贴图存在代替几何存在 |
| VIS-07 | 图像可见：城墙在上，树与围栏在左，地面向下展开 | 主 PDF，第 14 页图片 | xref 64 全图 | 图像要求 | CastleExterior 原始层级与世界坐标 | 未完全匹配；原布局与当前 V22 轴向也未对齐；不能任意挪建筑 |
| VIS-08 | 地面格子相对士兵比例 | 主 PDF，第 14 页图片与第 7 页示意图分开提供 | 两张图 | 不明确：没有合成后严格标尺 | 原地面与 V22 士兵世界尺寸 | 未确认；第 14 页背景图没有士兵，不能伪造文档给出的比例数值 |
| VIS-09 | 红、橙、黄方阵与蓝 U 相对关系 | 主 PDF，第 7 页，阵型1示意图 | 第 7 页 | 必须 | V22 原始军团位置和蓝方集结 | 保留；未移动士兵来适配场景 |
| VIS-10 | 图像可见：卡通 3D 空间、立体墙体/树/围栏及透视 | 主 PDF，第 14 页图片；用户最新明确必须真实 3D | xref 64 | 必须 | 原 Unity 网格、Prefab、原材质与贴图 | 来源通过，外观/布局只部分匹配；预览不是截图贴片 |
| ACT-01 | 「在不改变现有战斗逻辑的前提下，通过局部战斗行为、动作差异、受击反馈、阵型变化和前线推进表现，提升军团战斗的真实感。」 | 主 PDF，第 13 页，表达效果及规则 | 不适用 | 必须 | V22 原行为 | 冻结，场景调查未改战斗实现 |
| ACT-02 | 「士兵的攻击、停顿、移动和补位不完全同步，保持合理的动作与站位差异。」 | 主 PDF，第 13 页，群体动作差异 | 不适用 | 必须 | V22 个人动作、独立启动实验 | 不以阵型紧凑为由冻结个人动作 |

表中 `Common/...` 为真实扫描得到的 `Assets/ArtOfWar-II_Art/Environment/Common/...` 路径缩写；逐对象完整模型/材质/贴图路径见 `PACKAGE-RESOURCE-MAP.md`。

## 已搜索目录与缺失边界

递归检索 `C:/Users/89trillion/Downloads`、`C:/Users/89trillion/Documents/WXWork`、`C:/Users/89trillion/Desktop`、`C:/Users/89trillion/My project/Assets`、本工作树 `assets/imported`。文件清单 9577 条；明确排除 .git、Library、Temp、node_modules、ThirdParty 等无关缓存/依赖目录，逐文件状态和排除目录保存在 `original-document-search.json`。检查了 docx、pdf、md、txt、xlsx、csv、json、yaml、html 等，不把 Codex 旧报告当作原始需求。一个无关的 Excel `~$商品选品册_20261027_1503.xlsx` 锁文件不可读，未宣称无错误全读完。

- `C:/Users/89trillion/Downloads/PVE：守关敌万军 (1).docx`：正文第 62 段「地形参考：双桥，大场景，拥挤」，第 122–123 段「场景」「参考图pve竞技场场景资源底图.png」；45 张嵌入图片已检查。它对应双桥关卡，不能覆盖本次阵型1单独指定的场景。
- `C:/Users/89trillion/Desktop/PVE：守关敌万军.pdf`：同类双桥关卡材料，不作本次城堡场景的替代指定。
- `C:/Users/89trillion/Desktop/素材.docx`：有「底图（背景用）」与另一组角色资料；正文及 7 张嵌入媒体已检查。这不能覆盖当前用户明确的真实 3D 要求。
- 主 PDF 对完整混剪曾要求切镜，与当前这个短片的一镜到底冲突；当前用户要求优先。旧 4 秒时长已被约 3 秒覆盖。

## 当前结论

**原始文档与其场景图已找到；指定包内真实城堡场景也已找到；包内这一版与文档图完全一致尚未证明，明确存在树木、围栏/牌、城门轮廓差异。** 不把另一工程的散件组合成假原场景，不替换正式场景。候选静帧用于确认版本，不代表视觉验收通过。
