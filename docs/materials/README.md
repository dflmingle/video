# 项目物料归档与复现入口

本次把当前项目实际可用的原生资源、运行素材和最新完整预览依赖纳入 Git，修正此前整个 `assets/` 和 `variants/` 被忽略造成的缺失。仅归档及调整跟踪规则，没有改动战斗、相机或场景表现逻辑。

## 归档范围

| 内容 | 仓库路径 | 说明 |
|---|---|---|
| 四段完整原始需求及逐页文字、链接 | `docs/requirements/` | 16 页 PDF 原件完整保留图片、表格与四段要求 |
| 用户提供的完整原始资源包 | `assets/source-packages/` | 包含 PVE 混剪、角色、贴图、特效、防御塔及历史场景素材；8 个已知来源路径按内容去重为 7 份包，逐包来源与 SHA256 见 `all-package-sources.json` |
| 已提取的 Unity 原生物料 | `assets/imported/Assets/` | 模型、骨骼动画、Prefab、场景、材质、贴图和 `.meta`；包含本项目此前扫描导入的可用资源 |
| 士兵运行模型与贴图 | `assets/runtime/` | 四类士兵 FBX、配套贴图和包含原始来源、哈希及动画区间的 `manifest.json` |
| 原始动作参考 | `assets/references/cut.gif` | 与已有 `docs/core-reference.json` 的 SHA256 一致 |
| 场景运行导出 | `public/native-scenes/` | 已有原生网格二进制、场景 manifest、浏览器贴图及阴影派生图；不收录 `native-scenes/native-scenes/` 的重复目录 |
| 当前完整预览的精确运行数据 | `variants/V22R-topfield-T1/*.f32`、`*.json` | 保留现有模拟、轨迹、事件和场景布局配置；不重新模拟 |
| 当前布局的种子参数 | `variants/V22R-topfield-T1-seed/params.json` | 归档配置，不意味着重跑可以忽略工具和求解器环境差异 |

`DecShadow.shader` 和 `Grid.shader` 原先未提取，本次按场景 manifest 中的真实 GUID 从用户提供的 `PVE混剪.unitypackage` 提取原文件及 `.meta`。来源与哈希见 [shader-source-provenance.json](shader-source-provenance.json)。Unity 内置资源 `Resources/unity_builtin_extra` 是引擎内置标识，不是遗漏的磁盘文件。

原始物料以 `.gitattributes` 保留字节及原作者格式；不清理原生文件的行尾或空白。清单记录文件大小和 SHA256，见 [manifest.json](manifest.json)。检查脚本为 [audit_material_archive.py](../../tools/audit_material_archive.py)。

## 当前完整预览入口

在仓库根目录执行 `npm ci` 安装锁定的 Node 依赖，再执行 `npm run dev`。默认地址：

`http://127.0.0.1:5257/v22.html?variant=V22R-topfield-T1&presentation=approved-castle`

此链接明确选择最新完整候选和已确认固定镜头；旧 HTML 入口的默认候选可能是历史版本。归档后无需访问原机器的 `assets` 或 `variants` 外部路径即可读取这一候选的浏览器运行物料。下载 Node 依赖仍需要 npm 环境。

运行 `python tools/audit_material_archive.py` 核对清单哈希和引用完整性；追加 `--check-index` 可检查全部归档依赖是否已纳入 Git。

## 范围与历史限制

- 归档四段原始需求不代表已完成四段制作；当前实现以第一段迭代为主。
- PDF 中的远程链接完整保留，但尚未下载的第二至第四段外部资源不能声称已归档。
- 用户原始 `.unitypackage` 压缩包及已提取物料都纳入仓库；包本体的来源与哈希见 [package-source-provenance.json](package-source-provenance.json)。来源机器上的文件保持不动。
- 历史候选模拟、重复 `.npy`、求解器 pickle 检查点、导出视频和逐帧截图仍保留本地，不作为模型物料重复提交。当前完整预览需要的 `.f32` 和 JSON 已单独保留。
- 这是现有 Web 视频项目的资源与播放数据归档，不宣称是包含全部 Unity Packages/ProjectSettings 的完整 Unity 工程。
- 本次没有修复或重新验收战斗表现；最新 T1 报告中已经披露的近战弧形拥挤及后期追击出画限制仍然存在。

换机实际测试、剩余三段资源对应缺口及环境安装说明见 [HANDOFF.md](../HANDOFF.md)。额外收录资源包不代表包内角色、场景已经与第二至第四段逐项匹配；不得据包名替用户选定资源。
