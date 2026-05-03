from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.account import AccountConfig
from models.global_config import GlobalConfig


class ConfigManager:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.history_path = self.data_dir / "history_configs.json"
        self.active_path = self.data_dir / "active_configs.json"
        self.global_path = self.data_dir / "global_config.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_global_config(self) -> GlobalConfig:
        data = self._read_json(self.global_path, default={})
        return GlobalConfig.from_dict(data)

    def save_global_config(self, config: GlobalConfig) -> None:
        self._write_json(self.global_path, config.to_dict())

    def load_history(self) -> list[AccountConfig]:
        raw = self._read_json(self.history_path, default=[])
        if not isinstance(raw, list):
            return []
        return [AccountConfig.from_dict(item) for item in raw if isinstance(item, dict)]

    def save_history(self, accounts: list[AccountConfig]) -> None:
        self._write_json(self.history_path, [account.to_dict() for account in accounts])

    def append_history(self, account: AccountConfig) -> None:
        accounts = self.load_history()
        accounts.append(account)
        self.save_history(accounts)

    def load_active(self) -> list[AccountConfig] | None:
        raw = self._read_json(self.active_path, default=None)
        if raw is None:
            return None
        if not isinstance(raw, list):
            return []
        return [AccountConfig.from_dict(item) for item in raw if isinstance(item, dict)]

    def save_active(self, accounts: list[AccountConfig]) -> None:
        self._write_json(self.active_path, [account.to_dict() for account in accounts])

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        tmp.replace(path)
