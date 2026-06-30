from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class SourcesConfig:
    urls: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OutputConfig:
    m3u_path: Path = Path("output/mytv.m3u")
    report_md_path: Path = Path("output/report.md")
    report_json_path: Path = Path("output/report.json")
    epg_url: str = "epg.xml"


@dataclass(slots=True)
class NetworkConfig:
    timeout_seconds: float = 10
    concurrency: int = 30
    user_agent: str = "Mozilla/5.0 (AppleTV; IPTV-M3U-TOOL)"
    proxy: str | None = None
    max_bytes_to_read: int = 1_048_576


@dataclass(slots=True)
class FilterConfig:
    keep_per_channel: int = 2
    channel_keywords: list[str] = field(default_factory=list)
    allowed_schemes: list[str] = field(default_factory=lambda: ["http", "https"])


@dataclass(slots=True)
class BlacklistConfig:
    url_contains: list[str] = field(default_factory=list)
    channel_contains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppConfig:
    sources: SourcesConfig
    output: OutputConfig
    network: NetworkConfig
    filter: FilterConfig
    aliases: dict[str, str]
    blacklist: BlacklistConfig
    base_dir: Path


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _resolve(base_dir: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def load_app_config(path: Path) -> AppConfig:
    path = path.resolve()
    base_dir = path.parent
    data = _read_yaml(path)

    sources_data = data.get("sources", {})
    output_data = data.get("output", {})
    network_data = data.get("network", {})
    filter_data = data.get("filter", {})
    paths_data = data.get("paths", {})

    aliases_path = _resolve(base_dir, paths_data.get("channel_aliases", "channel_aliases.yaml"))
    blacklist_path = _resolve(base_dir, paths_data.get("blacklist", "blacklist.yaml"))
    alias_data = _read_yaml(aliases_path)
    blacklist_data = _read_yaml(blacklist_path)

    output = OutputConfig(
        m3u_path=_resolve(base_dir, output_data.get("m3u_path", "output/mytv.m3u")),
        report_md_path=_resolve(base_dir, output_data.get("report_md_path", "output/report.md")),
        report_json_path=_resolve(base_dir, output_data.get("report_json_path", "output/report.json")),
        epg_url=str(output_data.get("epg_url", "epg.xml")),
    )

    return AppConfig(
        sources=SourcesConfig(
            urls=list(sources_data.get("urls", []) or []),
            files=list(sources_data.get("files", []) or []),
        ),
        output=output,
        network=NetworkConfig(
            timeout_seconds=float(network_data.get("timeout_seconds", 10)),
            concurrency=int(network_data.get("concurrency", 30)),
            user_agent=str(network_data.get("user_agent", "Mozilla/5.0 (AppleTV; IPTV-M3U-TOOL)")),
            proxy=network_data.get("proxy"),
            max_bytes_to_read=int(network_data.get("max_bytes_to_read", 1_048_576)),
        ),
        filter=FilterConfig(
            keep_per_channel=int(filter_data.get("keep_per_channel", 2)),
            channel_keywords=list(filter_data.get("channel_keywords", []) or []),
            allowed_schemes=list(filter_data.get("allowed_schemes", ["http", "https"]) or ["http", "https"]),
        ),
        aliases={str(k).strip().lower(): str(v).strip() for k, v in (alias_data.get("aliases", {}) or {}).items()},
        blacklist=BlacklistConfig(
            url_contains=list(blacklist_data.get("url_contains", []) or []),
            channel_contains=list(blacklist_data.get("channel_contains", []) or []),
        ),
        base_dir=base_dir,
    )
