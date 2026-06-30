from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Channel:
    channel_name: str
    url: str
    group_title: str = ""
    tvg_id: str = ""
    tvg_logo: str = ""
    raw_extinf: str = ""
    source: str = ""
    normalized_name: str = ""
    normalized_group: str = ""


@dataclass(slots=True)
class TestResult:
    channel: Channel
    playable: bool
    status: int | None = None
    response_time_ms: float | None = None
    download_speed_kbps: float | None = None
    tested_url: str = ""
    segment_url: str = ""
    reason: str = ""
    details: dict[str, str | int | float | bool | None] = field(default_factory=dict)
