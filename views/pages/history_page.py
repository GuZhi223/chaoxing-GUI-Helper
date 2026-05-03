from __future__ import annotations

import configparser
import difflib
import json
from pathlib import Path

import flet as ft

from models.account import AccountConfig
from services.config_manager import ConfigManager
from viewmodels.account_viewmodel import AccountViewModel
from views.theme import colors

_MAX_IMPORT_BYTES = 5 * 1024 * 1024


class HistoryPage(ft.Container):
    def __init__(self, config_manager: ConfigManager, account_vm: AccountViewModel) -> None:
        super().__init__()
        self.config_manager = config_manager
        self.account_vm = account_vm
        self.expand = True
        self.sort_desc = False
        self._import_dialog: ft.AlertDialog | None = None
        self._confirm_dialog: ft.AlertDialog | None = None
        self._pending_import_data: list[dict] | None = None
        self._file_picker: ft.FilePicker | None = None
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
        self.search_count = ft.Text(size=13, color=colors.TEXT_MUTED, visible=False)
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
                                self.search_count,
                                self.sort_button,
                                self._toolbar_action("导出", ft.Icons.FILE_UPLOAD_ROUNDED, lambda _: self.page.run_task(self._export), colors.MINT),
                                self._toolbar_action("导入", ft.Icons.FILE_DOWNLOAD_ROUNDED, lambda _: self.page.run_task(self._import), colors.KLEIN_BLUE_SOFT),
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
            if not query or self._fuzzy_match(query, self._search_blob(config))
        ]
        if self.sort_desc:
            indexed_configs = list(reversed(indexed_configs))

        if not configs:
            message = "暂无历史配置。"
            self.search_count.visible = False
        elif query and not indexed_configs:
            message = "没有匹配的历史配置。"
            self.search_count.value = "找到 0 个结果"
            self.search_count.visible = True
        elif query:
            message = ""
            self.search_count.value = f"找到 {len(indexed_configs)} 个结果"
            self.search_count.visible = True
        else:
            message = ""
            self.search_count.visible = False

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

    def _fuzzy_match(self, query: str, blob: str) -> bool:
        if not query:
            return True
        if query in blob:
            return True
        tokens = query.split()
        if len(tokens) > 1 and all(t in blob for t in tokens):
            return True
        if self._is_subsequence(query, blob):
            return True
        if len(query) >= 2:
            sm = difflib.SequenceMatcher(None, query, blob)
            if sm.find_longest_match(0, len(query), 0, len(blob)).size >= len(query) * 0.6:
                return True
        return False

    @staticmethod
    def _is_subsequence(query: str, blob: str) -> bool:
        it = iter(blob)
        return all(c in it for c in query)

    def _get_file_picker(self) -> ft.FilePicker:
        if self._file_picker is None:
            self._file_picker = ft.FilePicker()
        return self._file_picker

    async def _export(self) -> None:
        if not self._is_mounted():
            return
        picker = self._get_file_picker()
        path = await picker.save_file(
            dialog_title="导出历史配置",
            file_name="history_configs.json",
            allowed_extensions=["json"],
            file_type=ft.FilePickerFileType.CUSTOM,
        )
        if not path:
            return
        configs = self.config_manager.load_history()
        data = [config.to_dict() for config in configs]
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._show_snackbar(f"已成功导出 {len(data)} 个配置", colors.MINT_DARK)
        except OSError:
            self._show_snackbar("导出失败，无法写入文件", colors.CORAL_DARK)

    async def _import(self) -> None:
        if not self._is_mounted():
            return
        picker = self._get_file_picker()
        files = await picker.pick_files(
            dialog_title="选择要导入的配置文件（支持 JSON / INI）",
            allowed_extensions=["json", "ini"],
            file_type=ft.FilePickerFileType.CUSTOM,
            allow_multiple=True,
        )
        if not files:
            return
        valid: list[dict] = []
        errors: list[str] = []
        for f in files:
            path = Path(f.path)
            ext = path.suffix.lower()
            if ext not in (".json", ".ini"):
                errors.append(f"{path.name}：不支持的文件格式")
                continue
            if path.stat().st_size > _MAX_IMPORT_BYTES:
                errors.append(f"{path.name}：文件过大（超过 5MB）")
                continue
            if path.stat().st_size == 0:
                errors.append(f"{path.name}：文件为空")
                continue
            if ext == ".json":
                parsed, err = self._parse_json_import(path)
                if err:
                    errors.append(f"{path.name}：{err}")
                else:
                    valid.extend(parsed)
            elif ext == ".ini":
                parsed, err = self._parse_ini_config(path)
                if err:
                    errors.append(f"{path.name}：{err}")
                elif parsed:
                    valid.append(parsed)
        if errors:
            self._show_snackbar("；".join(errors[:3]) + ("..." if len(errors) > 3 else ""), colors.WARNING)
        if not valid:
            if not errors:
                self._show_snackbar("导入文件中没有有效的配置数据", colors.CORAL_DARK)
            return
        self._pending_import_data = valid
        self._show_import_dialog(len(valid))

    @staticmethod
    def _parse_json_import(path: Path) -> tuple[list[dict], str | None]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            return [], f"JSON 解析失败：{exc}"
        if isinstance(data, dict):
            if not data.get("username") and not data.get("remark"):
                return [], "JSON 对象缺少必要字段（username 或 remark）"
            return [data], None
        if isinstance(data, list):
            items = [item for item in data if isinstance(item, dict)]
            if not items:
                return [], "JSON 数组中没有有效的配置对象"
            return items, None
        return [], f"不支持的 JSON 数据类型：{type(data).__name__}"

    @staticmethod
    def _parse_ini_config(path: Path) -> tuple[dict | None, str | None]:
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(path, encoding="utf-8")
        except (OSError, configparser.Error) as exc:
            return None, f"INI 解析失败：{exc}"
        if not parser.has_section("common"):
            return None, "INI 文件缺少 [common] 配置节"
        username = parser.get("common", "username", fallback="")
        password = parser.get("common", "password", fallback="")
        if not username:
            return None, "INI 文件中 [common] 缺少 username 字段"
        course_list = parser.get("common", "course_list", fallback="")
        speed = parser.get("common", "speed", fallback="1.0")
        jobs = parser.getint("common", "jobs", fallback=3)
        options: dict = {
            "speed": speed,
            "workers": jobs,
        }
        if course_list:
            options["course_id"] = course_list
        if parser.has_section("tiku"):
            options["enable_tiku"] = True
            tiku_token = parser.get("tiku", "tokens", fallback="")
            if tiku_token:
                options["tiku_token"] = tiku_token
        else:
            options["enable_tiku"] = False
        return {
            "username": username,
            "password": password,
            "school": "",
            "remark": "",
            "course_url": course_list,
            "options": options,
        }, None

    def _show_import_dialog(self, count: int) -> None:
        if not self._is_mounted():
            return
        self._import_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=colors.SURFACE_LOW,
            title=ft.Text("导入配置", size=20, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
            content=ft.Container(
                width=400,
                content=ft.Column(
                    tight=True,
                    spacing=14,
                    controls=[
                        ft.Text(f"检测到 {count} 个配置，请选择导入方式：", size=14, color=colors.TEXT_SECONDARY),
                        ft.Container(
                            border_radius=14,
                            bgcolor=colors.SURFACE,
                            border=ft.border.all(1, colors.OUTLINE_SOFT),
                            padding=16,
                            content=ft.Column(
                                tight=True,
                                spacing=10,
                                controls=[
                                    ft.Row(
                                        spacing=10,
                                        controls=[
                                            ft.Icon(ft.Icons.CALL_MERGE_ROUNDED, size=20, color=colors.KLEIN_BLUE_SOFT),
                                            ft.Column(
                                                spacing=2,
                                                controls=[
                                                    ft.Text("合并导入", size=14, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                                                    ft.Text("将导入的配置追加到现有列表（相同账号自动更新）", size=12, color=colors.TEXT_MUTED),
                                                ],
                                            ),
                                        ],
                                    ),
                                    ft.Row(
                                        spacing=10,
                                        controls=[
                                            ft.Icon(ft.Icons.SWAP_HORIZ_ROUNDED, size=20, color=colors.WARNING),
                                            ft.Column(
                                                spacing=2,
                                                controls=[
                                                    ft.Text("覆盖导入", size=14, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                                                    ft.Text("用导入的配置替换全部现有配置（不可撤销）", size=12, color=colors.TEXT_MUTED),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            actions=[
                ft.TextButton("取消", on_click=self._close_import_dialog),
                ft.Container(
                    height=40,
                    border_radius=12,
                    bgcolor=colors.KLEIN_BLUE,
                    padding=ft.padding.symmetric(horizontal=18),
                    ink=True,
                    on_click=lambda _: self._do_import(merge=True),
                    content=ft.Row(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.CALL_MERGE_ROUNDED, size=18, color=colors.TEXT_PRIMARY),
                            ft.Text("合并", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                        ],
                    ),
                ),
                ft.Container(
                    height=40,
                    border_radius=12,
                    bgcolor=colors.WARNING,
                    padding=ft.padding.symmetric(horizontal=18),
                    ink=True,
                    on_click=lambda _: self._confirm_overwrite_import(),
                    content=ft.Row(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.SWAP_HORIZ_ROUNDED, size=18, color=colors.SURFACE_BG),
                            ft.Text("覆盖", size=13, weight=ft.FontWeight.W_600, color=colors.SURFACE_BG),
                        ],
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self._import_dialog not in self.page.overlay:
            self.page.overlay.append(self._import_dialog)
        self._import_dialog.open = True
        self.page.update()

    def _close_import_dialog(self, _: ft.ControlEvent | None = None) -> None:
        if self._import_dialog is not None:
            self._import_dialog.open = False
            if self._is_mounted():
                self.page.update()

    def _confirm_overwrite_import(self) -> None:
        if not self._pending_import_data or not self._is_mounted():
            return
        self._import_dialog.open = False
        count = len(self._pending_import_data)
        self._confirm_dialog = ft.AlertDialog(
            modal=True,
            bgcolor=colors.SURFACE_LOW,
            title=ft.Text("确认覆盖", size=20, weight=ft.FontWeight.W_700, color=colors.CORAL),
            content=ft.Text(
                f"即将用 {count} 个导入配置替换所有现有历史配置，此操作不可撤销。是否继续？",
                size=14,
                color=colors.TEXT_SECONDARY,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._close_confirm_dialog()),
                ft.Container(
                    height=40,
                    border_radius=12,
                    bgcolor=colors.CORAL,
                    padding=ft.padding.symmetric(horizontal=18),
                    ink=True,
                    on_click=lambda _: self._do_import(merge=False),
                    content=ft.Text("确认覆盖", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_PRIMARY),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if self._confirm_dialog not in self.page.overlay:
            self.page.overlay.append(self._confirm_dialog)
        self._confirm_dialog.open = True
        self.page.update()

    def _close_confirm_dialog(self, _: ft.ControlEvent | None = None) -> None:
        if self._confirm_dialog is not None:
            self._confirm_dialog.open = False
        self._pending_import_data = None
        if self._is_mounted():
            self.page.update()

    def _do_import(self, merge: bool) -> None:
        if not self._pending_import_data:
            self._close_import_dialog()
            self._close_confirm_dialog()
            return
        raw_items = self._pending_import_data
        imported: list[AccountConfig] = []
        skipped = 0
        for item in raw_items:
            try:
                imported.append(AccountConfig.from_dict(item))
            except (TypeError, ValueError, KeyError):
                skipped += 1
        self._pending_import_data = None
        if not imported:
            self._close_import_dialog()
            self._close_confirm_dialog()
            self._show_snackbar(f"导入失败：所有 {len(raw_items)} 个配置数据格式均无效", colors.CORAL_DARK)
            return
        try:
            if merge:
                existing = self.config_manager.load_history()
                existing_map: dict[str, AccountConfig] = {}
                for c in existing:
                    if c.username:
                        existing_map[c.username] = c
                    else:
                        existing_map[id(c)] = c
                for c in imported:
                    if c.username:
                        existing_map[c.username] = c
                    else:
                        existing_map[id(c)] = c
                merged = list(existing_map.values())
                self.config_manager.save_history(merged)
                self.config_manager.save_active(merged)
                total = len(merged)
            else:
                self.config_manager.save_history(imported)
                self.config_manager.save_active(imported)
                total = len(imported)
        except OSError as exc:
            self._close_import_dialog()
            self._close_confirm_dialog()
            self._show_snackbar(f"导入失败：写入配置文件时出错（{exc}）", colors.CORAL_DARK)
            return
        self._close_import_dialog()
        self._close_confirm_dialog()
        self.refresh()
        mode = "合并" if merge else "覆盖"
        msg = f"已{mode}导入 {len(imported)} 个配置，当前共 {total} 个"
        if skipped:
            msg += f"（跳过 {skipped} 个无效条目）"
        self._show_snackbar(msg, colors.MINT_DARK)

    def _show_snackbar(self, message: str, bgcolor: str) -> None:
        if not self._is_mounted():
            return
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=colors.TEXT_PRIMARY),
            bgcolor=bgcolor,
        )
        self.page.snack_bar.open = True
        self.page.update()

    def _is_mounted(self) -> bool:
        try:
            return self.page is not None
        except RuntimeError:
            return False
