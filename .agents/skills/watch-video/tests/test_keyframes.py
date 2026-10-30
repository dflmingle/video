import unittest

from watchvideo.keyframes import (
    candidate_timestamps,
    perceptual_hash_ppm,
    parse_ppm,
    score_ppm_sharpness,
    write_ppm_png,
)


class KeyframeTests(unittest.TestCase):
    def test_candidate_timestamps_rejects_non_finite_duration(self):
        for duration in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(ValueError, "duration_seconds"):
                    candidate_timestamps(duration)

    def test_candidate_timestamps_avoid_window_edges(self):
        groups = candidate_timestamps(duration_seconds=25.0, interval_seconds=10.0)

        self.assertEqual(groups[0], [0.75, 5.0, 9.25])
        self.assertEqual(groups[1], [10.75, 15.0, 19.25])
        self.assertEqual(groups[2], [20.75, 22.5, 24.25])

    def test_candidate_timestamps_handles_short_video(self):
        groups = candidate_timestamps(duration_seconds=2.0, interval_seconds=10.0)

        self.assertEqual(groups, [[0.75, 1.0, 1.25]])

    def test_candidate_timestamps_limits_work_and_keeps_full_timeline(self):
        groups = candidate_timestamps(
            duration_seconds=100.0,
            interval_seconds=10.0,
            max_groups=3,
        )

        self.assertEqual(len(groups), 3)
        self.assertLess(groups[0][0], 10.0)
        self.assertGreater(groups[-1][0], 90.0)

    def test_ppm_sharpness_scores_edges_higher_than_flat_image(self):
        flat = (
            b"P6\n3 2\n255\n"
            + bytes([20, 20, 20] * 6)
        )
        edge = (
            b"P6\n3 2\n255\n"
            + bytes(
                [
                    0,
                    0,
                    0,
                    255,
                    255,
                    255,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    255,
                    255,
                    255,
                    0,
                    0,
                    0,
                ]
            )
        )

        self.assertLess(score_ppm_sharpness(flat), score_ppm_sharpness(edge))
        self.assertEqual(parse_ppm(edge).width, 3)
        self.assertEqual(parse_ppm(edge).height, 2)

    def test_parse_ppm_preserves_leading_whitespace_pixel_bytes(self):
        # 函数边界：header 后只有一个分隔空白，后续字节即使像空白也属于像素数据。
        payload = bytes([32, 9, 10, 255, 0, 0])
        image = parse_ppm(b"P6\n2 1\n255\n" + payload)

        self.assertEqual(image.width, 2)
        self.assertEqual(image.height, 1)
        self.assertEqual(image.pixels, payload)

    def test_perceptual_hash_ignores_uniform_brightness_shift(self):
        dark = b"P6\n3 2\n255\n" + bytes([10, 10, 10, 40, 40, 40, 90, 90, 90] * 2)
        light = b"P6\n3 2\n255\n" + bytes([80, 80, 80, 110, 110, 110, 160, 160, 160] * 2)

        self.assertEqual(perceptual_hash_ppm(dark), perceptual_hash_ppm(light))

    def test_write_ppm_png_creates_valid_png_signature(self):
        ppm = b"P6\n2 1\n255\n" + bytes([0, 0, 0, 255, 255, 255])

        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "frame.png"
            write_ppm_png(ppm, output)
            data = output.read_bytes()

        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
