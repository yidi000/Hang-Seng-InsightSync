from __future__ import annotations

import re

from .models import BusinessEvent, ExtractedMetric, ManagementDiscussion, ParsedSection, ParsedTable, RiskFactor
from .utils import extract_date_candidates, normalize_text

_METRIC_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("revenue", r"(?:\brevenue\b|\bsales\b|\bturnover\b|营业收入|营收|收入)", False),
    ("net profit", r"(?:\bnet profit\b|\bprofit attributable\b|\bnet income\b|净利润|归母净利润)", False),
    ("operating profit", r"(?:\boperating profit\b|\boperating income\b|\bebitda\b|营业利润)", False),
    ("total assets", r"(?:\btotal assets\b|\bassets under management\b|总资产)", False),
    ("loan book", r"(?:\bloan book\b|\bgross loans\b|\bcustomer loans\b|\bloan balance\b|贷款余额)", False),
    ("customer deposits", r"(?:\bcustomer deposits\b|\bdeposit balance\b|\bdeposits\b|存款余额|客户存款)", False),
    (
        "npl ratio",
        r"(?:\bnpl ratio\b|\bnon-performing loan ratio\b|\bnonperforming loan ratio\b|不良贷款率)",
        True,
    ),
    (
        "capital adequacy ratio",
        r"(?:\bcapital adequacy ratio\b|\bcapital ratio\b|\bcet1\b|\btier 1 ratio\b|资本充足率|核心一级资本充足率|一级资本充足率)",
        True,
    ),
    ("cost-to-income ratio", r"(?:\bcost-to-income ratio\b|\bcost income ratio\b|成本收入比)", True),
    ("liquidity coverage ratio", r"(?:\bliquidity coverage ratio\b|\blcr\b|流动性覆盖率)", True),
)

_VALUE_RE = re.compile(
    r"(?P<value>"
    r"(?:(?:HK\$|US\$|RMB|CNY|\$)\s*)?"
    r"(?:[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+))"
    r"(?:\s?(?:million|billion|trillion|bn|mn|m|%|亿港元|亿元|万元|百万元|万亿元|亿))?"
    r")",
    re.I,
)
_PERIOD_RE = re.compile(
    r"\b(?:FY\s?20\d{2}|20\d{2}|Q[1-4]\s?20\d{2}|H[12]\s?20\d{2}|[1-4]Q20\d{2}|[1-4]季度|1-2月|1-3月|1-6月|1-9月)\b"
    r"|(?:20\d{2}年(?:上半年|下半年)?)"
)
_NOISE_MARKERS = (
    "all rights reserved",
    "copyright",
    "member firm",
    "private english company limited by guarantee",
    "contact us",
    "table of contents",
    "contents",
    "kpmg.com",
    "www.",
    "http://",
    "https://",
)
_RISK_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("regulatory", ("regulatory", "compliance", "investigation", "penalty", "监管", "合规", "处罚")),
    ("credit", ("credit risk", "default", "impairment", "bad debt", "non-performing", "违约", "减值", "坏账", "不良贷款")),
    ("liquidity", ("liquidity", "funding", "cash flow", "refinancing", "流动性", "融资", "现金流")),
    ("market", ("volatility", "foreign exchange", "fx", "exchange rate", "rate hike", "devaluation", "波动", "汇率", "利率风险")),
    ("operational", ("cyber", "outage", "supply chain", "operational risk", "network security", "网络", "停摆", "运营风险", "信息安全")),
    ("geopolitical", ("tariff", "geopolitical", "trade war", "出口管制", "地缘", "制裁", "关税")),
)
_RISK_ANCHORS = (
    "risk",
    "risks",
    "exposure",
    "pressure",
    "uncertainty",
    "headwind",
    "challenge",
    "default",
    "impairment",
    "investigation",
    "penalty",
    "litigation",
    "illiquidity",
    "opacity",
    "风险",
    "压力",
    "不确定",
    "违约",
    "减值",
    "诉讼",
    "处罚",
)
_HIGH_SEVERITY_HINTS = ("material", "significant", "severe", "critical", "重大", "显著", "严重")
_EVENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "acquisition",
        (
            r"\b(?:acquired|acquire|acquisition|merged with|merger|takeover|agreed to acquire)\b",
            r"(?:收购|并购|合并)",
        ),
    ),
    (
        "expansion",
        (
            r"\b(?:opened|launched|expanded|established|set up|invested in|rolled out)\b",
            r"(?:开设|设立|启动|投建|扩张|扩展|落地)",
        ),
    ),
    (
        "partnership",
        (
            r"\b(?:signed|entered into|announced|formed|agreed on)\b.{0,80}\b(?:partnership|agreement|collaboration|mou)\b",
            r"\b(?:partnership|agreement|collaboration|mou)\b.{0,80}\b(?:signed|entered into|announced|formed)\b",
            r"(?:签署|签订|达成).{0,40}(?:合作协议|战略合作|合作备忘录|协议|合作)",
        ),
    ),
    (
        "financing",
        (
            r"\b(?:raised|secured|obtained|issued|signed)\b.{0,80}\b(?:bond|facility|funding|financing|loan)\b",
            r"(?:融资|授信|发债|发行债券|贷款安排)",
        ),
    ),
    (
        "regulatory",
        (
            r"\b(?:approved|received approval|licensed|granted a license|permit granted)\b",
            r"(?:获批|取得牌照|批准|许可)",
        ),
    ),
    (
        "risk_alert",
        (
            r"\b(?:warning|impairment|default|litigation|dispute|going concern)\b",
            r"(?:风险提示|减值|诉讼|违约|纠纷)",
        ),
    ),
)
_EVENT_NEGATIVE_PATTERNS = (
    "member firm",
    "all rights reserved",
    "private english company limited by guarantee",
    "hong kong (sar) partnership",
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+|\n{2,}")
_MD_HEADINGS = (
    "management discussion",
    "management's discussion",
    "management discussion and analysis",
    "md&a",
    "chairman's statement",
    "ceo message",
    "management review",
    "management commentary",
    "管理层讨论",
    "管理层讨论与分析",
    "主席报告",
    "主席致辞",
)
_MD_HIGHLIGHT_HINTS = (
    "growth",
    "strategy",
    "demand",
    "margin",
    "risk",
    "opportunity",
    "expansion",
    "pipeline",
    "regulatory",
    "liquidity",
    "增长",
    "战略",
    "需求",
    "风险",
    "机会",
    "扩张",
    "监管",
    "流动性",
)
_NON_PERCENT_METRICS = {name for name, _, allow_percent in _METRIC_SPECS if not allow_percent}


def _split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(normalized) if part.strip()]
    return parts or [normalized]


