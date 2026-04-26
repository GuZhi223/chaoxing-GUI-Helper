from __future__ import annotations

from collections.abc import Callable
from typing import Any

import flet as ft

from models.account import AccountConfig
from views.theme import colors


class AccountDialog:
    def __init__(
        self,
        on_save: Callable[[AccountConfig], None],
        on_fetch_courses: Callable[[AccountConfig], list[tuple[str, str]]] | None = None,
        account: Any | None = None,
        title: str = "账号配置",
    ) -> None:
        self._on_save = on_save
        self._on_fetch_courses = on_fetch_courses
        self._initial = self._resolve_config(account)
        self._dialog: ft.AlertDialog | None = None
        self._course_picker: ft.AlertDialog | None = None

        options = self._initial.options or {}
        self.phone = self._field("手机号", self._initial.username, ft.Icons.PHONE_ANDROID_ROUNDED)
        self.password = self._field("密码", self._initial.password, ft.Icons.LOCK_ROUNDED, password=True)
        self.remark = self._field("备注名", self._initial.remark, ft.Icons.BADGE_ROUNDED)
        self.course_id = self._field(
            "课程",
            self._initial.course_url or str(options.get("course_id", "")),
            ft.Icons.MENU_BOOK_ROUNDED,
        )
        self.course_id.hint_text = "留空则自动处理全部未完成课程；也可填多个课程 ID"
        self.course_status = ft.Text("课程留空时会自动扫描账号下全部未完成课程。", size=12, color=colors.TEXT_MUTED)
        self.speed = ft.Dropdown(
            label="倍速",
            value=str(options.get("speed", "1.0")),
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            options=[ft.dropdown.Option(value) for value in ("1.0", "1.25", "1.5", "1.75", "2.0")],
        )
        self.workers = ft.Dropdown(
            label="章节并发 jobs",
            value=str(options.get("workers", "3")),
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            options=[ft.dropdown.Option(str(value)) for value in range(1, 9)],
        )
        self.enable_tiku = ft.Switch(label="启用题库", value=bool(options.get("enable_tiku", True)), active_color=colors.MINT)
        self.auto_submit = ft.Switch(label="自动提交", value=bool(options.get("auto_submit", True)), active_color=colors.KLEIN_BLUE_SOFT)
        self.title = title

    def build(self) -> ft.AlertDialog:
        self._dialog = ft.AlertDialog(
            modal=True,
            bgcolor=colors.SURFACE_LOW,
            title=ft.Text(self.title, size=20, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
            content=self._content(),
            actions=[
                ft.TextButton("取消", on_click=self._close),
                ft.Container(
                    height=40,
                    border_radius=12,
                    bgcolor=colors.KLEIN_BLUE,
                    padding=ft.padding.symmetric(horizontal=18),
                    ink=True,
                    on_click=self._save,
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.CHECK_ROUNDED, size=18, color=colors.TEXT_PRIMARY),
                            ft.Text("保存", weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                        ],
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        return self._dialog

    def _content(self) -> ft.Control:
        return ft.Container(
            width=560,
            content=ft.Column(
                tight=True,
                spacing=14,
                controls=[
                    self.phone,
                    self.password,
                    self.remark,
                    ft.Column(
                        tight=True,
                        spacing=6,
                        controls=[
                            ft.Row(spacing=12, controls=[ft.Container(expand=True, content=self.course_id), self._fetch_button()]),
                            self.course_status,
                        ],
                    ),
                    ft.Container(
                        border_radius=14,
                        bgcolor=colors.SURFACE,
                        border=ft.border.all(1, colors.OUTLINE_SOFT),
                        padding=16,
                        content=ft.Column(
                            tight=True,
                            spacing=14,
                            controls=[
                                ft.Text("高级设置", size=14, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                ft.Row(spacing=12, controls=[ft.Container(expand=True, content=self.speed), ft.Container(expand=True, content=self.workers)]),
                                ft.Row(spacing=28, controls=[self.enable_tiku, self.auto_submit]),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _fetch_button(self) -> ft.Control:
        return ft.Container(
            height=48,
            border_radius=12,
            bgcolor=colors.SURFACE_HIGH,
            padding=ft.padding.symmetric(horizontal=14),
            ink=True,
            on_click=self._fetch_courses,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.CLOUD_DOWNLOAD_ROUNDED, size=18, color=colors.KLEIN_BLUE_SOFT),
                    ft.Text("获取课程", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                ],
            ),
        )

    def _field(self, label: str, value: str, icon: str, password: bool = False) -> ft.TextField:
        return ft.TextField(
            label=label,
            value=value,
            password=password,
            can_reveal_password=password,
            prefix_icon=icon,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            cursor_color=colors.KLEIN_BLUE_SOFT,
        )

    def _fetch_courses(self, _: ft.ControlEvent) -> None:
        if self._on_fetch_courses is None:
            self._set_status("当前版本未接入课程获取服务。", colors.WARNING)
            return
        self._set_status("正在登录查询课程，请稍候...", colors.KLEIN_BLUE_SOFT)
        courses = self._on_fetch_courses(self._draft_config())
        if not courses:
            self._set_status("未获取到课程；可留空保存，运行时自动扫描全部未完成课程。", colors.WARNING)
            return
        self._set_status(f"已获取到 {len(courses)} 门课程，请选择。", colors.MINT)
        self._open_course_picker(courses)

    def _open_course_picker(self, courses: list[tuple[str, str]]) -> None:
        page = self._page_or_none()
        if page is None:
            return

        checks: list[tuple[ft.Checkbox, str]] = []
        rows: list[ft.Control] = []
        existing = self.course_id.value or ""
        for course_id, title in courses:
            value = f"{title}({course_id})"
            checkbox = ft.Checkbox(label=value, value=(course_id in existing), active_color=colors.KLEIN_BLUE_SOFT)
            checks.append((checkbox, value))
            rows.append(checkbox)

        def confirm(_: ft.ControlEvent) -> None:
            selected = [value for checkbox, value in checks if checkbox.value]
            self.course_id.value = ", ".join(selected)
            self.course_id.update()
            self._set_status(f"已选择 {len(selected)} 门课程。", colors.MINT)
            self._close_picker()

        self._course_picker = ft.AlertDialog(
            modal=True,
            bgcolor=colors.SURFACE_LOW,
            title=ft.Text("请选择要学习的课程", size=18, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
            content=ft.Container(
                width=520,
                height=420,
                content=ft.ListView(spacing=8, controls=rows),
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._close_picker()),
                ft.TextButton("确认选择", on_click=confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self._course_picker not in page.overlay:
            page.overlay.append(self._course_picker)
        self._course_picker.open = True
        page.update()
        self._course_picker.update()

    def _close_picker(self) -> None:
        if self._course_picker is None:
            return
        self._course_picker.open = False
        page = self._page_or_none()
        if page is not None:
            page.update()

    def _draft_config(self) -> AccountConfig:
        return AccountConfig(
            username=(self.phone.value or "").strip(),
            password=(self.password.value or "").strip(),
            remark=(self.remark.value or "").strip(),
            course_url=(self.course_id.value or "").strip(),
            options={
                "course_id": (self.course_id.value or "").strip(),
                "speed": self.speed.value or "1.0",
                "workers": int(self.workers.value or 3),
                "enable_tiku": bool(self.enable_tiku.value),
                "auto_submit": bool(self.auto_submit.value),
            },
        )

    def _save(self, event: ft.ControlEvent) -> None:
        self._on_save(self._draft_config())
        self._close(event)

    def _set_status(self, message: str, color: str) -> None:
        self.course_status.value = message
        self.course_status.color = color
        try:
            self.course_status.update()
        except RuntimeError:
            pass

    def _resolve_config(self, account: Any | None) -> AccountConfig:
        if account is None:
            return AccountConfig()
        if isinstance(account, AccountConfig):
            return account
        config = getattr(account, "config", None)
        if isinstance(config, AccountConfig):
            return config
        return AccountConfig(username=str(getattr(account, "phone", "") or ""), remark=str(getattr(account, "title", "") or ""))

    def _close(self, _: ft.ControlEvent | None = None) -> None:
        if self._dialog is None:
            return
        self._dialog.open = False
        page = self._page_or_none()
        if page is not None:
            page.update()

    def _page_or_none(self) -> ft.Page | None:
        control = self._dialog or self._course_picker
        if control is None:
            return None
        try:
            return control.page
        except RuntimeError:
            return None
