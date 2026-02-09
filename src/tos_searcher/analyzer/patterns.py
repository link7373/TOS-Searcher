from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PatternMatch:
    pattern_name: str
    category: str  # strong, medium, weak
    matched_text: str
    start: int
    end: int
    weight: float


# (name, category, compiled_regex, weight)
PRIZE_PATTERNS: list[tuple[str, str, re.Pattern[str], float]] = [
    # STRONG signals — language that explicitly indicates a hidden reward
    (
        "read_this_far",
        "strong",
        re.compile(
            r"(?i)if\s+you['\u2019]?ve?\s+read\s+this\s+far",
        ),
        0.8,
    ),
    (
        "first_person_to",
        "strong",
        re.compile(
            r"(?i)first\s+person\s+to\s+"
            r"(read|find|notice|discover|email|contact|call|respond)",
        ),
        0.7,
    ),
    (
        "hidden_reward",
        "strong",
        re.compile(
            r"(?i)hidden\s+(prize|reward|contest|message|bonus|easter\s+egg|offer)",
        ),
        0.7,
    ),
    (
        "congratulations_found",
        "strong",
        re.compile(
            r"(?i)congratulations.*?you\s+"
            r"(found|discovered|are\s+one\s+of|actually\s+read)",
        ),
        0.8,
    ),
    (
        "claim_instruction",
        "strong",
        re.compile(
            r"(?i)(email|call|contact|write)\s+(us|to)\s+.{0,80}"
            r"(to\s+)?(claim|win|receive|collect|get)\s+.{0,30}"
            r"(prize|reward|gift|bonus|money|card)",
        ),
        0.7,
    ),
    (
        "email_to_win",
        "strong",
        re.compile(
            r"(?i)email\s+us\s+at\s+\S+@\S+.{0,100}(prize|reward|win|gift|bonus)",
        ),
        0.8,
    ),
    (
        "dollar_prize",
        "strong",
        re.compile(
            r"(?i)\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*"
            r"(prize|reward|gift\s*card|bonus|cash\s*prize)",
        ),
        0.7,
    ),
    (
        "few_who_read",
        "strong",
        re.compile(
            r"(?i)(one\s+of\s+the\s+(very\s+)?few|rare\s+person|"
            r"actually\s+read(s|ing)?)\s+.{0,50}"
            r"(terms|policy|agreement|contract|fine\s+print|document)",
        ),
        0.8,
    ),
    # MEDIUM signals — suggestive but could be normal contest language
    (
        "contest_words",
        "medium",
        re.compile(r"(?i)\b(sweepstakes|giveaway|raffle|drawing|jackpot)\b"),
        0.3,
    ),
    (
        "winner_language",
        "medium",
        re.compile(
            r"(?i)(you\s+(could\s+)?win|winner\s+will\s+(be\s+)?"
            r"(selected|chosen|notified)|eligible\s+to\s+win|chance\s+to\s+win)",
        ),
        0.3,
    ),
    (
        "reward_mention",
        "medium",
        re.compile(
            r"(?i)\b(prize|reward|bonus|gift\s*card|"
            r"free\s+(product|service|subscription|item))\b",
        ),
        0.2,
    ),
    # WEAK signals — context-dependent, high false positive rate
    (
        "easter_egg_mention",
        "weak",
        re.compile(r"(?i)\b(easter\s+egg|secret\s+message|buried\s+in)\b"),
        0.1,
    ),
    (
        "urgency_scarcity",
        "weak",
        re.compile(
            r"(?i)(limited\s+(time|offer)|act\s+(now|fast|quickly)|"
            r"first\s+\d+\s+(people|readers|customers))",
        ),
        0.1,
    ),
]

# Negative patterns — REDUCE confidence (indicates standard contest rules, not hidden prizes)
NEGATIVE_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    (
        "official_rules",
        re.compile(
            r"(?i)(official\s+rules|no\s+purchase\s+necessary|"
            r"void\s+where\s+prohibited)"
        ),
        -0.4,
    ),
    (
        "sweepstakes_terms",
        re.compile(
            r"(?i)(sweepstakes\s+(rules|terms|conditions)|"
            r"contest\s+rules|odds\s+of\s+winning|eligibility\s+requirements)"
        ),
        -0.3,
    ),
    (
        "legal_boilerplate",
        re.compile(
            r"(?i)(this\s+promotion\s+is\s+sponsored\s+by|"
            r"by\s+entering.*?you\s+agree\s+to|"
            r"open\s+to\s+(legal\s+)?residents)"
        ),
        -0.3,
    ),
]


def find_all_matches(text: str) -> list[PatternMatch]:
    """Run all prize patterns against text and return matches."""
    matches: list[PatternMatch] = []
    for name, category, pattern, weight in PRIZE_PATTERNS:
        for m in pattern.finditer(text):
            matches.append(
                PatternMatch(
                    pattern_name=name,
                    category=category,
                    matched_text=m.group(),
                    start=m.start(),
                    end=m.end(),
                    weight=weight,
                )
            )
    return matches


def find_negative_matches(text: str) -> list[tuple[str, float]]:
    """Find patterns indicating this is a standard contest rules page."""
    negatives: list[tuple[str, float]] = []
    for name, pattern, penalty in NEGATIVE_PATTERNS:
        if pattern.search(text):
            negatives.append((name, penalty))
    return negatives
