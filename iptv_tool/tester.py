from __future__ import annotations

import asyncio
import logging
import time
from urllib.parse import urljoin

import aiohttp

from .config import NetworkConfig
from .models import Channel, TestResult

LOGGER = logging.getLogger(__name__)


async def test_channels(channels: list[Channel], config: NetworkConfig) -> list[TestResult]:
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds, sock_connect=config.timeout_seconds)
    headers = {"User-Agent": config.user_agent, "Accept": "*/*"}
    connector = aiohttp.TCPConnector(limit=max(config.concurrency, 1), ssl=False)
    semaphore = asyncio.Semaphore(max(config.concurrency, 1))

    async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
        tasks = [_test_one_with_limit(semaphore, session, channel, config) for channel in channels]
        results: list[TestResult] = []
        for index, task in enumerate(asyncio.as_completed(tasks), start=1):
            result = await task
            results.append(result)
            if index % 50 == 0 or index == len(tasks):
                LOGGER.info("Tested %s/%s streams", index, len(tasks))
    return results


async def _test_one_with_limit(
    semaphore: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    channel: Channel,
    config: NetworkConfig,
) -> TestResult:
    async with semaphore:
        try:
            return await _test_one(session, channel, config)
        except asyncio.TimeoutError:
            return TestResult(channel=channel, playable=False, reason="timeout")
        except aiohttp.ClientResponseError as exc:
            return TestResult(channel=channel, playable=False, status=exc.status, reason=f"http_{exc.status}")
        except Exception as exc:
            return TestResult(channel=channel, playable=False, reason=exc.__class__.__name__)


async def _test_one(session: aiohttp.ClientSession, channel: Channel, config: NetworkConfig) -> TestResult:
    start = time.perf_counter()
    async with session.get(channel.url, proxy=config.proxy, allow_redirects=True) as response:
        status = response.status
        if status < 200 or status >= 400:
            return TestResult(channel=channel, playable=False, status=status, reason=f"http_{status}")
        content_type = response.headers.get("Content-Type", "")
        text = await response.text(errors="ignore")

    response_time_ms = (time.perf_counter() - start) * 1000
    if not _looks_like_playlist(text, channel.url, content_type):
        return TestResult(
            channel=channel,
            playable=False,
            status=status,
            response_time_ms=response_time_ms,
            reason="not_m3u8",
        )

    media_url = _pick_media_playlist(channel.url, text)
    segment_url = _pick_first_segment(media_url, text if media_url == channel.url else await _fetch_text(session, media_url, config))
    if not segment_url:
        return TestResult(
            channel=channel,
            playable=False,
            status=status,
            response_time_ms=response_time_ms,
            tested_url=media_url,
            reason="no_segment",
        )

    speed_kbps = await _download_segment(session, segment_url, config)
    if speed_kbps <= 0:
        return TestResult(
            channel=channel,
            playable=False,
            status=status,
            response_time_ms=response_time_ms,
            tested_url=media_url,
            segment_url=segment_url,
            reason="segment_download_failed",
        )

    return TestResult(
        channel=channel,
        playable=True,
        status=status,
        response_time_ms=response_time_ms,
        download_speed_kbps=speed_kbps,
        tested_url=media_url,
        segment_url=segment_url,
        reason="ok",
    )


async def _fetch_text(session: aiohttp.ClientSession, url: str, config: NetworkConfig) -> str:
    async with session.get(url, proxy=config.proxy, allow_redirects=True) as response:
        response.raise_for_status()
        return await response.text(errors="ignore")


async def _download_segment(session: aiohttp.ClientSession, url: str, config: NetworkConfig) -> float:
    start = time.perf_counter()
    total = 0
    async with session.get(url, proxy=config.proxy, allow_redirects=True) as response:
        if response.status < 200 or response.status >= 400:
            return 0
        async for chunk in response.content.iter_chunked(65536):
            total += len(chunk)
            if total >= config.max_bytes_to_read:
                break
    elapsed = max(time.perf_counter() - start, 0.001)
    return (total * 8 / 1000) / elapsed


def _looks_like_playlist(text: str, url: str, content_type: str) -> bool:
    lowered_type = content_type.lower()
    return (
        "#EXTM3U" in text[:512]
        or url.lower().endswith(".m3u8")
        or "mpegurl" in lowered_type
        or "vnd.apple.mpegurl" in lowered_type
    )


def _pick_media_playlist(url: str, playlist: str) -> str:
    lines = [line.strip() for line in playlist.splitlines() if line.strip()]
    variants: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        bandwidth = _extract_bandwidth(line)
        next_url = _next_uri(lines, index + 1)
        if next_url:
            variants.append((bandwidth, urljoin(url, next_url)))
    if not variants:
        return url
    variants.sort(key=lambda item: item[0], reverse=True)
    return variants[0][1]


def _pick_first_segment(url: str, playlist: str) -> str:
    lines = [line.strip() for line in playlist.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("#"):
            continue
        return urljoin(url, line)
    return ""


def _next_uri(lines: list[str], start_index: int) -> str:
    for line in lines[start_index:]:
        if line.startswith("#"):
            continue
        return line
    return ""


def _extract_bandwidth(line: str) -> int:
    marker = "BANDWIDTH="
    if marker not in line:
        return 0
    value = line.split(marker, 1)[1].split(",", 1)[0]
    try:
        return int(value)
    except ValueError:
        return 0
