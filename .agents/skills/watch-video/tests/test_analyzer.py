from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from watchvideo.analyzer import VideoAnalyzer
from watchvideo.models import DownloadAttempt, Keyframe, MediaInfo, SubtitleCue, TranscriptionInfo


class FakeDownloader:
    def __init__(self):
        self.downloaded = False
        self.subtitle_downloaded = False
        self.download_attempts = [
            DownloadAttempt(step="plain yt-dlp", status="failed", detail="fresh cookies"),
            DownloadAttempt(step="mobile share page play_addr", status="ok", detail="share-page-play-addr.mp4"),
        ]

    def fetch_remote(self, url, output_dir, max_height):
        self.downloaded = True
        return Path(output_dir) / "remote.mp4"

    def fetch_subtitles(self, url, output_dir, languages):
        self.subtitle_downloaded = True
        subtitle = Path(output_dir) / "caption.srt"
        subtitle.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\n已有字幕\n",
            encoding="utf-8",
        )
        return [subtitle]


class WritingDownloader(FakeDownloader):
    def __init__(self):
        super().__init__()
        self.downloaded_path = None

    def fetch_remote(self, url, output_dir, max_height):
        self.downloaded = True
        path = Path(output_dir) / "remote.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake mp4")
        self.downloaded_path = path
        return path


class EmptyWritingDownloader(WritingDownloader):
    def fetch_subtitles(self, url, output_dir, languages):
        self.subtitle_downloaded = True
        return []


class OutsidePathDownloader(FakeDownloader):
    def __init__(self, downloaded_path):
        super().__init__()
        self.downloaded_path = downloaded_path

    def fetch_remote(self, url, output_dir, max_height):
        self.downloaded = True
        self.downloaded_path.write_bytes(b"fake mp4")
        return self.downloaded_path


class FakeMediaClient:
    def __init__(self):
        self.max_keyframes = None

    def probe(self, video_path):
        return MediaInfo(path=Path(video_path), duration_seconds=12.0, width=1920, height=1080)

    def extract_keyframes(self, video_path, output_dir, duration_seconds, interval_seconds, max_keyframes=None):
        self.max_keyframes = max_keyframes
        return [
            Keyframe(path=Path(output_dir) / "frame_0001.jpg", timestamp_seconds=5.0, score=10.0)
        ]


class EmptyMediaClient(FakeMediaClient):
    def extract_keyframes(self, video_path, output_dir, duration_seconds, interval_seconds, max_keyframes=None):
        return []


class FailingMediaClient(FakeMediaClient):
    def probe(self, video_path):
        raise OSError("probe failed")


class TallMediaClient(FakeMediaClient):
    def probe(self, video_path):
        return MediaInfo(path=Path(video_path), duration_seconds=12.0, width=3840, height=2160)


class FailingKeyframeMediaClient(FakeMediaClient):
    def extract_keyframes(
        self,
        video_path,
        output_dir,
        duration_seconds,
        interval_seconds,
        max_keyframes=None,
    ):
        raise OSError("keyframe extraction failed")


class FakeTranscriber:
    def __init__(self):
        self.called = False
        self.cues = [
            SubtitleCue(start_seconds=0.0, end_seconds=1.0, text="转写字幕")
        ]
        self.last_info = None

    def transcribe(self, video_path, output_dir, language):
        self.called = True
        self.last_info = TranscriptionInfo(
            source="fake-asr",
            model="fake-model",
            language=language,
            prompt_used=False,
            transcript_files=[Path(output_dir) / "fake.srt"],
        )
        return self.cues


class EmptyTranscriber(FakeTranscriber):
    def __init__(self):
        super().__init__()
        self.cues = []


class FakeOcr:
    def __init__(self):
        self.called = False

    def extract(self, keyframes, warnings):
        self.called = True
        return []


class FailingOcr(FakeOcr):
    def extract(self, keyframes, warnings):
        self.called = True
        raise OSError("ocr failed")


class BrokenThenValidSubtitleDownloader(WritingDownloader):
    def fetch_subtitles(self, url, output_dir, languages):
        self.subtitle_downloaded = True
        root = Path(output_dir)
        broken = root / "broken.srt"
        valid = root / "valid.srt"
        valid.write_text(
            "1\n00:00:00,000 --> 00:00:01,000\n后备字幕\n",
            encoding="utf-8",
        )
        return [broken, valid]


class FakeWhisperCppSetup:
    def __init__(self):
        self.called = False
        self.prompt = None
        self.transcriber = FakeTranscriber()

    def ensure_transcriber(self, prompt=None):
        self.called = True
        self.prompt = prompt
        return self.transcriber


