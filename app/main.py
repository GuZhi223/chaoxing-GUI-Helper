from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.event_bus import EventBus
from services.config_manager import ConfigManager
from services.log_parser import LogParser
from services.task_engine import TaskEngine
from viewmodels.account_viewmodel import AccountViewModel
from views.shell import AppShell
from views.theme import colors


def main(page: ft.Page) -> None:
    page.title = "chaoxing GUI Helper"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = colors.SURFACE_BG
    page.padding = 0

    page.window.width = 1180
    page.window.height = 820
    page.window.min_width = 980
    page.window.min_height = 700
    page.window.prevent_close = True

    event_bus = EventBus()
    config_manager = ConfigManager(PROJECT_ROOT / "data")
    log_parser = LogParser(event_bus)
    task_engine = TaskEngine(event_bus, log_parser, PROJECT_ROOT)
    account_vm = AccountViewModel(config_manager, task_engine, event_bus, PROJECT_ROOT)

    page.session.store.set("event_bus", event_bus)
    page.session.store.set("config_manager", config_manager)
    page.session.store.set("log_parser", log_parser)
    page.session.store.set("task_engine", task_engine)
    page.session.store.set("account_vm", account_vm)

    shell = AppShell(page, account_vm, config_manager, event_bus)

    def on_window_event(event: ft.ControlEvent) -> None:
        event_type = getattr(getattr(event, "type", None), "value", None) or getattr(event, "data", "")
        if str(event_type).lower() == "close":
            shell.handle_exit()

    page.window.on_event = on_window_event
    page.on_window_event = on_window_event
    page.add(shell.build())


if __name__ == "__main__":
    ft.run(main)
