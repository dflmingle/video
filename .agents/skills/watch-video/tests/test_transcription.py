from pathlib import Path
import hashlib
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from watchvideo.commands import CommandResult
from watchvideo.transcription import (
    LOCAL_CMAKE_VERSION,
    WHISPER_CPP_COMMIT,
    WhisperCppAutoSetup,
    WhisperCppTranscriber,
    WhisperTranscriber,
)


class FakeRunner:
    def __init__(self):
        self.commands = []

    def run(self, args, cwd=None, check=True, text=True):
        self.commands.append(list(args))
        if Path(str(args[0])).name == "ffmpeg":
            Path(args[-1]).write_bytes(b"temporary audio")
        elif "whisper-cli" in str(args[0]):
            output_prefix = Path(args[args.index("-of") + 1])
            output_prefix.with_suffix(".srt").write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n自动转写\n",
                encoding="utf-8",
            )
        elif Path(str(args[0])).name == "whisper":
            audio_path = Path(args[1])
            output_dir = Path(args[args.index("--output_dir") + 1])
            (output_dir / audio_path.with_suffix(".srt").name).write_text(
                "1\n00:00:00,000 --> 00:00:01,000\n系统转写\n",
                encoding="utf-8",
            )
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


class FailingAfterAudioRunner(FakeRunner):
    def run(self, args, cwd=None, check=True, text=True):
        if Path(str(args[0])).name == "whisper":
            raise OSError("whisper failed")
        return super().run(args, cwd=cwd, check=check, text=text)


class FakeSetupRunner:
    def __init__(self):
        self.calls = []

    def run(self, args, cwd=None, check=True, text=True):
        self.calls.append((list(args), Path(cwd) if cwd else None))
        if args[:2] == ["git", "clone"]:
            repo_dir = Path(args[-1])
            repo_dir.mkdir(parents=True, exist_ok=True)
        elif args[:3] == ["git", "rev-parse", "HEAD"]:
            return CommandResult(args=list(args), returncode=0, stdout=WHISPER_CPP_COMMIT + "\n", stderr="")
        elif args[1:3] == ["-m", "venv"]:
            venv_dir = Path(args[-1])
            bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
            bin_dir.mkdir(parents=True, exist_ok=True)
            (bin_dir / ("python.exe" if os.name == "nt" else "python")).write_text(
                "#!/bin/sh\n",
                encoding="utf-8",
            )
            (bin_dir / ("python.exe" if os.name == "nt" else "python")).chmod(0o755)
        elif args[1:4] == ["-m", "pip", "install"]:
            cmake_bin = Path(args[0]).parent / ("cmake.exe" if os.name == "nt" else "cmake")
            cmake_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            cmake_bin.chmod(0o755)
        elif Path(args[0]).name in {"cmake", "cmake.exe"} and args[1:3] == ["--build", "build"]:
            assert cwd is not None
            bin_dir = Path(cwd) / "build" / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            whisper_bin = bin_dir / "whisper-cli"
            whisper_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            whisper_bin.chmod(0o755)
        return CommandResult(args=list(args), returncode=0, stdout="", stderr="")


def write_fake_model(url, output_path, max_bytes):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"model")


class WhisperTranscriberTests(unittest.TestCase):
    def test_system_whisper_uses_model_and_prompt_and_removes_temp_audio(self):
        runner = FakeRunner()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            video.write_bytes(b"fake")
            transcriber = WhisperTranscriber(
                runner=runner,
                model_name="small",
                prompt="Agent, Codex",
            )
            with patch("watchvideo.transcription.shutil.which", return_value="/usr/bin/whisper"):
                cues = transcriber.transcribe(video, root / "transcript", language="zh")
            audio_files = list((root / "transcript").glob("*.wav"))

        command = runner.commands[1]
        self.assertEqual([cue.text for cue in cues], ["系统转写"])
        self.assertIn("--model", command)
        self.assertIn("small", command)
        self.assertIn("--initial_prompt", command)
        self.assertIn("Agent, Codex", command)
        self.assertEqual(audio_files, [])
        self.assertTrue(transcriber.last_info.prompt_used)

    def test_system_whisper_removes_temp_audio_when_transcription_fails(self):
        runner = FailingAfterAudioRunner()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            video.write_bytes(b"fake")
            transcriber = WhisperTranscriber(runner=runner)

            with patch("watchvideo.transcription.shutil.which", return_value="/usr/bin/whisper"):
                with self.assertRaisesRegex(OSError, "whisper failed"):
                    transcriber.transcribe(video, root / "transcript", language="zh")

            self.assertEqual(list((root / "transcript").glob("*.wav")), [])


