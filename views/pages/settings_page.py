from __future__ import annotations

import flet as ft

from models.global_config import GlobalConfig
from services.config_manager import ConfigManager
from views.theme import colors


class SettingsPage(ft.Container):
    def __init__(self, config_manager: ConfigManager) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.config = self.config_manager.load_global_config()
        self.expand = True

        self.provider = ft.Dropdown(
            label="题库提供商",
            value=self.config.tiku_provider,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            options=[
                ft.dropdown.Option("TikuYanxi"),
                ft.dropdown.Option("TikuLike"),
                ft.dropdown.Option("AI"),
                ft.dropdown.Option("SiliconFlow"),
            ],
        )
        self.token = ft.TextField(
            label="全局题库 Token / Key",
            value=self.config.tiku_token,
            password=True,
            can_reveal_password=True,
            prefix_icon=ft.Icons.KEY_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
        )
        self.provider.on_change = self._autosave
        self.token.on_change = self._autosave
        self.token.on_blur = self._autosave
        self.save_hint = ft.Text("已自动保存", size=12, color=colors.MINT, opacity=0)

        self.content = self._build()

    def _build(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=22,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text(
                                    "全局设置",
                                    size=30,
                                    weight=ft.FontWeight.W_700,
                                    color=colors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "以下参数将应用到所有账号的底层任务中。",
                                    size=14,
                                    color=colors.TEXT_MUTED,
                                ),
                            ],
                        ),
                        ft.Container(
                            width=48,
                            height=48,
                            border_radius=14,
                            bgcolor=colors.SURFACE_HIGH,
                            content=ft.Icon(ft.Icons.TUNE_ROUNDED, color=colors.KLEIN_BLUE_SOFT),
                        ),
                    ],
                ),
                ft.Container(
                    border_radius=18,
                    bgcolor=colors.SURFACE_LOW,
                    border=ft.border.all(1, colors.OUTLINE_SOFT),
                    padding=28,
                    shadow=ft.BoxShadow(
                        blur_radius=32,
                        spread_radius=-8,
                        color="#66000000",
                        offset=ft.Offset(0, 18),
                    ),
                    content=ft.Column(
                        tight=True,
                        spacing=18,
                        controls=[
                            ft.Row(
                                spacing=14,
                                controls=[
                                    ft.Container(width=260, content=self.provider),
                                    ft.Container(expand=True, content=self.token),
                                ],
                            ),
                            ft.Container(
                                border_radius=14,
                                bgcolor=colors.SURFACE,
                                border=ft.border.all(1, colors.OUTLINE_SOFT),
                                padding=18,
                                content=ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Row(
                                            spacing=12,
                                            controls=[
                                                ft.Icon(ft.Icons.SAVE_ROUNDED, color=colors.MINT, size=20),
                                                ft.Column(
                                                    spacing=2,
                                                    controls=[
                                                        ft.Text(
                                                            "无缝保存已启用",
                                                            size=14,
                                                            weight=ft.FontWeight.W_700,
                                                            color=colors.TEXT_PRIMARY,
                                                        ),
                                                        ft.Text(
                                                            "修改提供商或 Token 后会自动写入 global_config.json。",
                                                            size=12,
                                                            color=colors.TEXT_MUTED,
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        self.save_hint,
                                    ],
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _autosave(self, _: ft.ControlEvent | None = None) -> None:
        self.config = GlobalConfig(
            tiku_provider=self.provider.value or "TikuYanxi",
            tiku_token=self.token.value or "",
            max_workers=self.config.max_workers,
            command=self.config.command,
            dark_mode=self.config.dark_mode,
            enable_motion=self.config.enable_motion,
        )
        self.config_manager.save_global_config(self.config)
        self._show_saved_hint()

    def _show_saved_hint(self) -> None:
        self.save_hint.opacity = 1
        page = self._page_or_none()
        if page is None:
            return
        self.save_hint.update()
        page.run_task(self._fade_hint)

    async def _fade_hint(self) -> None:
        import asyncio

        await asyncio.sleep(1.1)
        self.save_hint.opacity = 0
        if self._page_or_none() is not None:
            self.save_hint.update()

    def _page_or_none(self) -> ft.Page | None:
        try:
            return self.page
        except RuntimeError:
            return None
