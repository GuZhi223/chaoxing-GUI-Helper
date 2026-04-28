from __future__ import annotations

import flet as ft

from models.global_config import GlobalConfig
from services.config_manager import ConfigManager
from views.theme import colors

_VALID_PROXY_SCHEMES = ("http://", "https://", "socks5://", "socks4://")

_PROVIDER_LABELS = {
    "TikuYanxi": "言溪题库",
    "TikuLike": "LIKE 知识库",
    "TikuAdapter": "通用适配器",
    "AI": "AI 大模型",
    "SiliconFlow": "硅基流动 AI",
    "disabled": "关闭",
}

_PROVIDERS_NEED_TOKEN = {"TikuYanxi", "TikuLike", "AI", "SiliconFlow"}
_PROVIDERS_NEED_ENDPOINT = {"AI", "SiliconFlow"}
_PROVIDERS_NEED_MODEL = {"AI", "SiliconFlow"}
_PROVIDERS_NEED_ADAPTER_URL = {"TikuAdapter"}


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
            options=[ft.dropdown.Option(k, _PROVIDER_LABELS.get(k, k)) for k in _PROVIDER_LABELS],
        )
        self.token = ft.TextField(
            label="Token / API Key",
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
        self.endpoint = ft.TextField(
            label="Endpoint (接口地址)",
            value=self.config.tiku_endpoint,
            hint_text="https://open.bigmodel.cn/api/paas/v4",
            prefix_icon=ft.Icons.LINK_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            expand=True,
        )
        self.model = ft.TextField(
            label="Model (模型名称)",
            value=self.config.tiku_model,
            hint_text="glm-4-flash",
            prefix_icon=ft.Icons.SMART_TOY_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            width=220,
        )
        self.adapter_url = ft.TextField(
            label="适配器地址",
            value=self.config.tiku_adapter_url,
            hint_text="https://your-tiku-adapter.example.com",
            prefix_icon=ft.Icons.API_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            expand=True,
        )

        self.tiku_submit = ft.Switch(
            value=self.config.tiku_submit,
            active_color=colors.KLEIN_BLUE,
            active_track_color=colors.KLEIN_BLUE_SOFT,
            inactive_track_color=colors.SURFACE_HIGH,
            on_change=self._autosave,
        )
        self.tiku_coverage = ft.TextField(
            label="覆盖率",
            value=str(self.config.tiku_coverage),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.PERCENT_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            width=120,
        )
        self.tiku_delay = ft.TextField(
            label="查询延迟 (秒)",
            value=str(self.config.tiku_delay),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.HOURGLASS_TOP_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            width=140,
        )

        self.token_row = ft.Container()
        self.endpoint_model_row = ft.Container()
        self.adapter_url_row = ft.Container()
        self.tiku_common_row = ft.Container()

        self.provider.on_select = self._on_provider_change
        self.token.on_change = self._autosave
        self.token.on_blur = self._autosave
        self.endpoint.on_change = self._autosave
        self.endpoint.on_blur = self._autosave
        self.model.on_change = self._autosave
        self.model.on_blur = self._autosave
        self.adapter_url.on_change = self._autosave
        self.adapter_url.on_blur = self._autosave
        self.tiku_coverage.on_blur = self._on_validate_and_save
        self.tiku_delay.on_blur = self._on_validate_and_save

        self.max_workers = ft.TextField(
            label="并发数",
            value=str(self.config.max_workers),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.WORKSPACES_OUTLINED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            width=140,
        )
        self.timeout = ft.TextField(
            label="超时时间 (秒)",
            value=str(self.config.timeout),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.TIMER_OUTLINED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            width=180,
        )
        self.retry_count = ft.TextField(
            label="重试次数",
            value=str(self.config.retry_count),
            keyboard_type=ft.KeyboardType.NUMBER,
            prefix_icon=ft.Icons.REFRESH_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
            width=140,
        )
        self.proxy = ft.TextField(
            label="代理地址",
            value=self.config.proxy,
            hint_text="http://127.0.0.1:7890",
            prefix_icon=ft.Icons.LANGUAGE_ROUNDED,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
        )

        self.max_workers.on_blur = self._on_validate_and_save
        self.timeout.on_blur = self._on_validate_and_save
        self.retry_count.on_blur = self._on_validate_and_save
        self.proxy.on_change = self._autosave
        self.proxy.on_blur = self._autosave

        self.save_hint = ft.Text("已自动保存", size=12, color=colors.MINT, opacity=0)

        self.content = self._build()
        self._sync_provider_fields()

    def _build_card(self, title: str, controls: list) -> ft.Container:
        return ft.Container(
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
                spacing=14,
                controls=[
                    ft.Text(title, size=16, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                    *controls,
                ],
            ),
        )

    def _build(self) -> ft.Control:
        self.token_row = ft.Row(
            spacing=14,
            controls=[ft.Container(width=260, content=self.provider), ft.Container(expand=True, content=self.token)],
        )
        self.endpoint_model_row = ft.Row(
            spacing=14,
            visible=self.config.tiku_provider in _PROVIDERS_NEED_ENDPOINT,
            controls=[self.endpoint, self.model],
        )
        self.adapter_url_row = ft.Container(
            content=self.adapter_url,
            visible=self.config.tiku_provider in _PROVIDERS_NEED_ADAPTER_URL,
        )
        self.tiku_common_row = ft.Row(
            spacing=14,
            visible=self.config.tiku_provider != "disabled",
            controls=[
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text("自动提交", size=13, color=colors.TEXT_SECONDARY),
                        self.tiku_submit,
                    ],
                ),
                self.tiku_coverage,
                self.tiku_delay,
            ],
        )

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
                                ft.Text("全局设置", size=30, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                ft.Text("以下参数将应用到所有账号的底层任务中。", size=14, color=colors.TEXT_MUTED),
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
                self._build_card("题库设置", [
                    self.token_row,
                    self.endpoint_model_row,
                    self.adapter_url_row,
                    self.tiku_common_row,
                ]),
                self._build_card("任务参数", [
                    ft.Row(spacing=14, controls=[self.max_workers, self.timeout, self.retry_count]),
                ]),
                self._build_card("网络设置", [self.proxy]),
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
                                            ft.Text("无缝保存已启用", size=14, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                            ft.Text("修改任意配置后会自动写入 global_config.json。", size=12, color=colors.TEXT_MUTED),
                                        ],
                                    ),
                                ],
                            ),
                            self.save_hint,
                        ],
                    ),
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[
                        ft.OutlinedButton(
                            content="重置为默认值",
                            icon=ft.Icons.RESTART_ALT_ROUNDED,
                            icon_color=colors.CORAL,
                            style=ft.ButtonStyle(
                                color=colors.CORAL,
                                side=ft.BorderSide(1, colors.CORAL_DARK),
                                shape=ft.RoundedRectangleBorder(radius=10),
                                padding=ft.padding.symmetric(horizontal=20, vertical=12),
                            ),
                            on_click=self._on_reset,
                        ),
                    ],
                ),
            ],
        )

    def _on_provider_change(self, _: ft.ControlEvent | None = None) -> None:
        self._sync_provider_fields()
        self._autosave()

    def _sync_provider_fields(self) -> None:
        p = self.provider.value or "TikuYanxi"
        self.token.visible = p in _PROVIDERS_NEED_TOKEN
        self.endpoint_model_row.visible = p in _PROVIDERS_NEED_ENDPOINT
        self.adapter_url_row.visible = p in _PROVIDERS_NEED_ADAPTER_URL
        self.tiku_common_row.visible = p != "disabled"
        if self._page_or_none() is not None:
            self.token.update()
            self.endpoint_model_row.update()
            self.adapter_url_row.update()
            self.tiku_common_row.update()

    def _validate_int(self, field: ft.TextField, lo: int, hi: int, label: str) -> int | None:
        raw = (field.value or "").strip()
        if not raw:
            field.error_text = f"{label}不能为空"
            field.update()
            return None
        try:
            val = int(raw)
        except ValueError:
            field.error_text = f"{label}必须为整数"
            field.update()
            return None
        if val < lo or val > hi:
            field.error_text = f"{label}范围: {lo} ~ {hi}"
            field.update()
            return None
        field.error_text = None
        field.update()
        return val

    def _validate_float(self, field: ft.TextField, lo: float, hi: float, label: str) -> float | None:
        raw = (field.value or "").strip()
        if not raw:
            field.error_text = f"{label}不能为空"
            field.update()
            return None
        try:
            val = float(raw)
        except ValueError:
            field.error_text = f"{label}必须为数字"
            field.update()
            return None
        if val < lo or val > hi:
            field.error_text = f"{label}范围: {lo} ~ {hi}"
            field.update()
            return None
        field.error_text = None
        field.update()
        return val

    def _validate_proxy(self) -> bool:
        raw = (self.proxy.value or "").strip()
        if raw and not any(raw.startswith(s) for s in _VALID_PROXY_SCHEMES):
            self.proxy.error_text = "需以 http://、https://、socks4:// 或 socks5:// 开头"
            self.proxy.update()
            return False
        self.proxy.error_text = None
        self.proxy.update()
        return True

    def _on_validate_and_save(self, _: ft.ControlEvent | None = None) -> None:
        workers = self._validate_int(self.max_workers, 1, 16, "并发数")
        timeout = self._validate_int(self.timeout, 1, 300, "超时时间")
        retries = self._validate_int(self.retry_count, 1, 10, "重试次数")
        proxy_ok = self._validate_proxy()
        coverage = self._validate_float(self.tiku_coverage, 0.0, 1.0, "覆盖率")
        delay = self._validate_int(self.tiku_delay, 0, 60, "查询延迟")
        if workers is None or timeout is None or retries is None or not proxy_ok or coverage is None or delay is None:
            return
        self._autosave()

    def _on_reset(self, _: ft.ControlEvent | None = None) -> None:
        defaults = GlobalConfig.default()
        self.provider.value = defaults.tiku_provider
        self.token.value = defaults.tiku_token
        self.endpoint.value = defaults.tiku_endpoint
        self.model.value = defaults.tiku_model
        self.adapter_url.value = defaults.tiku_adapter_url
        self.tiku_submit.value = defaults.tiku_submit
        self.tiku_coverage.value = str(defaults.tiku_coverage)
        self.tiku_delay.value = str(defaults.tiku_delay)
        self.max_workers.value = str(defaults.max_workers)
        self.timeout.value = str(defaults.timeout)
        self.retry_count.value = str(defaults.retry_count)
        self.proxy.value = defaults.proxy

        for field in (self.tiku_coverage, self.tiku_delay, self.max_workers, self.timeout, self.retry_count, self.proxy):
            field.error_text = None

        self.config = defaults
        self.config_manager.save_global_config(self.config)

        self._sync_provider_fields()
        self.provider.update()
        self.token.update()
        self.tiku_coverage.update()
        self.tiku_delay.update()
        self.tiku_submit.update()
        self.max_workers.update()
        self.timeout.update()
        self.retry_count.update()
        self.proxy.update()
        self._show_saved_hint()

    def _autosave(self, _: ft.ControlEvent | None = None) -> None:
        self.config = GlobalConfig(
            tiku_provider=self.provider.value or "TikuYanxi",
            tiku_token=self.token.value or "",
            tiku_endpoint=(self.endpoint.value or "").strip(),
            tiku_model=(self.model.value or "").strip(),
            tiku_adapter_url=(self.adapter_url.value or "").strip(),
            tiku_submit=self.tiku_submit.value if self.tiku_submit.value is not None else True,
            tiku_coverage=float(self.tiku_coverage.value) if self.tiku_coverage.value else 0.6,
            tiku_delay=int(self.tiku_delay.value) if self.tiku_delay.value else 0,
            max_workers=int(self.max_workers.value) if self.max_workers.value else 3,
            command=self.config.command,
            dark_mode=self.config.dark_mode,
            enable_motion=self.config.enable_motion,
            timeout=int(self.timeout.value) if self.timeout.value else 30,
            retry_count=int(self.retry_count.value) if self.retry_count.value else 3,
            proxy=(self.proxy.value or "").strip(),
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
