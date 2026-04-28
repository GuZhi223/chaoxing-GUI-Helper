from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from core.events import TaskStatus


@dataclass(slots=True)
class AccountConfig:
    username: str = ""
    password: str = ""
    school: str = ""
    remark: str = ""
    course_url: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccountConfig:
        return cls(
            username=str(data.get("username", "")),
            password=str(data.get("password", "")),
            school=str(data.get("school", "")),
            remark=str(data.get("remark", "")),
            course_url=str(data.get("course_url", "")),
            options=dict(data.get("options", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AccountRuntimeState:
    account_id: str = field(default_factory=lambda: uuid4().hex)
    title: str = "新账号"
    status: TaskStatus = TaskStatus.IDLE
    percent: float = 0.0
    chapter: str = ""
    video_title: str = ""
    last_message: str = ""
    config: AccountConfig = field(default_factory=AccountConfig)
    last_run_time: str = ""
    run_start_time: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccountRuntimeState:
        status_value = data.get("status", TaskStatus.IDLE.value)
        run_start_raw = data.get("run_start_time")
        run_start_time = datetime.fromisoformat(run_start_raw) if run_start_raw else None
        return cls(
            account_id=str(data.get("account_id") or uuid4().hex),
            title=str(data.get("title", "新账号")),
            status=TaskStatus(status_value),
            percent=float(data.get("percent", 0.0)),
            chapter=str(data.get("chapter", "")),
            video_title=str(data.get("video_title", "")),
            last_message=str(data.get("last_message", "")),
            config=AccountConfig.from_dict(dict(data.get("config", {}))),
            last_run_time=str(data.get("last_run_time", "")),
            run_start_time=run_start_time,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        if self.run_start_time is not None:
            data["run_start_time"] = self.run_start_time.isoformat()
        else:
            data["run_start_time"] = None
        return data
