from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Callable, Iterator
from urllib.request import Request, urlopen
from uuid import uuid4

from .commands import CommandRunner
from .models import SubtitleCue, TranscriptionInfo
from .subtitles import load_subtitle_file


WHISPER_CPP_COMMIT = "43d78af5be58f41d6ffbc227d608f104577741ea"
WHISPER_CPP_REPOSITORY = "https://github.com/ggerganov/whisper.cpp"
WHISPER_MODEL_URLS = {
    "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
}
WHISPER_MODEL_SHA256 = {
    "base": "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe",
}
LOCAL_CMAKE_VERSION = "4.3.4"
MAX_MODEL_BYTES = 200 * 1024 * 1024
ModelFetcher = Callable[[str, Path, int], None]


class WhisperTranscriber:
    def __init__(
        self,
        runner: CommandRunner | None = None,
        ffmpeg: str = "ffmpeg",
        whisper: str = "whisper",
        model_name: str | None = None,
        prompt: str | None = None,
        keep_audio: bool = False,
    ):
        self.runner = runner or CommandRunner()
        self.ffmpeg = ffmpeg
        self.whisper = whisper
        self.model_name = model_name
        self.prompt = prompt
        self.keep_audio = keep_audio
        self.last_info: TranscriptionInfo | None = None

    def available(self) -> bool:
        return shutil.which(self.whisper) is not None

    def transcribe(
        self,
        video_path: Path,
        output_dir: Path,
        language: str | None = None,
    ) -> list[SubtitleCue]:
        self.last_info = None
        if not self.available():
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        run_name = f"whisper-{uuid4().hex}"
        audio_path = output_dir / f"{run_name}.wav"
        srt_path = output_dir / f"{run_name}.srt"
        try:
            self.runner.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(audio_path),
                ]
            )

            command = [
                self.whisper,
                str(audio_path),
                "--task",
                "transcribe",
                "--output_format",
                "srt",
                "--output_dir",
                str(output_dir),
            ]
            if self.model_name:
                command.extend(["--model", self.model_name])
            if language:
                command.extend(["--language", language])
            if self.prompt:
                command.extend(["--initial_prompt", self.prompt])
            self.runner.run(command)

            if not srt_path.is_file():
                return []
            self.last_info = TranscriptionInfo(
                source="system whisper",
                model=self.model_name or "default",
                language=language,
                prompt_used=bool(self.prompt),
                transcript_files=[srt_path],
            )
            return load_subtitle_file(srt_path)
        finally:
            if not self.keep_audio:
                _remove_owned_file(audio_path)


class WhisperCppTranscriber:
    def __init__(
        self,
        runner: CommandRunner | None = None,
        ffmpeg: str = "ffmpeg",
        whisper_cpp_bin: str | Path | None = None,
        model_path: str | Path | None = None,
        prompt: str | None = None,
        keep_audio: bool = False,
    ):
        self.runner = runner or CommandRunner()
        self.ffmpeg = ffmpeg
        self.whisper_cpp_bin = Path(whisper_cpp_bin) if whisper_cpp_bin else None
        self.model_path = Path(model_path) if model_path else None
        self.prompt = prompt
        self.keep_audio = keep_audio
        self.last_info: TranscriptionInfo | None = None

    def available(self) -> bool:
        return self.unavailable_reason() is None

    def unavailable_reason(self) -> str | None:
        if self.whisper_cpp_bin is None and self.model_path is None:
            return "未配置 whisper.cpp，已跳过本地 whisper.cpp 转写"
        if self.whisper_cpp_bin is None or self.model_path is None:
            return "whisper.cpp 参数不完整：需要同时提供 --whisper-cpp-bin 和 --whisper-model"
        if self._resolved_binary() is None:
            return f"whisper.cpp 二进制不存在: {self.whisper_cpp_bin}"
        if not self.model_path.is_file():
            return f"whisper.cpp 模型不存在: {self.model_path}"
        return None

    def has_config(self) -> bool:
        return self.whisper_cpp_bin is not None or self.model_path is not None

    def transcribe(
        self,
        video_path: Path,
        output_dir: Path,
        language: str | None = None,
    ) -> list[SubtitleCue]:
        # 函数边界：只封装 whisper.cpp CLI，不负责下载模型或构建二进制。
        self.last_info = None
        if not self.available():
            return []

        output_dir.mkdir(parents=True, exist_ok=True)
        run_name = f"whisper-cpp-{uuid4().hex}"
        audio_path = output_dir / f"{run_name}.wav"
        output_prefix = output_dir / run_name
        srt_path = output_prefix.with_suffix(".srt")
        txt_path = output_prefix.with_suffix(".txt")
        try:
            self.runner.run(
                [
                    self.ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    str(audio_path),
                ]
            )

            command = [
                str(self._resolved_binary()),
                "-m",
                str(self.model_path),
                "-f",
                str(audio_path),
                "-osrt",
                "-otxt",
                "-of",
                str(output_prefix),
            ]
            if language:
                command.extend(["-l", language])
            if self.prompt:
                command.extend(["--prompt", self.prompt])
            self.runner.run(command)

            if not srt_path.is_file():
                return []
            transcript_files = [path for path in (srt_path, txt_path) if path.is_file()]
            self.last_info = TranscriptionInfo(
                source="whisper.cpp",
                model=_whisper_cpp_model_name(self.model_path),
                language=language,
                prompt_used=bool(self.prompt),
                transcript_files=transcript_files,
            )
            return load_subtitle_file(srt_path)
        finally:
            if not self.keep_audio:
                _remove_owned_file(audio_path)

    def _resolved_binary(self) -> Path | None:
        if self.whisper_cpp_bin is None:
            return None
        if self.whisper_cpp_bin.is_file() and os.access(self.whisper_cpp_bin, os.X_OK):
            return self.whisper_cpp_bin
        if self.whisper_cpp_bin.parent == Path("."):
            found = shutil.which(str(self.whisper_cpp_bin))
            return Path(found) if found else None
        return None


