# 架构说明

本文记录当前实现的真实边界。这个仓库的目标是把视频整理成可供 Codex 理解的材料，而不是直接替代 Codex 做完整内容分析。

## 数据流

```text
source
  -> classify_source
  -> output/.runs/run-* 隔离工作区
  -> YtDlpClient、分享页 play_addr 兜底或本地文件
  -> FfmpegClient.probe
  -> 字幕加载或 WhisperTranscriber 或 WhisperCppAutoSetup/WhisperCppTranscriber
  -> FfmpegClient.extract_keyframes，可限制数量
  -> 可选 TesseractOcr
  -> 清理远程下载 MP4（默认）
  -> AnalysisReport
  -> report.json / report.md / summary-input.md / current-run.json
```

## 模块边界

- `watchvideo/cli.py`
  命令行入口。负责参数解析、输出目录锁、调用分析器、分阶段原子发布互斥的成功/失败状态、自动生成摘要输入包和打印进程检查结果。`current-run.json` 指向当前 run。

- `watchvideo/analyzer.py`
  编排层。每次分析在 `output/.runs/run-*` 独立目录里完成，不复用旧字幕、视频或转写。负责下载、转写、抽帧、OCR 和清理顺序，不删除用户本地输入文件。

- `watchvideo/downloader.py`
  下载适配层。优先使用 `yt-dlp`；遇到 cookies/login/bot 拦截时按配置重试浏览器 cookies；仍失败时结构化解析移动端分享页中的 SSR `play_addr` 候选。分享页、每次重定向和视频候选均校验公网 HTTP(S) 地址，拒绝私网/回环/链路本地目标；同时限制页面与视频大小，校验 Content-Type 和已知视频容器签名，临时 `.part` 成功后才原子发布。

- `watchvideo/media.py`
  `ffmpeg` / `ffprobe` 适配层。负责读取视频元信息、按预算抽候选帧、保存代表帧，默认最多保留 80 张。

- `watchvideo/keyframes.py`
  关键帧策略。按固定时间窗口取候选点，用 PPM 边缘变化做清晰度评分，再用低成本 dHash/Hamming distance 跳过高度相似帧。候选时间会在有关键帧上限时覆盖完整时间线，而不是只从开头截断。

- `watchvideo/subtitles.py`
  字幕解析。支持 `.srt` 和 `.vtt`，会清理标签、合并多行文本、去掉相邻重复句。

- `watchvideo/transcription.py`
  自动转写入口。支持系统 `whisper` CLI 和显式传入的 `whisper.cpp`。自动准备时使用用户缓存（支持 `WATCHVIDEO_TOOLS_DIR`），锁定 whisper.cpp commit 和 cmake 版本，并验证模型 SHA-256。转写成功后记录 ASR 来源、模型、语言、prompt 和逐字稿文件；默认清理临时 WAV。

- `watchvideo/commands.py`
  外部命令边界。统一应用可配置超时、有界 stdout/stderr 和不包含参数的阶段进度回调；错误信息会屏蔽敏感参数与 URL 凭据。超时或调用方中断时终止本次命令的 POSIX 进程组，避免遗留子进程。

- `watchvideo/ocr.py`
  OCR 入口。当前只在用户传 `--ocr` 时调用 `tesseract`，并只处理已经抽出的关键帧。

- `watchvideo/summarizer.py`
  摘要输入包生成器。CLI 摘要入口只接受当前 `schema_version` 且通过严格类型/有限数校验的 `report.json`。持久化前脱敏 URL 凭据和查询参数，并将字幕、OCR、画面文字、路径、URL 和诊断明确包裹为不可信视频数据，防止将其中的命令当成 Agent 指令。

- `watchvideo/processes.py`
  进程检查。扫描 `watchvideo` 根进程，并通过 PPID 递归纳入位于仓库外的后代 `yt-dlp` / `ffmpeg` / `whisper-cli`；扫描有超时，只报告不清理。

- `watchvideo/reporting.py`
  报告写出。写入前校验 schema 并递归脱敏 URL；Markdown 输出会明确标注视频派生内容不可信。CLI 负责将 `report.*` / `summary-input.md` 与 `failure.*` 作为互斥状态分阶段原子发布。

- `watchvideo/models.py`
  数据模型。集中定义 source、media、subtitle、keyframe、download attempt、cleanup record、transcription info、report 等结构。

## 大模型能力边界

仓库代码本身不调用 OpenAI、Claude、Gemini 或其他云端 LLM API。

仓库也不把视频标题、简介、搜索结果或同主题网页当作视频证据。远程视频必须先拿到 MP4、字幕/转写或关键帧；拿不到时应报告下载阻塞，而不是生成内容总结。

当前大模型相关能力分两类：

- 语音识别：如果安装 `whisper` CLI，或自动/显式准备 `whisper.cpp`，脚本会本地生成字幕。
- 内容理解：目前由 Codex 在对话中读取报告、摘要输入包和关键帧后完成，不在代码里自动执行。

本地 `whisper.cpp` 流程已纳入 `python3 -m watchvideo analyze` 的默认路径：没有字幕且系统 `whisper` 无结果时，CLI 会尝试在 macOS `~/Library/Caches/watchvideo` 或 Linux `${XDG_CACHE_HOME:-~/.cache}/watchvideo` 准备固定版本的 `whisper.cpp`。显式传入二进制和模型路径时，CLI 使用用户指定路径，不覆盖配置错误。

如果 Codex 已经得出“视频讲了什么”的最终总结，调用方应把总结写入 `AnalysisReport.summary_text`，让 `report.md` 出现 `视频内容总结` 区块。总结不能只存在于对话上下文里。

## 当前限制

- 没有场景检测，当前是固定窗口采样、清晰度评分和相似帧去重。
- 没有内置摘要生成，视频总结仍需要 Codex 或其他 LLM 读取报告后完成。
- OCR 只处理关键帧，不覆盖所有视频帧。
- 进程检查只报告，不自动结束进程。
- `summarize` 只生成输入包，不调用模型。
- 媒体分析、环境检查和进程扫描只支持 macOS/Linux（POSIX）。

## 下一步设计方向

优先级从高到低：

1. 增加场景检测或镜头切分，进一步减少固定窗口采样的冗余。
2. 改进 OCR 区域选择，只处理底部字幕区或关键帧主要文本区。
3. 增加可选 LLM 集成，把 `summarize` 输入包送入 OpenAI API。
4. 增加更多脱敏平台 fixture，覆盖真实短视频样本的页面结构变化。
