from contextlib import redirect_stderr
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.update_report_summary import main, replace_summary, update_report_files
from watchvideo.models import REPORT_SCHEMA_VERSION


class UpdateReportSummaryTests(unittest.TestCase):
    def test_main_reports_input_error_without_traceback(self):
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(["missing-report.md", "--summary-file", "missing-summary.md"])

        self.assertEqual(exit_code, 2)
        self.assertIn("更新报告失败", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_replace_summary_is_idempotent_when_summary_contains_h2_and_h3(self):
        report = """# 视频分析报告

## 视频内容总结

旧开头

## 旧二级标题

旧内容

## 时间线速览

- 时间线

## 关键帧

- 关键帧
"""
        summary = """一句话总结

## 视频主线

新内容

### 细节

更多内容

<!-- watchvideo:summary:end -->
"""

        once = replace_summary(report, summary)
        twice = replace_summary(once, summary)

        self.assertEqual(once, twice)
        self.assertNotIn("旧开头", twice)
        self.assertNotIn("旧二级标题", twice)
        self.assertEqual(twice.count("## 视频内容总结"), 1)
        self.assertEqual(twice.count("## 视频主线"), 1)
        self.assertEqual(twice.count("<!-- watchvideo:summary:end -->"), 1)
        self.assertIn("&lt;!-- watchvideo:summary:end --&gt;", twice)
        self.assertIn("## 时间线速览", twice)
        self.assertIn("## 关键帧", twice)

    def test_update_report_files_syncs_report_json_summary(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            report_md = root / "report.md"
            report_json = root / "report.json"
            report_md.write_text(
                "# 视频分析报告\n\n## 时间线速览\n\n- 时间线\n",
                encoding="utf-8",
            )
            report_json.write_text(
                json.dumps(
                    {
                        "schema_version": REPORT_SCHEMA_VERSION,
                        "source": {
                            "kind": "url",
                            "value": "https://alice:secret@example.com/watch?token=private",
                            "path": None,
                        },
                        "work_dir": str(root),
                        "video_path": "video.mp4",
                        "media": {
                            "path": "video.mp4",
                            "duration_seconds": 1.0,
                            "width": None,
                            "height": None,
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
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            update_report_files(report_md, "## 主线\n\n新总结")

            payload = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary_text"], "## 主线\n\n新总结")
            persisted_json = json.dumps(payload, ensure_ascii=False)
            self.assertNotIn("alice", persisted_json)
            self.assertNotIn("private", persisted_json)
            self.assertIn("## 主线", report_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
