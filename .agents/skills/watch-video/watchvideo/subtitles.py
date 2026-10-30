from __future__ import annotations

from pathlib import Path
import re

from .models import SubtitleCue

TIMESTAMP_PATTERN = r"(?:\d{2,}:\d{2}:\d{2}|\d{2}:\d{2})[,.]\d{3}"
TIME_PATTERN = re.compile(
    rf"(?P<start>{TIMESTAMP_PATTERN})\s*-->\s*(?P<end>{TIMESTAMP_PATTERN})"
)
TAG_PATTERN = re.compile(r"<[^>]+>")


def parse_timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = "0"
        minutes, rest = parts
    elif len(parts) == 3:
        hours, minutes, rest = parts
    else:
        raise ValueError(f"无效字幕时间戳: {value}")
    seconds, millis = rest.split(".")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def clean_subtitle_text(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines if line.strip())
    text = TAG_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_srt(content: str) -> list[SubtitleCue]:
    return _parse_cue_blocks(content)


def parse_vtt(content: str) -> list[SubtitleCue]:
    lines = content.replace("\ufeff", "").splitlines()
    without_header = "\n".join(line for line in lines if line.strip() != "WEBVTT")
    return _parse_cue_blocks(without_header)


def load_subtitle_file(path: Path) -> list[SubtitleCue]:
    content = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".vtt" or content.lstrip().startswith("WEBVTT"):
        return parse_vtt(content)
    return parse_srt(content)


def collect_subtitle_files(
    directory: Path,
    stem: str | None = None,
    languages: list[str] | None = None,
) -> list[Path]:
    # 函数职责：只收集目标视频的字幕，并按调用方语言优先级返回。
    patterns = ["*.srt", "*.vtt"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(directory.glob(pattern))
    if stem:
        files = [
            path
            for path in files
            if path.stem == stem or path.stem.startswith(f"{stem}.")
        ]
    return sorted(
        set(files),
        key=lambda path: (_subtitle_language_rank(path, languages or [], stem), path.name),
    )


def cues_to_plain_text(cues: list[SubtitleCue]) -> str:
    lines: list[str] = []
    previous = None
    for cue in cues:
        text = cue.text.strip()
        if text and text != previous:
            lines.append(text)
            previous = text
    return "\n".join(lines)


def _parse_cue_blocks(content: str) -> list[SubtitleCue]:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n{2,}", normalized.strip())
    cues: list[SubtitleCue] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        time_index = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if time_index is None:
            continue

        match = TIME_PATTERN.search(lines[time_index])
        if not match:
            continue

        text = clean_subtitle_text(lines[time_index + 1 :])
        if not text:
            continue

        cues.append(
            SubtitleCue(
                start_seconds=parse_timestamp(match.group("start")),
                end_seconds=parse_timestamp(match.group("end")),
                text=text,
            )
        )
    return cues


def _subtitle_language_rank(path: Path, languages: list[str], stem: str | None) -> int:
    subtitle_stem = path.stem.lower()
    if stem and subtitle_stem.startswith(f"{stem.lower()}."):
        language_part = subtitle_stem[len(stem) + 1 :]
    elif stem and subtitle_stem == stem.lower():
        language_part = ""
    else:
        language_part = subtitle_stem

    for index, pattern in enumerate(languages):
        language = pattern.lower().strip()
        if language.endswith(".*"):
            language = language[:-2]
        elif language.endswith("*"):
            language = language[:-1].rstrip(".-_")
        if not language:
            continue
        marker = re.compile(rf"(?:^|[.]){re.escape(language)}(?:$|[.\-_])")
        if marker.search(language_part):
            return index
    return len(languages)
