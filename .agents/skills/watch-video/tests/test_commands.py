import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from watchvideo.commands import CommandError, CommandResult, CommandRunner


class CommandRunnerTests(unittest.TestCase):
    def test_command_error_redacts_sensitive_arguments_and_urls(self):
        error = CommandError(
            CommandResult(
                args=[
                    "whisper",
                    "--initial_prompt",
                    "internal-secret-phrase",
                    "--token=secret-token",
                    "https://user:password@example.com/video?signature=secret",
                ],
                returncode=1,
                stdout="",
                stderr=(
                    "failed internal-secret-phrase at "
                    "https://user:password@example.com/video?signature=secret"
                ),
            )
        )

        message = str(error)
        self.assertNotIn("internal-secret-phrase", message)
        self.assertNotIn("secret-token", message)
        self.assertNotIn("password", message)
        self.assertNotIn("signature=secret", message)
        self.assertIn("[REDACTED]", message)

    def test_run_bounds_captured_output(self):
        runner = CommandRunner(max_output_bytes=64, max_error_bytes=32)

        result = runner.run(
            [sys.executable, "-c", "import sys; print('x' * 200); sys.stderr.write('y' * 100)"],
            check=False,
        )

        self.assertLessEqual(len(result.stdout.encode("utf-8")), 96)
        self.assertLessEqual(len(result.stderr.encode("utf-8")), 64)
        self.assertTrue(result.stdout_truncated)
        self.assertTrue(result.stderr_truncated)
        self.assertIn("已截断", result.stdout)
        self.assertIn("已截断", result.stderr)

    def test_run_times_out_with_bounded_error(self):
        runner = CommandRunner(timeout_seconds=0.05, max_error_bytes=128)

        with self.assertRaises(CommandError) as context:
            runner.run([sys.executable, "-c", "import time; time.sleep(2)"])

        self.assertIn("超过 0.05 秒", str(context.exception))
        self.assertLess(len(str(context.exception)), 2048)

    def test_run_reports_program_stage_without_exposing_arguments(self):
        stages = []
        runner = CommandRunner(progress=stages.append)

        runner.run([sys.executable, "-c", "print('secret argument')"])

        self.assertEqual(stages, [Path(sys.executable).name])
        self.assertNotIn("secret argument", stages[0])

    @unittest.skipUnless(sys.platform in {"darwin", "linux"}, "需要 POSIX 进程组")
    def test_timeout_terminates_descendant_process_group(self):
        with TemporaryDirectory() as tmp:
            marker = Path(tmp) / "child-terminated"
            child = (
                "import pathlib,signal,time; "
                f"p=pathlib.Path({str(marker)!r}); "
                "signal.signal(signal.SIGTERM, lambda *_: (p.write_text('term'), exit(0))); "
                "time.sleep(10)"
            )
            parent = (
                "import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
                "time.sleep(10)"
            )
            runner = CommandRunner(timeout_seconds=0.3)

            with self.assertRaises(CommandError):
                runner.run([sys.executable, "-c", parent])

            deadline = time.monotonic() + 2.0
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists(), "超时后应向整个子进程组发送 SIGTERM")


if __name__ == "__main__":
    unittest.main()
