from tos_searcher.analyzer.patterns import find_all_matches, find_negative_matches


def test_strong_read_this_far() -> None:
    text = "If you've read this far, email us at prize@company.com"
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "read_this_far" in names
    assert any(m.category == "strong" for m in matches)


def test_strong_first_person_to() -> None:
    text = "The first person to email us will receive a special gift."
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "first_person_to" in names


def test_strong_hidden_reward() -> None:
    text = "You found the hidden prize in our terms of service!"
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "hidden_reward" in names


def test_strong_congratulations() -> None:
    text = "Congratulations! You are one of the few who actually read our terms."
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "congratulations_found" in names


def test_strong_email_to_win() -> None:
    text = "Email us at secret@company.com to claim your $10,000 prize."
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "email_to_win" in names


def test_strong_dollar_prize() -> None:
    text = "You will receive a $500 gift card for finding this message."
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "dollar_prize" in names


def test_strong_few_who_read() -> None:
    text = "You are one of the very few who actually reads the fine print."
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "few_who_read" in names


def test_medium_contest_words() -> None:
    text = "Enter our sweepstakes for a chance to win."
    matches = find_all_matches(text)
    names = [m.pattern_name for m in matches]
    assert "contest_words" in names
    assert "winner_language" in names


def test_normal_tos_no_matches(sample_normal_tos: str) -> None:
    matches = find_all_matches(sample_normal_tos)
    strong_matches = [m for m in matches if m.category == "strong"]
    assert len(strong_matches) == 0


def test_hidden_prize_tos_matches(sample_tos_with_prize: str) -> None:
    matches = find_all_matches(sample_tos_with_prize)
    strong_matches = [m for m in matches if m.category == "strong"]
    assert len(strong_matches) >= 1
    names = [m.pattern_name for m in matches]
    assert "read_this_far" in names


def test_negative_official_rules() -> None:
    text = "OFFICIAL RULES: No purchase necessary to enter or win."
    negatives = find_negative_matches(text)
    names = [n[0] for n in negatives]
    assert "official_rules" in names


def test_negative_sweepstakes_rules(sample_sweepstakes_rules: str) -> None:
    negatives = find_negative_matches(sample_sweepstakes_rules)
    assert len(negatives) >= 1
    names = [n[0] for n in negatives]
    assert "official_rules" in names


def test_negative_not_triggered_on_normal_tos(sample_normal_tos: str) -> None:
    negatives = find_negative_matches(sample_normal_tos)
    assert len(negatives) == 0
