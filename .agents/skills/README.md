# 项目使用的 skills

当前项目的主要制作流程是 [web-game-video-production](web-game-video-production/SKILL.md)，用于 Web 视频制作、原生三维素材复用、战斗表现迭代、浏览器录制及编码后视觉验收。

完整目录提交到 `.agents/skills/web-game-video-production/`，包含 `SKILL.md`、`agents/openai.yaml` 及五份 `references` 文档。支持项目级 skills 的工具可从该目录发现；也可通过仓库根目录的 `AGENTS.md` 直接找到入口。

## 完整收录清单

回查项目相关历史会话的实际工具调用，确认以下五个 skill 的入口文件曾被读取。入口读取不代表工具执行成功，也不表示每个任务都必须使用全部 skill。

| Skill | 本项目中的用途 |
|---|---|
| [web-game-video-production](web-game-video-production/SKILL.md) | Web 视频制作、浏览器录制、视觉验收主流程 |
| [video-replication](video-replication/SKILL.md) | 参考复刻、素材映射、视觉事件与逐时段纠错 |
| [watch-video](watch-video/SKILL.md) | 视频分析、抽帧与证据提取；历史报告记载当前 Windows 环境的 CLI 不可用，收录不代表已修复或已完成正常速度观看 |
| [unity-ad-video-production](unity-ad-video-production/SKILL.md) | Unity 端制作方案、场景演出及验收流程参考 |
| [unity-cli](unity-cli/SKILL.md) | 需要时进行 Unity 工程或编辑器操作；不是当前 Web 渲染的运行依赖 |

各目录包含来源提供的引用文档及配套脚本、模板或配置（如有）；排除来源仓库的 `.git`、Python 缓存和虚拟环境。安装依赖和外部工具仍按各自说明操作，本次没有安装或启动它们。

## 来源与维护

- 来源：本机 `C:/Users/89trillion/.codex/skills/` 下上述五个同名目录的当前文件快照。
- 本次仅将已有 skill 纳入项目；未修改工作流程及脚本逻辑，也不声称这是历史渲染当时的精确版本。`unity-cli` 的七份引用文档仅清理了来源已有的行末空格或多余文件末尾空行，以通过 Git 空白检查。
- 项目副本由 Git 跟踪，供本项目后续工作直接使用，不依赖原机器上的全局 skill 路径。
- 项目副本与全局副本没有自动同步关系。更新时审阅差异并提交完整依赖，避免只更新 `SKILL.md` 后遗漏引用文档。
- 通用流程改进维护在 skill 中；本项目专有的布局、剧情、参数、脚本命令和用户确认记录继续放在项目文档中。

初次提交 `63947d0` 只收录了 Web 制作 skill；此次回查后补齐另外四个。未批量收录其余全局 skills，也未修改战斗代码、场景、相机或历史产物。
