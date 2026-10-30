from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
import signal
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, IO

from .models import ToolStatus, redact_sensitive_urls


SENSITIVE_OPTION_MARKERS = (
    "prompt",
    "password",
    "passwd",
    "token",
    "cookie",
    "header",
    "authorization",
    "api-key",
    "apikey",
    "secret",
)


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str | bytes
    stderr: str | bytes
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class CommandError(RuntimeError):
    def __init__(self, result: CommandResult):
        self.result = result
        stderr = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else result.stderr
        safe_arguments, secrets = _redact_command_arguments(result.args)
        command = " ".join(safe_arguments)
        if len(command) > 1000:
            command = command[:997] + "..."
        detail = stderr
        for secret in secrets:
            detail = detail.replace(secret, "[REDACTED]")
        detail = redact_sensitive_urls(detail).strip()
        suffix = f"\n{detail}" if detail else ""
        super().__init__(f"命令执行失败: {command}{suffix}")


class CommandRunner:
    """函数职责和边界：统一限制外部命令的执行时间和返回文本大小。"""

    def __init__(
        self,
        timeout_seconds: float = 7200.0,
        max_output_bytes: int = 4 * 1024 * 1024,
        max_error_bytes: int = 64 * 1024,
        progress: Callable[[str], None] | None = None,
    ):
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds 必须是有限正数")
        if max_output_bytes <= 0 or max_error_bytes <= 0:
            raise ValueError("输出上限必须大于 0")
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.max_error_bytes = max_error_bytes
        self.progress = progress

    def run(
        self,
        args: list[str],
        cwd: Path | None = None,
        check: bool = True,
        text: bool = True,
        timeout_seconds: float | None = None,
    ) -> CommandResult:
        effective_timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        if not math.isfinite(effective_timeout) or effective_timeout <= 0:
            raise ValueError("timeout_seconds 必须是有限正数")
        if self.progress:
            self.progress(Path(str(args[0])).name if args else "unknown")

        # 使用临时文件承接输出，避免长时间命令将 stdout/stderr 无界累积在内存中。
        with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(
            mode="w+b"
        ) as stderr_file:
            process = subprocess.Popen(
                args,
                cwd=cwd,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=os.name == "posix",
            )
            try:
                returncode = process.wait(timeout=effective_timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process)
                returncode = 124
                timed_out = True
            except BaseException:
                _terminate_process_tree(process)
                raise

            stdout, stdout_truncated = _read_bounded_output(
                stdout_file,
                limit=self.max_output_bytes,
                text=text,
            )
            stderr, stderr_truncated = _read_bounded_output(
                stderr_file,
                limit=self.max_error_bytes,
                text=text,
            )

        if timed_out:
            timeout_message = f"命令执行超过 {effective_timeout:g} 秒，已终止"
            stderr = _append_error(stderr, timeout_message, text=text)
        result = CommandResult(
            args=args,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
        )
        if timed_out or (check and result.returncode != 0):
            raise CommandError(result)
        return result

    def run_json(self, args: list[str], cwd: Path | None = None) -> dict[str, Any]:
        result = self.run(args, cwd=cwd, text=True)
        if result.stdout_truncated:
            raise CommandError(
                CommandResult(
                    args=result.args,
                    returncode=1,
                    stdout=result.stdout,
                    stderr="命令输出超过上限，无法安全解析 JSON",
                    stdout_truncated=True,
                    stderr_truncated=result.stderr_truncated,
                )
            )
        return json.loads(str(result.stdout))


def check_tool(name: str) -> ToolStatus:
    path = shutil.which(name)
    if not path:
        return ToolStatus(name=name, path=None)

    version: str | None = None
    try:
        completed = CommandRunner(
            timeout_seconds=10.0,
            max_output_bytes=16 * 1024,
            max_error_bytes=16 * 1024,
        ).run([name, "--version"], check=False)
        output = (str(completed.stdout) or str(completed.stderr)).splitlines()
        version = output[0] if output else None
    except (CommandError, OSError):
        version = None
    return ToolStatus(name=name, path=path, version=version)


def _read_bounded_output(
    handle: IO[bytes],
    limit: int,
    text: bool,
) -> tuple[str | bytes, bool]:
    handle.flush()
    size = handle.seek(0, 2)
    truncated = size > limit
    if truncated:
        handle.seek(-limit, 2)
    else:
        handle.seek(0)
    payload = handle.read(limit)
    if truncated:
        payload = "[... 输出已截断 ...]\n".encode("utf-8") + payload
    if text:
        return payload.decode("utf-8", errors="replace"), truncated
    return payload, truncated


def _append_error(value: str | bytes, message: str, text: bool) -> str | bytes:
    if text:
        prefix = str(value).rstrip()
        return f"{prefix}\n{message}" if prefix else message
    prefix = bytes(value).rstrip()
    encoded = message.encode("utf-8")
    return prefix + (b"\n" if prefix else b"") + encoded


def _terminate_process_tree(process: subprocess.Popen, grace_seconds: float = 1.0) -> None:
    """函数职责和边界：超时或中断时先 TERM 再 KILL 本次命令进程组。"""
    if os.name != "posix":  # pragma: no cover - 媒体流程不支持 Windows
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        return

    process_group = process.pid
    try:
        os.killpg(process_group, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return

    # 在 KILL 前不 reap 进程组 leader，避免 PID 被复用后误伤无关进程。
    time.sleep(grace_seconds)
    try:
        os.killpg(process_group, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _redact_command_arguments(args: list[str]) -> tuple[list[str], set[str]]:
    """函数职责和边界：屏蔽敏感选项值和 URL 凭据，仅用于错误展示。"""
    redacted: list[str] = []
    secrets: set[str] = set()
    hide_next = False
    for raw_argument in args:
        argument = str(raw_argument)
        if hide_next:
            if argument:
                secrets.add(argument)
            redacted.append("[REDACTED]")
            hide_next = False
            continue

        if argument.startswith("-") and "=" in argument:
            option, value = argument.split("=", 1)
            if _is_sensitive_option(option):
                if value:
                    secrets.add(value)
                redacted.append(f"{option}=[REDACTED]")
                continue

        redacted.append(redact_sensitive_urls(argument))
        if argument.startswith("-") and _is_sensitive_option(argument):
            hide_next = True
    return redacted, secrets


def _is_sensitive_option(option: str) -> bool:
    normalized = option.lower().replace("_", "-")
    return any(marker in normalized for marker in SENSITIVE_OPTION_MARKERS)
