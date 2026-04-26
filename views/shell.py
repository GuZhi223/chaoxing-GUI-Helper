from __future__ import annotations

import asyncio

import flet as ft

from core.event_bus import EventBus
from core.events import TaskStatus
from services.config_manager import ConfigManager
from viewmodels.account_viewmodel import AccountViewModel
from views.pages.account_page import AccountPage
from views.pages.history_page import HistoryPage
from views.pages.logs_page import LogsPage
from views.pages.settings_page import SettingsPage
from views.theme import colors


class AppShell:
    def __init__(
        self,
        page: ft.Page,
        account_vm: AccountViewModel,
        config_manager: ConfigManager,
        event_bus: EventBus,
    ) -> None:
        self.page = page
        self.account_vm = account_vm
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.selected_route = "accounts"
        self._nav_items: dict[str, ft.Container] = {}
        self._page_cache: dict[str, ft.Control] = {}
        self._exit_dialog: ft.AlertDialog | None = None
        self.content_host = ft.AnimatedSwitcher(
            content=self._build_page("accounts"),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=260,
            reverse_duration=180,
            switch_in_curve=ft.AnimationCurve.EASE_OUT_CUBIC,
            switch_out_curve=ft.AnimationCurve.EASE_IN_CUBIC,
            expand=True,
        )

    def build(self) -> ft.Control:
        return ft.Row(
            expand=True,
            spacing=0,
            controls=[
                self._sidebar(),
                ft.Container(
                    expand=True,
                    bgcolor=colors.SURFACE_BG,
                    padding=ft.padding.symmetric(horizontal=28, vertical=24),
                    content=self.content_host,
                ),
            ],
        )

    def _sidebar(self) -> ft.Control:
        return ft.Container(
            width=252,
            bgcolor=colors.SURFACE_SIDEBAR,
            padding=ft.padding.only(left=18, right=18, top=26, bottom=18),
            content=ft.Column(
                spacing=14,
                controls=[
                    self._brand(),
                    ft.Divider(height=24, color=colors.OUTLINE_SOFT),
                    self._nav_item("accounts", "账号运行", ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED),
                    self._nav_item("history", "历史配置", ft.Icons.HISTORY_ROUNDED),
                    self._nav_item("settings", "全局设置", ft.Icons.TUNE_ROUNDED),
                    self._nav_item("logs", "运行日志", ft.Icons.TERMINAL_ROUNDED),
                    ft.Container(expand=True),
                    self._status_card(),
                ],
            ),
        )

    def _brand(self) -> ft.Control:
        return ft.Row(
            spacing=12,
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    border_radius=12,
                    bgcolor=colors.KLEIN_BLUE,
                    shadow=ft.BoxShadow(
                        blur_radius=22,
                        spread_radius=1,
                        color="#402F65FF",
                        offset=ft.Offset(0, 8),
                    ),
                    content=ft.Icon(ft.Icons.AUTO_AWESOME_ROUNDED, color=colors.TEXT_PRIMARY, size=22),
                ),
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text("chaoxing", size=20, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                        ft.Text("任务控制台", size=12, color=colors.TEXT_MUTED),
                    ],
                ),
            ],
        )

    def _nav_item(self, route: str, label: str, icon: str) -> ft.Container:
        item = ft.Container(
            height=46,
            border_radius=12,
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            ink=True,
            on_click=lambda _: self._select(route),
            padding=ft.padding.symmetric(horizontal=14),
        )
        item.content = ft.Row(spacing=12, controls=[ft.Icon(icon, size=21), ft.Text(label, size=14)])
        self._nav_items[route] = item
        self._apply_nav_style(route)
        return item

    def _apply_nav_style(self, route: str) -> None:
        item = self._nav_items.get(route)
        if item is None:
            return

        selected = self.selected_route == route
        item.bgcolor = colors.SURFACE_HIGH if selected else colors.TRANSPARENT
        row = item.content
        if not isinstance(row, ft.Row):
            return
        icon = row.controls[0]
        label = row.controls[1]
        icon.color = colors.KLEIN_BLUE_SOFT if selected else colors.TEXT_MUTED
        label.color = colors.TEXT_PRIMARY if selected else colors.TEXT_SECONDARY
        label.weight = ft.FontWeight.W_600 if selected else ft.FontWeight.W_500

    def _status_card(self) -> ft.Control:
        return ft.Container(
            border_radius=14,
            bgcolor=colors.SURFACE,
            padding=16,
            border=ft.border.all(1, colors.OUTLINE_SOFT),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.CIRCLE, size=10, color=colors.MINT),
                            ft.Text("Core online", size=12, color=colors.TEXT_SECONDARY),
                        ],
                    ),
                    ft.Text("Flet + MVVM", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                ],
            ),
        )

    def _select(self, route: str) -> None:
        if route == self.selected_route:
            return

        previous_route = self.selected_route
        self.selected_route = route
        self.content_host.content = self._build_page(route)

        self._apply_nav_style(previous_route)
        self._apply_nav_style(route)

        self.content_host.update()
        for item in (self._nav_items.get(previous_route), self._nav_items.get(route)):
            if item is not None:
                item.update()

    def _build_page(self, route: str) -> ft.Control:
        if route == "accounts":
            return AccountPage(self.account_vm)
        if route == "settings":
            return SettingsPage(self.config_manager)
        if route == "logs":
            if route not in self._page_cache:
                self._page_cache[route] = LogsPage(self.account_vm, self.event_bus)
            return self._page_cache[route]
        if route == "history":
            return HistoryPage(self.config_manager, self.account_vm)

        return self._placeholder_page(title="模块骨架", subtitle="页面正在建设中。", icon=ft.Icons.APPS_ROUNDED)

    def handle_exit(self) -> None:
        has_running_task = any(card.status == TaskStatus.RUNNING for card in self.account_vm.cards)
        if not has_running_task:
            self._exit_now()
            return

        self._show_exit_dialog()

    def _show_exit_dialog(self) -> None:
        self._exit_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=colors.SURFACE_LOW,
            title=ft.Text("确认退出", size=20, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
            content=ft.Text(
                "当前有正在运行的刷课任务，确认要退出并强制结束所有任务吗？",
                size=14,
                color=colors.TEXT_SECONDARY,
            ),
            actions=[
                ft.TextButton("取消", on_click=self._cancel_exit),
                ft.Container(
                    height=40,
                    border_radius=10,
                    bgcolor=colors.CORAL,
                    ink=True,
                    padding=ft.padding.symmetric(horizontal=18),
                    on_click=self._confirm_exit,
                    content=ft.Row(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.POWER_SETTINGS_NEW_ROUNDED, size=18, color=colors.TEXT_PRIMARY),
                            ft.Text("确认退出", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                        ],
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self._exit_dialog not in self.page.overlay:
            self.page.overlay.append(self._exit_dialog)
        self._exit_dialog.open = True
        self.page.update()
        self._exit_dialog.update()

    def _cancel_exit(self, _: ft.ControlEvent | None = None) -> None:
        if self._exit_dialog is not None:
            self._exit_dialog.open = False
            self.page.update()

    def _confirm_exit(self, _: ft.ControlEvent | None = None) -> None:
        if self._exit_dialog is not None:
            self._exit_dialog.open = False
            self.page.update()
        self._exit_now()

    def _exit_now(self) -> None:
        self.account_vm.stop_all()
        self.page.window.prevent_close = False
        self.page.update()
        self.page.run_task(self._destroy_window)

    async def _destroy_window(self) -> None:
        result = self.page.window.destroy()
        if asyncio.iscoroutine(result):
            await result

    def _placeholder_page(self, title: str, subtitle: str, icon: str) -> ft.Control:
        return ft.Container(
            expand=True,
            animate_opacity=260,
            content=ft.Column(
                spacing=22,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text(title, size=30, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                    ft.Text(subtitle, size=14, color=colors.TEXT_MUTED),
                                ],
                            ),
                            ft.Container(
                                width=48,
                                height=48,
                                border_radius=14,
                                bgcolor=colors.SURFACE_HIGH,
                                content=ft.Icon(icon, color=colors.KLEIN_BLUE_SOFT),
                            ),
                        ],
                    ),
                    ft.Container(
                        expand=True,
                        border_radius=18,
                        bgcolor=colors.SURFACE_LOW,
                        border=ft.border.all(1, colors.OUTLINE_SOFT),
                        padding=28,
                        content=ft.Column(
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.ProgressRing(width=68, height=68, stroke_width=5, color=colors.KLEIN_BLUE_SOFT),
                                ft.Text("模块骨架已就绪", size=18, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                                ft.Text("下一阶段会把真实业务模块接入这里。", size=13, color=colors.TEXT_MUTED),
                            ],
                        ),
                    ),
                ],
            ),
        )
