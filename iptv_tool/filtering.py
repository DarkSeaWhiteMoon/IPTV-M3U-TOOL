from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlparse

from .config import BlacklistConfig
from .models import Channel, TestResult


def dedupe_by_url(channels: list[Channel], allowed_schemes: list[str] | None = None) -> list[Channel]:
    schemes = set(allowed_schemes or ["http", "https"])
    seen: set[str] = set()
    unique: list[Channel] = []
    for channel in channels:
        key = channel.url.strip()
        if not key or key in seen:
            continue
        parsed = urlparse(key)
        if parsed.scheme not in schemes:
            continue
        seen.add(key)
        unique.append(channel)
    return unique


def apply_blacklist(channels: list[Channel], blacklist: BlacklistConfig) -> list[Channel]:
    url_terms = [term.lower() for term in blacklist.url_contains]
    channel_terms = [term.lower() for term in blacklist.channel_contains]
    kept: list[Channel] = []
    for channel in channels:
        url = channel.url.lower()
        name = f"{channel.channel_name} {channel.normalized_name}".lower()
        if any(term in url for term in url_terms):
            continue
        if any(term in name for term in channel_terms):
            continue
        kept.append(channel)
    return kept


def apply_keyword_filter(channels: list[Channel], keywords: list[str]) -> list[Channel]:
    if not keywords:
        return channels
    terms = [keyword.lower() for keyword in keywords]
    return [
        channel
        for channel in channels
        if any(term in f"{channel.channel_name} {channel.normalized_name} {channel.group_title}".lower() for term in terms)
    ]


def select_fastest(results: list[TestResult], keep_per_channel: int) -> dict[str, list[TestResult]]:
    grouped: dict[str, list[TestResult]] = defaultdict(list)
    for result in results:
        if result.playable:
            grouped[result.channel.normalized_name].append(result)

    selected: dict[str, list[TestResult]] = {}
    for name, items in grouped.items():
        items.sort(
            key=lambda item: (
                -(item.download_speed_kbps or 0),
                item.response_time_ms if item.response_time_ms is not None else float("inf"),
            )
        )
        selected[name] = items[: max(1, keep_per_channel)]
    return dict(sorted(selected.items(), key=lambda pair: pair[0]))
