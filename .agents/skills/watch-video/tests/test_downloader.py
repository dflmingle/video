from io import BytesIO
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from watchvideo.commands import CommandError, CommandResult
from watchvideo.downloader import SharePageClient, YtDlpClient, extract_play_addr_urls


class FailingRunner:
    def run(self, args, cwd=None, check=True, text=True):
        result = CommandResult(
            args=list(args),
            returncode=1,
            stdout="",
            stderr="fresh cookies required",
        )
        raise CommandError(result)


class SuccessWithoutOutputRunner:
    def run(self, args, cwd=None, check=True, text=True):
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


class PartialWritingFailingRunner:
    def run(self, args, cwd=None, check=True, text=True):
        output_dir = Path(args[args.index("-P") + 1])
        (output_dir / "new-video.mp4.part").write_bytes(b"partial")
        (output_dir / "new-video.mp4").write_bytes(b"incomplete")
        result = CommandResult(
            args=list(args),
            returncode=1,
            stdout="",
            stderr="network failed",
        )
        raise CommandError(result)


class InterruptedRunner:
    def run(self, args, cwd=None, check=True, text=True):
        output_dir = Path(args[args.index("-P") + 1])
        (output_dir / "interrupted.mp4.part").write_bytes(b"partial")
        raise KeyboardInterrupt


class RecordingRunner:
    def __init__(self):
        self.commands = []

    def run(self, args, cwd=None, check=True, text=True):
        self.commands.append(list(args))
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


class SubtitleCookieRunner:
    def __init__(self):
        self.commands = []

    def run(self, args, cwd=None, check=True, text=True):
        self.commands.append(list(args))
        if "--cookies-from-browser" not in args:
            result = CommandResult(
                args=list(args),
                returncode=1,
                stdout="",
                stderr="fresh cookies required",
            )
            raise CommandError(result)
        output_dir = Path(args[args.index("-P") + 1])
        (output_dir / "demo.en.srt").write_text("en", encoding="utf-8")
        (output_dir / "demo.zh-Hans.srt").write_text("zh", encoding="utf-8")
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


class CookieRetryRunner:
    def __init__(self):
        self.commands = []

    def run(self, args, cwd=None, check=True, text=True):
        self.commands.append(list(args))
        if "--cookies-from-browser" not in args:
            result = CommandResult(
                args=list(args),
                returncode=1,
                stdout="",
                stderr="Sign in to confirm you are not a bot. Use fresh cookies.",
            )
            raise CommandError(result)
        output_dir = Path(args[args.index("-P") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "cookie-video.mp4").write_bytes(b"mp4")
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


class CookieAutoFallbackRunner:
    def __init__(self):
        self.commands = []

    def run(self, args, cwd=None, check=True, text=True):
        self.commands.append(list(args))
        browser = _browser_from_args(args)
        if browser != "edge":
            result = CommandResult(
                args=list(args),
                returncode=1,
                stdout="",
                stderr="Fresh cookies are needed",
            )
            raise CommandError(result)
        output_dir = Path(args[args.index("-P") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "edge-cookie-video.mp4").write_bytes(b"mp4")
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


class FakeSharePageClient:
    def __init__(self, html="", video_bytes=b"video"):
        self.html = html
        self.video_bytes = video_bytes
        self.fetched_pages = []
        self.downloaded_urls = []
        self.downloaded_referers = []

    def fetch_text(self, url):
        self.fetched_pages.append(url)
        return self.html

    def download(self, url, output_path, referer=None):
        self.downloaded_urls.append(url)
        self.downloaded_referers.append(referer)
        Path(output_path).write_bytes(self.video_bytes)


class RedirectingSharePageClient(FakeSharePageClient):
    def __init__(self, html="", video_bytes=b"video", final_url="https://cdn.example.test/video.mp4"):
        super().__init__(html=html, video_bytes=video_bytes)
        self.final_url = final_url

    def download(self, url, output_path, referer=None):
        super().download(url, output_path, referer=referer)
        return self.final_url


class CandidateFallbackSharePageClient(FakeSharePageClient):
    def download(self, url, output_path, referer=None):
        self.downloaded_urls.append(url)
        self.downloaded_referers.append(referer)
        Path(output_path).write_bytes(b"partial" if "first" in url else b"complete")
        if "first" in url:
            raise OSError("first candidate failed")
        return url


class FakeUrlResponse(BytesIO):
    def __init__(self, content, headers=None, final_url="https://example.com/final"):
        super().__init__(content)
        self.headers = headers or {}
        self.final_url = final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def geturl(self):
        return self.final_url


class FakeUrlOpener:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def open(self, request, timeout=None):
        self.calls.append((request.full_url, timeout))
        return self.response


def _public_dns(host, port, *args, **kwargs):
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", port),
        )
    ]


