from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass(frozen=True, slots=True)
class BaseEvent:
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, slots=True)
class LogEvent(BaseEvent):
    account_id: str = ""
    message: str = ""
    level: LogLevel = LogLevel.INFO
    raw: str | None = None
    is_elegant: bool = False


@dataclass(frozen=True, slots=True)
class ProgressEvent(BaseEvent):
    account_id: str = ""
    course: str = ""
    chapter: str = ""
    video_title: str = ""
    percent: float = 0.0
    status: TaskStatus = TaskStatus.RUNNING
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChapterEvent(BaseEvent):
    account_id: str = ""
    chapter: str = ""
    status: TaskStatus = TaskStatus.RUNNING
    message: str = ""


@dataclass(frozen=True, slots=True)
class TaskStateEvent(BaseEvent):
    account_id: str = ""
    status: TaskStatus = TaskStatus.IDLE
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ConfigChangedEvent(BaseEvent):
    scope: str = "global"
    payload: dict[str, Any] = field(default_factory=dict)
