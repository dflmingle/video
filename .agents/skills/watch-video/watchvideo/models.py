from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


REPORT_SCHEMA_VERSION = 1

_URL_PATTERN = re.compile(r"https?://[^\s`<>\"']+", re.IGNORECASE)
_URL_TRAILING_PUNCTUATION = ".,;:!?)]}，。；：！？）】"


def redact_sensitive_urls(text: str) -> str:
    """函数职责和边界：清除文本中 HTTP(S) URL 的用户凭据和查询参数。"""

    def replace(match: re.Match[str]) -> str:
        candidate = match.group(0)
        url = candidate.rstrip(_URL_TRAILING_PUNCTUATION)
        trailing = candidate[len(url) :]

        def redact_entire_url() -> str:
            scheme = url.split(":", 1)[0].lower()
            return f"{scheme}://REDACTED{trailing}"

        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            if not hostname:
                return redact_entire_url() if "@" in url or "?" in url else candidate
            host = f"[{hostname}]" if ":" in hostname else hostname
            try:
                port = parsed.port
            except ValueError:
                port = None
            netloc = f"{host}:{port}" if port is not None else host
            query = "REDACTED" if parsed.query else ""
            fragment = "REDACTED" if parsed.fragment else ""
            return urlunsplit((parsed.scheme, netloc, parsed.path, query, fragment)) + trailing
        except ValueError:
            return redact_entire_url()

    return _URL_PATTERN.sub(replace, text)


def sanitize_persisted_value(value: Any) -> Any:
    """函数职责和边界：递归脱敏将要持久化的 JSON/Markdown 字符串。"""
    if isinstance(value, str):
        return redact_sensitive_urls(value)
    if isinstance(value, list):
        return [sanitize_persisted_value(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_persisted_value(item) for key, item in value.items()}
    return value


def parse_report_json(text: str, *, allow_legacy: bool = False) -> dict[str, Any]:
    """函数职责和边界：受控解析 report.json，拒绝无效 schema、类型和非有限数字。"""

    def reject_non_finite(value: str) -> None:
        raise ValueError(f"report.json 包含非有限数字: {value}")

    try:
        payload = json.loads(text, parse_constant=reject_non_finite)
    except json.JSONDecodeError as error:
        raise ValueError(f"report.json 不是有效 JSON: {error.msg}") from error
    except RecursionError as error:
        raise ValueError("report.json 嵌套层级过深") from error
    if not isinstance(payload, dict):
        raise ValueError("report.json 顶层必须是对象")

    if allow_legacy and "schema_version" not in payload:
        payload = {"schema_version": REPORT_SCHEMA_VERSION, **payload}
    validate_report_dict(payload)
    return payload


def validate_report_dict(report: dict[str, Any]) -> None:
    """函数职责和边界：校验当前 report schema，不执行宽松类型转换。"""
    version = report.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError("report.json 缺少有效的 schema_version")
    if version != REPORT_SCHEMA_VERSION:
        raise ValueError(
            f"不支持的 report.json schema_version: {version}，"
            f"当前仅支持 {REPORT_SCHEMA_VERSION}"
        )

    source = _required_dict(report, "source")
    _required_string(source, "kind", "source")
    _required_string(source, "value", "source")
    _optional_string(source, "path", "source")
    _required_string(report, "work_dir", "report")
    _required_string(report, "video_path", "report")

    media = _required_dict(report, "media")
    _required_string(media, "path", "media")
    _optional_number(media, "duration_seconds", "media", minimum=0.0)
    _optional_integer(media, "width", "media", minimum=1)
    _optional_integer(media, "height", "media", minimum=1)

    _required_string(report, "transcript_text", "report")
    _required_string(report, "summary_text", "report")
    _validate_transcript_cues(_required_list(report, "transcript_cues"))
    _validate_keyframes(_required_list(report, "keyframes"))
    _validate_ocr_results(_required_list(report, "ocr_results"))
    _validate_string_list(_required_list(report, "subtitle_files"), "subtitle_files")
    _validate_download_attempts(_required_list(report, "download_attempts"))
    _validate_transcription_info(report.get("transcription_info"))
    _validate_cleanup_records(_required_list(report, "cleanup_records"))
    _validate_string_list(_required_list(report, "warnings"), "warnings")


def _required_dict(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    if not isinstance(item, dict):
        raise ValueError(f"report.json 字段 {key} 必须是对象")
    return item


def _required_list(value: dict[str, Any], key: str) -> list[Any]:
    item = value.get(key)
    if not isinstance(item, list):
        raise ValueError(f"report.json 字段 {key} 必须是数组")
    return item


def _required_string(value: dict[str, Any], key: str, parent: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"report.json 字段 {parent}.{key} 必须是字符串")
    return item


def _optional_string(value: dict[str, Any], key: str, parent: str) -> None:
    item = value.get(key)
    if item is not None and not isinstance(item, str):
        raise ValueError(f"report.json 字段 {parent}.{key} 必须是字符串或 null")


def _number(value: Any, field_name: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"report.json 字段 {field_name} 必须是数字")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"report.json 字段 {field_name} 必须是有限数字") from error
    if not math.isfinite(result):
        raise ValueError(f"report.json 字段 {field_name} 必须是有限数字")
    if minimum is not None and result < minimum:
        raise ValueError(f"report.json 字段 {field_name} 不能小于 {minimum:g}")
    return result


def _optional_number(
    value: dict[str, Any], key: str, parent: str, *, minimum: float | None = None
) -> None:
    item = value.get(key)
    if item is not None:
        _number(item, f"{parent}.{key}", minimum=minimum)


def _optional_integer(
    value: dict[str, Any], key: str, parent: str, *, minimum: int | None = None
) -> None:
    item = value.get(key)
    if item is None:
        return
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"report.json 字段 {parent}.{key} 必须是整数或 null")
    if minimum is not None and item < minimum:
        raise ValueError(f"report.json 字段 {parent}.{key} 不能小于 {minimum}")


