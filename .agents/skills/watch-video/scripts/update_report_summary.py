#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile


# 函数职责和边界：脚本可从任意工作目录运行，始终使用同仓库的报告 schema。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from watchvideo.models import (  # noqa: E402
    REPORT_SCHEMA_VERSION,
    parse_report_json,
    redact_sensitive_urls,
    sanitize_persisted_value,
)
from watchvideo.cli import _output_lock  # noqa: E402


SUMMARY_HEADING = "## 视频内容总结"
SUMMARY_START_MARKER = "<!-- watchvideo:summary:start -->"
SUMMARY_END_MARKER = "<!-- watchvideo:summary:end -->"
FALLBACK_HEADINGS = (
    "## 时间线速览",
    "## 关键帧",
    "## OCR 文本",
    "## 字幕/转写文本",
)


def replace_summary(report_text: str, summary: str) -> str:
    """函数职责和边界：只替换报告总结区块，不改警告、关键帧和字幕内容。"""
    clean_summary = _sanitize_summary(summary)
    if not clean_summary:
        raise ValueError("summary must not be empty")

    replacement = (
        f"{SUMMARY_START_MARKER}\n{SUMMARY_HEADING}\n\n{clean_summary}\n\n"
        f"{SUMMARY_END_MARKER}\n\n"
    )
    marked_pattern = re.compile(
        rf"^{re.escape(SUMMARY_START_MARKER)}\s*$.*?"
        rf"^{re.escape(SUMMARY_END_MARKER)}\s*\n*",
        re.MULTILINE | re.DOTALL,
    )
    if marked_pattern.search(report_text):
        updated = marked_pattern.sub(replacement, report_text, count=1)
        return _normalize_trailing_newline(updated)

    legacy_pattern = _legacy_summary_pattern()
    if legacy_pattern.search(report_text):
        updated = legacy_pattern.sub(replacement, report_text, count=1)
        return _normalize_trailing_newline(updated)

    insertion_index = _find_insertion_index(report_text)
    if insertion_index is None:
        base = report_text.rstrip()
        return f"{base}\n\n{replacement}".rstrip() + "\n"

    prefix = report_text[:insertion_index].rstrip()
    suffix = report_text[insertion_index:].lstrip("\n")
    return f"{prefix}\n\n{replacement}{suffix}".rstrip() + "\n"


def _find_insertion_index(report_text: str) -> int | None:
    for heading in FALLBACK_HEADINGS:
        match = re.search(rf"^{re.escape(heading)}\s*$", report_text, re.MULTILINE)
        if match:
            return match.start()
    return None


def _legacy_summary_pattern() -> re.Pattern[str]:
    managed_heading = "|".join(re.escape(heading) for heading in FALLBACK_HEADINGS)
    return re.compile(
        rf"^{re.escape(SUMMARY_HEADING)}\s*$.*?(?=^(?:{managed_heading})\s*$|\Z)",
        re.MULTILINE | re.DOTALL,
    )


def _normalize_trailing_newline(text: str) -> str:
    return text.rstrip() + "\n"


def _sanitize_summary(summary: str) -> str:
    """函数职责和边界：脱敏总结并阻止正文伪造持久化区块标记。"""
    return (
        redact_sensitive_urls(summary.strip())
        .replace(SUMMARY_START_MARKER, "&lt;!-- watchvideo:summary:start --&gt;")
        .replace(SUMMARY_END_MARKER, "&lt;!-- watchvideo:summary:end --&gt;")
    )


def _read_summary(args: argparse.Namespace) -> str:
    if args.summary_file:
        return Path(args.summary_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise ValueError("provide --summary-file or pipe summary text through stdin")


def update_report_files(report_path: Path, summary: str) -> None:
    """函数职责和边界：幂等更新 Markdown，并在同目录存在 JSON 时同步 summary_text。"""
    with _output_lock(report_path.parent):
        _update_report_files_locked(report_path, summary)


def _update_report_files_locked(report_path: Path, summary: str) -> None:
    """函数职责和边界：调用方持有输出锁后，校验并原子替换报告文件。"""
    report_text = report_path.read_text(encoding="utf-8")
    clean_summary = _sanitize_summary(summary)
    updated_markdown = redact_sensitive_urls(replace_summary(report_text, clean_summary))

    json_path = report_path.with_name("report.json")
    json_text: str | None = None
    if json_path.exists():
        payload = parse_report_json(
            json_path.read_text(encoding="utf-8"),
            allow_legacy=True,
        )
        payload["schema_version"] = REPORT_SCHEMA_VERSION
        payload["summary_text"] = clean_summary
        payload = sanitize_persisted_value(payload)
        json_text = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ) + "\n"

    # 所有输入先完成解析和校验，避免 JSON 错误时只更新 Markdown。
    if json_text is not None:
        _atomic_write_text(json_path, json_text)
    _atomic_write_text(report_path, updated_markdown)


def _atomic_write_text(path: Path, content: str) -> None:
    """函数职责和边界：仅原子替换目标文本文件，并清理本次临时文件。"""
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update the 视频内容总结 section in a watchvideo report.md file."
    )
    parser.add_argument("report_md", help="Path to report.md")
    parser.add_argument("--summary-file", help="Markdown file containing final summary")
    args = parser.parse_args(argv)

    try:
        report_path = Path(args.report_md)
        summary = _read_summary(args)
        update_report_files(report_path, summary)
    except (OSError, ValueError) as exc:
        print(f"更新报告失败: {exc}", file=sys.stderr)
        return 2
    print(report_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
