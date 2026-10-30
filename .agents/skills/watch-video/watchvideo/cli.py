from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows 仅支持纯 Python summarize
    fcntl = None

from .analyzer import VideoAnalyzer
from .commands import CommandError, CommandRunner, check_tool
from .downloader import YtDlpClient
from .keyframes import DEFAULT_MAX_KEYFRAMES
from .media import FfmpegClient
from .models import parse_report_json
from .ocr import TesseractOcr
from .processes import render_process_report, scan_processes
from .reporting import write_failure_report, write_json_report, write_markdown_report
from .summarizer import render_summary_prompt
from .transcription import WhisperCppAutoSetup, WhisperCppTranscriber, WhisperTranscriber


DOCTOR_TOOLS = (
    ("python3", True),
    ("yt-dlp", True),
    ("ffmpeg", True),
    ("ffprobe", True),
    ("git", False),
    ("cmake", False),
    ("whisper", False),
    ("tesseract", False),
)

SUPPORTED_PLATFORMS = {"darwin", "linux"}
SUCCESS_ARTIFACTS = ("report.json", "report.md", "summary-input.md")
FAILURE_ARTIFACTS = ("failure.json", "failure.md")
CURRENT_RUN_ARTIFACT = "current-run.json"


def _bounded_int(value: str, *, minimum: int, maximum: int, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{label}必须是整数") from exc
    if parsed < minimum or parsed > maximum:
        raise argparse.ArgumentTypeError(f"{label}必须在 {minimum} 到 {maximum} 之间")
    return parsed


def _bounded_float(value: str, *, minimum: float, maximum: float, label: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{label}必须是数字") from exc
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        raise argparse.ArgumentTypeError(f"{label}必须是 {minimum:g} 到 {maximum:g} 之间的有限数")
    return parsed


def _max_height(value: str) -> int:
    return _bounded_int(value, minimum=144, maximum=8640, label="--max-height")


def _max_keyframes(value: str) -> int:
    return _bounded_int(value, minimum=1, maximum=10_000, label="--max-keyframes")


def _keyframe_interval(value: str) -> float:
    return _bounded_float(
        value,
        minimum=0.1,
        maximum=3600.0,
        label="--keyframe-interval",
    )


def _chunk_seconds(value: str) -> float:
    return _bounded_float(value, minimum=1.0, maximum=86_400.0, label="--chunk-seconds")


def _command_timeout(value: str) -> float:
    return _bounded_float(value, minimum=1.0, maximum=86_400.0, label="--command-timeout")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="watchvideo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="分析本地视频或网络视频链接")
    analyze.add_argument("source", help="本地视频路径或 http/https 视频链接")
    analyze.add_argument("-o", "--output", default="analysis", help="输出目录")
    analyze.add_argument(
        "--max-height",
        type=_max_height,
        default=1080,
        help="网络视频下载最大高度（144-8640）",
    )
    analyze.add_argument(
        "--keyframe-interval",
        type=_keyframe_interval,
        default=10.0,
        help="关键帧采样窗口秒数（0.1-3600）",
    )
    analyze.add_argument(
        "--max-keyframes",
        type=_max_keyframes,
        default=DEFAULT_MAX_KEYFRAMES,
        help=f"最多保留的关键帧数量（默认 {DEFAULT_MAX_KEYFRAMES}）",
    )
    analyze.add_argument("--sub-lang", action="append", default=None, help="字幕语言，例如 zh.* 或 en.*")
    analyze.add_argument("--language", default=None, help="Whisper 转写语言，例如 Chinese")
    analyze.add_argument("--whisper-cpp-bin", default=None, help="whisper.cpp 的 whisper-cli 路径")
    analyze.add_argument("--whisper-model", default=None, help="whisper.cpp 模型路径")
    analyze.add_argument("--whisper-prompt", default=None, help="传给 whisper.cpp 的提示词")
    analyze.add_argument(
        "--cookies-from-browser",
        default="chrome",
        help="yt-dlp 需要 cookies 时读取的浏览器，例如 chrome、firefox 或 auto",
    )
    analyze.add_argument(
        "--no-browser-cookies",
        dest="cookies_from_browser",
        action="store_const",
        const=None,
        help="yt-dlp 下载失败时不读取浏览器 cookies",
    )
    analyze.add_argument("--tools-dir", default=None, help="自动准备 whisper.cpp 时使用的工具目录")
    analyze.add_argument(
        "--keep-video",
        action="store_true",
        help="保留网络视频下载文件；默认分析完成后自动删除下载视频",
    )
    analyze.add_argument(
        "--auto-transcribe-setup",
        dest="auto_transcribe_setup",
        action="store_true",
        help="缺少转写工具时自动在工具目录准备 whisper.cpp",
    )
    analyze.add_argument(
        "--no-auto-transcribe-setup",
        dest="auto_transcribe_setup",
        action="store_false",
        help="缺少转写工具时不自动准备 whisper.cpp",
    )
    analyze.set_defaults(auto_transcribe_setup=True)
    analyze.add_argument("--ocr", dest="enable_ocr", action="store_true", help="对关键帧运行 tesseract OCR")
    analyze.add_argument("--no-ocr", dest="enable_ocr", action="store_false", help="关闭关键帧 OCR")
    analyze.set_defaults(enable_ocr=False)
    analyze.add_argument("--check-processes", action="store_true", help="分析结束后检查疑似残留进程")
    analyze.add_argument(
        "--command-timeout",
        type=_command_timeout,
        default=7200.0,
        help="单个外部命令超时秒数（默认 7200，最大 86400）",
    )

    summarize = subparsers.add_parser("summarize", help="根据 report.json 生成摘要输入包")
    summarize.add_argument("report_json", help="analyze 生成的 report.json 路径")
    summarize.add_argument("-o", "--output", default=None, help="输出 Markdown 路径")
    summarize.add_argument(
        "--chunk-seconds",
        type=_chunk_seconds,
        default=300.0,
        help="字幕分段秒数（1-86400）",
    )

    processes = subparsers.add_parser("processes", help="检查疑似 watchvideo 残留进程")
    processes.add_argument(
        "--command-timeout",
        type=_command_timeout,
        default=10.0,
        help="ps 扫描超时秒数（默认 10）",
    )
    subparsers.add_parser("doctor", help="检查本机可用外部工具")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in {"analyze", "processes", "doctor"} and sys.platform not in SUPPORTED_PLATFORMS:
        print(
            "watchvideo 的外部工具流程目前仅支持 macOS 和 Linux（POSIX）；"
            f"当前平台: {sys.platform}",
            file=sys.stderr,
        )
        return 2

    if args.command == "doctor":
        statuses = {}
        for tool, required in DOCTOR_TOOLS:
            status = check_tool(tool)
            statuses[tool] = status
            group = "REQUIRED" if required else "OPTIONAL"
            state = "OK" if status.available else "MISSING"
            detail = status.version or status.path or ""
            print(f"{group}_{state}\t{tool}\t{detail}")
        _print_capability_status("local", ["python3", "ffmpeg", "ffprobe"], statuses)
        _print_capability_status("remote", ["python3", "yt-dlp", "ffmpeg", "ffprobe"], statuses)
        return 1 if any(required and not statuses[tool].available for tool, required in DOCTOR_TOOLS) else 0

    if args.command == "analyze":
        output_dir = Path(args.output)
        progress = _CommandProgress()
        runner = CommandRunner(timeout_seconds=args.command_timeout, progress=progress)
        downloader = YtDlpClient(
            cookies_from_browser=args.cookies_from_browser,
            runner=runner,
        )
        analyzer = VideoAnalyzer(
            downloader=downloader,
            media_client=FfmpegClient(runner=runner),
            transcriber=WhisperTranscriber(runner=runner, prompt=args.whisper_prompt),
            whisper_cpp_transcriber=WhisperCppTranscriber(
                runner=runner,
                whisper_cpp_bin=args.whisper_cpp_bin,
                model_path=args.whisper_model,
                prompt=args.whisper_prompt,
            ),
            whisper_cpp_setup=WhisperCppAutoSetup(tools_dir=args.tools_dir, runner=runner),
            ocr_engine=TesseractOcr(enabled=args.enable_ocr, runner=runner),
            auto_transcribe_setup=args.auto_transcribe_setup,
        )
        print("分析开始：正在准备视频证据…", file=sys.stderr)
        try:
            with _output_lock(output_dir):
                existing_runs = set(_run_directories(output_dir))
                try:
                    report = analyzer.analyze(
                        args.source,
                        output_dir=output_dir,
                        subtitle_languages=args.sub_lang or ["zh.*", "en.*"],
                        max_height=args.max_height,
                        keyframe_interval=args.keyframe_interval,
                        max_keyframes=args.max_keyframes,
                        language=args.language,
                        enable_ocr=args.enable_ocr,
                        cleanup_downloaded_video=not args.keep_video,
                    )
                    _publish_success(report, output_dir)
                    try:
                        _cleanup_old_runs(output_dir, preserve=Path(report.work_dir), keep=1)
                    except OSError as cleanup_error:
                        print(f"历史 run 清理失败: {cleanup_error}", file=sys.stderr)
                except (CommandError, FileNotFoundError, OSError, ValueError) as exc:
                    failed_run = _newest_new_run(output_dir, existing_runs)
                    _publish_failure(
                        source_value=args.source,
                        output_dir=output_dir,
                        error=exc,
                        download_attempts=list(getattr(downloader, "download_attempts", [])),
                        run_dir=failed_run,
                    )
                    try:
                        _cleanup_old_runs(output_dir, preserve=failed_run, keep=2)
                    except OSError as cleanup_error:
                        print(f"历史 run 清理失败: {cleanup_error}", file=sys.stderr)
                    print(
                        f"分析失败，已写入: {(output_dir / 'failure.md').resolve()}",
                        file=sys.stderr,
                    )
                    if args.check_processes:
                        _print_processes(
                            timeout_seconds=min(args.command_timeout, 30.0),
                            file=sys.stderr,
                        )
                    return 1
        except (OSError, TimeoutError) as exc:
            print(f"分析失败: {exc}", file=sys.stderr)
            if args.check_processes:
                _print_processes(
                    timeout_seconds=min(args.command_timeout, 30.0),
                    file=sys.stderr,
                )
            return 1
        print("分析完成：报告和摘要输入包已生成。", file=sys.stderr)
        print(output_dir.resolve())
        if args.check_processes:
            _print_processes(timeout_seconds=min(args.command_timeout, 30.0), file=sys.stdout)
        return 0

    if args.command == "summarize":
        report_path = Path(args.report_json)
        output_path = Path(args.output) if args.output else report_path.parent / "summary-input.md"
        try:
            if not report_path.is_file():
                raise FileNotFoundError(f"report.json 不存在: {report_path}")
            with _output_lock(report_path.parent):
                report = parse_report_json(report_path.read_text(encoding="utf-8"))
                _atomic_write_text(
                    output_path,
                    render_summary_prompt(report, chunk_seconds=args.chunk_seconds),
                )
        except (OSError, TypeError, ValueError) as exc:
            print(f"摘要输入生成失败: {exc}", file=sys.stderr)
            return 2
        print(output_path.resolve())
        return 0

    if args.command == "processes":
        return _print_processes(timeout_seconds=args.command_timeout, file=sys.stdout)

    parser.print_help(sys.stderr)
    return 2


class _CommandProgress:
    """函数职责和边界：只报告当前外部工具，不打印可能含敏感 URL 的参数。"""

    LABELS = {
        "yt-dlp": "下载视频或字幕",
        "ffprobe": "读取媒体信息",
        "ffmpeg": "处理音频或关键帧",
        "whisper": "转写语音",
        "whisper-cli": "转写语音",
        "tesseract": "识别关键帧文字",
        "git": "准备 whisper.cpp",
        "cmake": "构建 whisper.cpp",
    }

    def __init__(self):
        self._last_program: str | None = None

    def __call__(self, program: str) -> None:
        if program == self._last_program:
            return
        self._last_program = program
        label = self.LABELS.get(program, f"运行 {program}")
        print(f"分析阶段：{label}…", file=sys.stderr)


def _print_capability_status(capability: str, required_tools: list[str], statuses: dict) -> None:
    missing = [tool for tool in required_tools if not statuses[tool].available]
    if missing:
        print(f"CAPABILITY_BLOCKED\t{capability}\t缺少 {', '.join(missing)}")
        return
    label = "可分析本地视频" if capability == "local" else "可分析远程视频"
    print(f"CAPABILITY_READY\t{capability}\t{label}")


def _publish_success(report, output_dir: Path) -> None:
    """函数职责和边界：同目录分阶段写入成功产物，并移除过期失败状态。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".watchvideo-publish-", dir=output_dir) as temporary:
        staged = Path(temporary)
        write_json_report(report, staged / "report.json")
        write_markdown_report(report, staged / "report.md")
        (staged / "summary-input.md").write_text(
            render_summary_prompt(report.to_dict()),
            encoding="utf-8",
        )
        _write_run_manifest(staged / CURRENT_RUN_ARTIFACT, "success", Path(report.work_dir))
        # 发布边界：manifest 最后切换；进程中断时旧 manifest 仍指向完整旧状态。
        for name in SUCCESS_ARTIFACTS:
            os.replace(staged / name, output_dir / name)
        os.replace(staged / CURRENT_RUN_ARTIFACT, output_dir / CURRENT_RUN_ARTIFACT)
        _remove_artifacts(output_dir, FAILURE_ARTIFACTS)


def _publish_failure(
    source_value: str,
    output_dir: Path,
    error: Exception,
    download_attempts,
    run_dir: Path | None = None,
) -> None:
    """函数职责和边界：同目录分阶段写入失败状态，避免和旧成功报告并存。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".watchvideo-failure-", dir=output_dir) as temporary:
        staged = Path(temporary)
        write_failure_report(
            source_value=source_value,
            output_dir=staged,
            error=error,
            download_attempts=download_attempts,
        )
        _write_run_manifest(staged / CURRENT_RUN_ARTIFACT, "failure", run_dir)
        for name in FAILURE_ARTIFACTS:
            os.replace(staged / name, output_dir / name)
        os.replace(staged / CURRENT_RUN_ARTIFACT, output_dir / CURRENT_RUN_ARTIFACT)
        _remove_artifacts(output_dir, SUCCESS_ARTIFACTS)


def _remove_artifacts(output_dir: Path, names: tuple[str, ...]) -> None:
    for name in names:
        (output_dir / name).unlink(missing_ok=True)


def _atomic_write_text(path: Path, content: str) -> None:
    """函数职责和边界：在目标目录写临时文件后原子替换单个文本产物。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


@contextmanager
def _output_lock(output_dir: Path, timeout_seconds: float = 30.0):
    """函数职责和边界：序列化同一输出目录的分析与报告发布，不锁其他目录。"""
    if fcntl is None:
        # Windows 仅允许 summarize；没有 POSIX flock 时退化为进程内无操作。
        yield
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / ".watchvideo.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"等待输出目录锁超时: {output_dir}")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _write_run_manifest(path: Path, status: str, run_dir: Path | None) -> None:
    payload = {
        "status": status,
        "run_dir": str(run_dir.resolve()) if run_dir is not None else None,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_directories(output_dir: Path) -> list[Path]:
    runs_dir = output_dir.resolve() / ".runs"
    if not runs_dir.is_dir():
        return []
    return [
        path.resolve()
        for path in runs_dir.glob("run-*")
        if path.is_dir() and not path.is_symlink()
    ]


def _newest_new_run(output_dir: Path, existing_runs: set[Path]) -> Path | None:
    created = [path for path in _run_directories(output_dir) if path not in existing_runs]
    if not created:
        return None
    return max(created, key=lambda path: path.stat().st_mtime_ns)


def _cleanup_old_runs(output_dir: Path, preserve: Path | None, keep: int) -> None:
    """函数职责和边界：只清理 `.runs/run-*` 直接子目录，不触碰其他用户文件。"""
    runs = sorted(
        _run_directories(output_dir),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    preserve_resolved = preserve.resolve() if preserve is not None else None
    retained: set[Path] = set()
    if preserve_resolved is not None and preserve_resolved in runs and keep > 0:
        retained.add(preserve_resolved)
    for run_dir in runs:
        if len(retained) >= max(keep, 0):
            break
        retained.add(run_dir)
    for run_dir in runs:
        if run_dir in retained:
            continue
        shutil.rmtree(run_dir)


def _print_processes(timeout_seconds: float, file) -> int:
    try:
        processes = scan_processes(timeout_seconds=timeout_seconds)
    except (CommandError, OSError, subprocess.SubprocessError) as exc:
        print(f"进程检查失败: {exc}", file=sys.stderr)
        return 1
    print(render_process_report(processes), end="", file=file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
