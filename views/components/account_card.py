from __future__ import annotations

from collections.abc import Callable

import flet as ft

from core.events import TaskStatus
from viewmodels.account_viewmodel import AccountCardState
from views.theme import colors


class AccountCard(ft.Container):
    def __init__(
        self,
        state: AccountCardState,
        on_edit: Callable[[AccountCardState], None],
        on_start: Callable[[str], None],
        on_stop: Callable[[str], None],
        on_delete: Callable[[str], None],
        reveal_delay_ms: int = 0,
    ) -> None:
        super().__init__()
        self.account = state
        self.on_edit = on_edit
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_delete = on_delete
        self._reveal_delay_ms = reveal_delay_ms
        self.opacity = 0
        self.offset = ft.Offset(0, 0.08)
        self.animate_opacity = ft.Animation(260, ft.AnimationCurve.EASE_OUT_CUBIC)
        self.animate_offset = ft.Animation(320, ft.AnimationCurve.EASE_OUT_CUBIC)
        self.animate = ft.Animation(180, ft.AnimationCurve.EASE_OUT)
        self.border_radius = 16
        self.bgcolor = colors.SURFACE
        self.padding = ft.padding.symmetric(horizontal=18, vertical=16)
        self.border = ft.border.all(1, colors.OUTLINE_SOFT)
        self.shadow = ft.BoxShadow(blur_radius=28, spread_radius=-12, color="#66000000", offset=ft.Offset(0, 14))
        self.content = self._build_content()

    def did_mount(self) -> None:
        if self._is_mounted():
            self.page.run_task(self._reveal)

    async def _reveal(self) -> None:
        if self._reveal_delay_ms:
            import asyncio

            await asyncio.sleep(self._reveal_delay_ms / 1000)
        self.opacity = 1
        self.offset = ft.Offset(0, 0)
        self.update()

    def refresh_state(self, state: AccountCardState) -> None:
        self.account = state
        self.content = self._build_content()
        if self._is_mounted():
            self.update()

    def _build_content(self) -> ft.Control:
        return ft.Row(
            spacing=18,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self._progress_block(), self._text_block(), self._status_pill(), self._actions()],
        )

    def _progress_block(self) -> ft.Control:
        progress_value = max(0, min(self.account.percent, 100)) / 100
        return ft.Container(
            width=64,
            height=64,
            border_radius=18,
            bgcolor=colors.SURFACE_HIGH,
            content=ft.Stack(
                alignment=ft.Alignment(0, 0),
                controls=[
                    ft.ProgressRing(
                        value=progress_value,
                        width=48,
                        height=48,
                        stroke_width=5,
                        color=self._progress_color(),
                        bgcolor=colors.OUTLINE_SOFT,
                    ),
                    ft.Text(f"{int(self.account.percent)}%", size=11, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                ],
            ),
        )

    def _text_block(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=4,
            controls=[
                ft.Text(
                    self.account.title or self.account.phone or "未命名账号",
                    size=16,
                    weight=ft.FontWeight.W_700,
                    color=colors.TEXT_PRIMARY,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    self.account.course_info,
                    size=13,
                    color=colors.TEXT_MUTED,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    self.account.action_info,
                    size=12,
                    color=colors.KLEIN_BLUE_SOFT,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
        )

    def _status_pill(self) -> ft.Control:
        label, fg, bg = self._status_style()
        return ft.Container(
            height=30,
            border_radius=15,
            padding=ft.padding.symmetric(horizontal=12),
            bgcolor=bg,
            content=ft.Row(
                spacing=7,
                controls=[
                    ft.Icon(ft.Icons.CIRCLE, size=8, color=fg),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=fg),
                ],
            ),
        )

    def _actions(self) -> ft.Control:
        account_id = self.account.account_id
        running = self.account.status == TaskStatus.RUNNING
        return ft.Row(
            spacing=8,
            controls=[
                self._icon_action(ft.Icons.TUNE_ROUNDED, "配置", lambda _: self.on_edit(self.account)),
                self._icon_action(ft.Icons.PLAY_ARROW_ROUNDED, "启动", lambda _: self.on_start(account_id), colors.MINT, enabled=not running, active=not running),
                self._icon_action(ft.Icons.STOP_ROUNDED, "停止", lambda _: self.on_stop(account_id), colors.WARNING, enabled=running, active=running),
                self._icon_action(ft.Icons.DELETE_OUTLINE_ROUNDED, "删除", lambda _: self.on_delete(account_id), colors.CORAL),
            ],
        )

    def _icon_action(
        self,
        icon: str,
        tooltip: str,
        on_click,
        icon_color: str | None = None,
        enabled: bool = True,
        active: bool = True,
    ) -> ft.Control:
        button = ft.Container(
            width=38,
            height=38,
            border_radius=12,
            bgcolor=colors.SURFACE_HIGH if active else colors.SURFACE,
            ink=enabled,
            tooltip=tooltip,
            animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            opacity=1 if enabled else 0.38,
            on_click=on_click if enabled else None,
            content=ft.Icon(icon, size=19, color=icon_color or colors.KLEIN_BLUE_SOFT),
        )

        def handle_hover(event: ft.HoverEvent) -> None:
            if not enabled:
                return
            button.bgcolor = colors.SURFACE_HIGHEST if event.data == "true" else colors.SURFACE_HIGH
            button.scale = 1.04 if event.data == "true" else 1
            button.update()

        button.on_hover = handle_hover
        return button

    def _progress_color(self) -> str:
        if self.account.status == TaskStatus.COMPLETED:
            return colors.MINT
        if self.account.status == TaskStatus.FAILED:
            return colors.CORAL
        if self.account.status == TaskStatus.STOPPED:
            return colors.WARNING
        return colors.KLEIN_BLUE_SOFT

    def _status_style(self) -> tuple[str, str, str]:
        match self.account.status:
            case TaskStatus.RUNNING:
                return "运行中", colors.MINT, "#1D3F32"
            case TaskStatus.COMPLETED:
                return "已完成", colors.MINT, "#1D3F32"
            case TaskStatus.FAILED:
                return "失败", colors.CORAL, "#4A282A"
            case TaskStatus.STOPPED:
                return "已停止", colors.WARNING, "#4A3D24"
            case _:
                return "待启动", colors.KLEIN_BLUE_SOFT, "#22345F"

    def _is_mounted(self) -> bool:
        try:
            return self.page is not None
        except RuntimeError:
            return False
