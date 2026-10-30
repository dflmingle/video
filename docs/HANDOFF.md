# 换机接续与远端交付

## 已实际验证

从提交 `8ac7816` 执行 `git archive`，导出到独立临时目录，不复制原机器的 `node_modules`、`output`、求解器缓存或其他被忽略文件。随后：

1. `npm ci --no-audit --no-fund` 成功安装锁文件中的 17 个 Node 包。
2. 物料校验通过：原始归档的 773 个文件、199 项依赖没有缺失。
3. 启动导出副本的独立 Vite 服务，浏览器加载当前 T1 入口成功：1224 个角色、34 个原生场景对象，检查 0、1、2.65、4 秒及最后有效帧的渲染调用，没有页面错误、HTTP 失败或网络请求失败。
4. 已查看从导出副本生成的开场截图，城堡在顶部、红军与蓝军 U 型及场景素材均正常出现。此次仅为加载和指定时刻检查，不是全片正常速度视觉验收。

证据：[clean-export.json](requirements/verification/clean-export.json)、[浏览器检查](requirements/verification/clean-export-browser-smoke.json)、[开场截图](requirements/verification/clean-export-opening.png)。临时目录路径只是本次证据，不是运行依赖。

随后补入的其余 6 份原始资源包按当前文件逐包检查 SHA256 与包内容清单；不依赖它们改变现有 T1 播放数据。

## 新电脑准备

先完整取得 Git 仓库（包含源素材大文件）。如果远端采用 Git LFS，先安装 Git LFS、执行 `git lfs install`，克隆后执行 `git lfs pull`，避免只拿到指针文件。远端地址及存储方式必须以实际交付为准。

在项目根目录执行：

```powershell
npm ci
python tools/audit_material_archive.py --check-index
npm run dev
```

当前预览地址：`http://127.0.0.1:5257/v22.html?variant=V22R-topfield-T1&presentation=approved-castle`。

已测试环境：Windows，Node.js 24.16.0 / npm 10.9.4，Python 3.12.7。Vite 7 要求满足其 Node 版本条件，不能用旧版 Node 直接运行。仅网页播放需要 Node；以下 Python 依赖用于模拟、资源分析和视频工具：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r tools/requirements-handoff.txt
.venv\Scripts\python tools/audit_material_archive.py --check-index
```

依赖文件固定本机已使用版本；OSQP 1.1.3 的版本取自当前近战工具实际加载的 `output/v22r-volley-deps`。新电脑应正常安装 OSQP，不能依赖该旧本地目录。安装命令已整理，但本轮没有在第二台真实电脑重装整套 Python/Unity 环境。

验证浏览器资源加载：

```powershell
npx playwright install chromium
node tools/verify_handoff_preview.mjs
```

该脚本支持 `--browser` 或环境变量 `PVE_BROWSER_PATH`；Windows 默认优先使用标准路径 Chrome，否则使用 Playwright 的 Chromium。它使用独立临时端口，检查指定时刻并将报告和开场图写入 `output/handoff-verification/`，不模拟新战斗。

旧完整录制和编码脚本仍包含 `C:/Program Files/Google/Chrome/Application/chrome.exe`、Windows 字体、指定端口以及历史 `output` 对比证据路径。换机录制前需按脚本检查这些条件；不能把当前网页可播放说成所有历史脚本都已完全跨平台。当前 T1 的最终 `.f32` 和 JSON 可直接播放；重建历史候选还需要各自配置、检查点及求解器环境，不能只运行默认 builder 覆盖已有数据。

## 剩余三段准备情况

详细结论见 [REMAINING-SECTIONS-AUDIT.md](requirements/REMAINING-SECTIONS-AUDIT.md)。需求和参考图完整；已知 8 个用户资源包来源按内容去重的 7 份原包全部纳入项目。但刺客、立盾兵、指定场景和第四段白金角色仍缺可靠的资产对应，10 个分享链接均返回元数据错误 `1002`。

第四段有 PDF 内的 Logo 轮廓示意，不是完全没有参考；独立设计源文件尚未找到。资源缺口必须继续核对，不能宣布三段所有物料已经匹配完成。

## 远端状态

开始本次核查时 `git remote` 为空，已向用户请求目的仓库地址。不能擅自使用其他项目的仓库、选择公开可见性或推送到猜测的地址。

原始包 `PVE混剪.unitypackage`（约 347.5 MiB）及 `角色资源.unitypackage`（约 314.1 MiB）超过 GitHub 普通 Git 的单文件 100 MiB 限制。若目的地是 GitHub，需要 Git LFS 或目的地支持的大文件方案。**只在新提交里启用 LFS 不足以消除旧提交中的超限对象**；发布前必须按选定远端处理相关发布历史，并保留原本地提交的可追溯记录，不能直接强推覆盖已有远端分支。

未取得目标地址或未完成大文件上传时，交付状态只能记为「本地提交完成，远端推送待完成」。