def _whisper_cpp_model_name(model_path: Path | None) -> str | None:
    if model_path is None:
        return None
    name = model_path.name
    if name.startswith("ggml-") and name.endswith(".bin"):
        return name[len("ggml-") : -len(".bin")]
    return model_path.stem


class WhisperCppAutoSetup:
    def __init__(
        self,
        tools_dir: str | Path | None = None,
        runner: CommandRunner | None = None,
        model_name: str = "base",
        cmake_bin: str | Path | None = None,
        whisper_cpp_commit: str = WHISPER_CPP_COMMIT,
        model_url: str | None = None,
        model_sha256: str | None = None,
        model_fetcher: ModelFetcher | None = None,
    ):
        self.tools_dir = Path(tools_dir) if tools_dir else _default_tools_dir()
        self.runner = runner or CommandRunner()
        self.model_name = model_name
        self.cmake_bin = Path(cmake_bin) if cmake_bin else None
        self.whisper_cpp_commit = whisper_cpp_commit
        self.model_url = model_url or WHISPER_MODEL_URLS.get(model_name)
        self.model_sha256 = model_sha256 or WHISPER_MODEL_SHA256.get(model_name)
        self.model_fetcher = model_fetcher or _download_file

    @property
    def repo_dir(self) -> Path:
        return self.tools_dir / f"whisper.cpp-{self.whisper_cpp_commit[:12]}"

    @property
    def whisper_cpp_bin(self) -> Path:
        return self.repo_dir / "build" / "bin" / "whisper-cli"

    @property
    def model_path(self) -> Path:
        return self.repo_dir / "models" / f"ggml-{self.model_name}.bin"

    @property
    def venv_dir(self) -> Path:
        return self.tools_dir / f".venv-cmake-{LOCAL_CMAKE_VERSION}"

    @property
    def venv_bin_dir(self) -> Path:
        return self.venv_dir / ("Scripts" if os.name == "nt" else "bin")

    @property
    def venv_python(self) -> Path:
        return self.venv_bin_dir / ("python.exe" if os.name == "nt" else "python")

    @property
    def local_cmake(self) -> Path:
        return self.venv_bin_dir / ("cmake.exe" if os.name == "nt" else "cmake")

    def ensure_transcriber(self, prompt: str | None = None) -> WhisperCppTranscriber:
        # 函数边界：只准备版本固定且校验过的本地缓存，不修改系统依赖。
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        with _exclusive_setup_lock(self.tools_dir / ".setup.lock"):
            self._ensure_checkout()
            self._ensure_model()
            if not self.whisper_cpp_bin.is_file() or not os.access(self.whisper_cpp_bin, os.X_OK):
                cmake = self._ensure_cmake()
                self.runner.run(
                    [cmake, "-B", "build", "-DCMAKE_BUILD_TYPE=Release"],
                    cwd=self.repo_dir,
                )
                self.runner.run(
                    [
                        cmake,
                        "--build",
                        "build",
                        "--config",
                        "Release",
                        "-j",
                        str(min(os.cpu_count() or 2, 8)),
                    ],
                    cwd=self.repo_dir,
                )

        if not self.whisper_cpp_bin.is_file() or not os.access(self.whisper_cpp_bin, os.X_OK):
            raise FileNotFoundError(f"whisper.cpp 二进制不存在: {self.whisper_cpp_bin}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"whisper.cpp 模型不存在: {self.model_path}")

        return WhisperCppTranscriber(
            runner=self.runner,
            whisper_cpp_bin=self.whisper_cpp_bin,
            model_path=self.model_path,
            prompt=prompt,
        )

    def _ensure_checkout(self) -> None:
        if self.repo_dir.is_dir() and self._checkout_matches():
            return
        if self.repo_dir.exists():
            shutil.rmtree(self.repo_dir)

        staging = self.tools_dir / f".{self.repo_dir.name}.{uuid4().hex}.tmp"
        try:
            self.runner.run(
                [
                    "git",
                    "clone",
                    "--filter=blob:none",
                    "--no-checkout",
                    WHISPER_CPP_REPOSITORY,
                    str(staging),
                ]
            )
            self.runner.run(
                ["git", "fetch", "--depth", "1", "origin", self.whisper_cpp_commit],
                cwd=staging,
            )
            self.runner.run(
                ["git", "checkout", "--detach", self.whisper_cpp_commit],
                cwd=staging,
            )
            revision = self.runner.run(["git", "rev-parse", "HEAD"], cwd=staging)
            if str(revision.stdout).strip() != self.whisper_cpp_commit:
                raise OSError("whisper.cpp checkout 校验失败")
            staging.replace(self.repo_dir)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def _checkout_matches(self) -> bool:
        try:
            result = self.runner.run(["git", "rev-parse", "HEAD"], cwd=self.repo_dir)
        except (OSError, RuntimeError):
            return False
        return str(result.stdout).strip() == self.whisper_cpp_commit

    def _ensure_model(self) -> None:
        if not self.model_url or not self.model_sha256:
            raise OSError(f"模型 {self.model_name} 缺少固定 URL 或 SHA-256")
        if self.model_path.is_file() and _sha256_file(self.model_path) == self.model_sha256:
            return

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        part_path = self.model_path.with_suffix(self.model_path.suffix + f".{uuid4().hex}.part")
        try:
            self.model_fetcher(self.model_url, part_path, MAX_MODEL_BYTES)
            actual = _sha256_file(part_path)
            if actual != self.model_sha256:
                raise OSError(
                    f"模型 SHA-256 校验失败: expected={self.model_sha256}, actual={actual}"
                )
            part_path.replace(self.model_path)
        finally:
            _remove_owned_file(part_path)

    def _ensure_cmake(self) -> str:
        if self.cmake_bin is not None:
            return str(self.cmake_bin)

        system_cmake = shutil.which("cmake")
        if system_cmake:
            return system_cmake

        # 函数职责：把构建依赖限制在用户缓存的隔离 venv，
        # 避免修改系统 Python 或全局 PATH。
        if not _is_executable(self.venv_python):
            if self.venv_dir.exists():
                shutil.rmtree(self.venv_dir)
            self.runner.run([sys.executable, "-m", "venv", str(self.venv_dir)])
        if not _is_executable(self.local_cmake):
            self.runner.run(
                [
                    str(self.venv_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--force-reinstall",
                    f"cmake=={LOCAL_CMAKE_VERSION}",
                ]
            )
        if not _is_executable(self.local_cmake):
            raise FileNotFoundError(f"本地 cmake 不存在: {self.local_cmake}")
        return str(self.local_cmake)


def _default_tools_dir() -> Path:
    configured = os.environ.get("WATCHVIDEO_TOOLS_DIR")
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "watchvideo"
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "watchvideo"


def _download_file(url: str, output_path: Path, max_bytes: int) -> None:
    request = Request(url, headers={"User-Agent": "watchvideo/0.1"})
    total = 0
    with urlopen(request, timeout=60) as response, output_path.open("wb") as handle:
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise OSError(f"模型下载超过大小上限: {max_bytes} bytes")
            handle.write(chunk)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _remove_owned_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


@contextmanager
def _exclusive_setup_lock(lock_path: Path, timeout_seconds: float = 300.0) -> Iterator[None]:
    """函数职责和边界：串行化共享缓存初始化，不负责锁外的分析任务。"""
    if os.name != "posix":
        raise OSError("自动准备 whisper.cpp 当前仅支持 POSIX 系统")
    import fcntl

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("等待 whisper.cpp 初始化锁超时")
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
