from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock

import flet as ft

from core.event_bus import EventBus
from core.events import LogEvent, LogLevel, ProgressEvent, TaskStateEvent, TaskStatus
from viewmodels.account_viewmodel import AccountViewModel
from views.theme import colors

TASK_BLUE = "#002FA7"
LOG_BG = "#05070A"


@dataclass(slots=True)
class VideoSlotState:
    key: str
    title: str
    course: str = ""
    chapter: str = ""
    total_seconds: float = 0.0
    current_seconds: float = 0.0
    percent: float = 0.0
    updated_at: datetime = field(default_factory=datetime.now)
    real_updated_at: datetime = field(default_factory=datetime.now)
    last_source: str = ""


class LogsPage(ft.Container):
    def __init__(self, account_vm: AccountViewModel, event_bus: EventBus) -> None:
        super().__init__()
        self.account_vm = account_vm
        self.event_bus = event_bus
        self.expand = True
        self._logs: dict[str, list[LogEvent]] = self.account_vm.log_events
        self._slots_by_account: dict[str, list[VideoSlotState]] = defaultdict(list)
        self._completed_keys_by_account: dict[str, set[str]] = defaultdict(set)
        self._selected_account_id = ""
        self._disposed = False
        self._needs_refresh = True
        self._state_lock = RLock()

        self.elegant_mode = ft.Switch(label="优雅模式", value=True, active_color=colors.KLEIN_BLUE_SOFT)
        self.elegant_mode.on_change = self._toggle_mode
        self._level_filter = "ALL"
        self._search_query = ""
        self._MAX_DISPLAY = 300
        self.level_filter = ft.Dropdown(
            value="ALL",
            width=120,
            height=42,
            border_radius=12,
            border_color=colors.OUTLINE_SOFT,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
            options=[
                ft.dropdown.Option("ALL", "全部"),
                ft.dropdown.Option("INFO", "INFO"),
                ft.dropdown.Option("WARNING", "WARNING"),
                ft.dropdown.Option("ERROR", "ERROR"),
                ft.dropdown.Option("SUCCESS", "SUCCESS"),
            ],
            on_select=self._on_level_filter_change,
        )
        self.search_field = ft.TextField(
            hint_text="搜索日志内容…",
            prefix_icon=ft.Icons.SEARCH_ROUNDED,
            height=42,
            width=240,
            border_radius=12,
            border_color=colors.OUTLINE_SOFT,
            focused_border_color=colors.KLEIN_BLUE_SOFT,
            color=colors.TEXT_PRIMARY,
            bgcolor=colors.SURFACE,
            text_size=13,
            content_padding=ft.padding.only(left=12, right=12, top=8, bottom=8),
            on_change=self._on_search_change,
        )
        self.clear_button = ft.Container(
            height=42,
            border_radius=12,
            bgcolor=colors.SURFACE,
            border=ft.border.all(1, colors.OUTLINE_SOFT),
            ink=True,
            on_click=self._on_clear_logs,
            padding=ft.padding.symmetric(horizontal=14),
            content=ft.Row(
                tight=True,
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.DELETE_SWEEP_ROUNDED, size=18, color=colors.CORAL),
                    ft.Text("清空", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_SECONDARY),
                ],
            ),
        )
        self.log_count_label = ft.Text("", size=12, color=colors.TEXT_MUTED)
        self.account_tabs = ft.Row(spacing=8, controls=[])
        self.stats_row = ft.Row(spacing=12)
        self.summary_row = ft.Row(spacing=12)
        self.slot_list = ft.ListView(expand=True, spacing=10, auto_scroll=False, padding=2)
        self.log_list = ft.ListView(expand=True, spacing=8, auto_scroll=True, padding=16)

        self._replay_progress_events()
        self._selected_account_id = self._default_account_id()
        self.content = self._build()
        self.event_bus.subscribe_sync(LogEvent, self._on_log)
        self.event_bus.subscribe_sync(ProgressEvent, self._on_progress)
        self.event_bus.subscribe_sync(TaskStateEvent, self._on_task_state)
        self._refresh_all()

    def did_mount(self) -> None:
        self._disposed = False
        if self._is_mounted():
            self.page.run_task(self._tick_loop)

    def will_unmount(self) -> None:
        self._disposed = True

    def _build(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=16,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text("运行监控", size=30, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                ft.Text("只显示正在运行或已经产生运行日志的账号。", size=14, color=colors.TEXT_MUTED),
                            ],
                        ),
                        ft.Row(
                            spacing=16,
                            controls=[
                                self.elegant_mode,
                                ft.Container(width=420, content=self.account_tabs),
                            ],
                        ),
                    ],
                ),
                self.stats_row,
                self.summary_row,
                ft.Container(
                    height=245,
                    border_radius=18,
                    bgcolor=colors.SURFACE_LOW,
                    border=ft.border.all(1, colors.OUTLINE_SOFT),
                    padding=14,
                    content=ft.Column(
                        expand=True,
                        spacing=10,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("并发视频槽位", size=15, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                    ft.Text("显示底层实际运行的视频任务。", size=12, color=colors.TEXT_MUTED),
                                ],
                            ),
                            self.slot_list,
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    border_radius=18,
                    bgcolor=LOG_BG,
                    border=ft.border.all(1, colors.OUTLINE_SOFT),
                    padding=ft.padding.only(top=10, left=12, right=12, bottom=4),
                    content=ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text("运行日志", size=15, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY),
                                    ft.Container(expand=True),
                                    self.level_filter,
                                    self.search_field,
                                    self.clear_button,
                                    self.log_count_label,
                                ],
                            ),
                            ft.Container(
                                expand=True,
                                padding=ft.padding.only(top=8),
                                content=self.log_list,
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _on_log(self, event: LogEvent) -> None:
        with self._state_lock:
            events = self._logs.setdefault(event.account_id, [])
            if not events or events[-1] is not event:
                events.append(event)
                if len(events) > 1200:
                    self._logs[event.account_id] = events[-1200:]
            self._select_first_active_if_needed(event.account_id)
            self._needs_refresh = True

    def _on_progress(self, event: ProgressEvent) -> None:
        with self._state_lock:
            self._upsert_slot(event)
            self._select_first_active_if_needed(event.account_id)
            self._needs_refresh = True

    def _on_task_state(self, event: TaskStateEvent) -> None:
        with self._state_lock:
            if event.status == TaskStatus.RUNNING:
                self._slots_by_account[event.account_id].clear()
                self._completed_keys_by_account[event.account_id].clear()
                self._select_first_active_if_needed(event.account_id)
            elif event.status in {TaskStatus.STOPPED, TaskStatus.FAILED, TaskStatus.COMPLETED}:
                self._slots_by_account[event.account_id].clear()
            self._needs_refresh = True

    def _select_account_id(self, account_id: str) -> None:
        with self._state_lock:
            if account_id not in self._account_ids():
                return
            self._selected_account_id = account_id
            self._needs_refresh = True
        self._refresh_all()

    def _toggle_mode(self, _: ft.ControlEvent) -> None:
        with self._state_lock:
            self._needs_refresh = True
        self._refresh_all()

    def _on_level_filter_change(self, e: ft.ControlEvent) -> None:
        self._level_filter = e.control.value or "ALL"
        with self._state_lock:
            self._needs_refresh = True
        self._refresh_all()

    def _on_search_change(self, e: ft.ControlEvent) -> None:
        self._search_query = (e.control.value or "").strip().lower()
        with self._state_lock:
            self._needs_refresh = True
        self._refresh_logs()
        self._request_update()

    def _on_clear_logs(self, _: ft.ControlEvent) -> None:
        with self._state_lock:
            self._logs.pop(self._selected_account_id, None)
            self._needs_refresh = True
        self._refresh_all()

    def _refresh_all(self) -> None:
        self._normalize_selected_account()
        self._refresh_stats()
        self._refresh_summary()
        self._refresh_slots()
        self._refresh_logs()
        self._sync_account_tabs()
        if self._is_mounted():
            self._request_update()

    def _refresh_stats(self) -> None:
        stats = self.account_vm.get_session_stats()
        running = int(stats.get("running_tasks", 0))
        completed_videos = int(stats.get("completed_videos", 0))
        success_rate = stats.get("success_rate", 0.0)
        total_seconds = stats.get("total_duration", 0.0)
        tiku_submitted = int(stats.get("tiku_submitted", 0))
        tiku_obtained = int(stats.get("tiku_obtained", 0))
        duration_text = self._format_stat_duration(total_seconds)
        tiku_rate = (tiku_obtained / tiku_submitted * 100) if tiku_submitted > 0 else 0.0
        self.stats_row.controls = [
            self._summary_card("当前运行任务", str(running), colors.KLEIN_BLUE_SOFT),
            self._summary_card("总运行时长", duration_text, colors.TEXT_SECONDARY),
            self._summary_card("已完成视频", str(completed_videos), colors.MINT),
            self._summary_card("提交题目", str(tiku_submitted), colors.KLEIN_BLUE_SOFT),
            self._summary_card("获取答案", f"{tiku_obtained}", colors.MINT),
            self._summary_card("答题命中率", f"{tiku_rate:.0f}%", colors.MINT if tiku_rate >= 70 else colors.WARNING if tiku_rate >= 40 else colors.CORAL),
            self._summary_card("任务完成率", f"{success_rate:.0f}%", colors.MINT if success_rate >= 80 else colors.WARNING if success_rate >= 50 else colors.CORAL),
        ]

    def _format_stat_duration(self, seconds: float) -> str:
        total = int(max(seconds, 0))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}时{minutes:02d}分{secs:02d}秒"
        if minutes > 0:
            return f"{minutes}分{secs:02d}秒"
        return f"{secs}秒"

    def _refresh_summary(self) -> None:
        slots = self._slots_by_account.get(self._selected_account_id, [])
        done = len(self._completed_keys_by_account.get(self._selected_account_id, set()))
        current_course = next((slot.course for slot in reversed(slots) if slot.course), "等待课程开始")
        current_chapter = next((slot.chapter for slot in reversed(slots) if slot.chapter), "等待章节解析")
        self.summary_row.controls = [
            self._summary_card("当前课程", current_course, colors.KLEIN_BLUE_SOFT, expand=True),
            self._summary_card("当前章节", current_chapter, colors.TEXT_SECONDARY, expand=True),
            self._summary_card("当前运行", str(len(slots)), colors.KLEIN_BLUE_SOFT),
            self._summary_card("已完成视频", str(done), colors.MINT),
        ]

    def _refresh_slots(self) -> None:
        slots = self._slots_by_account.get(self._selected_account_id, [])
        if not slots:
            self.slot_list.controls = [
                ft.Container(
                    alignment=ft.Alignment(0, 0),
                    padding=28,
                    content=ft.Text("等待底层输出视频任务。", size=13, color=colors.TEXT_MUTED),
                )
            ]
            return
        self.slot_list.controls = [self._slot_card(index, slot) for index, slot in enumerate(slots, start=1)]

    def _refresh_logs(self) -> None:
        entries = self._logs.get(self._selected_account_id, [])
        if self.elegant_mode.value:
            elegant_entries = [entry for entry in entries if entry.is_elegant]
            entries = elegant_entries if elegant_entries else entries

        if self._level_filter != "ALL":
            level_val = self._level_filter.lower()
            entries = [e for e in entries if e.level.value == level_val]

        if self._search_query:
            q = self._search_query
            entries = [e for e in entries if q in e.message.lower()]

        if not entries:
            self.log_list.controls = [ft.Text("等待底层日志输出。", size=13, color=colors.TEXT_MUTED, font_family="Consolas")]
            self.log_count_label.value = ""
            return

        total = len(entries)
        display = entries[-self._MAX_DISPLAY:]
        self.log_list.controls = [
            self._elegant_card(entry) if self.elegant_mode.value and entry.is_elegant else self._raw_line(entry)
            for entry in display
        ]
        if total > self._MAX_DISPLAY:
            self.log_count_label.value = f"显示 {len(display)}/{total} 条"
        else:
            self.log_count_label.value = f"{total} 条"

    def _summary_card(self, label: str, value: str, accent: str, expand: bool = False) -> ft.Control:
        return ft.Container(
            expand=expand,
            height=76,
            border_radius=16,
            bgcolor=colors.SURFACE,
            border=ft.border.all(1, colors.OUTLINE_SOFT),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Text(label, size=12, color=colors.TEXT_MUTED),
                    ft.Text(value, size=16, weight=ft.FontWeight.W_700, color=accent, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
            ),
        )

    def _slot_card(self, index: int, slot: VideoSlotState) -> ft.Control:
        ratio = max(0.0, min(slot.percent / 100, 1.0))
        duration = self._duration_pair(slot.current_seconds, slot.total_seconds)
        subtitle = " / ".join(part for part in [slot.course, slot.chapter] if part) or "等待课程上下文"
        return ft.Container(
            border_radius=12,
            bgcolor="#0D1117",
            border=ft.border.all(1, "#1D2733"),
            padding=12,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(
                                width=34,
                                height=34,
                                border_radius=10,
                                bgcolor="#111A2B",
                                alignment=ft.Alignment(0, 0),
                                content=ft.Text(str(index), size=13, weight=ft.FontWeight.W_700, color=colors.KLEIN_BLUE_SOFT),
                            ),
                            ft.Column(
                                expand=True,
                                spacing=3,
                                controls=[
                                    ft.Text(slot.title, size=14, weight=ft.FontWeight.W_700, color=colors.TEXT_PRIMARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(subtitle, size=12, color=colors.TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ],
                            ),
                            ft.Text("播放中", size=12, weight=ft.FontWeight.W_700, color=colors.KLEIN_BLUE_SOFT),
                            ft.Text(duration, size=12, color=colors.TEXT_SECONDARY, font_family="Consolas"),
                        ],
                    ),
                    ft.ProgressBar(value=ratio, height=7, color=colors.KLEIN_BLUE_SOFT, bgcolor="#202A38"),
                ],
            ),
        )

    def _elegant_card(self, event: LogEvent) -> ft.Control:
        bar_color = self._bar_color(event)
        label = self._label(event)
        timestamp = event.created_at.strftime("%H:%M:%S")
        return ft.Container(
            border_radius=8,
            bgcolor="#0D1117",
            border=ft.border.all(1, "#1D2733"),
            content=ft.Row(
                spacing=0,
                controls=[
                    ft.Container(width=4, bgcolor=bar_color),
                    ft.Container(
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=14, vertical=10),
                        content=ft.Row(
                            spacing=14,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    width=72,
                                    content=ft.Text(label, size=12, weight=ft.FontWeight.W_700, color=bar_color, font_family="Consolas"),
                                ),
                                ft.Text(event.message, expand=True, size=13, color=colors.TEXT_PRIMARY, font_family="Consolas"),
                                ft.Text(timestamp, size=12, color=colors.TEXT_MUTED, font_family="Consolas"),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _raw_line(self, event: LogEvent) -> ft.Control:
        timestamp = event.created_at.strftime("%H:%M:%S")
        return ft.Text(
            f"[{timestamp}] [{event.level.value.upper()}] {event.message}",
            size=13,
            color=self._raw_color(event.level),
            font_family="Consolas",
            selectable=True,
        )

    def _replay_progress_events(self) -> None:
        for events in self.account_vm.progress_events.values():
            for event in events:
                self._upsert_slot(event)

    def _upsert_slot(self, event: ProgressEvent) -> None:
        title = event.video_title or event.chapter or "未知视频"
        key = self._slot_key(title)
        slots = self._slots_by_account[event.account_id]
        completed = bool(event.meta.get("completed")) or event.percent >= 100
        slot = next((item for item in slots if item.key == key), None)

        if completed:
            self._completed_keys_by_account[event.account_id].add(key)
            self._slots_by_account[event.account_id] = [item for item in slots if item.key != key]
            return

        if key in self._completed_keys_by_account[event.account_id]:
            return

        if slot is None:
            capacity = self._slot_capacity(event.account_id)
            if len(slots) >= capacity:
                return
            slot = VideoSlotState(key=key, title=title)
            slots.append(slot)

        total = float(event.meta.get("total_seconds") or slot.total_seconds or 0.0)
        current = float(event.meta.get("current_seconds") or 0.0)
        if total <= 0 and slot.total_seconds > 0:
            total = slot.total_seconds
        if current <= 0 and total > 0:
            current = total * max(0.0, min(event.percent, 100.0)) / 100

        slot.course = event.course or slot.course
        slot.chapter = event.chapter or slot.chapter
        if total > 0:
            slot.total_seconds = total
        if "current_seconds" in event.meta or current > 0:
            slot.current_seconds = max(0.0, current)
        slot.percent = max(0.0, min(event.percent, 99.0))
        now = datetime.now()
        slot.updated_at = now
        slot.real_updated_at = now
        slot.last_source = str(event.meta.get("source") or "")

        capacity = self._slot_capacity(event.account_id)
        if len(slots) > capacity:
            del slots[capacity:]

    def _sync_account_tabs(self) -> None:
        account_ids = self._account_ids()
        if not account_ids:
            self.account_tabs.controls = [
                ft.Container(
                    height=40,
                    border_radius=12,
                    bgcolor=colors.SURFACE,
                    border=ft.border.all(1, colors.OUTLINE_SOFT),
                    padding=ft.padding.symmetric(horizontal=14),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text("暂无运行账号", size=13, color=colors.TEXT_MUTED),
                )
            ]
            return
        self.account_tabs.controls = [self._account_tab(account_id) for account_id in account_ids]

    def _account_tab(self, account_id: str) -> ft.Control:
        selected = account_id == self._selected_account_id
        return ft.Container(
            height=40,
            border_radius=12,
            bgcolor=colors.SURFACE_HIGH if selected else colors.SURFACE,
            border=ft.border.all(1, colors.KLEIN_BLUE_SOFT if selected else colors.OUTLINE_SOFT),
            padding=ft.padding.symmetric(horizontal=14),
            ink=True,
            on_click=lambda _, aid=account_id: self._select_account_id(aid),
            content=ft.Row(
                tight=True,
                spacing=8,
                controls=[
                    ft.Icon(
                        ft.Icons.RADIO_BUTTON_CHECKED_ROUNDED if selected else ft.Icons.ACCOUNT_CIRCLE_ROUNDED,
                        size=16,
                        color=colors.KLEIN_BLUE_SOFT if selected else colors.TEXT_MUTED,
                    ),
                    ft.Text(
                        self._account_name(account_id),
                        size=13,
                        weight=ft.FontWeight.W_700 if selected else ft.FontWeight.W_500,
                        color=colors.TEXT_PRIMARY if selected else colors.TEXT_SECONDARY,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
            ),
        )

    def _account_menu_anchor(self) -> ft.Control:
        return ft.Container(
            height=44,
            border_radius=14,
            bgcolor=colors.SURFACE,
            border=ft.border.all(1, colors.OUTLINE),
            padding=ft.padding.symmetric(horizontal=14),
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE_ROUNDED, size=18, color=colors.KLEIN_BLUE_SOFT),
                    ft.Container(expand=True, content=self.account_label),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=22, color=colors.TEXT_MUTED),
                ],
            ),
        )

    def _sync_account_menu(self) -> None:
        self.account_label.value = self._selected_account_label()
        self.account_menu.items = self._account_menu_items()

    def _account_menu_items(self) -> list[ft.PopupMenuItem]:
        items: list[ft.PopupMenuItem] = []
        for account_id in self._account_ids():
            label = self._account_name(account_id)
            items.append(
                ft.PopupMenuItem(
                    content=label,
                    checked=account_id == self._selected_account_id,
                    on_click=lambda _, aid=account_id: self._select_account_id(aid),
                )
            )
        return items

    def _selected_account_label(self) -> str:
        if not self._selected_account_id:
            return "暂无运行账号"
        return self._account_name(self._selected_account_id)

    async def _tick_loop(self) -> None:
        while not self._disposed:
            await asyncio.sleep(1.0)
            with self._state_lock:
                simulated = self._tick_stale_slots()
                should_refresh = self._needs_refresh or simulated
                self._needs_refresh = False
            if should_refresh and self._is_mounted():
                self._refresh_all()

    def _tick_stale_slots(self) -> bool:
        now = datetime.now()
        changed = False
        for account_id, slots in self._slots_by_account.items():
            speed = self._speed_for_account(account_id)
            for slot in slots:
                if slot.total_seconds <= 0 or slot.current_seconds >= slot.total_seconds * 0.99:
                    continue

                stale_seconds = (now - slot.real_updated_at).total_seconds()
                if slot.last_source == "terminal" and stale_seconds < 4.0:
                    continue

                elapsed = max((now - slot.updated_at).total_seconds(), 0.0)
                if elapsed < 0.8:
                    continue

                next_current = min(slot.total_seconds * 0.99, slot.current_seconds + elapsed * speed)
                if next_current <= slot.current_seconds:
                    continue

                slot.current_seconds = next_current
                slot.percent = min(next_current / slot.total_seconds * 100, 99.0)
                slot.updated_at = now
                changed = True
        return changed

    def _select_first_active_if_needed(self, account_id: str) -> None:
        if self._selected_account_id:
            return
        if account_id in self._account_ids():
            self._selected_account_id = account_id

    def _normalize_selected_account(self) -> None:
        ids = self._account_ids()
        if not ids:
            self._selected_account_id = ""
            return
        if self._selected_account_id not in ids:
            self._selected_account_id = ids[0]

    def _account_ids(self) -> list[str]:
        ids: list[str] = []

        def add(account_id: str) -> None:
            if account_id and account_id != "course_fetch" and account_id not in ids:
                ids.append(account_id)

        for card in self.account_vm.cards:
            if card.status == TaskStatus.RUNNING or self._has_account_activity(card.account_id):
                add(card.account_id)
        for account_id in [
            *self._logs.keys(),
            *self._slots_by_account.keys(),
            *self._completed_keys_by_account.keys(),
            *self.account_vm.progress_events.keys(),
        ]:
            if self._has_account_activity(account_id):
                add(account_id)
        return ids

    def _default_account_id(self) -> str:
        ids = self._account_ids()
        return ids[0] if ids else ""

    def _has_account_activity(self, account_id: str) -> bool:
        return bool(
            self._logs.get(account_id)
            or self._slots_by_account.get(account_id)
            or self._completed_keys_by_account.get(account_id)
            or self.account_vm.progress_events.get(account_id)
        )

    def _account_name(self, account_id: str) -> str:
        card = next((item for item in self.account_vm.cards if item.account_id == account_id), None)
        if card is None:
            return account_id
        return card.title or card.phone or account_id

    def _speed_for_account(self, account_id: str) -> float:
        card = next((item for item in self.account_vm.cards if item.account_id == account_id), None)
        if card is None or card.config is None:
            return 1.0
        try:
            return max(0.1, min(float(card.config.options.get("speed", 1.0)), 2.0))
        except (TypeError, ValueError):
            return 1.0

    def _chapter_jobs(self, account_id: str) -> int:
        card = next((item for item in self.account_vm.cards if item.account_id == account_id), None)
        if card is not None and card.config is not None:
            raw = card.config.options.get("workers", card.config.options.get("jobs", 3))
        elif self.account_vm.config_manager is not None:
            raw = self.account_vm.config_manager.load_global_config().max_workers
        else:
            raw = 3
        try:
            return max(1, min(int(raw), 16))
        except (TypeError, ValueError):
            return 3

    def _slot_capacity(self, account_id: str) -> int:
        return max(16, self._chapter_jobs(account_id))

    def _slot_key(self, title: str) -> str:
        return " ".join((title or "").strip().lower().split())

    def _bar_color(self, event: LogEvent) -> str:
        if event.level == LogLevel.ERROR:
            return colors.CORAL
        if event.level == LogLevel.WARNING:
            return colors.WARNING
        if event.level == LogLevel.SUCCESS:
            return colors.MINT
        return TASK_BLUE

    def _label(self, event: LogEvent) -> str:
        if event.level == LogLevel.ERROR:
            return "[ERROR]"
        if event.level == LogLevel.WARNING:
            return "[WARN]"
        if event.level == LogLevel.SUCCESS:
            return "[DONE]"
        return "[TASK]"

    def _raw_color(self, level: LogLevel) -> str:
        if level == LogLevel.ERROR:
            return colors.CORAL
        if level == LogLevel.WARNING:
            return colors.WARNING
        if level == LogLevel.SUCCESS:
            return colors.MINT
        return "#D7DEE8"

    def _duration_pair(self, current: float, total: float) -> str:
        if total <= 0:
            return "--:-- / --:--"
        return f"{self._duration(current)} / {self._duration(total)}"

    def _duration(self, seconds: float) -> str:
        seconds = int(max(seconds, 0))
        minutes, sec = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        if hour:
            return f"{hour:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"

    def _request_update(self) -> None:
        try:
            self.update()
        except Exception:
            try:
                self.page.schedule_update()
            except Exception:
                pass

    def _is_mounted(self) -> bool:
        try:
            return self.page is not None
        except RuntimeError:
            return False
