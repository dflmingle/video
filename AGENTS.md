# 项目工作入口

本仓库为 PveMontageShot01V22R 视频项目。进行本项目的视频制作、战斗表现、场景布局、录制及视觉验收时，先阅读并使用项目内的 [web-game-video-production skill](.agents/skills/web-game-video-production/SKILL.md)，按任务需要读取其 references 文档。

其他项目相关 skill 按任务选用，不要求每次全部执行：

- 参考视频复刻、素材对应与视觉纠错：[video-replication](.agents/skills/video-replication/SKILL.md)。
- 参考视频分析、抽帧及证据提取：[watch-video](.agents/skills/watch-video/SKILL.md)。
- 涉及 Unity 端的视频制作与场景演出：[unity-ad-video-production](.agents/skills/unity-ad-video-production/SKILL.md)。
- 确实需要操作 Unity Editor 或 Unity 工程时：[unity-cli](.agents/skills/unity-cli/SKILL.md)。

收录 Unity 相关 skill 不改变当前 Web 视频项目的技术路线，也不要求为此启动或重建 Unity 项目。

- 用户当前指令及已经确认的约束优先；局部修改保持在授权范围内，不顺手重做已认可的战斗。
- 项目参数、资源路径、候选方案和验证证据保留在 docs 等项目记录中，不写进通用 skill。
- 历史报告只代表当时版本；开始工作时核对当前代码、产物和用户最新要求。
- 工具请求和返回控制大小，定向读取文件、日志和图片，避免 Payload Too Large。

项目内 skill 的来源及维护方法见 [.agents/skills/README.md](.agents/skills/README.md)。

完整四段原始需求入口为 [docs/requirements/README.md](docs/requirements/README.md)；模型、动画、材质、贴图、原始资源包及当前预览数据的归档说明为 [docs/materials/README.md](docs/materials/README.md)。开始相关工作时先读对应原始需求，不以项目总结替代原文。
