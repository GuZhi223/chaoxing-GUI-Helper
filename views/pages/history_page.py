from __future__ import annotations

import flet as ft

from models.account import AccountConfig
from services.config_manager import ConfigManager
from viewmodels.account_viewmodel import AccountViewModel
from views.theme import colors


class HistoryPage(ft.Container):
    def __init__(self, config_manager: ConfigManager, account_vm: AccountViewModel) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.account_vm = account_vm
        self.expand = True
        self.sort_desc = False
        self.search_field = ft.TextField(
            hint_text="搜索备注、手机号、课程名或课程 ID",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            height=44,
            border_radius=14,
            border_color=colors.OUTLINE,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
        )
        self.search_field.on_change = self._on_search
        self.sort_button = self._toolbar_action(self._sort_label(), self._sort_icon(), self._toggle_sort, colors.KLEIN_BLUE_SOFT)
        self.list_view = ft.ListView(expand=True, spacing=12, padding=ft.padding.only(right=4))
        self.content = self._build()
        self.refresh()

    def _build(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=18,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text("历史配置", size=30, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                ft.Text("查看已保存的账号配置，可搜索并一键恢复到账号运行页。", size=14, color=colors.TEXT_MUTED),
                            ],
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Container(width=340, content=self.search_field),
                                self.sort_button,
                                self._toolbar_action("刷新", ft.Icons.REFRESH_ROUNDED, lambda _: self.refresh(), colors.KLEIN_BLUE_SOFT),
                            ],
                        ),
                    ],
                ),
                ft.Container(
                    expand=True,
                    border_radius=18,
                    bgcolor=colors.SURFACE_LOW,
                    border=ft.border.all(1, colors.OUTLINE_SOFT),
                    padding=18,
                    content=self.list_view,
                ),
            ],
        )

    def refresh(self) -> None:
        configs = self.config_manager.load_history()
        query = (self.search_field.value or "").strip().lower()
        indexed_configs = [
            (index, config)
            for index, config in enumerate(configs)
            if not query or query in self._search_blob(config)
        ]
        if self.sort_desc:
            indexed_configs = list(reversed(indexed_configs))

        if not configs:
            message = "暂无历史配置。"
        elif query and not indexed_configs:
            message = "没有匹配的历史配置。"
        else:
            message = ""

        if message:
            self.list_view.controls = [
                ft.Container(
                    alignment=ft.Alignment(0, 0),
                    padding=40,
                    content=ft.Text(message, color=colors.TEXT_MUTED),
                )
            ]
        else:
            self.list_view.controls = [self._history_card(index, config) for index, config in indexed_configs]

        if self._is_mounted():
            self.update()

    def _history_card(self, index: int, config: AccountConfig) -> ft.Control:
        course = config.course_url or config.options.get("course_id", "")
        return ft.Container(
            border_radius=16,
            bgcolor=colors.SURFACE,
            border=ft.border.all(1, colors.OUTLINE_SOFT),
            padding=18,
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Container(
                        width=44,
                        height=44,
                        border_radius=12,
                        bgcolor=colors.SURFACE_HIGH,
                        content=ft.Icon(ft.Icons.PERSON_ROUNDED, color=colors.KLEIN_BLUE_SOFT),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=5,
                        controls=[
                            ft.Text(config.remark or config.username or "未命名账号", size=16, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                            ft.Text(f"手机号：{config.username or '未配置'}", size=12, color=colors.TEXT_SECONDARY),
                            ft.Text(f"课程：{course or '未配置'}", size=12, color=colors.TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    self._action("恢复", ft.Icons.RESTORE_ROUNDED, lambda _: self._restore(index), colors.MINT),
                    self._action("删除", ft.Icons.DELETE_OUTLINE_ROUNDED, lambda _: self._delete(index), colors.CORAL),
                ],
            ),
        )

    def _toolbar_action(self, label: str, icon: str, on_click, color: str) -> ft.Control:
        return ft.Container(
            height=42,
            border_radius=12,
            bgcolor=colors.SURFACE_HIGH,
            padding=ft.padding.symmetric(horizontal=14),
            ink=True,
            on_click=on_click,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                ],
            ),
        )

    def _action(self, label: str, icon: str, on_click, color: str) -> ft.Control:
        return ft.Container(
            height=38,
            border_radius=12,
            bgcolor=colors.SURFACE_HIGH,
            padding=ft.padding.symmetric(horizontal=12),
            ink=True,
            on_click=on_click,
            content=ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                ],
            ),
        )

    def _restore(self, index: int) -> None:
        configs = self.config_manager.load_history()
        if 0 <= index < len(configs):
            self.account_vm.add_account(configs[index])

    def _delete(self, index: int) -> None:
        configs = self.config_manager.load_history()
        if 0 <= index < len(configs):
            del configs[index]
            self.config_manager.save_history(configs)
            self.refresh()

    def _on_search(self, _: ft.ControlEvent) -> None:
        self.refresh()

    def _toggle_sort(self, _: ft.ControlEvent) -> None:
        self.sort_desc = not self.sort_desc
        self._sync_sort_button()
        self.refresh()

    def _sort_label(self) -> str:
        return "倒序" if self.sort_desc else "正序"

    def _sort_icon(self) -> str:
        return ft.Icons.SOUTH_ROUNDED if self.sort_desc else ft.Icons.NORTH_ROUNDED

    def _sync_sort_button(self) -> None:
        row = self.sort_button.content
        if not isinstance(row, ft.Row):
            return
        icon = row.controls[0]
        label = row.controls[1]
        icon.icon = self._sort_icon()
        label.value = self._sort_label()
        if self._is_mounted():
            self.sort_button.update()

    def _search_blob(self, config: AccountConfig) -> str:
        parts = [
            config.remark,
            config.username,
            config.school,
            config.course_url,
            str(config.options.get("course_id", "")),
        ]
        return " ".join(str(part) for part in parts if part).lower()

    def _is_mounted(self) -> bool:
        try:
            return self.page is not None
        except RuntimeError:
            return False