def _validate_transcript_cues(items: list[Any]) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"report.json 字段 transcript_cues[{index}] 必须是对象")
        start = _number(
            item.get("start_seconds"),
            f"transcript_cues[{index}].start_seconds",
            minimum=0.0,
        )
        end = _number(
            item.get("end_seconds"),
            f"transcript_cues[{index}].end_seconds",
            minimum=0.0,
        )
        if end < start:
            raise ValueError(f"report.json 字段 transcript_cues[{index}] 结束时间早于开始时间")
        _required_string(item, "text", f"transcript_cues[{index}]")


def _validate_keyframes(items: list[Any]) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"report.json 字段 keyframes[{index}] 必须是对象")
        _required_string(item, "path", f"keyframes[{index}]")
        _number(
            item.get("timestamp_seconds"),
            f"keyframes[{index}].timestamp_seconds",
            minimum=0.0,
        )
        _number(item.get("score"), f"keyframes[{index}].score")


def _validate_ocr_results(items: list[Any]) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"report.json 字段 ocr_results[{index}] 必须是对象")
        _required_string(item, "frame_path", f"ocr_results[{index}]")
        _number(
            item.get("timestamp_seconds"),
            f"ocr_results[{index}].timestamp_seconds",
            minimum=0.0,
        )
        _required_string(item, "text", f"ocr_results[{index}]")


def _validate_string_list(items: list[Any], field_name: str) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, str):
            raise ValueError(f"report.json 字段 {field_name}[{index}] 必须是字符串")


def _validate_download_attempts(items: list[Any]) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"report.json 字段 download_attempts[{index}] 必须是对象")
        for key in ("step", "status", "detail"):
            _required_string(item, key, f"download_attempts[{index}]")


