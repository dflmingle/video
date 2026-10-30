from __future__ import annotations

import html
import ipaddress
import json
import math
from pathlib import Path
import re
import socket
from urllib.parse import unquote, urlparse
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .commands import CommandError, CommandRunner
from .models import DownloadAttempt
from .subtitles import collect_subtitle_files


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}
DIRECT_VIDEO_NAME = "share-page-play-addr.mp4"
AUTO_COOKIE_BROWSERS = ("chrome", "chromium", "edge", "firefox")
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DEFAULT_PAGE_TIMEOUT_SECONDS = 30
DEFAULT_VIDEO_TIMEOUT_SECONDS = 60
DEFAULT_MAX_PAGE_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_VIDEO_BYTES = 2 * 1024 * 1024 * 1024
YT_DLP_MAX_FILESIZE = "2G"
VIDEO_SNIFF_BYTES = 1024 * 1024


class _ValidatingRedirectHandler(HTTPRedirectHandler):
    # 重定向边界：在 urllib 发出下一跳请求前重新校验目标主机。
    def __init__(self, validate_url):
        super().__init__()
        self.validate_url = validate_url

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.validate_url(urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class SharePageClient:
    def __init__(
        self,
        page_timeout_seconds: float = DEFAULT_PAGE_TIMEOUT_SECONDS,
        video_timeout_seconds: float = DEFAULT_VIDEO_TIMEOUT_SECONDS,
        max_page_bytes: int = DEFAULT_MAX_PAGE_BYTES,
        max_video_bytes: int = DEFAULT_MAX_VIDEO_BYTES,
        resolver=None,
        opener=None,
    ):
        if not math.isfinite(page_timeout_seconds) or page_timeout_seconds <= 0:
            raise ValueError("page_timeout_seconds 必须是有限正数")
        if not math.isfinite(video_timeout_seconds) or video_timeout_seconds <= 0:
            raise ValueError("video_timeout_seconds 必须是有限正数")
        if max_page_bytes <= 0 or max_video_bytes <= 0:
            raise ValueError("下载大小上限必须大于 0")
        self.page_timeout_seconds = page_timeout_seconds
        self.video_timeout_seconds = video_timeout_seconds
        self.max_page_bytes = max_page_bytes
        self.max_video_bytes = max_video_bytes
        self.resolver = resolver or socket.getaddrinfo
        self.opener = opener or build_opener(
            _ValidatingRedirectHandler(self._validate_remote_url)
        )

    def fetch_text(self, url: str) -> str:
        self._validate_remote_url(url)
        request = Request(
            url,
            headers={
                "User-Agent": MOBILE_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with self.opener.open(request, timeout=self.page_timeout_seconds) as response:
            self._validate_remote_url(response.geturl() or url)
            raw = _read_response_with_limit(response, self.max_page_bytes, "分享页")
        return raw.decode("utf-8", errors="replace")

    def download(self, url: str, output_path: Path, referer: str | None = None) -> str:
        self._validate_remote_url(url)
        headers = {
            "User-Agent": MOBILE_USER_AGENT,
            "Accept": "video/*,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = referer
        request = Request(
            url,
            headers=headers,
        )
        try:
            with self.opener.open(request, timeout=self.video_timeout_seconds) as response:
                final_url = response.geturl() or url
                self._validate_remote_url(final_url)
                _check_content_length(response, self.max_video_bytes, "视频")
                _validate_video_content_type(response)
                first_chunk = response.read(min(VIDEO_SNIFF_BYTES, self.max_video_bytes + 1))
                written = len(first_chunk)
                if written > self.max_video_bytes:
                    raise OSError(f"视频超过大小上限 {self.max_video_bytes} 字节")
                _validate_video_container_prefix(first_chunk)
                with output_path.open("wb") as handle:
                    handle.write(first_chunk)
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > self.max_video_bytes:
                            raise OSError(f"视频超过大小上限 {self.max_video_bytes} 字节")
                        handle.write(chunk)
                return final_url
        except BaseException:
            output_path.unlink(missing_ok=True)
            raise

    def _validate_remote_url(self, url: str) -> None:
        _validate_public_network_url(url, self.resolver)


class YtDlpClient:
    def __init__(
        self,
        runner: CommandRunner | None = None,
        executable: str = "yt-dlp",
        page_client: SharePageClient | None = None,
        cookies_from_browser: str | None = "chrome",
    ):
        self.runner = runner or CommandRunner()
        self.executable = executable
        self.page_client = page_client or SharePageClient()
        self.cookies_from_browser = cookies_from_browser
        self.download_attempts: list[DownloadAttempt] = []

    def fetch_subtitles(
        self,
        url: str,
        output_dir: Path,
        languages: list[str],
    ) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        language_arg = ",".join(languages or ["zh.*", "en.*"])
        before = set(collect_subtitle_files(output_dir))
        try:
            self._run_yt_dlp_subtitles(url, output_dir, language_arg)
        except (CommandError, FileNotFoundError, OSError) as exc:
            if not (_is_cookie_error(exc) and self.cookies_from_browser):
                raise
            last_error: Exception = exc
            for browser in self._cookie_browsers():
                try:
                    self._run_yt_dlp_subtitles(
                        url,
                        output_dir,
                        language_arg,
                        cookies_from_browser=browser,
                    )
                    break
                except (CommandError, FileNotFoundError, OSError) as cookie_exc:
                    last_error = cookie_exc
            else:
                raise last_error

        new_files = set(collect_subtitle_files(output_dir)) - before
        return sorted(
            new_files,
            key=lambda path: (
                _subtitle_language_rank_for_download(path, languages),
                path.name,
            ),
        )

    def fetch_remote(self, url: str, output_dir: Path, max_height: int | None = 1080) -> Path:
        self.download_attempts = []
        output_dir.mkdir(parents=True, exist_ok=True)
        before_files = _directory_files(output_dir)
        before = _media_files(output_dir)
        format_selector = "bv*+ba/b"
        if max_height:
            format_selector = f"bv*[height<={max_height}]+ba/b[height<={max_height}]"

        try:
            self._run_yt_dlp_video(url, output_dir, format_selector)
            return self._latest_downloaded_media(
                output_dir=output_dir,
                before=before,
                step="plain yt-dlp",
            )
        except (CommandError, FileNotFoundError, OSError) as exc:
            _remove_files_created_since(output_dir, before_files)
            self._record_download_attempt("plain yt-dlp", "failed", exc)
            original_error = exc
            if _is_cookie_error(exc) and self.cookies_from_browser:
                for browser in self._cookie_browsers():
                    try:
                        self._run_yt_dlp_video(
                            url,
                            output_dir,
                            format_selector,
                            cookies_from_browser=browser,
                        )
                        return self._latest_downloaded_media(
                            output_dir=output_dir,
                            before=before,
                            step=f"yt-dlp browser cookies ({browser})",
                        )
                    except (CommandError, FileNotFoundError, OSError) as cookie_exc:
                        _remove_files_created_since(output_dir, before_files)
                        self._record_download_attempt(
                            f"yt-dlp browser cookies ({browser})",
                            "failed",
                            cookie_exc,
                        )
                        original_error = cookie_exc
                    except BaseException:
                        _remove_files_created_since(output_dir, before_files)
                        raise
            elif _is_cookie_error(exc):
                self._record_download_attempt(
                    "yt-dlp browser cookies",
                    "skipped",
                    "browser cookies retry is disabled",
                )
            else:
                self._record_download_attempt(
                    "yt-dlp browser cookies",
                    "skipped",
                    "plain yt-dlp failure was not a cookie/login blocker",
                )

            try:
                return self._fetch_remote_from_share_page(
                    url,
                    output_dir,
                    original_error=original_error,
                )
            except (FileNotFoundError, OSError, ValueError):
                _remove_files_created_since(output_dir, before_files)
                raise
            except BaseException:
                _remove_files_created_since(output_dir, before_files)
                raise
        except BaseException:
            _remove_files_created_since(output_dir, before_files)
            raise

    def _latest_downloaded_media(
        self,
        output_dir: Path,
        before: set[Path],
        step: str,
    ) -> Path:
        after = _media_files(output_dir)
        new_files = sorted(after - before, key=lambda path: path.stat().st_mtime, reverse=True)
        if not new_files:
            raise FileNotFoundError("yt-dlp 执行结束，但没有找到下载后的视频文件")
        if new_files[0].stat().st_size > DEFAULT_MAX_VIDEO_BYTES:
            raise OSError(f"视频超过大小上限 {DEFAULT_MAX_VIDEO_BYTES} 字节")
        self._record_download_attempt(step, "ok", new_files[0].name)
        return new_files[0]

    def _run_yt_dlp_subtitles(
        self,
        url: str,
        output_dir: Path,
        language_arg: str,
        cookies_from_browser: str | None = None,
    ) -> None:
        command = [
            self.executable,
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            language_arg,
            "--convert-subs",
            "srt",
            "--skip-download",
            "--socket-timeout",
            str(DEFAULT_PAGE_TIMEOUT_SECONDS),
            "--retries",
            "3",
            "-P",
            str(output_dir),
            "-o",
            "%(title).200B.%(ext)s",
            url,
        ]
        if cookies_from_browser:
            command[1:1] = ["--cookies-from-browser", cookies_from_browser]
        self.runner.run(command)

    def _run_yt_dlp_video(
        self,
        url: str,
        output_dir: Path,
        format_selector: str,
        cookies_from_browser: str | None = None,
    ) -> None:
        command = [
            self.executable,
            "-f",
            format_selector,
            "--merge-output-format",
            "mp4",
            "--socket-timeout",
            str(DEFAULT_VIDEO_TIMEOUT_SECONDS),
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            "--max-filesize",
            YT_DLP_MAX_FILESIZE,
            "-P",
            str(output_dir),
            "-o",
            "%(title).200B.%(ext)s",
            url,
        ]
        if cookies_from_browser:
            command[1:1] = ["--cookies-from-browser", cookies_from_browser]
        self.runner.run(command)

    def _cookie_browsers(self) -> list[str]:
        if self.cookies_from_browser == "auto":
            return list(AUTO_COOKIE_BROWSERS)
        return [self.cookies_from_browser] if self.cookies_from_browser else []

    def _fetch_remote_from_share_page(self, url: str, output_dir: Path, original_error: Exception) -> Path:
        # 函数职责：只尝试公开分享页里的直链；浏览器 cookies 由 yt-dlp 路径读取。
        try:
            page_html = self.page_client.fetch_text(url)
        except (OSError, ValueError) as exc:
            self._record_download_attempt("mobile share page", "failed", exc)
            raise self._download_failure(original_error, exc) from exc

        self._record_download_attempt("mobile share page", "ok", f"{len(page_html)} chars")
        play_urls = extract_play_addr_urls(page_html)
        if not play_urls:
            exc = FileNotFoundError("分享页没有发现 play_addr 视频直链")
            self._record_download_attempt("mobile share page play_addr", "failed", exc)
            raise self._download_failure(original_error, exc) from exc

        self._record_download_attempt(
            "mobile share page play_addr",
            "ok",
            f"{len(play_urls)} candidate(s)",
        )
        output_path = output_dir / DIRECT_VIDEO_NAME
        part_path = output_path.with_name(f"{output_path.name}.part")
        last_error: Exception | None = None
        for index, play_url in enumerate(play_urls, start=1):
            part_path.unlink(missing_ok=True)
            try:
                final_url = self.page_client.download(play_url, part_path, referer=url)
                if not part_path.is_file() or part_path.stat().st_size <= 0:
                    raise FileNotFoundError("play_addr 下载结束，但没有生成有效视频文件")
                if part_path.stat().st_size > DEFAULT_MAX_VIDEO_BYTES:
                    raise OSError(f"视频超过大小上限 {DEFAULT_MAX_VIDEO_BYTES} 字节")
                part_path.replace(output_path)
                detail = output_path.name
                if final_url and final_url != play_url:
                    detail = f"{output_path.name} via {final_url}"
                self._record_download_attempt("direct video download", "ok", detail)
                return output_path
            except (FileNotFoundError, OSError, ValueError) as exc:
                last_error = exc
                self._record_download_attempt(
                    f"direct video download candidate {index}",
                    "failed",
                    exc,
                )
            finally:
                part_path.unlink(missing_ok=True)

        assert last_error is not None
        self._record_download_attempt("direct video download", "failed", last_error)
        raise self._download_failure(original_error, last_error) from last_error

    def _download_failure(self, original_error: Exception, play_addr_error: Exception) -> FileNotFoundError:
        return FileNotFoundError(
            "视频下载失败：yt-dlp 下载失败，分享页/SSR play_addr 兜底也失败。"
            "已在需要时尝试直接读取浏览器 cookies；请提供本地视频文件或可访问直链。"
            f" yt-dlp: {_brief_error(original_error)}; play_addr: {_brief_error(play_addr_error)}"
        )

    def _record_download_attempt(self, step: str, status: str, detail: object = "") -> None:
        self.download_attempts.append(
            DownloadAttempt(step=step, status=status, detail=_brief_error(detail))
        )


def _media_files(directory: Path) -> set[Path]:
    return {
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    }


def _directory_files(directory: Path) -> set[Path]:
    return {path for path in directory.iterdir() if path.is_file()}


def _remove_files_created_since(directory: Path, before: set[Path]) -> None:
    # 清理边界：仅删除本次尝试新增的普通文件，保留调用方已有内容。
    for path in _directory_files(directory) - before:
        try:
            path.unlink()
        except OSError:
            pass


def extract_play_addr_urls(page_html: str) -> list[str]:
    normalized = _normalize_page_text(page_html)
    router_data_urls = _extract_router_data_play_urls(normalized)
    script_data_urls = _extract_script_data_play_urls(normalized)
    play_addr_urls = _extract_play_addr_url_list(normalized)
    urls = re.findall(r"https?://[^\"'<>\s\\]+", normalized)
    results: list[str] = []
    seen: set[str] = set()
    structured_urls = router_data_urls + script_data_urls + play_addr_urls
    for url in structured_urls:
        cleaned = url.rstrip("),;]")
        if cleaned in seen or not _looks_like_video_url(cleaned):
            continue
        seen.add(cleaned)
        results.append(cleaned)
    for url in urls:
        cleaned = url.rstrip("),;]")
        if cleaned in seen or not _looks_like_trusted_generic_video_url(cleaned):
            continue
        seen.add(cleaned)
        results.append(cleaned)
    return results


def _extract_play_addr_url_list(page_text: str) -> list[str]:
    # 函数职责：兜底抽取 play_addr 片段；结构化 _ROUTER_DATA 解析优先级更高。
    results: list[str] = []
    pattern = re.compile(
        r'"play_addr"\s*:\s*\{.*?"url_list"\s*:\s*\[(?P<urls>.*?)\]',
        flags=re.DOTALL,
    )
    for match in pattern.finditer(page_text):
        for raw_url in re.findall(r'"([^"]+)"', match.group("urls")):
            results.append(_normalize_page_text(raw_url))
    return results


def _extract_router_data_play_urls(page_text: str) -> list[str]:
    # 函数职责：只解析明确的 SSR 数据对象，避免页面其他 play_addr 噪声抢先。
    results: list[str] = []
    for router_data in _extract_json_objects_after_markers(
        page_text,
        (
            "window._ROUTER_DATA",
            "window.__ROUTER_DATA__",
            "window.SIGI_STATE",
            "window.__UNIVERSAL_DATA_FOR_REHYDRATION__",
        ),
    ):
        results.extend(_find_play_addr_urls(router_data))
    return results


def _extract_script_data_play_urls(page_text: str) -> list[str]:
    # 函数职责：解析 script 标签内的 SSR JSON，覆盖 RENDER_DATA 这类非 window 赋值。
    results: list[str] = []
    for script_data in _extract_json_objects_from_script_ids(
        page_text,
        ("RENDER_DATA", "__NEXT_DATA__", "SIGI_STATE"),
    ):
        results.extend(_find_play_addr_urls(script_data))
    return results


def _extract_json_objects_after_markers(page_text: str, markers: tuple[str, ...]) -> list[object]:
    results: list[object] = []
    for marker in markers:
        start = 0
        while True:
            marker_index = page_text.find(marker, start)
            if marker_index < 0:
                break
            brace_index = page_text.find("{", marker_index + len(marker))
            if brace_index < 0:
                break
            json_text = _balanced_json_object(page_text, brace_index)
            if json_text:
                try:
                    results.append(json.loads(json_text))
                except json.JSONDecodeError:
                    pass
            start = marker_index + len(marker)
    return results


def _extract_json_objects_from_script_ids(page_text: str, script_ids: tuple[str, ...]) -> list[object]:
    results: list[object] = []
    for script_id in script_ids:
        pattern = re.compile(
            rf"<script\b[^>]*\bid=[\"']{re.escape(script_id)}[\"'][^>]*>(?P<body>.*?)</script>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(page_text):
            parsed = _parse_json_object_text(match.group("body"))
            if parsed is not None:
                results.append(parsed)
    return results


def _parse_json_object_text(text: str) -> object | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        brace_index = stripped.find("{")
        if brace_index < 0:
            return None
        json_text = _balanced_json_object(stripped, brace_index)
        if not json_text:
            return None
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None


def _balanced_json_object(text: str, open_index: int) -> str | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[open_index : index + 1]
    return None


def _find_play_addr_urls(value: object) -> list[str]:
    results: list[str] = []
    if isinstance(value, dict):
        play_addr = value.get("play_addr")
        if isinstance(play_addr, dict):
            results.extend(_url_list_values(play_addr))
        for child in value.values():
            results.extend(_find_play_addr_urls(child))
    elif isinstance(value, list):
        for child in value:
            results.extend(_find_play_addr_urls(child))
    return results


def _url_list_values(value: dict[object, object]) -> list[str]:
    url_list = value.get("url_list")
    if not isinstance(url_list, list):
        return []
    return [_normalize_page_text(item) for item in url_list if isinstance(item, str)]


def _normalize_page_text(page_html: str) -> str:
    normalized = html.unescape(page_html)
    normalized = unquote(normalized)
    replacements = {
        "\\/": "/",
        "\\u0026": "&",
        "\\u003d": "=",
        "\\u003f": "?",
        "\\u002F": "/",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


def _looks_like_video_url(url: str) -> bool:
    if not _is_safe_direct_url(url):
        return False
    lower = url.lower()
    return (
        ".mp4" in lower
        or "douyinvod.com" in lower
        or "bytevideo" in lower
        or "snssdk.com/aweme/v1/play" in lower
        or "/video/tos/" in lower
        or "playwm" in lower
    )


def _looks_like_trusted_generic_video_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    trusted_host = (
        _host_matches_domain(hostname, "douyinvod.com")
        or _host_matches_domain(hostname, "bytevideo.com")
        or _host_matches_domain(hostname, "snssdk.com")
    )
    return trusted_host and _looks_like_video_url(url)


def _host_matches_domain(hostname: str, domain: str) -> bool:
    return hostname == domain or hostname.endswith(f".{domain}")


def _is_safe_direct_url(url: str) -> bool:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not hostname:
        return False
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not _is_non_public_address(address)


def _subtitle_language_rank_for_download(path: Path, languages: list[str]) -> int:
    stem = path.stem.lower()
    for index, pattern in enumerate(languages):
        language = pattern.lower().strip()
        if language.endswith(".*"):
            language = language[:-2]
        elif language.endswith("*"):
            language = language[:-1].rstrip(".-_")
        if language and re.search(
            rf"(?:^|[.]){re.escape(language)}(?:$|[.\-_])",
            stem,
        ):
            return index
    return len(languages)


def _content_length(response: object) -> int | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    raw = headers.get("Content-Length")
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _check_content_length(response: object, limit: int, label: str) -> None:
    length = _content_length(response)
    if length is not None and length > limit:
        raise OSError(f"{label}超过大小上限 {limit} 字节")


def _read_response_with_limit(response: object, limit: int, label: str) -> bytes:
    _check_content_length(response, limit, label)
    raw = response.read(limit + 1)
    if len(raw) > limit:
        raise OSError(f"{label}超过大小上限 {limit} 字节")
    return raw


def _validate_public_network_url(url: str, resolver) -> None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise OSError("只允许访问带有效主机名的 HTTP/HTTPS URL")
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise OSError(f"URL 主机解析到非公网地址: {hostname}")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise OSError(f"URL 端口无效: {url}") from exc
    try:
        address_infos = resolver(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise OSError(f"URL 主机 DNS 解析失败: {hostname}: {exc}") from exc
    if not address_infos:
        raise OSError(f"URL 主机 DNS 没有返回地址: {hostname}")

    checked = 0
    for address_info in address_infos:
        socket_address = address_info[4]
        if not socket_address:
            continue
        raw_address = str(socket_address[0]).split("%", 1)[0]
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise OSError(f"URL 主机 DNS 返回无效地址: {raw_address}") from exc
        checked += 1
        if _is_non_public_address(address):
            raise OSError(f"URL 主机解析到非公网地址: {hostname} -> {address}")
    if checked == 0:
        raise OSError(f"URL 主机 DNS 没有返回可验证地址: {hostname}")


def _is_non_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _header_value(response: object, name: str) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        return ""
    return str(headers.get(name) or "").strip()


def _validate_video_content_type(response: object) -> None:
    content_type = _header_value(response, "Content-Type").lower().split(";", 1)[0]
    if not content_type:
        return
    invalid = (
        content_type.startswith("text/")
        or content_type.endswith(("+json", "+xml"))
        or content_type
        in {
            "application/json",
            "application/javascript",
            "application/xml",
            "application/xhtml+xml",
        }
    )
    if invalid:
        raise OSError(f"视频响应的 Content-Type 无效: {content_type}")


def _validate_video_container_prefix(prefix: bytes) -> None:
    if not prefix:
        raise OSError("视频响应为空")
    if _has_known_video_container_signature(prefix):
        return
    stripped = prefix.lstrip(b"\xef\xbb\xbf\x00\t\r\n ").lower()
    if stripped.startswith(
        (
            b"<!doctype",
            b"<html",
            b"<head",
            b"<body",
            b"<?xml",
            b"{",
            b"[",
        )
    ):
        raise OSError("响应不是有效视频容器，检测到 HTML/JSON/XML 文本")
    raise OSError("响应没有可识别的视频容器签名")


def _has_known_video_container_signature(prefix: bytes) -> bool:
    if len(prefix) >= 12 and prefix[4:8] in {
        b"ftyp",
        b"moov",
        b"mdat",
        b"free",
        b"wide",
        b"styp",
        b"sidx",
        b"moof",
    }:
        return True
    if prefix.startswith((b"\x1aE\xdf\xa3", b"OggS", b"FLV", b"\x00\x00\x01\xba")):
        return True
    if len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"AVI ":
        return True
    if prefix.startswith(bytes.fromhex("3026b2758e66cf11a6d900aa0062ce6c")):
        return True
    if prefix.startswith((b"\x00\x00\x01\xb3", b"\x00\x00\x00\x01")):
        return True
    if len(prefix) >= 188 and prefix[0] == 0x47 and (
        len(prefix) == 188 or prefix[188] == 0x47
    ):
        return True
    return False


def _is_cookie_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "fresh cookies",
            "cookies",
            "sign in",
            "login",
            "not a bot",
            "authentication",
            "authenticated",
        )
    )


def _brief_error(error: object, limit: int = 240) -> str:
    if isinstance(error, CommandError):
        raw = error.result.stderr
        message = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
    else:
        message = str(error)
    compact = " ".join(message.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."