def _is_noise_text(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return True
    lower = normalized.lower()
    if any(marker in lower for marker in _NOISE_MARKERS):
        return True
    if re.fullmatch(r"page\s+\d+", lower):
        return True
    if len(normalized) < 8 and not re.search(r"\d", normalized):
        return True
    return False


def _metric_period(text: str) -> str | None:
    match = _PERIOD_RE.search(text)
    return match.group(0) if match else None


def _looks_like_metric_value(value: str, *, allow_percent: bool) -> bool:
    normalized = normalize_text(value)
    if not normalized or not re.search(r"\d", normalized):
        return False
    if normalized in {"-", "--", "—", "N/A"}:
        return False
    if re.fullmatch(r"[.,]+", normalized):
        return False
    if re.fullmatch(r"\d(?:,\d){2,}", normalized):
        return False
    if not allow_percent and normalized.endswith("%"):
        return False
    return True


def _value_quality_score(value: str, *, allow_percent: bool) -> tuple[int, int]:
    normalized = normalize_text(value)
    has_scale = 0 if re.search(r"(HK\$|US\$|RMB|CNY|\$|million|billion|trillion|bn|mn|亿港元|亿元|万元|百万元|万亿元)", normalized, flags=re.I) else 1
    percent_penalty = 0 if allow_percent or "%" not in normalized else 1
    return has_scale, percent_penalty


def _best_metric_value(sentence: str, *, metric_name: str, metric_pattern: str, allow_percent: bool) -> str | None:
    metric_match = re.search(metric_pattern, sentence, flags=re.I)
    if metric_match is None:
        return None

    candidates: list[tuple[tuple[int, int, int, int], str]] = []
    anchor_end = metric_match.end()
    for match in _VALUE_RE.finditer(sentence):
        value = normalize_text(match.group("value"))
        if not _looks_like_metric_value(value, allow_percent=allow_percent):
            continue
        score = (
            0 if match.start() >= anchor_end else 1,
            *_value_quality_score(value, allow_percent=allow_percent),
            abs(match.start() - anchor_end),
        )
        candidates.append((score, value))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _table_context(table: ParsedTable, row: list[str]) -> str:
    cells = [normalize_text(cell) for cell in row if normalize_text(cell)]
    headers = [normalize_text(header) for header in table.headers]
    if headers and len(headers) == len(row):
        pairs = [f"{header}: {value}" for header, value in zip(headers, row) if normalize_text(value)]
        if pairs:
            return " | ".join(pairs)
    return " | ".join(cells)


def _best_table_value(cells: list[str], *, allow_percent: bool) -> str | None:
    candidates: list[str] = []
    for cell in cells:
        normalized = normalize_text(cell)
        if _looks_like_metric_value(normalized, allow_percent=allow_percent):
            candidates.append(normalized)
    if not candidates:
        return None
    candidates.sort(key=lambda value: _value_quality_score(value, allow_percent=allow_percent))
    return candidates[0]


def _is_useful_period(period: str | None) -> bool:
    normalized = normalize_text(period)
    if not normalized:
        return False
    return re.search(r"(FY|Q[1-4]|H[12]|年|月)", normalized, flags=re.I) is not None


def _dedupe_metrics(metrics: list[ExtractedMetric]) -> list[ExtractedMetric]:
    kept: dict[tuple[str, str], ExtractedMetric] = {}
    for metric in metrics:
        key = (metric.name.lower(), metric.value)
        existing = kept.get(key)
        if existing is None:
            kept[key] = metric
            continue

        candidate_rank = (
            0 if _is_useful_period(metric.period) else 1,
            -(metric.confidence or 0),
            0 if metric.context and ":" not in metric.context[:8] else 1,
        )
        existing_rank = (
            0 if _is_useful_period(existing.period) else 1,
            -(existing.confidence or 0),
            0 if existing.context and ":" not in existing.context[:8] else 1,
        )
        if candidate_rank < existing_rank:
            kept[key] = metric

    return list(kept.values())


def extract_metrics(*, text: str, tables: list[ParsedTable] | None = None) -> list[ExtractedMetric]:
    metrics: list[ExtractedMetric] = []
    seen: set[tuple[str, str, str | None]] = set()

    for sentence in _split_sentences(text):
        if _is_noise_text(sentence):
            continue
        period = _metric_period(sentence)
        for metric_name, metric_pattern, allow_percent in _METRIC_SPECS:
            if not re.search(metric_pattern, sentence, flags=re.I):
                continue
            value = _best_metric_value(
                sentence,
                metric_name=metric_name,
                metric_pattern=metric_pattern,
                allow_percent=allow_percent,
            )
            if value is None:
                continue
            key = (metric_name.lower(), value, period)
            if key in seen:
                continue
            seen.add(key)
            metrics.append(
                ExtractedMetric(
                    name=metric_name,
                    value=value,
                    unit="%" if "%" in value else None,
                    period=period,
                    context=sentence[:240],
                    confidence=0.65,
                )
            )

    for table in tables or []:
        normalized_headers = [normalize_text(header) for header in table.headers]
        lower_headers = [header.lower() for header in normalized_headers]

        for metric_name, metric_pattern, allow_percent in _METRIC_SPECS:
            for row in table.rows[:20]:
                normalized_row = [normalize_text(cell) for cell in row]
                row_label = normalized_row[0] if normalized_row else ""
                if row_label and re.search(metric_pattern, row_label, flags=re.I):
                    value = _best_table_value(normalized_row[1:], allow_percent=allow_percent)
                    if value is None:
                        continue
                    period = None
                    for index, cell in enumerate(normalized_row[1:], start=1):
                        if normalize_text(cell) == value and index < len(normalized_headers):
                            header = normalized_headers[index]
                            if header and "增长" not in header and "%" not in header.lower():
                                period = header
                            break
                    key = (metric_name.lower(), value, period)
                    if key in seen:
                        continue
                    seen.add(key)
                    metrics.append(
                        ExtractedMetric(
                            name=metric_name,
                            value=value,
                            unit="%" if "%" in value else None,
                            period=period,
                            context=_table_context(table, normalized_row)[:240],
                            confidence=0.7,
                        )
                    )

            metric_index = next(
                (
                    index
                    for index, header in enumerate(lower_headers)
                    if re.search(metric_pattern, header, flags=re.I)
                ),
                None,
            )
            if metric_index is None:
                continue
            header_period = normalized_headers[metric_index] if metric_index < len(normalized_headers) else None
            period = header_period if header_period and metric_name in _NON_PERCENT_METRICS else None
            for row in table.rows[:20]:
                if metric_index >= len(row):
                    continue
                value = normalize_text(row[metric_index])
                if not _looks_like_metric_value(value, allow_percent=allow_percent):
                    continue
                key = (metric_name.lower(), value, period)
                if key in seen:
                    continue
                seen.add(key)
                metrics.append(
                    ExtractedMetric(
                        name=metric_name,
                        value=value,
                        unit="%" if "%" in value else None,
                        period=period,
                        context=_table_context(table, row)[:240],
                        confidence=0.6,
                    )
                )

    return _dedupe_metrics(metrics)[:20]


def _has_risk_signal(text: str) -> bool:
    return any(anchor in text for anchor in _RISK_ANCHORS)


def extract_risk_factors(*, text: str) -> list[RiskFactor]:
    risks: list[RiskFactor] = []
    seen: set[tuple[str, str]] = set()

    for sentence in _split_sentences(text):
        normalized = normalize_text(sentence)
        if _is_noise_text(normalized):
            continue
        lower = normalized.lower()
        if not _has_risk_signal(lower):
            continue
        for category, keywords in _RISK_KEYWORDS:
            if not any(keyword in lower for keyword in keywords):
                continue
            severity = "high" if any(hint in lower for hint in _HIGH_SEVERITY_HINTS) else "medium"
            key = (category, normalized[:180])
            if key in seen:
                continue
            seen.add(key)
            risks.append(
                RiskFactor(
                    category=category,
                    description=normalized[:300],
                    severity=severity,
                    confidence=0.6,
                )
            )
            break

    return risks[:12]


def extract_business_events(*, text: str, title: str | None = None) -> list[BusinessEvent]:
    events: list[BusinessEvent] = []
    seen: set[tuple[str, str]] = set()
    seeds = [normalize_text(title)] if title else []
    seeds.extend(_split_sentences(text))

    for sentence in seeds:
        normalized = normalize_text(sentence)
        if _is_noise_text(normalized):
            continue
        lower = normalized.lower()
        if any(marker in lower for marker in _EVENT_NEGATIVE_PATTERNS):
            continue
        for event_type, patterns in _EVENT_PATTERNS:
            if not any(re.search(pattern, normalized, flags=re.I) for pattern in patterns):
                continue
            key = (event_type, normalized[:180])
            if key in seen:
                continue
            seen.add(key)
            dates = extract_date_candidates(normalized)
            events.append(
                BusinessEvent(
                    event_type=event_type,
                    summary=normalized[:300],
                    event_date=dates[0] if dates else None,
                    confidence=0.6,
                )
            )
            break

    return events[:12]


def extract_management_discussion(
    *,
    title: str | None = None,
    sections: list[ParsedSection] | None = None,
    text: str = "",
) -> ManagementDiscussion | None:
    matched_sections: list[ParsedSection] = []
    for section in sections or []:
        heading = normalize_text(section.heading).lower()
        if any(marker in heading for marker in _MD_HEADINGS):
            matched_sections.append(section)

    if not matched_sections and title:
        title_lower = normalize_text(title).lower()
        if any(marker in title_lower for marker in _MD_HEADINGS):
            pseudo_text = text[:1500]
            if pseudo_text:
                matched_sections.append(ParsedSection(heading=normalize_text(title), text=pseudo_text))

    if not matched_sections:
        return None

    candidate_sentences: list[str] = []
    seen: set[str] = set()
    for section in matched_sections:
        for sentence in _split_sentences(section.text):
            normalized = normalize_text(sentence)
            if _is_noise_text(normalized):
                continue
            lower = normalized.lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                if any(hint in lower for hint in _MD_HIGHLIGHT_HINTS):
                    candidate_sentences.append(normalized)

    if not candidate_sentences:
        for section in matched_sections:
            for sentence in _split_sentences(section.text):
                normalized = normalize_text(sentence)
                if normalized and not _is_noise_text(normalized):
                    candidate_sentences.append(normalized)
                if len(candidate_sentences) >= 3:
                    break
            if len(candidate_sentences) >= 3:
                break

    summary = " ".join(candidate_sentences[:3]).strip()
    highlights = candidate_sentences[:5]
    if not summary:
        joined = " ".join(section.text[:240] for section in matched_sections if normalize_text(section.text))
        summary = normalize_text(joined)[:500]
    if not summary:
        return None

    return ManagementDiscussion(
        summary=summary[:600],
        highlights=[item[:240] for item in highlights],
        source_sections=[section.heading for section in matched_sections],
    )
