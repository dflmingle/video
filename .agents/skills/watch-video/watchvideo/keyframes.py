from __future__ import annotations

import binascii
from dataclasses import dataclass
import math
from pathlib import Path
import struct
import zlib


DEFAULT_MAX_KEYFRAMES = 80


@dataclass(frozen=True)
class PpmImage:
    width: int
    height: int
    pixels: bytes


def candidate_timestamps(
    duration_seconds: float,
    interval_seconds: float = 10.0,
    max_groups: int | None = None,
) -> list[list[float]]:
    if not math.isfinite(duration_seconds):
        raise ValueError("duration_seconds 必须是有限数")
    if duration_seconds <= 0:
        return []
    if not math.isfinite(interval_seconds) or interval_seconds <= 0:
        raise ValueError("interval_seconds 必须大于 0")
    if max_groups is not None and max_groups <= 0:
        raise ValueError("max_groups 必须大于 0")

    groups: list[list[float]] = []
    total_groups = math.ceil(duration_seconds / interval_seconds)
    if max_groups is None or total_groups <= max_groups:
        indexes = list(range(total_groups))
    elif max_groups == 1:
        indexes = [total_groups // 2]
    else:
        # 采样预算边界：均匀覆盖完整时间线，避免只处理长视频开头。
        indexes = [
            round(position * (total_groups - 1) / (max_groups - 1))
            for position in range(max_groups)
        ]

    for group_index in indexes:
        start = group_index * interval_seconds
        end = min(duration_seconds, start + interval_seconds)
        span = end - start
        margin = 0.75 if span >= 1.5 else span / 4
        group = [start + margin, start + span / 2, end - margin]
        groups.append([round(timestamp, 3) for timestamp in group])
    return groups


def parse_ppm(data: bytes) -> PpmImage:
    # PPM 解析边界：只支持 ffmpeg 输出的 P6 二进制格式，用于清晰度评分。
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 4:
        while index < len(data) and chr(data[index]).isspace():
            index += 1
        if index < len(data) and data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] != b"\n":
                index += 1
            continue
        start = index
        while index < len(data) and not chr(data[index]).isspace():
            index += 1
        tokens.append(data[start:index])

    magic, width, height, max_value = tokens
    if magic != b"P6" or max_value != b"255":
        raise ValueError("只支持 P6/255 PPM 图片")
    if index >= len(data) or not chr(data[index]).isspace():
        raise ValueError("PPM header 缺少像素分隔符")

    # 函数职责：只消费 header 与像素之间的分隔符，
    # 不把像素里的空白字节当作 header 空白。
    index += 2 if data[index:index + 2] == b"\r\n" else 1

    width_int = int(width)
    height_int = int(height)
    expected = width_int * height_int * 3
    pixels = data[index:index + expected]
    if len(pixels) != expected:
        raise ValueError("PPM 像素数据不完整")
    return PpmImage(width=width_int, height=height_int, pixels=pixels)


def score_ppm_sharpness(data: bytes) -> float:
    image = parse_ppm(data)
    if image.width < 2 or image.height < 2:
        return 0.0

    gray = [
        int(
            0.299 * image.pixels[i]
            + 0.587 * image.pixels[i + 1]
            + 0.114 * image.pixels[i + 2]
        )
        for i in range(0, len(image.pixels), 3)
    ]

    total = 0
    count = 0
    for y in range(image.height):
        row = y * image.width
        for x in range(image.width):
            current = gray[row + x]
            if x + 1 < image.width:
                total += abs(current - gray[row + x + 1])
                count += 1
            if y + 1 < image.height:
                total += abs(current - gray[row + image.width + x])
                count += 1
    return total / count if count else 0.0


def is_similar_ppm(left: bytes, right: bytes, threshold: float = 3.0) -> bool:
    left_image = parse_ppm(left)
    right_image = parse_ppm(right)
    if left_image.width != right_image.width or left_image.height != right_image.height:
        return False

    total = 0.0
    count = 0
    for index in range(0, len(left_image.pixels), 3):
        left_gray = (
            0.299 * left_image.pixels[index]
            + 0.587 * left_image.pixels[index + 1]
            + 0.114 * left_image.pixels[index + 2]
        )
        right_gray = (
            0.299 * right_image.pixels[index]
            + 0.587 * right_image.pixels[index + 1]
            + 0.114 * right_image.pixels[index + 2]
        )
        total += abs(left_gray - right_gray)
        count += 1
    return (total / count if count else 0.0) <= threshold


def perceptual_hash_ppm(data: bytes, hash_width: int = 9, hash_height: int = 8) -> int:
    """函数职责和边界：生成低成本 dHash，只用于关键帧近似去重。"""
    if hash_width < 2 or hash_height < 1:
        raise ValueError("dHash 尺寸无效")
    image = parse_ppm(data)
    if image.width < 2 or image.height < 1:
        return 0

    xs = [round(index * (image.width - 1) / (hash_width - 1)) for index in range(hash_width)]
    ys = [round(index * (image.height - 1) / max(1, hash_height - 1)) for index in range(hash_height)]
    result = 0
    for y in ys:
        row = y * image.width
        previous: float | None = None
        for x in xs:
            offset = (row + x) * 3
            gray = (
                0.299 * image.pixels[offset]
                + 0.587 * image.pixels[offset + 1]
                + 0.114 * image.pixels[offset + 2]
            )
            if previous is not None:
                result = (result << 1) | int(previous < gray)
            previous = gray
    return result


def hash_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def write_ppm_png(data: bytes, output_path: Path) -> None:
    """函数职责和边界：把 ffmpeg 的 P6 PPM 候选无损写为 PNG，不再次启动 ffmpeg。"""
    image = parse_ppm(data)
    scanlines = b"".join(
        b"\x00" + image.pixels[row * image.width * 3 : (row + 1) * image.width * 3]
        for row in range(image.height)
    )
    header = struct.pack(">IIBBBBB", image.width, image.height, 8, 2, 0, 0, 0)
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=6))
        + _png_chunk(b"IEND", b"")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)
