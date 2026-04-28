from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class GlobalConfig:
    tiku_provider: str = "TikuYanxi"
    tiku_token: str = ""
    tiku_endpoint: str = ""
    tiku_model: str = ""
    tiku_adapter_url: str = ""
    tiku_submit: bool = True
    tiku_coverage: float = 0.6
    tiku_delay: int = 0
    max_workers: int = 3
    command: list[str] | None = None
    dark_mode: bool = True
    enable_motion: bool = True
    timeout: int = 30
    retry_count: int = 3
    proxy: str = ""

    @classmethod
    def default(cls) -> GlobalConfig:
        return cls(command=["./chaoxing.exe"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalConfig:
        return cls(
            tiku_provider=str(data.get("tiku_provider", "TikuYanxi")),
            tiku_token=str(data.get("tiku_token", "")),
            tiku_endpoint=str(data.get("tiku_endpoint", "")),
            tiku_model=str(data.get("tiku_model", "")),
            tiku_adapter_url=str(data.get("tiku_adapter_url", "")),
            tiku_submit=bool(data.get("tiku_submit", True)),
            tiku_coverage=float(data.get("tiku_coverage", 0.6)),
            tiku_delay=int(data.get("tiku_delay", 0)),
            max_workers=int(data.get("max_workers", 3)),
            command=list(data.get("command") or ["./chaoxing.exe"]),
            dark_mode=bool(data.get("dark_mode", True)),
            enable_motion=bool(data.get("enable_motion", True)),
            timeout=int(data.get("timeout", 30)),
            retry_count=int(data.get("retry_count", 3)),
            proxy=str(data.get("proxy", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
