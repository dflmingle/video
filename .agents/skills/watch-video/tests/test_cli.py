from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from watchvideo.cli import build_parser, main
from watchvideo.commands import CommandError, CommandResult
from watchvideo.models import (
    REPORT_SCHEMA_VERSION,
    AnalysisReport,
    DownloadAttempt,
    MediaInfo,
    Source,
    ToolStatus,
)


def valid_report_payload() -> dict:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source": {"kind": "file", "value": "video.mp4", "path": "video.mp4"},
        "work_dir": "analysis",
        "video_path": "video.mp4",
        "media": {
            "path": "video.mp4",
            "duration_seconds": 10.0,
            "width": 1280,
            "height": 720,
        },
        "transcript_text": "",
        "summary_text": "",
        "transcript_cues": [],
        "keyframes": [],
        "ocr_results": [],
        "subtitle_files": [],
        "download_attempts": [],
        "transcription_info": None,
        "cleanup_records": [],
        "warnings": [],
    }


class FailingAnalyzer:
    def __init__(self, downloader, **kwargs):
        self.downloader = downloader
        self.downloader.download_attempts = [
            DownloadAttempt(step="plain yt-dlp", status="failed", detail="fresh cookies"),
            DownloadAttempt(step="mobile share page play_addr", status="failed", detail="no play_addr"),
        ]

    def analyze(self, *args, **kwargs):
        run_dir = kwargs["output_dir"] / ".runs" / "run-failed"
        run_dir.mkdir(parents=True, exist_ok=True)
        raise FileNotFoundError("视频下载失败：需要本地视频或可访问直链")


class SuccessfulAnalyzer:
    def __init__(self, downloader, **kwargs):
        self.downloader = downloader

    def analyze(self, source, output_dir, **kwargs):
        video_path = Path(source)
        run_dir = output_dir / ".runs" / "run-current"
        run_dir.mkdir(parents=True, exist_ok=True)
        return AnalysisReport(
            source=Source(kind="file", value=source, path=video_path),
            work_dir=run_dir,
            video_path=video_path,
            media=MediaInfo(
                path=video_path,
                duration_seconds=10.0,
                width=1280,
                height=720,
            ),
            transcript_cues=[],
            transcript_text="有效转写文本",
            keyframes=[],
        )