def _validate_transcription_info(item: Any) -> None:
    if item is None:
        return
    if not isinstance(item, dict):
        raise ValueError("report.json 字段 transcription_info 必须是对象或 null")
    _required_string(item, "source", "transcription_info")
    _optional_string(item, "model", "transcription_info")
    _optional_string(item, "language", "transcription_info")
    if not isinstance(item.get("prompt_used"), bool):
        raise ValueError("report.json 字段 transcription_info.prompt_used 必须是布尔值")
    _validate_string_list(
        _required_list(item, "transcript_files"),
        "transcription_info.transcript_files",
    )


def _validate_cleanup_records(items: list[Any]) -> None:
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"report.json 字段 cleanup_records[{index}] 必须是对象")
        for key in ("target", "path", "status", "detail"):
            _required_string(item, key, f"cleanup_records[{index}]")


@dataclass(frozen=True)
class Source:
    kind: str
    value: str
    path: Path | None = None


@dataclass(frozen=True)
class ToolStatus:
    name: str
    path: str | None
    version: str | None = None

    @property
    def available(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration_seconds: float | None
    width: int | None = None
    height: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubtitleCue:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class Keyframe:
    path: Path
    timestamp_seconds: float
    score: float


@dataclass(frozen=True)
class OcrResult:
    frame_path: Path
    timestamp_seconds: float
    text: str


@dataclass(frozen=True)
class DownloadAttempt:
    step: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class TranscriptionInfo:
    source: str
    model: str | None = None
    language: str | None = None
    prompt_used: bool = False
    transcript_files: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class CleanupRecord:
    target: str
    path: Path
    status: str
    detail: str = ""


@dataclass(frozen=True)
class AnalysisReport:
    source: Source
    work_dir: Path
    video_path: Path
    media: MediaInfo
    transcript_cues: list[SubtitleCue]
    transcript_text: str
    keyframes: list[Keyframe]
    summary_text: str = ""
    ocr_results: list[OcrResult] = field(default_factory=list)
    subtitle_files: list[Path] = field(default_factory=list)
    download_attempts: list[DownloadAttempt] = field(default_factory=list)
    transcription_info: TranscriptionInfo | None = None
    cleanup_records: list[CleanupRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        # 报告边界：只输出可 JSON 序列化的数据，不暴露内部对象。
        payload = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "source": {
                "kind": self.source.kind,
                "value": self.source.value,
                "path": str(self.source.path) if self.source.path else None,
            },
            "work_dir": str(self.work_dir),
            "video_path": str(self.video_path),
            "media": {
                "path": str(self.media.path),
                "duration_seconds": self.media.duration_seconds,
                "width": self.media.width,
                "height": self.media.height,
            },
            "transcript_text": self.transcript_text,
            "summary_text": self.summary_text,
            "transcript_cues": [
                {
                    "start_seconds": cue.start_seconds,
                    "end_seconds": cue.end_seconds,
                    "text": cue.text,
                }
                for cue in self.transcript_cues
            ],
            "keyframes": [
                {
                    "path": str(frame.path),
                    "timestamp_seconds": frame.timestamp_seconds,
                    "score": frame.score,
                }
                for frame in self.keyframes
            ],
            "ocr_results": [
                {
                    "frame_path": str(result.frame_path),
                    "timestamp_seconds": result.timestamp_seconds,
                    "text": result.text,
                }
                for result in self.ocr_results
            ],
            "subtitle_files": [str(path) for path in self.subtitle_files],
            "download_attempts": [
                {
                    "step": attempt.step,
                    "status": attempt.status,
                    "detail": attempt.detail,
                }
                for attempt in self.download_attempts
            ],
            "transcription_info": (
                {
                    "source": self.transcription_info.source,
                    "model": self.transcription_info.model,
                    "language": self.transcription_info.language,
                    "prompt_used": self.transcription_info.prompt_used,
                    "transcript_files": [
                        str(path) for path in self.transcription_info.transcript_files
                    ],
                }
                if self.transcription_info
                else None
            ),
            "cleanup_records": [
                {
                    "target": record.target,
                    "path": str(record.path),
                    "status": record.status,
                    "detail": record.detail,
                }
                for record in self.cleanup_records
            ],
            "warnings": self.warnings,
        }
        return sanitize_persisted_value(payload)
