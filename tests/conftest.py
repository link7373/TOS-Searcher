from pathlib import Path

import pytest

from tos_searcher.config import Settings
from tos_searcher.storage.database import Database


@pytest.fixture
def settings() -> Settings:
    return Settings(db_path=Path(":memory:"))


@pytest.fixture
def db(settings: Settings) -> Database:
    database = Database(settings.db_path)
    database.connect()
    yield database
    database.close()


@pytest.fixture
def sample_tos_with_prize() -> str:
    return (
        "Terms of Service - ACME Corporation\n"
        "Last updated: January 1, 2024\n\n"
        "1. ACCEPTANCE OF TERMS\n"
        "By accessing or using our services, you agree to be bound by these Terms "
        "of Service. If you do not agree, do not use our services.\n\n"
        "2. USER ACCOUNTS\n"
        "You must provide accurate information when creating an account. You are "
        "responsible for maintaining the security of your account.\n\n"
        "3. INTELLECTUAL PROPERTY\n"
        "All content on this platform is owned by ACME Corporation and protected "
        "by copyright law.\n\n"
        "47. GENERAL PROVISIONS\n"
        "If you've read this far, you are one of the very few people who actually "
        "reads our terms of service. As a reward, email us at prize@acme.com with "
        "the subject line 'I read the TOS' and we will send you a $500 gift card. "
        "This offer is limited to the first 10 people who contact us.\n\n"
        "48. GOVERNING LAW\n"
        "These Terms shall be governed by the laws of the State of Delaware.\n"
    )


@pytest.fixture
def sample_normal_tos() -> str:
    return (
        "Terms of Service - Normal Corp\n"
        "Last updated: March 15, 2024\n\n"
        "By using this website, you agree to these terms. We reserve the right to "
        "modify these terms at any time. Your continued use constitutes acceptance.\n\n"
        "LIMITATION OF LIABILITY\n"
        "In no event shall Normal Corp be liable for any indirect, incidental, "
        "special, consequential or punitive damages.\n\n"
        "GOVERNING LAW\n"
        "These terms are governed by the laws of California.\n"
    )


@pytest.fixture
def sample_sweepstakes_rules() -> str:
    return (
        "OFFICIAL SWEEPSTAKES RULES\n"
        "NO PURCHASE NECESSARY TO ENTER OR WIN.\n\n"
        "The contest is open to legal residents of the United States who are 18 "
        "years of age or older. Void where prohibited by law.\n\n"
        "PRIZE: One winner will receive a $1,000 gift card. Odds of winning depend "
        "on the number of eligible entries received.\n\n"
        "By entering, you agree to the official rules and the decisions of the "
        "judges, which are final.\n"
    )
