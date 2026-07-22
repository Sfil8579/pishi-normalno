#!/usr/bin/env python3
"""Audit Russian prose for hard artifacts and context-dependent style signals."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
ARROW_RANGES = (
    (0x2190, 0x21FF),
    (0x27F0, 0x27FF),
    (0x2900, 0x297F),
    (0x2B00, 0x2BFF),
)
HIDDEN_RANGES = (
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0xE200, 0xE204),
)
DECORATIVE_RANGES = (
    (0x25A0, 0x27BF),
    (0x1F000, 0x1FAFF),
)
PROTECTED_PATTERNS = (
    re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"<pre\b.*?</pre>|<code\b.*?</code>", re.IGNORECASE | re.DOTALL),
    re.compile(r"https?://[^\s<>)]+", re.IGNORECASE),
    re.compile(r"(?<=\]\()[^)\n]+(?=\))"),
)
ENTITY_RULES = (
    (
        "unicode-dash-entity",
        re.compile(r"&(?:m|n)dash;|&#(?:8211|8212);|&#x(?:2013|2014);", re.IGNORECASE),
        "HTML-сущность создает запрещенное длинное тире.",
        "Перестроить фразу и убрать сущность.",
    ),
    (
        "unicode-arrow-entity",
        re.compile(
            r"&(?:l|r|u|d|h|v)arr;|&#(?:8592|8593|8594|8595|8656|8658);|"
            r"&#x(?:2190|2191|2192|2193|21d0|21d2);",
            re.IGNORECASE,
        ),
        "HTML-сущность создает стрелку.",
        "Передать связь словами.",
    ),
)
NUMBER_RE = re.compile(
    r"(?<![\w])[-+]?\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?"
    r"(?:\s?(?:%|‰|₽|\$|€|руб\.?|тыс\.?|млн|млрд))?(?![\w])",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://[^\s<>)]+", re.IGNORECASE)
RAW_LINK_LEAK_RE = re.compile(
    r"sandbox:/|[?&]utm_source=(?:chatgpt(?:\.com)?|openai)(?:[&#]|$)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
QUOTE_RE = re.compile(r"[\"«]([^\"»\n]{1,500})[\"»]")
MODAL_RE = re.compile(
    r"\b(?:не\s+менее|не\s+более|при\s+условии|не|ни|нельзя|только|если|"
    r"может|могут|возможно|вероятно|примерно|чаще|обычно|иногда|редко|"
    r"всегда|никогда|надо|нужно|следует|обязан\w*|должен\w*)\b",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
QUOTED_SPEECH_RE = re.compile(r'"[^"\n]*"|«[^»\n]*»')
INFORMAL_ADDRESS_RE = re.compile(
    r"\b(?:ты|тебя|тебе|тобой|тво(?:его|ей|ему|ем|ими|их|им|ю|й|я|е|и))\b",
    re.IGNORECASE,
)
FORMAL_ADDRESS_RE = re.compile(
    r"\b(?:вы|вас|вам|вами|ваш(?:его|ей|ему|ем|ими|их|им|у|а|е|и)?)\b",
    re.IGNORECASE,
)
ASCII_ARROW_RE = re.compile(r"(?:<[-=]{1,3}|[-=]{1,3}>)")
SPACED_HYPHEN_RE = re.compile(r"(?<=\S)[ \t]+-[ \t]+(?=\S)")
MIXED_SCRIPT_RE = re.compile(
    r"(?:(?<=[А-Яа-я])[A-Za-z](?=[А-Яа-я])|"
    r"(?<=[A-Za-z])[А-Яа-я](?=[A-Za-z]))"
)
SENTENCE_BOUNDARY_RE = re.compile(r"[.!?]+(?:[\"»)]*)?\s+")
PAIRED_RELATION_RULES = (
    (
        "на входе, на выходе",
        re.compile(r"\bна\s+входе\b", re.IGNORECASE),
        re.compile(r"\bна\s+выходе\b", re.IGNORECASE),
    ),
    (
        "с одной стороны, с другой стороны",
        re.compile(r"\bс\s+одной\s+стороны\b", re.IGNORECASE),
        re.compile(r"\bс\s+другой\s+стороны\b", re.IGNORECASE),
    ),
    (
        "сначала, потом",
        re.compile(r"\bсначала\b", re.IGNORECASE),
        re.compile(r"\bпотом\b", re.IGNORECASE),
    ),
    (
        "либо, либо",
        re.compile(r"\bлибо\b", re.IGNORECASE),
        re.compile(r"\bлибо\b", re.IGNORECASE),
    ),
    (
        "если, то",
        re.compile(r"\bесли\b", re.IGNORECASE),
        re.compile(r"\bто\b", re.IGNORECASE),
    ),
    (
        "чем, тем",
        re.compile(r"\bчем\b", re.IGNORECASE),
        re.compile(r"\bтем\b", re.IGNORECASE),
    ),
)
VERB_ENDING_RE = re.compile(
    r"(?:ться|тся|[аяеиоуы]ть|[дсзй]ти|"
    r"ешь|ишь|ете|ите|емся|имся|ем|им|"
    r"утся|ются|атся|ятся|ут|ют|ется|ится|ет|ит|"
    r"(?:ал|ял|ел|ил|ол|ул|ыл)(?:ся|ась|ось|ись|а|о|и)?|"
    r"[аяеиоуы]ю|ую|усь|юсь)$",
    re.IGNORECASE,
)
PREDICATIVE_WORDS = {
    "безразлично",
    "больно",
    "будет",
    "буду",
    "будут",
    "был",
    "была",
    "были",
    "было",
    "важно",
    "возможно",
    "готово",
    "достаточно",
    "жаль",
    "интересно",
    "можно",
    "мочь",
    "надо",
    "нельзя",
    "непонятно",
    "нужно",
    "обидно",
    "понятно",
    "помочь",
    "пора",
    "приятно",
    "стыдно",
    "страшно",
    "трудно",
    "хватит",
    "ясно",
    "есть",
    "нет",
    "это",
}
ABSTRACT_FRAGMENT_TERMS = {
    "будущее",
    "важность",
    "выбор",
    "возможность",
    "вопрос",
    "итог",
    "ключ",
    "магия",
    "подход",
    "проблема",
    "причина",
    "решение",
    "результат",
    "сила",
    "смысл",
    "трата",
    "уровень",
    "факт",
    "цена",
    "ценность",
    "шанс",
    "ошибка",
}
BENEFIT_CLAIM_RE = re.compile(
    r"\b(?:эконом\w*\s+врем\w*|повыша\w*\s+конверси\w*|"
    r"увеличива\w*\s+продаж\w*|снижа\w*\s+расход\w*|"
    r"гарантиру\w*|без\s+ошибок|полн\w*\s+контрол\w*|"
    r"в\s+один\s+клик)\b",
    re.IGNORECASE,
)
CAUSALITY_RE = re.compile(
    r"\b(?:потому\s+что|поэтому|из-за|благодаря|в\s+результате|"
    r"прив(?:ел|ела|ело|ели)\s+к)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    category: str
    message: str
    line: int
    column: int
    excerpt: str
    suggestion: str
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _in_ranges(codepoint: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def _line_column(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    line_start = text.rfind("\n", 0, index) + 1
    return line, index - line_start + 1


def _excerpt(text: str, start: int, end: int, limit: int = 140) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    value = re.sub(r"\s+", " ", text[line_start:line_end]).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _finding(
    text: str,
    start: int,
    end: int,
    *,
    severity: str,
    code: str,
    category: str,
    message: str,
    suggestion: str,
    confidence: str = "high",
) -> Finding:
    line, column = _line_column(text, start)
    return Finding(
        severity=severity,
        code=code,
        category=category,
        message=message,
        line=line,
        column=column,
        excerpt=_excerpt(text, start, end),
        suggestion=suggestion,
        confidence=confidence,
    )


def _merge_ranges(ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def mask_protected(text: str, include_protected: bool = False) -> str:
    if include_protected:
        return text
    ranges = _merge_ranges(
        match.span() for pattern in PROTECTED_PATTERNS for match in pattern.finditer(text)
    )
    chars = list(text)
    for start, end in ranges:
        for index in range(start, end):
            if chars[index] not in "\r\n":
                chars[index] = " "
    return "".join(chars)


def mask_quoted_speech(text: str) -> str:
    chars = list(text)
    for match in QUOTED_SPEECH_RE.finditer(text):
        for index in range(match.start(), match.end()):
            if chars[index] not in "\r\n":
                chars[index] = " "
    return "".join(chars)


def _unicode_issue(codepoint: int) -> tuple[str, str, str, str, str] | None:
    if codepoint in {0x2013, 0x2014}:
        return (
            "error",
            "unicode-long-dash",
            "Запрещенное длинное тире.",
            "Перестроить фразу с точкой, запятой, двоеточием или скобками.",
            "high",
        )
    if codepoint in {0x0451, 0x0401}:
        return (
            "error",
            "unicode-dotted-letter",
            "В обычной прозе использована запрещенная буква с точками.",
            "Заменить ее на соответствующую букву без точек.",
            "high",
        )
    if _in_ranges(codepoint, ARROW_RANGES):
        return (
            "error",
            "unicode-arrow",
            "Стрелочный символ создает неуместную визуальную связь.",
            "Передать направление или последовательность словами.",
            "high",
        )
    if codepoint == 0x00AD or codepoint == 0xFEFF or _in_ranges(codepoint, HIDDEN_RANGES):
        return (
            "error",
            "unicode-hidden",
            "Найден скрытый или управляющий Unicode-символ.",
            "Удалить символ и проверить соседние пробелы.",
            "high",
        )
    if codepoint in {0x00A0, 0x202F}:
        return (
            "warning",
            "unicode-nonbreaking-space",
            "Неразрывный пробел может быть незаметным артефактом копирования.",
            "Проверить необходимость и при возможности заменить обычным пробелом.",
            "medium",
        )
    if _in_ranges(codepoint, DECORATIVE_RANGES):
        return (
            "error",
            "unicode-decorative",
            "Декоративный символ или emoji не несет самостоятельного смысла.",
            "Убрать символ или передать нужный смысл словами.",
            "high",
        )
    return None


def scan_unicode(text: str, visible_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for index, char in enumerate(visible_text):
        issue = _unicode_issue(ord(char))
        if issue is None:
            continue
        severity, code, message, suggestion, confidence = issue
        findings.append(
            _finding(
                text,
                index,
                index + 1,
                severity=severity,
                code=code,
                category="unicode",
                message=f"{message} Кодовая точка U+{ord(char):04X}.",
                suggestion=suggestion,
                confidence=confidence,
            )
        )
    return findings


def scan_entities(text: str, visible_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for code, pattern, message, suggestion in ENTITY_RULES:
        for match in pattern.finditer(visible_text):
            findings.append(
                _finding(
                    text,
                    match.start(),
                    match.end(),
                    severity="error",
                    code=code,
                    category="unicode",
                    message=message,
                    suggestion=suggestion,
                )
            )
    return findings


def scan_ascii_arrows(text: str, visible_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in ASCII_ARROW_RE.finditer(visible_text):
        findings.append(
            _finding(
                text,
                match.start(),
                match.end(),
                severity="error",
                code="ascii-arrow",
                category="typography",
                message="ASCII-последовательность использована как стрелка.",
                suggestion="Передать направление или последовательность словами.",
            )
        )
    return findings


def scan_mixed_script(text: str, visible_text: str) -> list[Finding]:
    return [
        _finding(
            text,
            match.start(),
            match.end(),
            severity="error",
            code="mixed-script-word",
            category="unicode",
            message="Внутри одного слова смешаны латинские и кириллические буквы.",
            suggestion="Заменить подмененную букву символом нужного алфавита.",
            confidence="high",
        )
        for match in MIXED_SCRIPT_RE.finditer(visible_text)
    ]


def _genre_enabled(genres: Sequence[str], genre: str) -> bool:
    return "*" in genres or genre in genres


def _all_rule_matches(rule: dict[str, Any], text: str) -> list[re.Match[str]]:
    matches: list[re.Match[str]] = []
    for expression in rule["patterns"]:
        matches.extend(re.finditer(expression, text, re.IGNORECASE | re.MULTILINE))
    return sorted(matches, key=lambda match: match.start())


def scan_lexical_rules(
    text: str,
    visible_text: str,
    genre: str,
    config: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in config["rules"]:
        if not _genre_enabled(rule["genres"], genre):
            continue
        matches = _all_rule_matches(rule, visible_text)
        if not matches:
            continue
        first = matches[0]
        count_note = f" Совпадений: {len(matches)}." if len(matches) > 1 else ""
        findings.append(
            _finding(
                text,
                first.start(),
                first.end(),
                severity=rule["level"],
                code=rule["id"],
                category=rule["category"],
                message=rule["message"] + count_note,
                suggestion=rule["suggestion"],
                confidence=rule["confidence"],
            )
        )
    return findings


def scan_service_leaks(text: str, visible_text: str, config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for expression in config["service_leaks"]:
        for match in re.finditer(expression, visible_text, re.IGNORECASE):
            findings.append(
                _finding(
                    text,
                    match.start(),
                    match.end(),
                    severity="error",
                    code="service-leak",
                    category="chatbot_artifact",
                    message="В тексте осталась служебная метка генератора или среды выполнения.",
                    suggestion="Удалить метку. Для ссылки проверить и очистить адрес назначения.",
                )
            )
    for match in RAW_LINK_LEAK_RE.finditer(text):
        findings.append(
            _finding(
                text,
                match.start(),
                match.end(),
                severity="warning",
                code="service-link-leak",
                category="chatbot_artifact",
                message="В цели ссылки остался служебный или генераторный адрес.",
                suggestion=("Проверить исходную ссылку. Менять ее только после подтверждения."),
                confidence="high",
            )
        )
    return findings


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    try:
        from razdel import sentenize  # type: ignore[import-not-found]
    except ImportError:
        return _fallback_sentence_spans(text)
    return [
        (item.start, item.stop) for item in sentenize(text) if text[item.start : item.stop].strip()
    ]


def _fallback_sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    boundary = re.compile(r"[.!?]+(?:[\"»)]*)?(?=\s|$)")
    for match in boundary.finditer(text):
        _append_trimmed_span(text, start, match.end(), spans)
        start = match.end()
    _append_trimmed_span(text, start, len(text), spans)
    return spans


def _append_trimmed_span(
    text: str,
    start: int,
    end: int,
    spans: list[tuple[int, int]],
) -> None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start < end:
        spans.append((start, end))


@dataclass(frozen=True)
class FragmentCandidate:
    ordinal: int
    start: int
    end: int
    words: tuple[str, ...]


@lru_cache(maxsize=1)
def _morph_analyzer() -> Any | None:
    try:
        import pymorphy3  # type: ignore[import-not-found]
    except ImportError:
        return None
    return pymorphy3.MorphAnalyzer()


def _contains_predicate(words: Sequence[str]) -> bool:
    analyzer = _morph_analyzer()
    if analyzer is not None:
        predicate_parts = {"VERB", "INFN", "PRED", "ADJS", "PRTS"}
        return any(analyzer.parse(word)[0].tag.POS in predicate_parts for word in words)
    return any(
        word in PREDICATIVE_WORDS
        or VERB_ENDING_RE.search(word)
        or re.search(r"(?:ен|ена|ено|ены)$", word, re.IGNORECASE)
        for word in words
    )


def _is_structural_sentence(text: str, start: int) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end < 0:
        line_end = len(text)
    line = text[line_start:line_end].lstrip()
    return bool(re.match(r"(?:#{1,6}\s|[-*+]\s|>\s|\d+[.)]\s)", line))


def _fragment_candidates(visible_text: str) -> list[FragmentCandidate]:
    unquoted_text = mask_quoted_speech(visible_text)
    candidates: list[FragmentCandidate] = []
    for ordinal, (start, end) in enumerate(_sentence_spans(visible_text)):
        value = unquoted_text[start:end]
        _, words = _normalized_sentence(value)
        if not 1 <= len(words) <= 6:
            continue
        if any(mark in value for mark in ("?", "!", ":", ";")):
            continue
        if _is_structural_sentence(visible_text, start):
            continue
        if _contains_predicate(words):
            continue
        candidates.append(
            FragmentCandidate(
                ordinal=ordinal,
                start=start,
                end=end,
                words=tuple(words),
            )
        )
    return candidates


def _fragment_runs(visible_text: str) -> list[list[FragmentCandidate]]:
    runs: list[list[FragmentCandidate]] = []
    current: list[FragmentCandidate] = []
    for candidate in _fragment_candidates(visible_text):
        if current:
            previous = current[-1]
            between = visible_text[previous.end : candidate.start]
            is_adjacent = candidate.ordinal == previous.ordinal + 1
            same_paragraph = re.search(r"\n\s*\n", between) is None
            if not is_adjacent or not same_paragraph:
                if len(current) >= 2:
                    runs.append(current)
                current = []
        current.append(candidate)
    if len(current) >= 2:
        runs.append(current)
    return runs


def scan_nominal_fragments(text: str, visible_text: str, genre: str) -> list[Finding]:
    if genre in {"technical", "scientific", "official", "legal"}:
        return []
    findings: list[Finding] = []
    for run in _fragment_runs(visible_text):
        words = {word for item in run for word in item.words}
        has_abstract_label = bool(words & ABSTRACT_FRAGMENT_TERMS)
        strong_genre = genre in {"casual", "social", "marketing"}
        severity = "warning" if has_abstract_label and strong_genre else "info"
        if len(run) >= 3:
            code = "short-abstract-run"
            message = (
                "Цепочка коротких фраз не содержит явной предикации и может "
                "изображать смысловой удар вместо завершенной мысли."
            )
        else:
            code = "nominal-fragment-pair"
            message = (
                "Две соседние короткие фразы не содержат явной предикации. "
                "Точка могла скрыть определение, причину или вывод."
            )
        findings.append(
            _finding(
                text,
                run[0].start,
                run[-1].end,
                severity=severity,
                code=code,
                category="semantic_fragmentation",
                message=message,
                suggestion=(
                    "Назвать связь и перечитать вслух. Объединять только если "
                    "фрагменты не выполняют самостоятельную авторскую функцию."
                ),
                confidence="medium" if has_abstract_label else "low",
            )
        )
    return findings


def scan_repeated_terms(
    text: str,
    visible_text: str,
    genre: str,
    config: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in config["repeat_terms"]:
        if not _genre_enabled(rule["genres"], genre):
            continue
        matches = list(re.finditer(rule["pattern"], visible_text, re.IGNORECASE))
        if len(matches) < rule["threshold"]:
            continue
        first = matches[0]
        findings.append(
            _finding(
                text,
                first.start(),
                first.end(),
                severity="info",
                code=rule["id"],
                category="lexical_repetition",
                message=f"{rule['message']} Совпадений: {len(matches)}.",
                suggestion="Проверить соседние формулировки и заменить только пустые повторы.",
                confidence="medium",
            )
        )
    return findings


def scan_generic_headings(text: str, visible_text: str, config: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for expression in config["generic_headings"]:
        for match in re.finditer(expression, visible_text, re.IGNORECASE | re.MULTILINE):
            findings.append(
                _finding(
                    text,
                    match.start(),
                    match.end(),
                    severity="info",
                    code="generic-heading",
                    category="composition",
                    message="Заголовок называет часть текста, но не сообщает ее содержание.",
                    suggestion=(
                        "Назвать вывод или пользу раздела. В коротком тексте убрать заголовок."
                    ),
                    confidence="medium",
                )
            )
    return findings


def _normalized_sentence(value: str) -> tuple[str, list[str]]:
    words = [word.casefold() for word in WORD_RE.findall(value)]
    return " ".join(words), words


def scan_duplicate_sentences(text: str, visible_text: str) -> list[Finding]:
    grouped: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for start, end in _sentence_spans(visible_text):
        normalized, words = _normalized_sentence(visible_text[start:end])
        if len(words) >= 8:
            grouped[normalized].append((start, end))
    findings: list[Finding] = []
    for spans in grouped.values():
        if len(spans) < 2:
            continue
        start, end = spans[1]
        findings.append(
            _finding(
                text,
                start,
                end,
                severity="warning",
                code="duplicate-sentence",
                category="composition",
                message=f"Предложение дословно повторяется {len(spans)} раза.",
                suggestion="Оставить один экземпляр или развести функции повторов.",
                confidence="high",
            )
        )
    return findings


def scan_repeated_starts(text: str, visible_text: str) -> list[Finding]:
    sentences = _sentence_spans(visible_text)
    if len(sentences) < 5:
        return []
    starts: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for start, end in sentences:
        _, words = _normalized_sentence(visible_text[start:end])
        if len(words) >= 2:
            starts[" ".join(words[:2])].append((start, end))
    findings: list[Finding] = []
    for phrase, spans in starts.items():
        if len(spans) < 3:
            continue
        start, end = spans[0]
        findings.append(
            _finding(
                text,
                start,
                end,
                severity="info",
                code="repeated-sentence-start",
                category="rhythm",
                message=f"{len(spans)} предложений начинаются одинаково: '{phrase}'.",
                suggestion="Проверить монотонность. Не менять повтор, если он нужен как анафора.",
                confidence="low",
            )
        )
    return findings


def scan_bold_list_labels(text: str, visible_text: str) -> list[Finding]:
    pattern = re.compile(r"(?m)^\s*[-*]\s+\*\*[^*\n]{1,80}\*\*[:.]?")
    matches = list(pattern.finditer(visible_text))
    if len(matches) < 3:
        return []
    first = matches[0]
    return [
        _finding(
            text,
            first.start(),
            first.end(),
            severity="info",
            code="bold-label-list",
            category="formatting",
            message=f"Список содержит {len(matches)} однотипных жирных ярлыка.",
            suggestion="Проверить, нужен ли список и помогают ли ярлыки чтению по диагонали.",
            confidence="low",
        )
    ]


def scan_uniform_sentence_length(text: str, visible_text: str, genre: str) -> list[Finding]:
    if genre in {"scientific", "official", "legal"}:
        return []
    sentence_data: list[tuple[int, int, int]] = []
    for start, end in _sentence_spans(visible_text):
        count = len(WORD_RE.findall(visible_text[start:end]))
        if count >= 4:
            sentence_data.append((start, end, count))
    if len(sentence_data) < 6:
        return []
    lengths = [item[2] for item in sentence_data]
    mean = statistics.fmean(lengths)
    if mean == 0 or statistics.pstdev(lengths) / mean >= 0.12:
        return []
    start, end, _ = sentence_data[0]
    return [
        _finding(
            text,
            start,
            end,
            severity="info",
            code="uniform-sentence-length",
            category="rhythm",
            message="Длина предложений почти не меняется по всему фрагменту.",
            suggestion="Прочитать вслух. Менять ритм только там, где он мешает смыслу.",
            confidence="low",
        )
    ]


def scan_final_question_chain(text: str, visible_text: str, genre: str) -> list[Finding]:
    if genre not in {"casual", "social", "marketing"}:
        return []
    paragraphs = [
        match
        for match in re.finditer(
            r"(?ms)^[ \t]*(?P<body>\S.*?)(?=\r?\n[ \t]*\r?\n|\Z)",
            visible_text,
        )
        if match.group("body").strip()
    ]
    if not paragraphs:
        return []
    last = paragraphs[-1]
    value = mask_quoted_speech(last.group("body"))
    if value.count("?") < 2:
        return []
    if re.match(
        r"(?is)^(?:#{1,6}[ \t]*)?(?:faq|интервью|опрос|"
        r"вопросы\s+и\s+ответы)\s*(?::|\n|$)",
        value.strip(),
    ):
        return []
    return [
        _finding(
            text,
            last.start("body"),
            last.end("body"),
            severity="warning" if genre in {"social", "marketing"} else "info",
            code="final-question-chain",
            category="generic_conclusion",
            message="Финальный абзац содержит несколько вопросов подряд.",
            suggestion=(
                "Оставить один конкретный пробел в знании или закончить без вопроса. "
                "Не менять интервью, опрос и настоящий диалог."
            ),
            confidence="medium",
        )
    ]


def _address_matches(
    visible_text: str,
) -> tuple[list[re.Match[str]], list[re.Match[str]]]:
    unquoted_text = mask_quoted_speech(visible_text)
    return (
        list(INFORMAL_ADDRESS_RE.finditer(unquoted_text)),
        list(FORMAL_ADDRESS_RE.finditer(unquoted_text)),
    )


def scan_address_register(text: str, visible_text: str) -> list[Finding]:
    informal, formal = _address_matches(visible_text)
    if not informal or not formal:
        return []
    informal_start = informal[0].start()
    formal_start = formal[0].start()
    if informal_start > formal_start:
        start, end = informal[0].span()
    else:
        start, end = formal[0].span()
    return [
        _finding(
            text,
            start,
            end,
            severity="info",
            code="mixed-address-register",
            category="voice",
            message="В одном авторском слое смешаны обращения на 'ты' и 'вы'.",
            suggestion=("Проверить, задумана ли смена адресата. Иначе выбрать одно обращение."),
            confidence="medium",
        )
    ]


def scan_structure(
    text: str,
    visible_text: str,
    genre: str,
    config: dict[str, Any],
) -> list[Finding]:
    return [
        *scan_repeated_terms(text, visible_text, genre, config),
        *scan_generic_headings(text, visible_text, config),
        *scan_duplicate_sentences(text, visible_text),
        *scan_repeated_starts(text, visible_text),
        *scan_bold_list_labels(text, visible_text),
        *scan_address_register(text, visible_text),
        *scan_uniform_sentence_length(text, visible_text, genre),
        *scan_nominal_fragments(text, visible_text, genre),
        *scan_final_question_chain(text, visible_text, genre),
    ]


def _counter(pattern: re.Pattern[str], text: str, group: int = 0) -> Counter[str]:
    return Counter(
        re.sub(r"\s+", " ", match.group(group)).strip().casefold()
        for match in pattern.finditer(text)
    )


def _compare_counters(
    result_text: str,
    source_values: Counter[str],
    result_values: Counter[str],
    *,
    label: str,
    code: str,
    severity: str,
) -> list[Finding]:
    findings: list[Finding] = []
    missing = source_values - result_values
    added = result_values - source_values
    for value, count in missing.items():
        findings.append(
            _finding(
                result_text,
                0,
                0,
                severity=severity,
                code=f"source-{code}-missing",
                category="meaning_fidelity",
                message=f"Из результата исчез {label}: '{value}'. Количество: {count}.",
                suggestion="Сверить с исходником и вернуть значение либо подтвердить удаление.",
            )
        )
    lowered_result = result_text.casefold()
    for value, count in added.items():
        index = lowered_result.find(value)
        if index < 0:
            index = 0
        findings.append(
            _finding(
                result_text,
                index,
                index + len(value),
                severity=severity,
                code=f"source-{code}-added",
                category="meaning_fidelity",
                message=f"В результате появился новый {label}: '{value}'. Количество: {count}.",
                suggestion="Удалить добавление либо подтвердить его по внешнему источнику.",
            )
        )
    return findings


def _address_kind(text: str) -> str:
    visible_text = mask_protected(text)
    informal, formal = _address_matches(visible_text)
    if informal and formal:
        return "mixed"
    if informal:
        return "informal"
    if formal:
        return "formal"
    return "none"


def _without_question_sentences(text: str) -> str:
    statements: list[str] = []
    for start, end in _sentence_spans(text):
        sentence = text[start:end]
        if re.search(r'\?["»)]*\s*$', sentence):
            continue
        statements.append(sentence)
    return "\n".join(statements)


def compare_address_register(result_text: str, source_text: str) -> list[Finding]:
    source_kind = _address_kind(source_text)
    result_kind = _address_kind(result_text)
    if source_kind == result_kind or source_kind == "mixed":
        return []

    labels = {
        "informal": "обращение на 'ты'",
        "formal": "обращение на 'вы'",
        "mixed": "смешанное обращение",
        "none": "без прямого обращения",
    }
    if source_kind == "none":
        code = "source-address-added"
        severity = "info"
        message = f"В результате появилось {labels[result_kind]}."
    elif result_kind == "none":
        code = "source-address-missing"
        severity = "info"
        message = f"Из результата исчезло {labels[source_kind]}."
    else:
        code = "source-address-changed"
        severity = "warning"
        message = f"Обращение изменилось: было {labels[source_kind]}, стало {labels[result_kind]}."
    return [
        _finding(
            result_text,
            0,
            0,
            severity=severity,
            code=code,
            category="meaning_fidelity",
            message=message,
            suggestion="Сверить адресата и вернуть исходную дистанцию либо подтвердить смену.",
            confidence="medium",
        )
    ]


def compare_fragmentation(result_text: str, source_text: str, genre: str) -> list[Finding]:
    if genre in {"technical", "scientific", "official", "legal"}:
        return []
    result_visible = mask_protected(result_text)
    source_visible = mask_protected(source_text)
    result_runs = _fragment_runs(result_visible)
    source_runs = _fragment_runs(source_visible)
    result_pressure = sum(len(run) - 1 for run in result_runs)
    source_pressure = sum(len(run) - 1 for run in source_runs)
    if result_pressure <= source_pressure or not result_runs:
        return []
    first_run = result_runs[0]
    return [
        _finding(
            result_text,
            first_run[0].start,
            first_run[-1].end,
            severity="warning",
            code="source-relation-split",
            category="meaning_fidelity",
            message=(
                "После редактуры стало больше соседних коротких фраз без "
                "явной предикации. Смысловая связь могла потеряться."
            ),
            suggestion=(
                "Сверить исходную конструкцию и восстановить определение, причину, "
                "следствие, условие или контраст."
            ),
            confidence="high",
        )
    ]


def compare_added_causality(result_text: str, source_text: str) -> list[Finding]:
    if CAUSALITY_RE.search(source_text):
        return []
    match = CAUSALITY_RE.search(result_text)
    if match is None:
        return []
    return [
        _finding(
            result_text,
            match.start(),
            match.end(),
            severity="warning",
            code="source-causality-added",
            category="meaning_fidelity",
            message="В результате появилась явная причинная связь, которой не было в исходнике.",
            suggestion=(
                "Проверить, подтверждена ли причинность. Иначе вернуть наблюдение "
                "без причинного вывода."
            ),
            confidence="medium",
        )
    ]


def _paired_relation_span(
    text: str, first_pattern: re.Pattern[str], second_pattern: re.Pattern[str]
) -> tuple[int, int, str] | None:
    for first in first_pattern.finditer(text):
        second = second_pattern.search(text, first.end())
        if second is None or second.start() - first.end() > 300:
            continue
        return first.start(), second.end(), text[first.end() : second.start()]
    return None


def compare_paired_relations(result_text: str, source_text: str) -> list[Finding]:
    result_visible = mask_protected(result_text)
    source_visible = mask_protected(source_text)
    findings: list[Finding] = []
    for label, first_pattern, second_pattern in PAIRED_RELATION_RULES:
        source_span = _paired_relation_span(source_visible, first_pattern, second_pattern)
        result_span = _paired_relation_span(result_visible, first_pattern, second_pattern)
        if source_span is None or result_span is None:
            continue
        if SENTENCE_BOUNDARY_RE.search(source_span[2]):
            continue
        boundary = SENTENCE_BOUNDARY_RE.search(result_span[2])
        if boundary is None:
            continue
        findings.append(
            _finding(
                result_text,
                result_span[0],
                result_span[1],
                severity="warning",
                code="source-paired-relation-split",
                category="meaning_fidelity",
                message=(
                    f"Парная связь '{label}' была внутри одного предложения, "
                    "но после правки разделена границей предложения."
                ),
                suggestion=(
                    "Вернуть части в одну синтаксическую конструкцию либо явно "
                    "сохранить их взаимную связь."
                ),
                confidence="high",
            )
        )
    return findings


def compare_mechanical_dash_replacement(result_text: str, source_text: str) -> list[Finding]:
    source_long_dash_count = source_text.count(chr(0x2013)) + source_text.count(chr(0x2014))
    if source_long_dash_count == 0:
        return []
    source_ascii_count = len(SPACED_HYPHEN_RE.findall(source_text))
    result_matches = list(SPACED_HYPHEN_RE.finditer(result_text))
    if len(result_matches) <= source_ascii_count:
        return []
    match = result_matches[source_ascii_count]
    return [
        _finding(
            result_text,
            match.start(),
            match.end(),
            severity="warning",
            code="source-mechanical-dash-replacement",
            category="meaning_fidelity",
            message=(
                "Запрещенное тире из исходника, вероятно, механически заменено "
                "пробельным ASCII-дефисом."
            ),
            suggestion=(
                "Определить функцию исходной связи. Для оценки или определения "
                "предпочесть глагол, связку либо двоеточие; дефис оставить только "
                "после осознанной синтаксической проверки."
            ),
            confidence="medium",
        )
    ]


def compare_source(result_text: str, source_text: str, genre: str) -> list[Finding]:
    specifications = (
        (NUMBER_RE, 0, "число", "number", "error"),
        (URL_RE, 0, "URL", "url", "error"),
        (EMAIL_RE, 0, "адрес почты", "email", "error"),
        (QUOTE_RE, 1, "текст цитаты", "quote", "warning"),
    )
    findings: list[Finding] = []
    for pattern, group, label, code, severity in specifications:
        findings.extend(
            _compare_counters(
                result_text,
                _counter(pattern, source_text, group),
                _counter(pattern, result_text, group),
                label=label,
                code=code,
                severity=severity,
            )
        )
    findings.extend(
        _compare_counters(
            result_text,
            _counter(MODAL_RE, _without_question_sentences(source_text)),
            _counter(MODAL_RE, _without_question_sentences(result_text)),
            label="маркер условия или модальности в утверждении",
            code="modality",
            severity="warning",
        )
    )
    findings.extend(
        _compare_counters(
            result_text,
            _counter(BENEFIT_CLAIM_RE, source_text),
            _counter(BENEFIT_CLAIM_RE, result_text),
            label="маркетинговое обещание",
            code="benefit-claim",
            severity="warning",
        )
    )
    findings.extend(compare_address_register(result_text, source_text))
    findings.extend(compare_fragmentation(result_text, source_text, genre))
    findings.extend(compare_added_causality(result_text, source_text))
    findings.extend(compare_paired_relations(result_text, source_text))
    findings.extend(compare_mechanical_dash_replacement(result_text, source_text))
    return findings


def validate_config(config: dict[str, Any]) -> None:
    required = {
        "schema",
        "genres",
        "rules",
        "repeat_terms",
        "generic_headings",
        "service_leaks",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"В patterns.json нет полей: {', '.join(missing)}")
    if config["schema"] != "pishi-normalno.patterns.v1":
        raise ValueError("Неизвестная версия patterns.json")
    for rule in config["rules"]:
        for expression in rule["patterns"]:
            re.compile(expression)
    for section in ("repeat_terms",):
        for rule in config[section]:
            re.compile(rule["pattern"])
    for expression in [*config["generic_headings"], *config["service_leaks"]]:
        re.compile(expression)


def load_config(path: Path) -> dict[str, Any]:
    config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def audit_text(
    text: str,
    *,
    genre: str,
    config: dict[str, Any],
    source_text: str | None = None,
    include_protected: bool = False,
) -> list[Finding]:
    if genre not in config["genres"]:
        raise ValueError(f"Неизвестный жанр: {genre}")
    visible_text = mask_protected(text, include_protected)
    findings = [
        *scan_unicode(text, visible_text),
        *scan_entities(text, visible_text),
        *scan_ascii_arrows(text, visible_text),
        *scan_mixed_script(text, visible_text),
        *scan_service_leaks(text, visible_text, config),
        *scan_lexical_rules(text, visible_text, genre, config),
        *scan_structure(text, visible_text, genre, config),
    ]
    if source_text is not None:
        findings.extend(compare_source(text, source_text, genre))
    return sorted(
        findings,
        key=lambda item: (
            item.line,
            item.column,
            SEVERITY_ORDER[item.severity],
            item.code,
        ),
    )


def _summary(findings: Sequence[Finding]) -> dict[str, int]:
    counts = Counter(item.severity for item in findings)
    return {name: counts.get(name, 0) for name in ("error", "warning", "info")}


def print_human_report(findings: Sequence[Finding], genre: str) -> None:
    print(f"Жанр: {genre}")
    if not findings:
        print("Формальных проблем не найдено. Смысловая проверка все равно нужна.")
        return
    for item in findings:
        print(f"[{item.severity.upper()}] {item.code} {item.line}:{item.column}")
        print(f"  {item.message}")
        if item.excerpt:
            print(f"  Фрагмент: {item.excerpt}")
        print(f"  Что проверить: {item.suggestion}")
    counts = _summary(findings)
    print(
        "Найдено: "
        f"ошибок {counts['error']}, предупреждений {counts['warning']}, "
        f"информационных сигналов {counts['info']}."
    )


def exit_status(findings: Sequence[Finding], strict: bool) -> int:
    if any(item.severity == "error" for item in findings):
        return 1
    if strict and any(item.severity == "warning" for item in findings):
        return 1
    return 0


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8-sig")


def build_parser(default_rules: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Аудит русской прозы без определения AI-авторства.",
    )
    parser.add_argument("file", help="UTF-8 файл или - для stdin")
    parser.add_argument("--source", help="Исходник для формальной сверки фактов")
    parser.add_argument("--genre", default="neutral", help="Жанровый профиль")
    parser.add_argument("--rules", type=Path, default=default_rules, help="Путь к patterns.json")
    parser.add_argument("--json", action="store_true", help="Вернуть JSON")
    parser.add_argument(
        "--strict", action="store_true", help="Считать предупреждения ошибкой запуска"
    )
    parser.add_argument(
        "--include-protected",
        action="store_true",
        help="Проверять код, URL и цели Markdown-ссылок вместе с прозой",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    default_rules = Path(__file__).resolve().parent.parent / "references" / "patterns.json"
    args = build_parser(default_rules).parse_args(argv)
    try:
        config = load_config(args.rules)
        text = _read_text(args.file)
        source_text = _read_text(args.source) if args.source else None
        findings = audit_text(
            text,
            genre=args.genre,
            config=config,
            source_text=source_text,
            include_protected=args.include_protected,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"Ошибка аудитора: {error}", file=sys.stderr)
        return 2
    if args.json:
        payload = {
            "schema": "pishi-normalno.audit.v1",
            "genre": args.genre,
            "summary": _summary(findings),
            "findings": [item.to_dict() for item in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human_report(findings, args.genre)
    return exit_status(findings, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
