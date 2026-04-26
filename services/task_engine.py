from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

from core.event_bus import EventBus
from core.events import LogEvent, LogLevel, TaskStateEvent, TaskStatus
from services.log_parser import LogParser


CMD_ENCODING = "gb18030" if sys.platform == "win32" else "utf-8"


class TaskEngine:
    def __init__(self, event_bus: EventBus, log_parser: LogParser, cwd: str | Path) -> None:
        self._event_bus = event_bus
        self._log_parser = log_parser
        self._cwd = Path(cwd)
        self._processes: dict[str, subprocess.Popen] = {}
        self._stopping: set[str] = set()
        self._lock = threading.RLock()

    def start(self, account_id: str, command: list[str]) -> None:
        with self._lock:
            process = self._processes.get(account_id)
            if process is not None and process.poll() is None:
                self._event_bus.publish_sync(LogEvent(account_id=account_id, message="任务已经在运行中。", level=LogLevel.WARNING))
                return
            self._stopping.discard(account_id)

            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(self._cwd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    encoding=CMD_ENCODING,
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                )
            except Exception as exc:
                self._event_bus.publish_sync(LogEvent(account_id=account_id, message=f"启动失败：{exc}", level=LogLevel.ERROR))
                self._event_bus.publish_sync(TaskStateEvent(account_id=account_id, status=TaskStatus.FAILED, reason=str(exc)))
                return

            self._processes[account_id] = process
            self._event_bus.publish_sync(TaskStateEvent(account_id=account_id, status=TaskStatus.RUNNING))
            self._event_bus.publish_sync(LogEvent(account_id=account_id, message=f"启动命令：{' '.join(command)}"))
            threading.Thread(target=self._read_stdout, args=(account_id, process), daemon=True).start()

    def stop(self, account_id: str) -> None:
        with self._lock:
            self._stopping.add(account_id)
            process = self._processes.pop(account_id, None)

        self._terminate_process(account_id, process)
        self._event_bus.publish_sync(TaskStateEvent(account_id=account_id, status=TaskStatus.STOPPED))

    def stop_all(self) -> None:
        with self._lock:
            items = list(self._processes.items())
            self._processes.clear()
            for account_id, _ in items:
                self._stopping.add(account_id)

        for account_id, process in items:
            self._terminate_process(account_id, process)
            self._event_bus.publish_sync(TaskStateEvent(account_id=account_id, status=TaskStatus.STOPPED))

    def _terminate_process(self, account_id: str, process: subprocess.Popen | None) -> None:
        if process is not None and process.poll() is None:
            self._event_bus.publish_sync(LogEvent(account_id=account_id, message="正在强制停止任务。", level=LogLevel.WARNING))
            try:
                if process.stdout is not None:
                    process.stdout.close()
            except Exception:
                pass

            if sys.platform == "win32":
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5,
                    )
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
            else:
                try:
                    process.kill()
                except Exception:
                    pass

    def _read_stdout(self, account_id: str, process: subprocess.Popen) -> None:
        stopped = False
        return_code = None
        buffer: list[str] = []
        try:
            if process.stdout is not None:
                while True:
                    if self._is_stopping(account_id):
                        break
                    char = process.stdout.read(1)
                    if not char:
                        break
                    if char in {"\n", "\r"}:
                        self._flush_stdout_buffer(account_id, buffer)
                        buffer = []
                    else:
                        buffer.append(char)
                self._flush_stdout_buffer(account_id, buffer)
        except ValueError:
            pass
        finally:
            return_code = process.poll()
            if return_code is None:
                try:
                    return_code = process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    return_code = -9

            with self._lock:
                self._processes.pop(account_id, None)
                stopped = account_id in self._stopping
                if stopped:
                    self._stopping.discard(account_id)

        if stopped:
            return

        status = TaskStatus.COMPLETED if return_code == 0 else TaskStatus.FAILED
        level = LogLevel.SUCCESS if return_code == 0 else LogLevel.ERROR
        self._event_bus.publish_sync(LogEvent(account_id=account_id, message=f"进程已退出，返回码：{return_code}", level=level))
        self._event_bus.publish_sync(TaskStateEvent(account_id=account_id, status=status, reason=str(return_code)))

    def _flush_stdout_buffer(self, account_id: str, buffer: list[str]) -> None:
        if not buffer or self._is_stopping(account_id):
            return
        self._log_parser.parse_line_sync(account_id, "".join(buffer))

    def _is_stopping(self, account_id: str) -> bool:
        with self._lock:
            return account_id in self._stopping
