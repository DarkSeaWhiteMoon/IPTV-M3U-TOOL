from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

from .config import OutputConfig
from .models import TestResult


def write_m3u(selected: dict[str, list[TestResult]], output: OutputConfig) -> None:
    output.m3u_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'#EXTM3U x-tvg-url="{_escape_attr(output.epg_url)}"']

    for channel_name, results in selected.items():
        for index, result in enumerate(results):
            display_name = channel_name if index == 0 else f"{channel_name} 备用{index}"
            channel = result.channel
            tvg_id = channel.tvg_id or channel_name
            logo = channel.tvg_logo
            group = channel.normalized_group or "其他"
            lines.append(
                f'#EXTINF:-1 tvg-id="{_escape_attr(tvg_id)}" '
                f'tvg-logo="{_escape_attr(logo)}" group-title="{_escape_attr(group)}",{display_name}'
            )
            lines.append(channel.url)

    output.m3u_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(
    all_results: list[TestResult],
    selected: dict[str, list[TestResult]],
    collected_count: int,
    deduped_count: int,
    output: OutputConfig,
) -> None:
    output.report_md_path.parent.mkdir(parents=True, exist_ok=True)
    playable = [result for result in all_results if result.playable]
    failed = [result for result in all_results if not result.playable]
    selected_flat = [result for results in selected.values() for result in results]
    failure_counts = Counter(result.reason for result in failed)

    output.report_md_path.write_text(
        _build_markdown_report(
            collected_count=collected_count,
            deduped_count=deduped_count,
            playable=playable,
            failed=failed,
            selected=selected,
            failure_counts=failure_counts,
        ),
        encoding="utf-8",
    )

    report_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collected_count": collected_count,
        "deduped_count": deduped_count,
        "playable_count": len(playable),
        "failed_count": len(failed),
        "selected_count": len(selected_flat),
        "failure_counts": dict(failure_counts),
        "fastest": _result_to_dict(_fastest(playable)),
        "slowest": _result_to_dict(_slowest(playable)),
        "selected": {
            name: [_result_to_dict(result) for result in results]
            for name, results in selected.items()
        },
    }
    output.report_json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _build_markdown_report(
    collected_count: int,
    deduped_count: int,
    playable: list[TestResult],
    failed: list[TestResult],
    selected: dict[str, list[TestResult]],
    failure_counts: Counter[str],
) -> str:
    fastest = _fastest(playable)
    slowest = _slowest(playable)
    lines = [
        "# IPTV 更新报告",
        "",
        f"- 生成时间：{datetime.now(timezone.utc).isoformat()}",
        f"- 总共收集：{collected_count}",
        f"- 去重后：{deduped_count}",
        f"- 可播放：{len(playable)}",
        f"- 不可播放：{len(failed)}",
        f"- 最终保留频道：{len(selected)}",
        "",
        "## 失败原因统计",
        "",
    ]
    if failure_counts:
        lines.extend(f"- {reason}: {count}" for reason, count in failure_counts.most_common())
    else:
        lines.append("- 无")

    lines.extend(["", "## 快慢统计", ""])
    lines.append(_speed_line("最快源", fastest))
    lines.append(_speed_line("最慢源", slowest))

    lines.extend(["", "## 每个频道保留的最快源", ""])
    if not selected:
        lines.append("没有可播放源。")
    for channel_name, results in selected.items():
        lines.append(f"### {channel_name}")
        for index, result in enumerate(results):
            suffix = "" if index == 0 else f" 备用{index}"
            speed = _fmt_speed(result.download_speed_kbps)
            latency = _fmt_latency(result.response_time_ms)
            lines.append(f"- {channel_name}{suffix}: {speed}, {latency}, {result.channel.url}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _speed_line(label: str, result: TestResult | None) -> str:
    if not result:
        return f"- {label}：无"
    return f"- {label}：{result.channel.normalized_name}，{_fmt_speed(result.download_speed_kbps)}，{result.channel.url}"


def _fastest(results: list[TestResult]) -> TestResult | None:
    return max(results, key=lambda result: result.download_speed_kbps or 0, default=None)


def _slowest(results: list[TestResult]) -> TestResult | None:
    return min(results, key=lambda result: result.download_speed_kbps or float("inf"), default=None)


def _result_to_dict(result: TestResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "channel_name": result.channel.channel_name,
        "normalized_name": result.channel.normalized_name,
        "group_title": result.channel.normalized_group,
        "url": result.channel.url,
        "playable": result.playable,
        "status": result.status,
        "response_time_ms": result.response_time_ms,
        "download_speed_kbps": result.download_speed_kbps,
        "tested_url": result.tested_url,
        "segment_url": result.segment_url,
        "reason": result.reason,
    }


def _fmt_speed(speed: float | None) -> str:
    if speed is None:
        return "未知速度"
    return f"{speed:.0f} kbps"


def _fmt_latency(latency: float | None) -> str:
    if latency is None:
        return "未知延迟"
    return f"{latency:.0f} ms"


def _escape_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;")
