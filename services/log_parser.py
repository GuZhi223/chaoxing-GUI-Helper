from __future__ import annotations

import re

from core.event_bus import EventBus
from core.events import ChapterEvent, LogEvent, LogLevel, ProgressEvent, TaskStatus

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
STANDARD_LOG = re.compile(
    r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+\s+\|\s+(?P<level>[A-Z]+)\s*\|\s+.*?-\s+(?P<message>.*)$"
)


class LogParser:
    TOTAL_COURSES = re.compile(r"课程列表过滤完毕,\s*当前课程任务数量:\s*(?P<count>\d+)|当前课程任务数量:\s*(?P<count2>\d+)")
    COURSE_START = re.compile(r"开始学习课程:\s*(?P<course>.*)")
    COURSE_START_MOJIBAKE = re.compile(r"寮.*?濮嬪.*?涔犺.*?绋.?\s*(?P<course>.*)")
    CHAPTER = re.compile(r"当前章节:\s*(?P<chapter>.*)")
    CHAPTER_MOJIBAKE = re.compile(r"褰撳墠绔犺妭:\s*(?P<chapter>.*)")
    UNFINISHED = re.compile(r"unfinished task:\s*(?P<count>\d+)", re.I)
    VIDEO_START = re.compile(
        r"开始任务:\s*(?P<title>.*?),\s*总时长:\s*(?P<total>\d+)s,\s*已进行:\s*(?P<current>\d+)s"
    )
    VIDEO_START_MOJIBAKE = re.compile(
        r"寮.*?濮嬩换鍔.?\s*(?P<title>.*?),\s*鎬绘椂闀.?\s*(?P<total>\d+)s,\s*宸茶繘琛.?\s*(?P<current>\d+)s"
    )
    VIDEO_FINISH = re.compile(r"任务(?:瞬间)?完成:\s*(?P<title>.*)")
    VIDEO_FINISH_MOJIBAKE = re.compile(r"浠诲姟(?:鐬.*?棿)?瀹屾垚:\s*(?P<title>.*)")
    ALL_DONE = re.compile(r"所有课程学习任务已完成")

    SUCCESS_PATTERNS = [re.compile(r"(完成|已完成|success|finished)", re.I)]
    WARNING_PATTERNS = [re.compile(r"(停止|取消|跳过|warning|warn|unfinished task)", re.I)]
    ERROR_PATTERNS = [re.compile(r"(错误|失败|异常|error|failed|traceback|EOFError)", re.I)]

    TERMINAL_PROGRESS = re.compile(
        r"^\[(?P<clock>\d{2}:\d{2}:\d{2})\]\s+\[(?P<level>[A-Z]+)\]\s+"
        r"(?P<title>.+?):\s*(?P<percent>\d+(?:\.\d+)?)%\s*.*?\|\s*"
        r"(?P<current>\d{1,2}:\d{2}(?::\d{2})?)\s*/\s*(?P<total>\d{1,2}:\d{2}(?::\d{2})?)"
    )

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._course_by_account: dict[str, str] = {}
        self._chapter_by_account: dict[str, str] = {}
        self._video_totals: dict[str, dict[str, float]] = {}

    async def parse_line(self, account_id: str, line: str) -> None:
        self.parse_line_sync(account_id, line)

    def parse_line_sync(self, account_id: str, line: str) -> None:
        clean = self.clean(line)
        if not clean:
            return

        level = self._detect_level(clean)
        self._event_bus.publish_sync(
            LogEvent(
                account_id=account_id,
                message=clean,
                level=level,
                raw=line,
                is_elegant=False,
            )
        )

        semantic_line = self._strip_standard_log_prefix(clean)
        self._publish_elegant_if_matched(account_id, semantic_line)
        self._publish_progress_if_matched(account_id, semantic_line)

    def clean(self, line: str) -> str:
        return ANSI_ESCAPE.sub("", line).strip().replace("...", "")

    def _strip_standard_log_prefix(self, line: str) -> str:
        if match := STANDARD_LOG.search(line):
            return match.group("message").strip()
        return line

    def _publish_elegant_if_matched(self, account_id: str, line: str) -> None:
        if match := self.TOTAL_COURSES.search(line):
            count = match.group("count") or match.group("count2") or "0"
            self._elegant(account_id, f"课程筛选完成：本次将处理 {count} 门课程", LogLevel.INFO)
            return

        if match := self._first_match((self.COURSE_START, self.COURSE_START_MOJIBAKE), line):
            course = match.group("course").strip()
            self._course_by_account[account_id] = course
            self._elegant(account_id, f"开始课程：{course}", LogLevel.INFO)
            self._event_bus.publish_sync(
                ChapterEvent(account_id=account_id, chapter=course, status=TaskStatus.RUNNING, message=line)
            )
            return

        if match := self._first_match((self.CHAPTER, self.CHAPTER_MOJIBAKE), line):
            chapter = match.group("chapter").strip()
            self._chapter_by_account[account_id] = chapter
            self._elegant(account_id, f"进入章节：{chapter}", LogLevel.INFO)
            self._event_bus.publish_sync(
                ChapterEvent(account_id=account_id, chapter=chapter, status=TaskStatus.RUNNING, message=line)
            )
            return

        if match := self.UNFINISHED.search(line):
            self._elegant(account_id, f"剩余任务点：{match.group('count')} 个", LogLevel.WARNING)
            return

        if match := self._first_match((self.VIDEO_START, self.VIDEO_START_MOJIBAKE), line):
            title = match.group("title").strip()
            total = float(match.group("total"))
            current = float(match.group("current"))
            context = self._playback_context(account_id, title)
            self._elegant(
                account_id,
                f"开始视频：{context}（{self._duration(current)} / {self._duration(total)}）",
                LogLevel.INFO,
            )
            return

        if match := self._first_match((self.VIDEO_FINISH, self.VIDEO_FINISH_MOJIBAKE), line):
            title = match.group("title").strip()
            self._elegant(account_id, f"视频完成：{self._playback_context(account_id, title)}", LogLevel.SUCCESS)
            return

        if self.ALL_DONE.search(line):
            self._elegant(account_id, "全部课程学习任务已完成", LogLevel.SUCCESS)

    def _publish_progress_if_matched(self, account_id: str, line: str) -> None:
        if match := self.TERMINAL_PROGRESS.search(line):
            title = match.group("title").strip()
            percent = float(match.group("percent"))
            current = self._parse_duration(match.group("current"))
            total = max(self._parse_duration(match.group("total")), 1.0)
            self._video_totals.setdefault(account_id, {})[title] = total
            self._progress(account_id, title, percent, current, total, completed=percent >= 100.0, source="terminal")
            return

        if match := self._first_match((self.VIDEO_START, self.VIDEO_START_MOJIBAKE), line):
            title = match.group("title").strip()
            total = max(float(match.group("total")), 1.0)
            current = float(match.group("current"))
            self._video_totals.setdefault(account_id, {})[title] = total
            self._progress(account_id, title, min(current / total * 100, 100.0), current, total, source="start")
            return

        if match := self._first_match((self.VIDEO_FINISH, self.VIDEO_FINISH_MOJIBAKE), line):
            title = match.group("title").strip()
            total = self._video_totals.get(account_id, {}).get(title, 0.0)
            self._progress(account_id, title, 100.0, total, total, completed=True, source="finish")

    def _progress(
        self,
        account_id: str,
        title: str,
        percent: float,
        current_seconds: float = 0.0,
        total_seconds: float = 0.0,
        completed: bool = False,
        source: str = "log",
    ) -> None:
        self._event_bus.publish_sync(
            ProgressEvent(
                account_id=account_id,
                chapter=self._chapter_by_account.get(account_id, ""),
                course=self._course_by_account.get(account_id, ""),
                video_title=title,
                percent=max(0.0, min(percent, 100.0)),
                status=TaskStatus.RUNNING,
                meta={
                    "current_seconds": current_seconds,
                    "total_seconds": total_seconds,
                    "completed": completed,
                    "source": source,
                },
            )
        )

    def _elegant(self, account_id: str, message: str, level: LogLevel = LogLevel.INFO) -> None:
        self._event_bus.publish_sync(
            LogEvent(account_id=account_id, message=message, level=level, is_elegant=True)
        )

    def _playback_context(self, account_id: str, video_title: str) -> str:
        pieces = [
            self._course_by_account.get(account_id, "").strip(),
            self._chapter_by_account.get(account_id, "").strip(),
            video_title.strip(),
        ]
        return " / ".join(piece for piece in pieces if piece)

    def _detect_level(self, line: str) -> LogLevel:
        if any(pattern.search(line) for pattern in self.ERROR_PATTERNS):
            return LogLevel.ERROR
        if any(pattern.search(line) for pattern in self.SUCCESS_PATTERNS):
            return LogLevel.SUCCESS
        if any(pattern.search(line) for pattern in self.WARNING_PATTERNS):
            return LogLevel.WARNING
        return LogLevel.INFO

    def _first_match(self, patterns, line: str):
        for pattern in patterns:
            if match := pattern.search(line):
                return match
        return None

    def _parse_duration(self, value: str) -> float:
        parts = [int(part) for part in value.strip().split(":")]
        if len(parts) == 2:
            minutes, seconds = parts
            return minutes * 60 + seconds
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds
        return 0.0

    def _duration(self, seconds: float) -> str:
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        if hour:
            return f"{hour:02d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:02d}:{sec:02d}"