class AnalyzerTests(unittest.TestCase):
    def test_default_analyzer_ocr_engine_is_enabled_when_ocr_is_requested(self):
        analyzer = VideoAnalyzer()

        self.assertTrue(analyzer.ocr_engine.enabled)

    def test_remote_analysis_prefers_downloaded_subtitles_over_transcription(self):
        downloader = FakeDownloader()
        media = FakeMediaClient()
        transcriber = FakeTranscriber()

        with TemporaryDirectory() as tmp:
            report = VideoAnalyzer(
                downloader=downloader,
                media_client=media,
                transcriber=transcriber,
            ).analyze(
                "https://example.com/video",
                output_dir=Path(tmp),
                subtitle_languages=["zh.*", "en.*"],
                max_keyframes=3,
            )

        self.assertTrue(downloader.downloaded)
        self.assertTrue(downloader.subtitle_downloaded)
        self.assertFalse(transcriber.called)
        self.assertEqual(report.transcript_text, "已有字幕")
        self.assertEqual(report.media.duration_seconds, 12.0)
        self.assertEqual(report.keyframes[0].timestamp_seconds, 5.0)
        self.assertEqual(media.max_keyframes, 3)
        self.assertEqual(report.download_attempts, downloader.download_attempts)

    def test_remote_analysis_deletes_downloaded_video_by_default(self):
        downloader = WritingDownloader()

        with TemporaryDirectory() as tmp:
            report = VideoAnalyzer(
                downloader=downloader,
                media_client=FakeMediaClient(),
                transcriber=FakeTranscriber(),
            ).analyze(
                "https://example.com/video",
                output_dir=Path(tmp),
            )

            assert downloader.downloaded_path is not None
            self.assertFalse(downloader.downloaded_path.exists())

        self.assertEqual(len(report.cleanup_records), 1)
        self.assertEqual(report.cleanup_records[0].target, "downloaded_video")
        self.assertEqual(report.cleanup_records[0].status, "deleted")

    def test_remote_analysis_cleans_download_on_pipeline_exception(self):
        downloader = WritingDownloader()

        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(OSError, "probe failed"):
                VideoAnalyzer(
                    downloader=downloader,
                    media_client=FailingMediaClient(),
                ).analyze("https://example.com/video", output_dir=Path(tmp))

            assert downloader.downloaded_path is not None
            self.assertFalse(downloader.downloaded_path.exists())

    def test_remote_analysis_rejects_download_above_max_height_and_cleans_it(self):
        downloader = WritingDownloader()

        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "超过 --max-height 上限"):
                VideoAnalyzer(
                    downloader=downloader,
                    media_client=TallMediaClient(),
                ).analyze(
                    "https://example.com/video",
                    output_dir=Path(tmp),
                    max_height=1080,
                )

            assert downloader.downloaded_path is not None
            self.assertFalse(downloader.downloaded_path.exists())

    def test_keyframe_failure_keeps_existing_transcript_as_partial_success(self):
        downloader = WritingDownloader()

        with TemporaryDirectory() as tmp:
            report = VideoAnalyzer(
                downloader=downloader,
                media_client=FailingKeyframeMediaClient(),
                transcriber=FakeTranscriber(),
            ).analyze("https://example.com/video", output_dir=Path(tmp))

        self.assertEqual(report.transcript_text, "已有字幕")
        self.assertEqual(report.keyframes, [])
        self.assertTrue(any("关键帧提取失败" in warning for warning in report.warnings))

    def test_ocr_failure_keeps_existing_transcript_and_keyframes(self):
        ocr = FailingOcr()

        with TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake")
            report = VideoAnalyzer(
                media_client=FakeMediaClient(),
                transcriber=FakeTranscriber(),
                ocr_engine=ocr,
            ).analyze(
                str(video),
                output_dir=Path(tmp) / "out",
                enable_ocr=True,
            )

        self.assertTrue(ocr.called)
        self.assertEqual(report.transcript_text, "转写字幕")
        self.assertEqual(len(report.keyframes), 1)
        self.assertEqual(report.ocr_results, [])
        self.assertTrue(any("OCR 提取失败" in warning for warning in report.warnings))

    def test_broken_subtitle_is_skipped_before_loading_next_subtitle(self):
        downloader = BrokenThenValidSubtitleDownloader()
        transcriber = FakeTranscriber()

        with TemporaryDirectory() as tmp:
            report = VideoAnalyzer(
                downloader=downloader,
                media_client=FakeMediaClient(),
                transcriber=transcriber,
            ).analyze("https://example.com/video", output_dir=Path(tmp))

        self.assertEqual(report.transcript_text, "后备字幕")
        self.assertFalse(transcriber.called)
        self.assertTrue(any("字幕读取失败" in warning for warning in report.warnings))

    def test_remote_analysis_fails_and_cleans_video_when_no_derived_evidence_exists(self):
        downloader = EmptyWritingDownloader()
        empty = EmptyTranscriber()

        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "没有生成可用的派生证据"):
                VideoAnalyzer(
                    downloader=downloader,
                    media_client=EmptyMediaClient(),
                    transcriber=empty,
                    whisper_cpp_transcriber=empty,
                    auto_transcribe_setup=False,
                ).analyze("https://example.com/video", output_dir=Path(tmp))

            assert downloader.downloaded_path is not None
            self.assertFalse(downloader.downloaded_path.exists())

    def test_reused_output_directory_uses_isolated_run_workspaces(self):
        downloader = WritingDownloader()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "subtitles").mkdir()
            (root / "subtitles" / "stale.srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n旧字幕\n",
                encoding="utf-8",
            )
            analyzer = VideoAnalyzer(
                downloader=downloader,
                media_client=FakeMediaClient(),
                transcriber=FakeTranscriber(),
            )

            first = analyzer.analyze("https://example.com/one", output_dir=root)
            second = analyzer.analyze("https://example.com/two", output_dir=root)

            self.assertNotEqual(first.work_dir, second.work_dir)
            self.assertEqual(first.work_dir.parent, root.resolve() / ".runs")
            self.assertEqual(second.work_dir.parent, root.resolve() / ".runs")
            self.assertNotIn(root / "subtitles" / "stale.srt", first.subtitle_files)
            self.assertNotIn(root / "subtitles" / "stale.srt", second.subtitle_files)

    def test_remote_analysis_can_keep_downloaded_video(self):
        downloader = WritingDownloader()

        with TemporaryDirectory() as tmp:
            report = VideoAnalyzer(
                downloader=downloader,
                media_client=FakeMediaClient(),
                transcriber=FakeTranscriber(),
            ).analyze(
                "https://example.com/video",
                output_dir=Path(tmp),
                cleanup_downloaded_video=False,
            )

            assert downloader.downloaded_path is not None
            self.assertTrue(downloader.downloaded_path.exists())

        self.assertEqual(report.cleanup_records, [])

    def test_local_analysis_never_deletes_input_video(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "local.mp4"
            video.write_bytes(b"fake mp4")

            report = VideoAnalyzer(
                media_client=FakeMediaClient(),
                transcriber=FakeTranscriber(),
            ).analyze(
                str(video),
                output_dir=root / "out",
            )

            self.assertTrue(video.exists())

        self.assertEqual(report.cleanup_records, [])

    def test_remote_cleanup_skips_paths_outside_output_directory(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside_video = root / "outside.mp4"
            downloader = OutsidePathDownloader(outside_video)

            report = VideoAnalyzer(
                downloader=downloader,
                media_client=FakeMediaClient(),
                transcriber=FakeTranscriber(),
            ).analyze(
                "https://example.com/video",
                output_dir=root / "analysis",
            )

            self.assertTrue(outside_video.exists())

        self.assertEqual(len(report.cleanup_records), 1)
        self.assertEqual(report.cleanup_records[0].status, "skipped")
        self.assertTrue(any("不在本次输出目录内" in warning for warning in report.warnings))

    def test_analysis_falls_back_to_whisper_cpp_when_primary_transcriber_has_no_cues(self):
        media = FakeMediaClient()
        primary = FakeTranscriber()
        primary.cues = []
        whisper_cpp = FakeTranscriber()
        ocr = FakeOcr()

        with TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake")
            report = VideoAnalyzer(
                media_client=media,
                transcriber=primary,
                whisper_cpp_transcriber=whisper_cpp,
                ocr_engine=ocr,
            ).analyze(
                str(video),
                output_dir=Path(tmp) / "out",
                enable_ocr=True,
            )

        self.assertTrue(primary.called)
        self.assertTrue(whisper_cpp.called)
        self.assertTrue(ocr.called)
        self.assertEqual(report.transcript_text, "转写字幕")
        self.assertIsNotNone(report.transcription_info)
        assert report.transcription_info is not None
        self.assertEqual(report.transcription_info.source, "fake-asr")
        self.assertEqual(report.transcription_info.model, "fake-model")

    def test_analysis_records_whisper_cpp_config_warning_when_no_transcriber_is_available(self):
        primary = FakeTranscriber()
        primary.cues = []

        with TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake")
            report = VideoAnalyzer(
                media_client=FakeMediaClient(),
                transcriber=primary,
                auto_transcribe_setup=False,
            ).analyze(
                str(video),
                output_dir=Path(tmp) / "out",
            )

        self.assertTrue(
            any("whisper.cpp" in warning and "未配置" in warning for warning in report.warnings)
        )

    def test_analysis_auto_sets_up_whisper_cpp_when_no_transcriber_is_configured(self):
        primary = FakeTranscriber()
        primary.cues = []
        setup = FakeWhisperCppSetup()

        with TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"
            video.write_bytes(b"fake")
            report = VideoAnalyzer(
                media_client=FakeMediaClient(),
                transcriber=primary,
                whisper_cpp_setup=setup,
            ).analyze(
                str(video),
                output_dir=Path(tmp) / "out",
            )

        self.assertTrue(setup.called)
        self.assertEqual(report.transcript_text, "转写字幕")
        self.assertFalse(any("未配置 whisper.cpp" in warning for warning in report.warnings))


if __name__ == "__main__":
    unittest.main()