class WhisperCppTranscriberTests(unittest.TestCase):
    def test_missing_config_returns_no_cues_without_running_commands(self):
        runner = FakeRunner()
        transcriber = WhisperCppTranscriber(runner=runner)

        cues = transcriber.transcribe(
            video_path=Path("video.mp4"),
            output_dir=Path("transcript"),
            language="zh",
        )

        self.assertEqual(cues, [])
        self.assertEqual(runner.commands, [])
        self.assertIn("未配置", transcriber.unavailable_reason())

    def test_reports_partial_or_missing_whisper_cpp_config(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "ggml-base.bin"
            model.write_bytes(b"model")

            partial = WhisperCppTranscriber(model_path=model)
            missing = WhisperCppTranscriber(
                whisper_cpp_bin=root / "missing-whisper-cli",
                model_path=model,
            )

        self.assertIn("参数不完整", partial.unavailable_reason())
        self.assertIn("不存在", missing.unavailable_reason())

    def test_runs_whisper_cpp_and_loads_generated_srt(self):
        runner = FakeRunner()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            video.write_bytes(b"fake")
            whisper_bin = root / "whisper-cli"
            whisper_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            whisper_bin.chmod(0o755)
            model = root / "ggml-base.bin"
            model.write_bytes(b"model")

            cues = WhisperCppTranscriber(
                runner=runner,
                whisper_cpp_bin=whisper_bin,
                model_path=model,
                prompt="Agent, Codex",
            ).transcribe(
                video_path=video,
                output_dir=root / "transcript",
                language="zh",
            )

        self.assertEqual([cue.text for cue in cues], ["自动转写"])
        self.assertEqual(runner.commands[0][0], "ffmpeg")
        whisper_command = runner.commands[1]
        self.assertEqual(whisper_command[0], str(whisper_bin))
        self.assertIn("-m", whisper_command)
        self.assertIn(str(model), whisper_command)
        self.assertIn("-f", whisper_command)
        self.assertIn("-osrt", whisper_command)
        self.assertIn("-otxt", whisper_command)
        self.assertIn("-l", whisper_command)
        self.assertIn("zh", whisper_command)
        self.assertIn("--prompt", whisper_command)
        self.assertIn("Agent, Codex", whisper_command)

    def test_whisper_cpp_records_transcription_metadata(self):
        runner = FakeRunner()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            video.write_bytes(b"fake")
            whisper_bin = root / "whisper-cli"
            whisper_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            whisper_bin.chmod(0o755)
            model = root / "ggml-base.bin"
            model.write_bytes(b"model")
            transcriber = WhisperCppTranscriber(
                runner=runner,
                whisper_cpp_bin=whisper_bin,
                model_path=model,
                prompt="Agent, Codex",
            )

            transcriber.transcribe(
                video_path=video,
                output_dir=root / "transcript",
                language="zh",
            )

        self.assertIsNotNone(transcriber.last_info)
        assert transcriber.last_info is not None
        self.assertEqual(transcriber.last_info.source, "whisper.cpp")
        self.assertEqual(transcriber.last_info.model, "base")
        self.assertEqual(transcriber.last_info.language, "zh")
        self.assertTrue(transcriber.last_info.prompt_used)
        self.assertTrue(
            any(path.suffix == ".srt" for path in transcriber.last_info.transcript_files)
        )

    def test_whisper_cpp_removes_temporary_audio(self):
        runner = FakeRunner()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "video.mp4"
            video.write_bytes(b"fake")
            whisper_bin = root / "whisper-cli"
            whisper_bin.write_text("#!/bin/sh\n", encoding="utf-8")
            whisper_bin.chmod(0o755)
            model = root / "ggml-base.bin"
            model.write_bytes(b"model")
            transcriber = WhisperCppTranscriber(
                runner=runner,
                whisper_cpp_bin=whisper_bin,
                model_path=model,
            )

            transcriber.transcribe(video, root / "transcript")

            self.assertEqual(list((root / "transcript").glob("*.wav")), [])


class WhisperCppAutoSetupTests(unittest.TestCase):
    def test_installs_whisper_cpp_under_tools_dir_and_returns_transcriber(self):
        runner = FakeSetupRunner()
        with TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / ".tools"
            setup = WhisperCppAutoSetup(
                tools_dir=tools_dir,
                runner=runner,
                cmake_bin="cmake",
                model_sha256=hashlib.sha256(b"model").hexdigest(),
                model_fetcher=write_fake_model,
            )

            transcriber = setup.ensure_transcriber(prompt="Agent, Codex")

            repo_dir = tools_dir / f"whisper.cpp-{WHISPER_CPP_COMMIT[:12]}"
            model = repo_dir / "models" / "ggml-base.bin"
            whisper_bin = repo_dir / "build" / "bin" / "whisper-cli"

            self.assertEqual(transcriber.whisper_cpp_bin, whisper_bin)
            self.assertEqual(transcriber.model_path, model)
            self.assertEqual(transcriber.prompt, "Agent, Codex")
            self.assertTrue(model.exists())
            self.assertTrue(whisper_bin.exists())

        commands = [call[0] for call in runner.calls]
        self.assertEqual(commands[0][:2], ["git", "clone"])
        self.assertTrue(any(command[:2] == ["git", "fetch"] for command in commands))
        self.assertTrue(any(command[:2] == ["git", "checkout"] for command in commands))
        self.assertTrue(any(command[1:3] == ["-B", "build"] for command in commands))
        self.assertTrue(any(command[1:3] == ["--build", "build"] for command in commands))

    def test_bootstraps_local_cmake_when_system_cmake_is_missing(self):
        runner = FakeSetupRunner()
        with TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / ".tools"
            setup = WhisperCppAutoSetup(
                tools_dir=tools_dir,
                runner=runner,
                model_sha256=hashlib.sha256(b"model").hexdigest(),
                model_fetcher=write_fake_model,
            )

            with patch("watchvideo.transcription.shutil.which", return_value=None):
                setup.ensure_transcriber()

            venv_dir = tools_dir / f".venv-cmake-{LOCAL_CMAKE_VERSION}"
            venv_bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
            venv_python = venv_bin_dir / ("python.exe" if os.name == "nt" else "python")
            local_cmake = venv_bin_dir / ("cmake.exe" if os.name == "nt" else "cmake")

        commands = [call[0] for call in runner.calls]
        self.assertIn([sys.executable, "-m", "venv", str(venv_dir)], commands)
        self.assertIn(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--force-reinstall",
                f"cmake=={LOCAL_CMAKE_VERSION}",
            ],
            commands,
        )
        configure_commands = [command for command in commands if command[1:3] == ["-B", "build"]]
        self.assertEqual(configure_commands[0][0], str(local_cmake))

    def test_rebuilds_incomplete_cmake_venv(self):
        runner = FakeSetupRunner()
        with TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / ".tools"
            setup = WhisperCppAutoSetup(
                tools_dir=tools_dir,
                runner=runner,
                model_sha256=hashlib.sha256(b"model").hexdigest(),
                model_fetcher=write_fake_model,
            )
            setup.venv_python.parent.mkdir(parents=True, exist_ok=True)
            setup.venv_python.write_text("broken", encoding="utf-8")

            with patch("watchvideo.transcription.shutil.which", return_value=None):
                setup.ensure_transcriber()

        commands = [call[0] for call in runner.calls]
        self.assertIn([sys.executable, "-m", "venv", str(setup.venv_dir)], commands)

    def test_default_tools_dir_is_user_cache_not_package_source(self):
        with patch.dict(os.environ, {"WATCHVIDEO_TOOLS_DIR": "/tmp/watchvideo-cache"}):
            setup = WhisperCppAutoSetup()

        self.assertEqual(setup.tools_dir, Path("/tmp/watchvideo-cache"))


if __name__ == "__main__":
    unittest.main()
