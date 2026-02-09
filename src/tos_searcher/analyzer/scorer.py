from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tos_searcher.analyzer.patterns import PatternMatch

logger = logging.getLogger(__name__)

LEGAL_INDICATORS = frozenset({
    "hereby", "whereas", "notwithstanding", "herein", "pursuant",
    "indemnify", "liability", "arbitration", "jurisdiction",
    "governing", "warranties", "disclaimers", "severability",
    "termination", "confidentiality", "intellectual",
})

ACTION_WORDS = frozenset({
    "email", "call", "contact", "visit", "send", "write", "reply",
})


class NLPScorer:
    def __init__(self) -> None:
        self._nlp = None
        try:
            import spacy

            self._nlp = spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            logger.warning("spaCy model not available; NLP scoring disabled")

    def score_context(self, text: str, matches: list[PatternMatch]) -> float:
        """Use NLP to evaluate whether pattern matches are genuine hidden prizes.

        Returns a bonus score (0.0 to 0.4) to add to the base pattern score.
        """
        if not self._nlp or not matches:
            return 0.0

        # Limit text size for performance
        doc = self._nlp(text[:100_000])

        score = 0.0

        # 1. Check if document appears to be a legal/TOS document
        legal_count = sum(
            1
            for token in doc
            if token.text.lower() in LEGAL_INDICATORS
        )
        if legal_count >= 3:
            score += 0.1  # confirmed legal document context

        # 2. Check sentence-level context around each match
        for match in matches:
            for sent in doc.sents:
                if sent.start_char <= match.start <= sent.end_char:
                    sent_lower = sent.text.lower()

                    # Instructional sentence (email us, call us) = higher confidence
                    if any(w in sent_lower for w in ACTION_WORDS):
                        score += 0.1

                    # Conditional sentence ("if you...") = higher confidence
                    if "if you" in sent_lower:
                        score += 0.1
                    break

        # 3. MONEY entity near a pattern match
        for ent in doc.ents:
            if ent.label_ == "MONEY":
                for match in matches:
                    if abs(ent.start_char - match.start) < 300:
                        score += 0.15
                        break

        return min(score, 0.4)  # cap NLP bonus