def _browser_from_args(args):
    if "--cookies-from-browser" not in args:
        return None
    return args[args.index("--cookies-from-browser") + 1]


class DownloaderTests(unittest.TestCase):
    def test_share_page_client_rejects_invalid_resource_limits(self):
        invalid_options = (
            {"page_timeout_seconds": float("nan")},
            {"video_timeout_seconds": 0},
            {"max_page_bytes": 0},
            {"max_video_bytes": -1},
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    SharePageClient(**options)

    def test_share_page_client_limits_page_size_and_uses_configured_timeout(self):
        response = FakeUrlResponse(b"12345")
        opener = FakeUrlOpener(response)
        client = SharePageClient(
            page_timeout_seconds=7,
            max_page_bytes=4,
            resolver=_public_dns,
            opener=opener,
        )

        with self.assertRaisesRegex(OSError, "分享页超过大小上限"):
            client.fetch_text("https://example.com/share")

        self.assertEqual(opener.calls, [("https://example.com/share", 7)])

    def test_share_page_client_removes_partial_video_over_size_limit(self):
        response = FakeUrlResponse(b"12345")
        opener = FakeUrlOpener(response)
        client = SharePageClient(
            video_timeout_seconds=9,
            max_video_bytes=4,
            resolver=_public_dns,
            opener=opener,
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "video.part"
            with self.assertRaisesRegex(OSError, "视频超过大小上限"):
                client.download("https://example.com/video.mp4", output_path)

            self.assertFalse(output_path.exists())
        self.assertEqual(opener.calls, [("https://example.com/video.mp4", 9)])

    def test_share_page_client_rejects_hostname_resolving_to_private_network(self):
        opener = Mock()

        def private_dns(host, port, *args, **kwargs):
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    ("10.0.0.8", port),
                )
            ]

        client = SharePageClient(resolver=private_dns, opener=opener)

        with self.assertRaisesRegex(OSError, "非公网地址"):
            client.fetch_text("https://internal.example/share")

        opener.open.assert_not_called()

    def test_share_page_client_rejects_redirect_final_url_resolving_to_private_network(self):
        response = FakeUrlResponse(
            b"\x00\x00\x00\x18ftypisom",
            headers={"Content-Type": "video/mp4"},
            final_url="http://redirect.internal/video.mp4",
        )
        opener = FakeUrlOpener(response)

        def redirect_dns(host, port, *args, **kwargs):
            address = "10.0.0.9" if host == "redirect.internal" else "93.184.216.34"
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    socket.IPPROTO_TCP,
                    "",
                    (address, port),
                )
            ]

        client = SharePageClient(resolver=redirect_dns, opener=opener)

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "video.part"
            with self.assertRaisesRegex(OSError, "非公网地址"):
                client.download("https://public.example/video.mp4", output_path)
            self.assertFalse(output_path.exists())

    def test_share_page_client_rejects_html_content_type_and_cleans_output(self):
        response = FakeUrlResponse(
            b"<html><body>blocked</body></html>",
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        client = SharePageClient(
            resolver=_public_dns,
            opener=FakeUrlOpener(response),
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "video.part"
            with self.assertRaisesRegex(OSError, "Content-Type"):
                client.download("https://example.com/video.mp4", output_path)
            self.assertFalse(output_path.exists())

    def test_share_page_client_rejects_json_body_without_content_type(self):
        response = FakeUrlResponse(b'{"error":"not a video"}')
        client = SharePageClient(
            resolver=_public_dns,
            opener=FakeUrlOpener(response),
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "video.part"
            with self.assertRaisesRegex(OSError, "视频容器"):
                client.download("https://example.com/video.mp4", output_path)
            self.assertFalse(output_path.exists())

    def test_share_page_client_accepts_mp4_container_signature(self):
        body = b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42"
        response = FakeUrlResponse(body, headers={"Content-Type": "video/mp4"})
        client = SharePageClient(
            resolver=_public_dns,
            opener=FakeUrlOpener(response),
        )

        with TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "video.part"
            final_url = client.download("https://example.com/video.mp4", output_path)

            self.assertEqual(output_path.read_bytes(), body)
            self.assertEqual(final_url, "https://example.com/final")

    def test_extract_play_addr_urls_from_ssr_json(self):
        html = r'''
        <script id="RENDER_DATA">
        {"video":{"play_addr":{"url_list":["https:\/\/v3-web.douyinvod.com\/demo.mp4?x=1"]}}}
        </script>
        '''

        urls = extract_play_addr_urls(html)

        self.assertEqual(urls, ["https://v3-web.douyinvod.com/demo.mp4?x=1"])

    def test_extract_play_addr_urls_prioritizes_window_router_data(self):
        html = r'''
        <script>
        window.__noise = {
          "play_addr": {
            "url_list": ["https:\/\/v3-web.douyinvod.com\/noise.mp4"]
          }
        };
        </script>
        <script>
        window._ROUTER_DATA = {
          "loaderData": {
            "video_(id)/page": {
              "videoInfoRes": {
                "item_list": [
                  {
                    "video": {
                      "play_addr": {
                        "url_list": [
                          "https:\/\/aweme.snssdk.com\/aweme\/v1\/playwm\/?video_id=v0300&ratio=720p"
                        ]
                      }
                    }
                  }
                ]
              }
            }
          }
        };
        </script>
        '''

        urls = extract_play_addr_urls(html)

        self.assertEqual(
            urls[0],
            "https://aweme.snssdk.com/aweme/v1/playwm/?video_id=v0300&ratio=720p",
        )

    def test_extract_play_addr_urls_prioritizes_render_data_script(self):
        html = r'''
        <script>
        window.__noise = {
          "play_addr": {
            "url_list": ["https:\/\/v3-web.douyinvod.com\/noise.mp4"]
          }
        };
        </script>
        <script id="RENDER_DATA" type="application/json">
        %7B%22video%22%3A%7B%22play_addr%22%3A%7B%22url_list%22%3A%5B%22https%3A%5C%2F%5C%2Faweme.snssdk.com%5C%2Faweme%5C%2Fv1%5C%2Fplaywm%5C%2F%3Fvideo_id%3Dencoded%26ratio%3D720p%22%5D%7D%7D%7D
        </script>
        '''

        urls = extract_play_addr_urls(html)

        self.assertEqual(
            urls[0],
            "https://aweme.snssdk.com/aweme/v1/playwm/?video_id=encoded&ratio=720p",
        )

    def test_extract_play_addr_urls_does_not_accept_unrelated_generic_mp4(self):
        html = '<a href="https://example.com/tracking.mp4">tracking</a>'

        self.assertEqual(extract_play_addr_urls(html), [])

    def test_extract_play_addr_urls_rejects_private_network_candidate(self):
        html = r'{"play_addr":{"url_list":["http:\/\/127.0.0.1\/private.mp4"]}}'

        self.assertEqual(extract_play_addr_urls(html), [])

    def test_fetch_remote_does_not_fall_back_to_old_media(self):
        page_client = FakeSharePageClient(html="<html>no video</html>")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_video = root / "old.mp4"
            old_video.write_bytes(b"old")

            with self.assertRaises(FileNotFoundError):
                YtDlpClient(
                    runner=SuccessWithoutOutputRunner(),
                    page_client=page_client,
                    cookies_from_browser=None,
                ).fetch_remote("https://example.com/video", root)

            self.assertEqual(old_video.read_bytes(), b"old")

    def test_fetch_remote_failure_removes_only_files_created_by_current_attempt(self):
        page_client = FakeSharePageClient(html="<html>no video</html>")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_video = root / "old.mp4"
            old_video.write_bytes(b"old")

            with self.assertRaises(FileNotFoundError):
                YtDlpClient(
                    runner=PartialWritingFailingRunner(),
                    page_client=page_client,
                    cookies_from_browser=None,
                ).fetch_remote("https://example.com/video", root)

            self.assertEqual(old_video.read_bytes(), b"old")
            self.assertFalse((root / "new-video.mp4.part").exists())
            self.assertFalse((root / "new-video.mp4").exists())

    def test_fetch_remote_interrupt_removes_current_partial_download(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(KeyboardInterrupt):
                YtDlpClient(runner=InterruptedRunner()).fetch_remote(
                    "https://example.com/video",
                    root,
                )

            self.assertFalse((root / "interrupted.mp4.part").exists())

    def test_fetch_remote_uses_strict_max_height_selector_and_download_bounds(self):
        runner = RecordingRunner()
        page_client = FakeSharePageClient(html="<html>no video</html>")
        with TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                YtDlpClient(
                    runner=runner,
                    page_client=page_client,
                    cookies_from_browser=None,
                ).fetch_remote("https://example.com/video", Path(tmp), max_height=720)

        selector = runner.commands[0][runner.commands[0].index("-f") + 1]
        self.assertEqual(selector, "bv*[height<=720]+ba/b[height<=720]")
        self.assertIn("--socket-timeout", runner.commands[0])
        self.assertIn("--max-filesize", runner.commands[0])

    def test_fetch_subtitles_returns_only_new_files_in_language_priority_order(self):
        runner = SubtitleCookieRunner()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.zh.srt"
            old.write_text("old", encoding="utf-8")

            files = YtDlpClient(runner=runner).fetch_subtitles(
                "https://example.com/video",
                root,
                ["zh.*", "en.*"],
            )

        self.assertEqual([path.name for path in files], ["demo.zh-Hans.srt", "demo.en.srt"])
        self.assertEqual(_browser_from_args(runner.commands[1]), "chrome")

    def test_share_page_download_tries_all_candidates_and_uses_atomic_part_file(self):
        html = r'''{"play_addr":{"url_list":[
        "https:\/\/v3-web.douyinvod.com\/first.mp4",
        "https:\/\/v3-web.douyinvod.com\/second.mp4"
        ]}}'''
        page_client = CandidateFallbackSharePageClient(html=html)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_path = YtDlpClient(
                runner=FailingRunner(),
                page_client=page_client,
                cookies_from_browser=None,
            ).fetch_remote("https://www.douyin.com/share/video/123", root)

            self.assertEqual(video_path.read_bytes(), b"complete")
            self.assertFalse((root / "share-page-play-addr.mp4.part").exists())
        self.assertEqual(
            page_client.downloaded_urls,
            [
                "https://v3-web.douyinvod.com/first.mp4",
                "https://v3-web.douyinvod.com/second.mp4",
            ],
        )

    def test_fetch_remote_falls_back_to_share_page_play_addr_when_ytdlp_fails(self):
        html = r'{"play_addr":{"url_list":["https:\/\/v3-web.douyinvod.com\/fallback.mp4"]}}'
        page_client = FakeSharePageClient(html=html, video_bytes=b"mp4")

        with TemporaryDirectory() as tmp:
            video_path = YtDlpClient(
                runner=FailingRunner(),
                page_client=page_client,
            ).fetch_remote(
                "https://www.douyin.com/share/video/123",
                output_dir=Path(tmp),
            )

            self.assertEqual(video_path.name, "share-page-play-addr.mp4")
            self.assertEqual(video_path.read_bytes(), b"mp4")

        self.assertEqual(page_client.fetched_pages, ["https://www.douyin.com/share/video/123"])
        self.assertEqual(page_client.downloaded_urls, ["https://v3-web.douyinvod.com/fallback.mp4"])
        self.assertEqual(page_client.downloaded_referers, ["https://www.douyin.com/share/video/123"])

    def test_fetch_remote_fixture_covers_router_data_playwm_and_cdn_redirect(self):
        fixture = Path(__file__).parent / "fixtures" / "douyin_share_router_data.html"
        page_client = RedirectingSharePageClient(
            html=fixture.read_text(encoding="utf-8"),
            video_bytes=b"mp4",
            final_url="https://v26-cdn.example.test/obj/tos-cn-ve/redacted.mp4",
        )

        with TemporaryDirectory() as tmp:
            client = YtDlpClient(
                runner=FailingRunner(),
                page_client=page_client,
            )
            video_path = client.fetch_remote(
                "https://www.douyin.com/share/video/123",
                output_dir=Path(tmp),
            )

            self.assertEqual(video_path.name, "share-page-play-addr.mp4")
            self.assertEqual(video_path.read_bytes(), b"mp4")

        self.assertEqual(page_client.fetched_pages, ["https://www.douyin.com/share/video/123"])
        self.assertEqual(
            page_client.downloaded_urls,
            [
                "https://aweme.snssdk.com/aweme/v1/playwm/?video_id=v0300redacted&ratio=720p&line=0"
            ],
        )
        self.assertEqual(page_client.downloaded_referers, ["https://www.douyin.com/share/video/123"])
        attempts = [(attempt.step, attempt.status, attempt.detail) for attempt in client.download_attempts]
        self.assertIn(("mobile share page play_addr", "ok", "1 candidate(s)"), attempts)
        self.assertTrue(
            any(
                step == "direct video download"
                and status == "ok"
                and "v26-cdn.example.test" in detail
                and "share-page-play-addr.mp4" in detail
                for step, status, detail in attempts
            )
        )

    def test_fetch_remote_retries_with_chrome_cookies_before_share_page_fallback(self):
        runner = CookieRetryRunner()
        page_client = FakeSharePageClient(html="<html>should not fetch</html>")

        with TemporaryDirectory() as tmp:
            video_path = YtDlpClient(
                runner=runner,
                page_client=page_client,
            ).fetch_remote(
                "https://www.douyin.com/share/video/123",
                output_dir=Path(tmp),
            )

            self.assertEqual(video_path.name, "cookie-video.mp4")

        self.assertNotIn("--cookies-from-browser", runner.commands[0])
        self.assertIn("--cookies-from-browser", runner.commands[1])
        self.assertIn("chrome", runner.commands[1])
        self.assertEqual(page_client.fetched_pages, [])

    def test_fetch_remote_auto_cookies_falls_back_across_browsers(self):
        runner = CookieAutoFallbackRunner()
        page_client = FakeSharePageClient(html="<html>should not fetch</html>")

        with TemporaryDirectory() as tmp:
            video_path = YtDlpClient(
                runner=runner,
                page_client=page_client,
                cookies_from_browser="auto",
            ).fetch_remote(
                "https://www.douyin.com/share/video/123",
                output_dir=Path(tmp),
            )

            self.assertEqual(video_path.name, "edge-cookie-video.mp4")

        browsers = [_browser_from_args(command) for command in runner.commands]
        self.assertEqual(browsers, [None, "chrome", "chromium", "edge"])
        self.assertEqual(page_client.fetched_pages, [])

    def test_fetch_remote_failure_mentions_cookies_or_local_file(self):
        page_client = FakeSharePageClient(html="<html>no video</html>")

        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "cookies|本地视频"):
                YtDlpClient(
                    runner=FailingRunner(),
                    page_client=page_client,
                ).fetch_remote(
                    "https://www.douyin.com/share/video/123",
                    output_dir=Path(tmp),
                )


if __name__ == "__main__":
    unittest.main()
