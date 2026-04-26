from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class GlobalConfig:
    tiku_provider: str = "TikuYanxi"
    tiku_token: str = ""
    max_workers: int = 3
    command: list[str] | None = None
    dark_mode: bool = True
    enable_motion: bool = True

    @classmethod
    def default(cls) -> GlobalConfig:
        return cls(command=["./chaoxing.exe"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalConfig:
        return cls(
            tiku_provider=str(data.get("tiku_provider", "TikuYanxi")),
            tiku_token=str(data.get("tiku_token", "")),
            max_workers=int(data.get("max_workers", 3)),
            command=list(data.get("command") or ["./chaoxing.exe"]),
            dark_mode=bool(data.get("dark_mode", True)),
            enable_motion=bool(data.get("enable_motion", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
