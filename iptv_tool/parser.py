from __future__ import annotations

import re
from urllib.parse import urljoin

from .models import Channel

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def parse_m3u(content: str, source: str = "", base_url: str | None = None) -> list[Channel]:
    channels: list[Channel] = []
    pending_extinf = ""
    pending_attrs: dict[str, str] = {}
    pending_name = ""

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            pending_extinf = line
            pending_attrs = dict(ATTR_RE.findall(line))
            pending_name = _parse_name(line)
            continue
        if line.startswith("#"):
            continue
        if not pending_extinf:
            continue

        url = urljoin(base_url, line) if base_url else line
        channels.append(
            Channel(
                channel_name=pending_name or pending_attrs.get("tvg-name", "").strip() or url,
                url=url,
                group_title=pending_attrs.get("group-title", "").strip(),
                tvg_id=pending_attrs.get("tvg-id", "").strip(),
                tvg_logo=pending_attrs.get("tvg-logo", "").strip(),
                raw_extinf=pending_extinf,
                source=source,
            )
        )
        pending_extinf = ""
        pending_attrs = {}
        pending_name = ""

    return channels


def _parse_name(extinf: str) -> str:
    if "," not in extinf:
        return ""
    return extinf.rsplit(",", 1)[-1].strip()
