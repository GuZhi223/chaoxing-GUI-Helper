from __future__ import annotations

import flet as ft

from views.theme import animations, colors


class LoadingOverlay(ft.Container):
    def __init__(
        self,
        message: str = "加载中...",
        fullscreen: bool = False,
        visible: bool = False,
        spinner_size: float = 44,
        spinner_stroke_width: float = 4,
    ) -> None:
        super().__init__()
        self._fullscreen = fullscreen
        self.visible = visible
        self.opacity = 1 if visible else 0
        self.animate_opacity = animations.LOADING_OVERLAY_FADE
        self.bgcolor = colors.OVERLAY_DIM if fullscreen else colors.OVERLAY_BG
        self.border_radius = 0 if fullscreen else 16
        self.alignment = ft.Alignment(0, 0)

        spinner = ft.ProgressRing(
            width=spinner_size,
            height=spinner_size,
            stroke_width=spinner_stroke_width,
            color=colors.LOADING_SPINNER,
            bgcolor=colors.LOADING_SPINNER_TRACK,
        )

        controls: list[ft.Control] = [spinner]
        if message:
            controls.append(
                ft.Text(
                    message,
                    size=14,
                    weight=ft.FontWeight.W_500,
                    color=colors.TEXT_SECONDARY,
                )
            )

        self.content = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            tight=True,
            controls=controls,
        )

    def show(self, message: str | None = None) -> None:
        if message is not None and isinstance(self.content, ft.Column):
            label = self.content.controls[-1]
            if isinstance(label, ft.Text):
                label.value = message
        self.visible = True
        self.opacity = 1
        self._safe_update()

    def hide(self) -> None:
        self.opacity = 0
        self._safe_update()

    def attach_to_page(self, page: ft.Page) -> None:
        if self._fullscreen and self not in page.overlay:
            page.overlay.append(self)
            page.update()

    def detach_from_page(self, page: ft.Page) -> None:
        if self in page.overlay:
            page.overlay.remove(self)
            page.update()

    def _safe_update(self) -> None:
        try:
            self.update()
        except RuntimeError:
            pass


class LoadingDots(ft.Container):
    def __init__(
        self,
        dot_count: int = 3,
        dot_size: float = 8,
        color: str | None = None,
    ) -> None:
        super().__init__()
        self.alignment = ft.Alignment(0, 0)
        self._dot_size = dot_size
        self._active_index = 0
        self._dot_count = dot_count
        self._color = color or colors.LOADING_DOT
        self._inactive_color = colors.LOADING_DOT_INACTIVE
        self._dots: list[ft.Container] = []
        self.content = self._build_dots()

    def _build_dots(self) -> ft.Control:
        self._dots = [
            ft.Container(
                width=self._dot_size,
                height=self._dot_size,
                border_radius=self._dot_size / 2,
                bgcolor=self._color if i == 0 else self._inactive_color,
            )
            for i in range(self._dot_count)
        ]
        return ft.Row(
            spacing=self._dot_size * 0.8,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=self._dots,
        )

    def did_mount(self) -> None:
        if self._is_mounted():
            self.page.run_task(self._animate_loop)

    async def _animate_loop(self) -> None:
        import asyncio

        while self._is_mounted():
            for i in range(self._dot_count):
                if not self._is_mounted():
                    return
                for j, dot in enumerate(self._dots):
                    dot.bgcolor = self._color if j == i else self._inactive_color
                self._safe_update()
                await asyncio.sleep(0.4)

    def _safe_update(self) -> None:
        try:
            self.update()
        except RuntimeError:
            pass

    def _is_mounted(self) -> bool:
        try:
            return self.page is not None
        except RuntimeError:
            return False
