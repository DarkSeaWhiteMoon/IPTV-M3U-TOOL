from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from .config import AppConfig
from .normalize import classify_channel, normalize_channel_name
from .parser import parse_m3u

LOGGER = logging.getLogger(__name__)


async def collect_channels(config: AppConfig):
    channels = []
    timeout = aiohttp.ClientTimeout(total=config.network.timeout_seconds)
    headers = {"User-Agent": config.network.user_agent}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        for url in config.sources.urls:
            try:
                LOGGER.info("Fetching playlist: %s", url)
                async with session.get(url, proxy=config.network.proxy) as response:
                    response.raise_for_status()
                    content = await response.text(errors="ignore")
                parsed = parse_m3u(content, source=url, base_url=_base_url(url))
                channels.extend(parsed)
                LOGGER.info("Parsed %s channels from %s", len(parsed), url)
            except Exception as exc:
                LOGGER.warning("Failed to fetch playlist %s: %s", url, exc)

    for file_name in config.sources.files:
        file_path = Path(file_name)
        if not file_path.is_absolute():
            file_path = config.base_dir / file_path
        try:
            LOGGER.info("Reading local playlist: %s", file_path)
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            parsed = parse_m3u(content, source=str(file_path), base_url=file_path.parent.as_uri() + "/")
            channels.extend(parsed)
            LOGGER.info("Parsed %s channels from %s", len(parsed), file_path)
        except Exception as exc:
            LOGGER.warning("Failed to read local playlist %s: %s", file_path, exc)

    for channel in channels:
        channel.normalized_name = normalize_channel_name(channel.channel_name, config.aliases)
        channel.normalized_group = classify_channel(channel.normalized_name, channel.group_title)

    LOGGER.info("Collected %s channel entries", len(channels))
    return channels


def _base_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rsplit("/", 1)[0] + "/"
    return parsed._replace(path=path, params="", query="", fragment="").geturl()
