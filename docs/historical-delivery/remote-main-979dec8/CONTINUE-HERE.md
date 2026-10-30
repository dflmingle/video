# 换电脑继续制作

从本仓库即可接手，不需要旧电脑上的项目目录。以下命令支持 Windows PowerShell、macOS 和 Linux 终端；Linux 安装浏览器系统依赖时可能需要本机管理员权限。当前自动化已在 Windows 本机验证，其他系统尚未实机验证。

## 1. 新电脑先安装

- Git 与 Git LFS。
- Node.js **22 LTS，22.12 或更高版本**。
- Python **3.12**。检查点是在 Python 3.12 / NumPy 1.26.4 下保存，依赖版本已固定。
- **Google Chrome 当前稳定版**。已实际核对 Chrome 155 的角色画面。旧版 Chromium 141 存在蓝兵身体不显示的问题，不作为默认捕获环境。
- 仅在编辑原生场景时需要 Unity Hub + **Unity 6000.0.54f1**。浏览器预览、模拟和视频捕获不依赖 Unity Editor。

## 2. 下载并自动配置

```sh
git clone https://github.com/dflmingle/video.git
cd video
npm run setup
```

`setup` 会下载 LFS 资源、安装 npm 依赖、建立项目内 `.venv`、安装固定 Python 依赖、恢复逐帧基线，并检查本机 Chrome 和 C1 检查点能否加载。无需单独安装 FFmpeg，编码工具使用 Python 包自带的 FFmpeg。安装器不会更换本机 Chrome；缺少时请先安装 Google Chrome 当前稳定版。

成功后运行：

```sh
npm start
```

- 已确认 C1：<http://127.0.0.1:5267/v22.html?variant=V22R-C1&presentation=approved-castle>
- 续战快照：<http://127.0.0.1:5267/v22.html?variant=V22R-C1-melee&presentation=approved-castle>

服务保持运行，另开终端执行捕获。不要把 GitHub 的 Download ZIP 当作完整 LFS 克隆。原始资源下载失败时先解决 `git lfs pull`，不要用替代模型补齐。

## 3. 接手时先读

1. 本文件：当前要求和接续入口。
2. `docs/v22r-melee/PLAN.md`、`REVIEW.md`：本轮边界、失败诊断和遗留问题。
3. `docs/scene-requirements-r2/APPROVED-SCENE.md`：用户已确认场景，不要重新设计。
4. `DELIVERY-MANIFEST.json`、`docs/v22r-melee/data-audit.json`：入库快照与验证记录。

**已确认并必须锁定的是 C1 的 0–2.65 秒。** 红橙黄运动轨迹、蓝方集结、放箭时机、第一波密度、箭路、命中、死亡、场景和固定镜头不能改。C1 来源提交 `7c20b43` 保存在 `reference/source-history.bundle`，不等于本仓库当前提交号。

当前新增近战是**待视觉确认的工作快照**。入库模拟快照在 15.683 秒分出胜负、16.4 秒结束，结果红方869存活、蓝方0；这是数据结果，不是用户批准的成片。主会话可能在归档之后继续制作，换电脑前应先在旧电脑将后续修改提交推送，再在新电脑 `git pull --ff-only`；没有提交的文件不会自动同步。

本仓库位于旧电脑 `C:/Users/89trillion/video`，制作中的原工程另在 `C:/Users/89trillion/PveMontageShot01V22R`。它们不是自动同步目录；后者之后新增的成片或修改，需要整理进本仓库再提交。不要把本次归档误当作持续实时备份。

已有遗留：C1 开场部分军团出画和城墙穿越。本轮没有授权通过移动军团或机位改变已确认前段；单独报告和处理。身体碰撞模型是地面圆盘，不是动画网格逐三角面碰撞。

## 4. 从当前状态继续

先检查环境与已有数据，不必先重算整场：

```sh
npm run doctor
npm run battle:audit
npm run verify:runtime
```

已有模拟可以直接制作预览。在 `npm start` 服务运行时，另一终端：

```sh
# 先用少量帧核查当前环境与后续近战
npm run video:probe

# 前159个视频帧与原C1同步比较，输出新版前段PNG
npm run video:compare

# 捕获完整低成本480×720、60fps帧序列
npm run video:capture

# 编码完整片、2.3秒起续战片、前2.65秒同步对照
npm run video:encode
```

输出目录：`output/v22r-melee/`。先看真实预览和编码后画面，再决定正式1440×2160渲染。数据PASS不能代替正常速度视觉验收。

只有需要修改**后2.65秒**的模拟时才执行：

```sh
npm run battle:simulate
npm run battle:audit
```

该命令会从可信 F159 检查点重算续战，并覆盖本地 `variants/V22R-C1-melee/` 生成数据。先提交当前工作，保留对照。`npm run setup` 不重算战斗。

## 5. 可调整的机器设置

默认由 Playwright 的 `chrome` channel 查找本机 Google Chrome，不依赖旧电脑绝对路径。需要指定本机浏览器或解释器时可设置：

| 环境变量 | 用途 |
|---|---|
| `VIDEO_PYTHON` | 安装时指定 Python 3.12 路径；运行命令优先使用已配置的项目 `.venv` |
| `VIDEO_CHROME` | 自定义 Chromium/Chrome 可执行文件路径 |
| `VIDEO_URL` | 捕获服务器地址，默认 `http://127.0.0.1:5267` |
| `VIDEO_FONT` | 编码诊断标签字体文件；未设置时自动查本机字体 |

Windows 示例：`$env:VIDEO_PYTHON='D:/Python312/python.exe'`；macOS/Linux 示例：`export VIDEO_PYTHON=/path/to/python3.12`。若端口5267占用，可先 `npm start -- --port 5270`，再将捕获终端 `VIDEO_URL` 设为 `http://127.0.0.1:5270`。

历史调查工具和文档仍可能含旧绝对路径，仅作溯源；本文件列出的当前续作命令已移除旧 Chrome 和字体路径依赖。`collect_project.py` 是旧电脑归档工具，新电脑接手不需要运行。

`VIDEO_BROWSER=chromium` 可用于浏览器兼容诊断，此时安装器下载配套 Chromium；该选项不是当前已验证的默认生产环境。换浏览器或显卡后先检查 `npm run verify:runtime` 的截图，确认蓝兵身体、箭矢、材质齐全，再批量录制。环境检查不替代实际看图。

## 给新电脑 Codex 的接手提示

> 请先读 CONTINUE-HERE.md 和 docs/v22r-melee/PLAN.md、REVIEW.md。以仓库内 C1 为已确认基线，锁定0–2.65秒及场景、灯光、固定镜头、初始军团位置。只续写之后的真实战斗，不改前段冲锋和箭雨，不强制胜负。先运行 doctor和数据核查，查看低成本预览，交付前段同步对照、2.3秒起续战和完整预览；未经视觉确认不启动正式高分辨率渲染。报告城墙和出画等独立遗留，不擅自重排。