class CliTests(unittest.TestCase):
    def test_analyze_accepts_local_automation_options(self):
        args = build_parser().parse_args(
            [
                "analyze",
                "video.mp4",
                "--max-keyframes",
                "12",
                "--whisper-cpp-bin",
                ".tools/whisper.cpp/build/bin/whisper-cli",
                "--whisper-model",
                ".tools/whisper.cpp/models/ggml-base.bin",
                "--whisper-prompt",
                "Agent, Codex",
                "--ocr",
                "--check-processes",
            ]
        )

        self.assertEqual(args.max_keyframes, 12)
        self.assertEqual(args.whisper_cpp_bin, ".tools/whisper.cpp/build/bin/whisper-cli")
        self.assertEqual(args.whisper_model, ".tools/whisper.cpp/models/ggml-base.bin")
        self.assertEqual(args.whisper_prompt, "Agent, Codex")
        self.assertTrue(args.enable_ocr)
        self.assertTrue(args.check_processes)
        self.assertTrue(args.auto_transcribe_setup)
        self.assertFalse(args.keep_video)

        default_args = build_parser().parse_args(["analyze", "video.mp4"])
        self.assertEqual(default_args.max_keyframes, 80)

    def test_main_analyze_forwards_prompt_to_system_whisper(self):
        with TemporaryDirectory() as tmp:
            with (
                patch("watchvideo.cli.VideoAnalyzer", SuccessfulAnalyzer),
                patch("watchvideo.cli.WhisperTranscriber") as transcriber,
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = main(
                    [
                        "analyze",
                        "video.mp4",
                        "--whisper-prompt",
                        "Codex, Agent",
                        "-o",
                        str(Path(tmp) / "analysis"),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(transcriber.call_args.kwargs["prompt"], "Codex, Agent")

    def test_analyze_accepts_keep_video_option(self):
        args = build_parser().parse_args(["analyze", "https://example.com/video", "--keep-video"])

        self.assertTrue(args.keep_video)

    def test_analyze_accepts_auto_transcribe_setup_options(self):
        args = build_parser().parse_args(
            [
                "analyze",
                "video.mp4",
                "--no-auto-transcribe-setup",
                "--tools-dir",
                ".custom-tools",
            ]
        )

        self.assertFalse(args.auto_transcribe_setup)
        self.assertEqual(args.tools_dir, ".custom-tools")

    def test_analyze_uses_chrome_cookies_by_default_and_can_disable_them(self):
        default_args = build_parser().parse_args(["analyze", "video.mp4"])
        disabled_args = build_parser().parse_args(["analyze", "video.mp4", "--no-browser-cookies"])
        firefox_args = build_parser().parse_args(
            ["analyze", "video.mp4", "--cookies-from-browser", "firefox"]
        )
        auto_args = build_parser().parse_args(
            ["analyze", "video.mp4", "--cookies-from-browser", "auto"]
        )

        self.assertEqual(default_args.cookies_from_browser, "chrome")
        self.assertIsNone(disabled_args.cookies_from_browser)
        self.assertEqual(firefox_args.cookies_from_browser, "firefox")
        self.assertEqual(auto_args.cookies_from_browser, "auto")

    def test_main_analyze_writes_failure_report_when_analysis_fails(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "analysis"
            with patch("watchvideo.cli.VideoAnalyzer", FailingAnalyzer):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    try:
                        exit_code = main(
                            [
                                "analyze",
                                "https://www.douyin.com/share/video/123",
                                "-o",
                                str(output_dir),
                            ]
                        )
                    except FileNotFoundError as exc:
                        self.fail(f"main should write failure reports and return 1, got {exc}")

            failure_json = output_dir / "failure.json"
            failure_md = output_dir / "failure.md"
            self.assertTrue(failure_json.exists())
            self.assertTrue(failure_md.exists())
            failure = json.loads(failure_json.read_text(encoding="utf-8"))
            markdown = failure_md.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 1)
        self.assertEqual(failure["source"], "https://www.douyin.com/share/video/123")
        self.assertIn("download_attempts", failure)
        self.assertIn("plain yt-dlp", markdown)
        self.assertIn("不要基于标题、简介或搜索结果总结", markdown)
        self.assertIn("failure.md", stderr.getvalue())

    def test_max_keyframes_must_be_positive(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                build_parser().parse_args(["analyze", "video.mp4", "--max-keyframes", "0"])

    def test_numeric_arguments_reject_non_finite_and_unreasonable_values(self):
        invalid_cases = [
            ["analyze", "video.mp4", "--max-height", "0"],
            ["analyze", "video.mp4", "--max-height", "8641"],
            ["analyze", "video.mp4", "--keyframe-interval", "nan"],
            ["analyze", "video.mp4", "--keyframe-interval", "0"],
            ["analyze", "video.mp4", "--max-keyframes", "10001"],
            ["analyze", "video.mp4", "--command-timeout", "inf"],
            ["summarize", "report.json", "--chunk-seconds", "nan"],
            ["summarize", "report.json", "--chunk-seconds", "86401"],
        ]

        for argv in invalid_cases:
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    build_parser().parse_args(argv)

    def test_parser_accepts_summarize_and_processes_commands(self):
        summarize = build_parser().parse_args(
            ["summarize", "analysis/demo/report.json", "-o", "summary.md", "--chunk-seconds", "120"]
        )
        processes = build_parser().parse_args(["processes"])

        self.assertEqual(summarize.command, "summarize")
        self.assertEqual(summarize.report_json, "analysis/demo/report.json")
        self.assertEqual(summarize.output, "summary.md")
        self.assertEqual(summarize.chunk_seconds, 120.0)
        self.assertEqual(processes.command, "processes")

    def test_main_doctor_distinguishes_required_and_optional_tools(self):
        statuses = {
            "python3": ToolStatus(name="python3", path="/usr/bin/python3", version="Python 3"),
            "yt-dlp": ToolStatus(name="yt-dlp", path="/usr/bin/yt-dlp", version="yt-dlp 1"),
            "ffmpeg": ToolStatus(name="ffmpeg", path=None),
            "ffprobe": ToolStatus(name="ffprobe", path="/usr/bin/ffprobe"),
            "git": ToolStatus(name="git", path="/usr/bin/git"),
            "cmake": ToolStatus(name="cmake", path=None),
            "whisper": ToolStatus(name="whisper", path=None),
            "tesseract": ToolStatus(name="tesseract", path="/usr/bin/tesseract"),
        }

        with patch("watchvideo.cli.check_tool", side_effect=lambda name: statuses[name]):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["doctor"])

        lines = stdout.getvalue().splitlines()
        self.assertEqual(exit_code, 1)
        self.assertIn("REQUIRED_OK\tpython3\tPython 3", lines)
        self.assertIn("REQUIRED_MISSING\tffmpeg\t", lines)
        self.assertIn("OPTIONAL_OK\tgit\t/usr/bin/git", lines)
        self.assertIn("OPTIONAL_MISSING\tcmake\t", lines)
        self.assertIn("OPTIONAL_MISSING\twhisper\t", lines)
        self.assertIn("OPTIONAL_OK\ttesseract\t/usr/bin/tesseract", lines)
        self.assertIn("CAPABILITY_BLOCKED\tlocal\t缺少 ffmpeg", lines)
        self.assertIn("CAPABILITY_BLOCKED\tremote\t缺少 ffmpeg", lines)

    def test_main_doctor_reports_local_ready_when_only_remote_tool_is_missing(self):
        def status_for(name):
            if name == "yt-dlp":
                return ToolStatus(name=name, path=None)
            return ToolStatus(name=name, path=f"/usr/bin/{name}")

        with patch("watchvideo.cli.check_tool", side_effect=status_for):
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["doctor"])

        lines = stdout.getvalue().splitlines()
        self.assertEqual(exit_code, 1)
        self.assertIn("CAPABILITY_READY\tlocal\t可分析本地视频", lines)
        self.assertIn("CAPABILITY_BLOCKED\tremote\t缺少 yt-dlp", lines)

    def test_main_summarize_writes_markdown_prompt(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_json = root / "report.json"
            output = root / "summary.md"
            report = valid_report_payload()
            report["transcript_cues"] = [
                {"start_seconds": 0, "end_seconds": 1, "text": "开场"}
            ]
            report["transcript_text"] = "开场"
            report_json.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                exit_code = main(["summarize", str(report_json), "-o", str(output)])
            content = output.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("# 视频总结输入包", content)

    def test_main_summarize_defaults_output_next_to_report_json(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_json = root / "report.json"
            report_json.write_text(
                json.dumps(valid_report_payload(), ensure_ascii=False),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                exit_code = main(["summarize", str(report_json)])

            output = root / "summary-input.md"
            content = output.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("# 视频总结输入包", content)

    def test_main_summarize_holds_output_lock_while_reading_and_writing(self):
        events = []

        class LockProbe:
            def __enter__(self):
                events.append("enter")

            def __exit__(self, *args):
                events.append("exit")

        with TemporaryDirectory() as tmp:
            report_json = Path(tmp) / "report.json"
            report_json.write_text(
                json.dumps(valid_report_payload(), ensure_ascii=False),
                encoding="utf-8",
            )
            with (
                patch("watchvideo.cli._output_lock", return_value=LockProbe()) as lock,
                patch("watchvideo.cli._atomic_write_text", side_effect=lambda *_: events.append("write")),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(["summarize", str(report_json)])

        self.assertEqual(exit_code, 0)
        lock.assert_called_once_with(report_json.parent)
        self.assertEqual(events, ["enter", "write", "exit"])

    def test_main_summarize_reports_user_errors_without_traceback(self):
        with TemporaryDirectory() as tmp:
            report_json = Path(tmp) / "report.json"
            report_json.write_text("{broken", encoding="utf-8")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = main(["summarize", str(report_json)])

        self.assertEqual(exit_code, 2)
        self.assertIn("摘要输入生成失败", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_main_analyze_publishes_mutually_exclusive_success_artifacts(self):
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "analysis"
            output_dir.mkdir()
            (output_dir / "failure.json").write_text("{}", encoding="utf-8")
            (output_dir / "failure.md").write_text("old failure", encoding="utf-8")
            stale_run = output_dir / ".runs" / "run-stale"
            stale_run.mkdir(parents=True)

            with patch("watchvideo.cli.VideoAnalyzer", SuccessfulAnalyzer):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = main(
                        ["analyze", "video.mp4", "-o", str(output_dir)]
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "report.json").exists())
            self.assertTrue((output_dir / "report.md").exists())
            self.assertTrue((output_dir / "summary-input.md").exists())
            self.assertFalse((output_dir / "failure.json").exists())
            self.assertFalse((output_dir / "failure.md").exists())
            current = json.loads((output_dir / "current-run.json").read_text(encoding="utf-8"))
            self.assertEqual(current["status"], "success")
            self.assertTrue(current["run_dir"].endswith("run-current"))
            self.assertFalse(stale_run.exists())

    def test_main_analyze_failure_removes_stale_success_artifacts(self):
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "analysis"
            output_dir.mkdir()
            for name in ("report.json", "report.md", "summary-input.md"):
                (output_dir / name).write_text("stale", encoding="utf-8")

            with patch("watchvideo.cli.VideoAnalyzer", FailingAnalyzer):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    exit_code = main(
                        ["analyze", "https://example.com/video", "-o", str(output_dir)]
                    )

            self.assertEqual(exit_code, 1)
            self.assertTrue((output_dir / "failure.json").exists())
            self.assertTrue((output_dir / "failure.md").exists())
            self.assertFalse((output_dir / "report.json").exists())
            self.assertFalse((output_dir / "report.md").exists())
            self.assertFalse((output_dir / "summary-input.md").exists())
            current = json.loads((output_dir / "current-run.json").read_text(encoding="utf-8"))
            self.assertEqual(current["status"], "failure")
            self.assertTrue(current["run_dir"].endswith("run-failed"))

    def test_unsupported_platform_is_rejected_without_traceback(self):
        stderr = io.StringIO()
        with patch("watchvideo.cli.sys.platform", "win32"), redirect_stderr(stderr):
            exit_code = main(["analyze", "video.mp4"])

        self.assertEqual(exit_code, 2)
        self.assertIn("仅支持 macOS 和 Linux", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_processes_command_error_has_no_traceback(self):
        error = CommandError(
            CommandResult(
                args=["ps"],
                returncode=124,
                stdout="",
                stderr="命令执行超时",
            )
        )
        stderr = io.StringIO()
        with patch("watchvideo.cli.scan_processes", side_effect=error), redirect_stderr(stderr):
            exit_code = main(["processes"])

        self.assertEqual(exit_code, 1)
        self.assertIn("进程检查失败", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
