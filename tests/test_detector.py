from tos_searcher.analyzer.detector import Detector


def test_detect_hidden_prize(sample_tos_with_prize: str) -> None:
    detector = Detector()
    result = detector.analyze(sample_tos_with_prize)
    assert result is not None
    assert result.confidence >= 0.5
    assert len(result.matches) >= 1
    assert "read_this_far" in result.pattern_names


def test_no_detection_normal_tos(sample_normal_tos: str) -> None:
    detector = Detector()
    result = detector.analyze(sample_normal_tos)
    # Normal TOS should either return None or very low confidence
    if result is not None:
        assert result.confidence < 0.3


def test_sweepstakes_penalized(sample_sweepstakes_rules: str) -> None:
    detector = Detector()
    result = detector.analyze(sample_sweepstakes_rules)
    # Sweepstakes rules mention prizes but should be penalized by negative patterns
    if result is not None:
        assert result.confidence < 0.5


def test_context_extraction() -> None:
    text = "A" * 500 + "HIDDEN PRIZE HERE" + "B" * 500
    detector = Detector()
    context = detector._extract_context(text, 500, 517, window=50)
    assert "HIDDEN PRIZE HERE" in context
    assert len(context) < 200


def test_strong_signal_high_confidence() -> None:
    text = (
        "Terms of Service\n\n"
        "1. General Terms\n"
        "These terms govern your use of our service.\n\n"
        "2. Hidden Section\n"
        "If you've read this far, you are one of the very few customers "
        "who actually reads the fine print. Congratulations! "
        "Email us at secret@company.com to claim your $5,000 cash prize. "
        "This offer is limited to the first person to contact us.\n\n"
        "3. Governing Law\n"
        "These terms are governed by the laws of Delaware.\n"
    )
    detector = Detector()
    result = detector.analyze(text)
    assert result is not None
    assert result.confidence >= 0.7
    assert len(result.pattern_names) >= 2
