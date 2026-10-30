from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from watchvideo.media import FfmpegClient


class RecordingFfmpegClient(FfmpegClient):
    def __init__(self, identical_ppm=False):
        super().__init__()
        self.identical_ppm = identical_ppm
        self.ppm_timestamps = []

    def extract_ppm(self, video_path, timestamp_seconds):
        self.ppm_timestamps.append(timestamp_seconds)
        if self.identical_ppm:
            return b"P6\n3 2\n255\n" + bytes([0, 0, 0, 255, 255, 255, 0, 0, 0] * 2)
        value = min(255, int(timestamp_seconds * 5))
        if timestamp_seconds >= 20:
            pixels = [value, value, value, 0, 0, 0, 255, 255, 255] * 2
        else:
            pixels = [0, 0, 0, 255, 255, 255, value, value, value] * 2
        return b"P6\n3 2\n255\n" + bytes(pixels)


class MediaTests(unittest.TestCase):
    def test_extract_keyframes_has_a_library_level_default_work_limit(self):
        client = RecordingFfmpegClient(identical_ppm=True)

        with TemporaryDirectory() as tmp:
            client.extract_keyframes(
                video_path=Path("video.mp4"),
                output_dir=Path(tmp) / "keyframes",
                duration_seconds=10_000.0,
                interval_seconds=1.0,
            )

        self.assertEqual(len(client.ppm_timestamps), 80 * 3)
        self.assertGreater(client.ppm_timestamps[-1], 9_000.0)

    def test_extract_keyframes_stops_at_max_keyframes(self):
        client = RecordingFfmpegClient()

        with TemporaryDirectory() as tmp:
            frames = client.extract_keyframes(
                video_path=Path("video.mp4"),
                output_dir=Path(tmp) / "keyframes",
                duration_seconds=50.0,
                interval_seconds=10.0,
                max_keyframes=2,
            )

        self.assertEqual(len(frames), 2)
        self.assertEqual(len(client.ppm_timestamps), 6)
        self.assertEqual(frames[0].path.name, "frame_0001.png")
        self.assertEqual(frames[1].path.name, "frame_0002.png")
        self.assertTrue(all(frame.path.suffix == ".png" for frame in frames))
        self.assertGreater(client.ppm_timestamps[-1], 40.0)

    def test_extract_keyframes_deduplicates_similar_frames(self):
        client = RecordingFfmpegClient(identical_ppm=True)

        with TemporaryDirectory() as tmp:
            frames = client.extract_keyframes(
                video_path=Path("video.mp4"),
                output_dir=Path(tmp) / "keyframes",
                duration_seconds=30.0,
                interval_seconds=10.0,
            )

        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].path.name, "frame_0001.png")


if __name__ == "__main__":
    unittest.main()
