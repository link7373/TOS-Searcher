from unittest.mock import MagicMock, patch

from tos_searcher.config import Settings
from tos_searcher.scraper.fetcher import Fetcher


def test_fetch_success(settings: Settings) -> None:
    fetcher = Fetcher(settings)
    mock_resp = MagicMock()
    mock_resp.text = "<html><body>Terms of Service</body></html>"
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html; charset=utf-8"}
    mock_resp.raise_for_status = MagicMock()

    with patch.object(fetcher._session, "get", return_value=mock_resp):
        result = fetcher._fetch_with_requests("https://example.com/tos")
        assert result.success
        assert "Terms of Service" in result.html
        assert result.status_code == 200


def test_fetch_non_html_rejected(settings: Settings) -> None:
    fetcher = Fetcher(settings)
    mock_resp = MagicMock()
    mock_resp.text = "%PDF-1.4 binary data"
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/pdf"}
    mock_resp.raise_for_status = MagicMock()

    with patch.object(fetcher._session, "get", return_value=mock_resp):
        result = fetcher._fetch_with_requests("https://example.com/tos.pdf")
        assert not result.success
        assert "Non-HTML" in (result.error or "")


def test_fetch_timeout(settings: Settings) -> None:
    fetcher = Fetcher(settings)
    import requests

    with patch.object(
        fetcher._session, "get", side_effect=requests.Timeout("Connection timed out")
    ):
        result = fetcher._fetch_with_requests("https://example.com/tos")
        assert not result.success
        assert result.error is not None
