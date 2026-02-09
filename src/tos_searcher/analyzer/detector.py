from __future__ import annotations

import logging
from dataclasses import dataclass

from tos_searcher.analyzer.patterns import (
    PatternMatch,
    find_all_matches,
    find_negative_matches,
)
from tos_searcher.analyzer.scorer import NLPScorer

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    confidence: float
    matches: list[PatternMatch]
    matched_text: str  # best/strongest match text
    context: str  # paragraph surrounding best match
    pattern_names: list[str]


class Detector:
    def __init__(self) -> None:
        self._scorer = NLPScorer()

    def analyze(self, text: str) -> DetectionResult | None:
        """Analyze document text for hidden prize language.

        Returns None if no patterns match or score is too low.
        """
        # Fast pass: regex pattern matching
        matches = find_all_matches(text)
        if not matches:
            return None

        # Calculate base score from pattern weights (with diminishing returns)
        unique_weights: dict[str, float] = {}
        for m in matches:
            if m.pattern_name not in unique_weights:
                unique_weights[m.pattern_name] = m.weight
            else:
                unique_weights[m.pattern_name] = max(
                    unique_weights[m.pattern_name], m.weight
                )

        base_score = sum(unique_weights.values())
        base_score = min(base_score, 0.9)  # cap

        # Apply negative pattern penalties
        negatives = find_negative_matches(text)
        for _name, penalty in negatives:
            base_score += penalty  # penalty is negative

        # NLP scoring pass
        nlp_bonus = self._scorer.score_context(text, matches)

        final_score = max(0.0, min(1.0, base_score + nlp_bonus))

        if final_score < 0.1:
            return None

        # Find the best (highest weight) match for display
        best_match = max(matches, key=lambda m: m.weight)
        context = self._extract_context(text, best_match.start, best_match.end)

        return DetectionResult(
            confidence=round(final_score, 3),
            matches=matches,
            matched_text=best_match.matched_text,
            context=context,
            pattern_names=list({m.pattern_name for m in matches}),
        )

    @staticmethod
    def _extract_context(text: str, start: int, end: int, window: int = 300) -> str:
        """Extract surrounding context around a match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        context = text[ctx_start:ctx_end].strip()

        # Try to start/end on sentence boundaries
        if ctx_start > 0:
            first_period = context.find(". ")
            if 0 < first_period < 100:
                context = context[first_period + 2 :]

        return context
