from __future__ import annotations

import configparser
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from core.event_bus import EventBus
from core.events import LogEvent, LogLevel, ProgressEvent, TaskStateEvent, TaskStatus
from models.account import AccountConfig
from services.config_manager import ConfigManager
from services.log_parser import LogParser
from services.task_engine import TaskEngine

CMD_ENCODING = "gb18030" if sys.platform == "win32" else "utf-8"


@dataclass(slots=True)
class AccountCardState:
    account_id: str
    title: str
    course_info: str = "自动扫描全部未完成课程"
    action_info: str = "等待任务启动"
    percent: float = 0.0
    status: TaskStatus = TaskStatus.IDLE
    phone: str = ""
    config: AccountConfig | None = None
    temp_config_path: Path | None = None
    last_run_time: str = ""
    run_duration: str = ""
    run_start_time: datetime | None = None


class AccountViewModel:
    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        task_engine: TaskEngine | None = None,
        event_bus: EventBus | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.task_engine = task_engine
        self.event_bus = event_bus
        self.project_root = Path(project_root or ".").resolve()
        self.cards: list[AccountCardState] = []
        self.selected_accounts: set[str] = set()
        self.log_events: dict[str, list[LogEvent]] = defaultdict(list)
        self.progress_events: dict[str, list[ProgressEvent]] = defaultdict(list)
        self.on_change: Callable[[], None] | None = None
        self.session_stats: dict[str, int] = {
            "total_tasks": 0,
            "completed_videos": 0,
            "tiku_submitted": 0,
            "tiku_obtained": 0,
        }
        self._completed_video_keys: set[str] = set()
        self._tiku_pending_obtained: set[str] = set()
        self._load_history_cards()
        if self.event_bus is not None:
            self.event_bus.subscribe_sync(LogEvent, self._on_log)
            self.event_bus.subscribe_sync(TaskStateEvent, self._on_task_state)
            self.event_bus.subscribe_sync(ProgressEvent, self._on_progress)

    def add_account(self, config: AccountConfig | None = None) -> AccountCardState:
        config = config or AccountConfig(remark=f"学习账号 {len(self.cards) + 1}")
        card = self._state_from_config(config)
        self.cards.append(card)
        self._persist_history()
        self._notify()
        return card

    def update_account(self, account_id: str, config: AccountConfig) -> None:
        card = self._find(account_id)
        if card is None:
            self.add_account(config)
            return
        card.config = config
        card.title = config.remark or config.username or "未命名账号"
        card.phone = config.username or "未配置手机号"
        card.course_info = self._course_info_for_config(config)
        card.action_info = "配置已更新"
        if card.status == TaskStatus.FAILED:
            card.status = TaskStatus.IDLE
        self._persist_history()
        self._notify()

    def copy_account(self, account_id: str) -> AccountCardState | None:
        source = self._find(account_id)
        if source is None or source.config is None:
            return None
        new_config = AccountConfig(
            username=source.config.username,
            password=source.config.password,
            school=source.config.school,
            remark=f"{source.config.remark or '账号'}（副本）",
            course_url=source.config.course_url,
            options=dict(source.config.options),
        )
        return self.add_account(new_config)

    def remove_account(self, account_id: str) -> None:
        self.stop_account(account_id)
        self.cards = [card for card in self.cards if card.account_id != account_id]
        self._persist_history()
        self._notify()

    def start_account(self, account_id: str) -> None:
        card = self._find(account_id)
        if card is None or card.config is None:
            return
        if self.task_engine is None or self.config_manager is None:
            self._fail_before_start(card, "任务引擎尚未初始化。")
            return
        if not card.config.username or not card.config.password:
            self._fail_before_start(card, "请先填写手机号和密码。")
            return

        global_config = self.config_manager.load_global_config()
        course_list = self._course_list_for_tool(card.config)
        temp_path = self._write_temp_config(card.account_id, card.config, global_config, course_list)
        card.temp_config_path = temp_path
        command = [*(global_config.command or ["./chaoxing.exe"]), "-c", str(temp_path), "-v"]

        card.status = TaskStatus.RUNNING
        card.action_info = "正在启动底层任务..."
        card.percent = max(card.percent, 1.0)
        now = datetime.now()
        card.run_start_time = now
        card.last_run_time = now.strftime("%Y-%m-%d %H:%M:%S")
        card.run_duration = "00:00:00"
        self._notify()
        self._publish_log(account_id, f"已生成临时配置：{temp_path.name}")
        self._publish_log(account_id, f"课程范围：{'自动扫描全部未完成课程' if course_list == '0' else course_list}")
        self.task_engine.start(account_id, command)
        self.session_stats["total_tasks"] += 1

    def stop_account(self, account_id: str) -> None:
        card = self._find(account_id)
        if card is None:
            return
        card.status = TaskStatus.STOPPED
        card.action_info = "任务已停止"
        card.run_duration = self._format_duration(card.run_start_time)
        self._notify()
        if self.task_engine is not None:
            self.task_engine.stop(account_id)
        self._cleanup_temp_config(card)

    def stop_all(self) -> None:
        for card in self.cards:
            card.status = TaskStatus.STOPPED
            card.action_info = "任务已停止"
            card.percent = 0.0 if card.percent < 100 else card.percent
            self._cleanup_temp_config(card)
        if self.task_engine is not None:
            self.task_engine.stop_all()
        self._notify()

    def toggle_selection(self, account_id: str) -> None:
        if account_id in self.selected_accounts:
            self.selected_accounts.discard(account_id)
        else:
            self.selected_accounts.add(account_id)
        self._notify()

    def select_all(self) -> None:
        self.selected_accounts = {card.account_id for card in self.cards}
        self._notify()

    def deselect_all(self) -> None:
        self.selected_accounts.clear()
        self._notify()

    def batch_start(self) -> None:
        targets = list(self.selected_accounts)
        for account_id in targets:
            card = self._find(account_id)
            if card is not None and card.status != TaskStatus.RUNNING:
                self.start_account(account_id)

    def batch_stop(self) -> None:
        targets = list(self.selected_accounts)
        for account_id in targets:
            card = self._find(account_id)
            if card is not None and card.status == TaskStatus.RUNNING:
                self.stop_account(account_id)

    def batch_delete(self) -> None:
        targets = list(self.selected_accounts)
        for account_id in targets:
            self.stop_account(account_id)
            self.cards = [card for card in self.cards if card.account_id != account_id]
        self.selected_accounts.clear()
        self._persist_history()
        self._notify()

    def dispose(self) -> None:
        self.stop_all()

    def fetch_courses(self, config: AccountConfig) -> list[tuple[str, str]]:
        if self.config_manager is None:
            return []
        if not config.username or not config.password:
            self._publish_log("course_fetch", "请先填写手机号和密码，再获取课程。", LogLevel.WARNING)
            return []

        global_config = self.config_manager.load_global_config()
        cfg_path = self._write_temp_config(
            "fetch",
            config,
            global_config,
            course_list="",
            filename=f"config_temp_fetch_{self._safe_name(config.username)}.ini",
            include_tiku=False,
        )
        command = [*(global_config.command or ["./chaoxing.exe"]), "-c", str(cfg_path)]
        self._publish_log("course_fetch", f"正在登录并查询课程：{command[0]} -c {cfg_path.name}")
        output = ""
        try:
            result = subprocess.run(
                command,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding=CMD_ENCODING,
                errors="replace",
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output = result.stdout or ""
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            self._publish_log("course_fetch", "课程查询超时，已尝试解析已输出内容。", LogLevel.WARNING)
        except Exception as exc:
            self._publish_log("course_fetch", f"课程查询失败：{exc}", LogLevel.ERROR)
        finally:
            try:
                cfg_path.unlink(missing_ok=True)
            except OSError:
                pass

        for line in output.splitlines():
            clean = line.strip()
            if clean:
                self._publish_log("course_fetch", clean)
        courses = self._parse_courses(output)
        self._publish_log(
            "course_fetch",
            f"已获取到 {len(courses)} 门课程。" if courses else "未获取到课程列表，请检查账号状态或查看原始输出。",
            LogLevel.SUCCESS if courses else LogLevel.WARNING,
        )
        return courses

    def open_config(self, account_id: str) -> AccountCardState | None:
        return self._find(account_id)

    def _on_task_state(self, event: TaskStateEvent) -> None:
        card = self._find(event.account_id)
        if card is None or card.status == TaskStatus.STOPPED:
            return
        card.status = event.status
        if event.status == TaskStatus.RUNNING:
            card.action_info = "底层任务运行中"
        elif event.status == TaskStatus.COMPLETED:
            card.percent = 100.0
            card.action_info = "任务已完成"
            card.run_duration = self._format_duration(card.run_start_time)
            self._cleanup_temp_config(card)
        elif event.status == TaskStatus.FAILED:
            card.action_info = f"任务失败：{event.reason or '未知错误'}"
            card.run_duration = self._format_duration(card.run_start_time)
            self._cleanup_temp_config(card)
        self._notify()

    def _on_log(self, event: LogEvent) -> None:
        self.log_events[event.account_id].append(event)
        if len(self.log_events[event.account_id]) > 1200:
            self.log_events[event.account_id] = self.log_events[event.account_id][-1200:]
        tiku_type, submitted = LogParser.detect_tiku_metrics(event.message)
        aid = event.account_id
        if tiku_type == "obtained":
            self._tiku_pending_obtained.add(aid)
        elif tiku_type == "discarded":
            self._tiku_pending_obtained.discard(aid)
        elif tiku_type == "submitted":
            self.session_stats["tiku_submitted"] += submitted
            if aid in self._tiku_pending_obtained:
                self.session_stats["tiku_obtained"] += 1
                self._tiku_pending_obtained.discard(aid)

    def _on_progress(self, event: ProgressEvent) -> None:
        card = self._find(event.account_id)
        if card is None:
            return
        if card.status == TaskStatus.STOPPED:
            return

        self.progress_events[event.account_id].append(event)
        if len(self.progress_events[event.account_id]) > 300:
            self.progress_events[event.account_id] = self.progress_events[event.account_id][-300:]
        card.percent = event.percent
        card.status = event.status
        card.run_duration = self._format_duration(card.run_start_time)
        text = self._playback_text(card, event)
        card.action_info = f"正在播放：{text}" if event.percent < 100 else f"已完成：{text}"

        completed = bool(event.meta.get("completed")) or event.percent >= 100
        if completed:
            video = event.video_title or event.chapter or ""
            key = " ".join(video.strip().lower().split())
            if key and key not in self._completed_video_keys:
                self._completed_video_keys.add(key)
                self.session_stats["completed_videos"] += 1

        self._notify()

    def _write_temp_config(
        self,
        account_id: str,
        account: AccountConfig,
        global_config,
        course_list: str,
        filename: str | None = None,
        include_tiku: bool = True,
    ) -> Path:
        temp_dir = self.project_root / "data" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        path = temp_dir / (filename or f"config_temp_{self._safe_name(account_id)}.ini")
        options = account.options or {}
        parser = configparser.ConfigParser()
        parser["common"] = {
            "use_cookies": "false",
            "username": account.username,
            "password": account.password,
            "course_list": course_list,
            "speed": str(options.get("speed", "1.0")),
            "jobs": str(options.get("workers", global_config.max_workers)),
            "notopen_action": "retry",
        }
        if include_tiku and bool(options.get("enable_tiku", True)):
            token = global_config.tiku_token or ""
            provider = global_config.tiku_provider
            endpoint = global_config.tiku_endpoint or ""
            model = global_config.tiku_model or ""
            adapter_url = global_config.tiku_adapter_url or ""
            coverage = str(global_config.tiku_coverage)
            delay = str(global_config.tiku_delay)
            proxy = global_config.proxy or ""
            parser["tiku"] = {
                "provider": provider,
                "submit": "true" if global_config.tiku_submit else "false",
                "cover_rate": coverage,
                "delay": delay,
                "true_list": "正确,对,√,是",
                "false_list": "错误,错,×,否,不对,不正确",
                "tokens": token,
                "url": adapter_url or token,
                "endpoint": endpoint,
                "key": token,
                "model": model,
                "min_interval_seconds": "3",
                "http_proxy": proxy,
                "likeapi_search": "false",
                "likeapi_vision": "true",
                "likeapi_model": "glm-4.5-air",
                "likeapi_retry": "true",
                "likeapi_retry_times": "3",
                "siliconflow_key": token,
                "siliconflow_model": model or "deepseek-ai/DeepSeek-R1",
                "siliconflow_endpoint": endpoint or "https://api.siliconflow.cn/v1/chat/completions",
            }
        with path.open("w", encoding="utf-8") as file:
            parser.write(file)
        return path

    def _course_list_for_tool(self, config: AccountConfig) -> str:
        raw = str(config.course_url or config.options.get("course_id", "")).strip()
        if not raw or raw == "0":
            return "0"
        ids = []
        for item in re.split(r"[,，\n]+", raw):
            course_id = self._extract_course_id(item)
            if course_id:
                ids.append(course_id)
        return ",".join(ids) if ids else "0"

    def _parse_courses(self, output: str) -> list[tuple[str, str]]:
        courses: list[tuple[str, str]] = []
        seen: set[str] = set()
        for line in output.splitlines():
            clean = line.strip()
            if clean.startswith("ID:") and "课程名:" in clean:
                left, right = clean.split("课程名:", 1)
                course_id = left.replace("ID:", "").strip()
                title = right.strip()
            else:
                match = re.search(r"ID[:：]\s*(?P<id>\d+).*?(?:课程名|课程)[:：]\s*(?P<title>.+)", clean)
                if not match:
                    continue
                course_id = match.group("id").strip()
                title = match.group("title").strip()
            if course_id and course_id not in seen:
                seen.add(course_id)
                courses.append((course_id, title))
        return courses

    def _playback_text(self, card: AccountCardState, event: ProgressEvent) -> str:
        video = event.video_title or event.chapter or "正在更新视频进度"
        course_name = event.course.strip()
        course_id = self._course_id_for_name(card.config, course_name) or self._first_course_id(card.config)

        if course_name and course_id:
            return f"{course_name} [{course_id}] / {video}"
        if course_name:
            return f"{course_name} / {video}"
        if course_id:
            return f"课程 [{course_id}] / {video}"
        return video

    def _course_id_for_name(self, config: AccountConfig | None, course_name: str) -> str:
        if config is None or not course_name:
            return ""
        raw = str(config.course_url or config.options.get("course_id", "")).strip()
        for item in re.split(r"[,，\n]+", raw):
            item = item.strip()
            match = re.match(r"(?P<name>.+?)\s*[\(（](?P<id>\d+)[\)）]\s*$", item)
            if match and match.group("name").strip() == course_name:
                return match.group("id")
        return ""

    def _first_course_id(self, config: AccountConfig | None) -> str:
        if config is None:
            return ""
        raw = str(config.course_url or config.options.get("course_id", "")).strip()
        for item in re.split(r"[,，\n]+", raw):
            course_id = self._extract_course_id(item)
            if course_id:
                return course_id
        return ""

    def _extract_course_id(self, value: str) -> str:
        item = value.strip()
        if not item:
            return ""

        paren_matches = re.findall(r"[\(（]\s*(\d{5,})\s*[\)）]", item)
        if paren_matches:
            return paren_matches[-1]

        if re.fullmatch(r"\d+", item):
            return item

        for pattern in (
            r"(?:courseId|courseid|course_id|课程ID|课程id)[:=：]\s*(\d{5,})",
            r"(?:clazzId|classid|cpi)[:=：]\s*(\d{5,})",
        ):
            if match := re.search(pattern, item):
                return match.group(1)

        long_numbers = re.findall(r"\d{6,}", item)
        return long_numbers[-1] if long_numbers else ""

    def _course_info_for_config(self, config: AccountConfig) -> str:
        raw = str(config.course_url or config.options.get("course_id", "")).strip()
        if not raw or raw == "0":
            return "自动扫描全部未完成课程"
        formatted = []
        for item in re.split(r"[,，\n]+", raw):
            item = item.strip()
            if not item:
                continue
            match = re.match(r"(?P<name>.+?)\s*[\(（](?P<id>\d+)[\)）]\s*$", item)
            if match:
                formatted.append(f"{match.group('name').strip()} [{match.group('id')}]")
            else:
                formatted.append(item)
        return "；".join(formatted) if formatted else f"课程 ID: {raw}"

    def _fail_before_start(self, card: AccountCardState, message: str) -> None:
        card.status = TaskStatus.FAILED
        card.action_info = message
        self._cleanup_temp_config(card)
        self._publish_log(card.account_id, message, LogLevel.ERROR)
        self._notify()

    def _cleanup_temp_config(self, card: AccountCardState) -> None:
        path = card.temp_config_path
        card.temp_config_path = None
        if path is not None and path.exists():
            try:
                path.unlink()
            except OSError:
                self._publish_log(card.account_id, f"临时配置清理失败：{path}", LogLevel.WARNING)

    def _load_history_cards(self) -> None:
        if self.config_manager is None:
            self.cards.append(self._state_from_config(AccountConfig(remark="默认账号")))
            return
        history = self.config_manager.load_history()
        self.cards = [self._state_from_config(config) for config in history]
        if not self.cards:
            self.cards.append(self._state_from_config(AccountConfig(remark="默认账号")))

    def _state_from_config(self, config: AccountConfig) -> AccountCardState:
        return AccountCardState(
            account_id=uuid4().hex,
            title=config.remark or config.username or "未命名账号",
            course_info=self._course_info_for_config(config),
            action_info="等待任务启动",
            phone=config.username or "未配置手机号",
            config=config,
        )

    def _persist_history(self) -> None:
        if self.config_manager is None:
            return
        configs = [card.config for card in self.cards if card.config is not None and (card.config.username or card.config.remark)]
        self.config_manager.save_history(configs)

    def _publish_log(self, account_id: str, message: str, level: LogLevel = LogLevel.INFO) -> None:
        if self.event_bus is not None:
            self.event_bus.publish_sync(LogEvent(account_id=account_id, message=message, level=level, is_elegant=False))

    def _safe_name(self, value: str) -> str:
        return re.sub(r"[^0-9A-Za-z_-]+", "_", value or uuid4().hex[:8])

    def get_session_stats(self) -> dict[str, float]:
        total_duration = 0.0
        running_count = 0
        completed_tasks = 0
        failed_tasks = 0
        for card in self.cards:
            if card.run_start_time is not None:
                if card.status == TaskStatus.RUNNING:
                    running_count += 1
                    total_duration += (datetime.now() - card.run_start_time).total_seconds()
                elif card.status == TaskStatus.COMPLETED:
                    completed_tasks += 1
                    total_duration += self._parse_duration(card.run_duration)
                elif card.status in {TaskStatus.FAILED, TaskStatus.STOPPED}:
                    if card.status == TaskStatus.FAILED:
                        failed_tasks += 1
                    total_duration += self._parse_duration(card.run_duration)
        finished = completed_tasks + failed_tasks
        success_rate = (completed_tasks / finished * 100) if finished > 0 else 0.0
        return {
            **self.session_stats,
            "running_tasks": running_count,
            "total_duration": total_duration,
            "success_rate": success_rate,
        }

    def _parse_duration(self, duration_str: str) -> float:
        if not duration_str:
            return 0.0
        parts = duration_str.split(":")
        if len(parts) == 3:
            try:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except (ValueError, IndexError):
                return 0.0
        return 0.0

    def _format_duration(self, start_time: datetime | None) -> str:
        if start_time is None:
            return ""
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed < 0:
            elapsed = 0
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _find(self, account_id: str) -> AccountCardState | None:
        return next((card for card in self.cards if card.account_id == account_id), None)

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()
