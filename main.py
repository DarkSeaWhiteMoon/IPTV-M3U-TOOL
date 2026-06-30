from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from iptv_tool.config import load_app_config
from iptv_tool.fetcher import collect_channels
from iptv_tool.filtering import apply_blacklist, apply_keyword_filter, dedupe_by_url, select_fastest
from iptv_tool.output import write_m3u, write_reports
from iptv_tool.tester import test_channels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect, test, and generate an IPTV M3U playlist.")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--keywords", nargs="*", help="Only test channels matching these keywords")
    parser.add_argument("--keep", type=int, help="How many fastest sources to keep per channel")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    config = load_app_config(Path(args.config))

    if args.keywords is not None:
        config.filter.channel_keywords = args.keywords
    if args.keep is not None:
        config.filter.keep_per_channel = args.keep

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    channels = await collect_channels(config)
    collected_count = len(channels)
    channels = apply_blacklist(channels, config.blacklist)
    channels = apply_keyword_filter(channels, config.filter.channel_keywords)
    deduped = dedupe_by_url(channels, config.filter.allowed_schemes)

    tested = await test_channels(deduped, config.network)
    selected = select_fastest(tested, config.filter.keep_per_channel)

    write_m3u(selected, config.output)
    write_reports(
        all_results=tested,
        selected=selected,
        collected_count=collected_count,
        deduped_count=len(deduped),
        output=config.output,
    )


if __name__ == "__main__":
    asyncio.run(run())
