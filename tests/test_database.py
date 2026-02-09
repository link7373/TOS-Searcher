from tos_searcher.storage.database import Database
from tos_searcher.storage.models import Document, Result


def test_insert_and_retrieve_document(db: Database) -> None:
    doc = Document(url="https://example.com/tos", domain="example.com", source="test")
    doc_id = db.insert_document(doc)
    assert doc_id > 0

    retrieved = db.get_document_by_url("https://example.com/tos")
    assert retrieved is not None
    assert retrieved.url == "https://example.com/tos"
    assert retrieved.domain == "example.com"
    assert retrieved.status == "pending"


def test_url_deduplication(db: Database) -> None:
    doc = Document(url="https://example.com/tos", domain="example.com", source="test")
    db.insert_document(doc)
    db.insert_document(doc)  # duplicate

    assert db.url_exists("https://example.com/tos")
    assert not db.url_exists("https://other.com/tos")


def test_document_status_update(db: Database) -> None:
    doc = Document(url="https://example.com/tos", domain="example.com", source="test")
    doc_id = db.insert_document(doc)

    db.update_document_status(doc_id, "fetched", title="Example TOS")
    retrieved = db.get_document_by_url("https://example.com/tos")
    assert retrieved is not None
    assert retrieved.status == "fetched"
    assert retrieved.title == "Example TOS"
    assert retrieved.fetched_at is not None


def test_pending_and_fetched_queries(db: Database) -> None:
    for i in range(5):
        db.insert_document(
            Document(url=f"https://example.com/{i}", domain="example.com", source="test")
        )

    pending = db.get_pending_documents()
    assert len(pending) == 5

    db.update_document_status(pending[0].id, "fetched")
    db.update_document_status(pending[1].id, "fetched")

    assert len(db.get_pending_documents()) == 3
    assert len(db.get_fetched_documents()) == 2


def test_document_text_storage(db: Database) -> None:
    doc_id = db.insert_document(
        Document(url="https://example.com/tos", domain="example.com", source="test")
    )
    db.store_document_text(doc_id, "This is the full document text.")
    text = db.get_document_text(doc_id)
    assert text == "This is the full document text."


def test_insert_and_retrieve_results(db: Database) -> None:
    doc_id = db.insert_document(
        Document(url="https://example.com/tos", domain="example.com", source="test")
    )
    result = Result(
        document_id=doc_id,
        confidence=0.85,
        matched_text="email us at prize@acme.com",
        context="If you read this far, email us at prize@acme.com to win.",
        pattern_matches=["hidden_prize", "claim_instruction"],
    )
    result_id = db.insert_result(result)
    assert result_id > 0

    results = db.get_all_results(min_confidence=0.5)
    assert len(results) == 1
    assert results[0].confidence == 0.85
    assert "hidden_prize" in results[0].pattern_matches


def test_results_with_documents(db: Database) -> None:
    doc_id = db.insert_document(
        Document(url="https://acme.com/tos", domain="acme.com", source="duckduckgo")
    )
    db.insert_result(
        Result(
            document_id=doc_id,
            confidence=0.9,
            matched_text="hidden prize",
            context="context text",
            pattern_matches=["hidden_prize"],
        )
    )

    pairs = db.get_results_with_documents()
    assert len(pairs) == 1
    result, doc = pairs[0]
    assert result.confidence == 0.9
    assert doc.url == "https://acme.com/tos"


def test_confidence_filtering(db: Database) -> None:
    doc_id = db.insert_document(
        Document(url="https://example.com/tos", domain="example.com", source="test")
    )
    db.insert_result(Result(document_id=doc_id, confidence=0.2, matched_text="low"))
    db.insert_result(Result(document_id=doc_id, confidence=0.8, matched_text="high"))

    assert len(db.get_all_results(min_confidence=0.5)) == 1
    assert len(db.get_all_results(min_confidence=0.0)) == 2


def test_query_tracking(db: Database) -> None:
    assert not db.query_was_executed("terms of service", "duckduckgo")

    db.record_query("terms of service", "duckduckgo", 50)
    assert db.query_was_executed("terms of service", "duckduckgo")
    assert not db.query_was_executed("terms of service", "bing")


def test_count_by_status(db: Database) -> None:
    db.insert_document(
        Document(url="https://a.com/tos", domain="a.com", source="test")
    )
    db.insert_document(
        Document(url="https://b.com/tos", domain="b.com", source="test")
    )
    doc_id = db.insert_document(
        Document(url="https://c.com/tos", domain="c.com", source="test")
    )
    db.update_document_status(doc_id, "fetched")

    counts = db.count_by_status()
    assert counts["pending"] == 2
    assert counts["fetched"] == 1


def test_stats(db: Database) -> None:
    doc_id = db.insert_document(
        Document(url="https://a.com/tos", domain="a.com", source="test")
    )
    db.insert_result(
        Result(document_id=doc_id, confidence=0.9, matched_text="prize")
    )

    stats = db.get_stats()
    assert stats["total"] == 1
    assert stats["results"] == 1


def test_reset(db: Database) -> None:
    db.insert_document(
        Document(url="https://a.com/tos", domain="a.com", source="test")
    )
    db.record_query("test query", "duckduckgo", 10)

    db.reset()

    assert not db.url_exists("https://a.com/tos")
    assert not db.query_was_executed("test query", "duckduckgo")
    assert db.get_stats()["total"] == 0


def test_content_hash() -> None:
    h1 = Database.hash_content("hello world")
    h2 = Database.hash_content("hello world")
    h3 = Database.hash_content("different text")
    assert h1 == h2
    assert h1 != h3
