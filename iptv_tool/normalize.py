from __future__ import annotations

import re

GROUP_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("CCTV", ("CCTV", "央视", "中央")),
    ("卫视", ("卫视", "湖南", "浙江", "江苏", "东方", "北京", "广东", "深圳", "安徽", "山东", "河南", "湖北", "辽宁", "四川", "重庆", "广西", "贵州", "东南", "河北", "江西", "黑龙江", "吉林", "山西", "陕西", "云南", "甘肃", "青海", "宁夏", "内蒙古", "新疆", "西藏")),
    ("港澳台", ("香港", "澳门", "台湾", "翡翠", "明珠", "TVB", "凤凰", "港台", "民视", "中天", "东森", "三立", "华视", "台视", "中视")),
    ("电影", ("电影", "影院", "剧场", "影迷", "动作", "CHC")),
    ("体育", ("体育", "足球", "篮球", "赛事", "NBA", "五星", "高尔夫", "CCTV5")),
    ("新闻", ("新闻", "资讯", "财经", "第一财经", "CCTV13")),
    ("儿童", ("少儿", "儿童", "卡通", "动漫", "金鹰卡通", "CCTV14")),
]

CHINESE_CCTV_NUMBERS = {
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
    "十一": "11",
    "十二": "12",
    "十三": "13",
    "十四": "14",
    "十五": "15",
    "十六": "16",
    "十七": "17",
}


def normalize_channel_name(name: str, aliases: dict[str, str] | None = None) -> str:
    aliases = aliases or {}
    cleaned = _cleanup(name)
    alias = aliases.get(cleaned.lower()) or aliases.get(name.strip().lower())
    if alias:
        return alias

    cctv = _normalize_cctv(cleaned)
    if cctv:
        return cctv

    cleaned = re.sub(r"(高清|超清|蓝光|HD|FHD|4K|1080P|720P|标清)$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned or name.strip()


def classify_channel(name: str, original_group: str = "") -> str:
    text = f"{name} {original_group}".upper()
    for group, keywords in GROUP_RULES:
        if any(keyword.upper() in text for keyword in keywords):
            return group
    return "其他"


def _cleanup(name: str) -> str:
    text = name.strip()
    text = re.sub(r"\[[^\]]*]", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"（[^）]*）", "", text)
    text = re.sub(r"(高清|超清|蓝光|HD|FHD|4K|1080P|720P|标清)", "", text, flags=re.IGNORECASE)
    return text.strip(" -_")


def _normalize_cctv(name: str) -> str:
    compact = re.sub(r"[\s\-_]+", "", name.upper())
    match = re.search(r"CCTV(?:央视|中央电视台)?(\d{1,2})", compact)
    if match:
        return f"CCTV{match.group(1)}"
    match = re.search(r"(?:央视|中央)([一二三四五六七八九十]{1,2})套", name)
    if match and match.group(1) in CHINESE_CCTV_NUMBERS:
        return f"CCTV{CHINESE_CCTV_NUMBERS[match.group(1)]}"
    return ""
