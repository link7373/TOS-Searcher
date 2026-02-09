from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_path: Path = Path("tos_searcher.db")

    # Search
    search_delay_min: float = 2.0
    search_delay_max: float = 5.0
    max_results_per_query: int = 50
    max_total_documents: int = 10000
    search_timeout: int = 30

    # Fetching
    fetch_timeout: int = 15
    max_concurrent_fetches: int = 3
    use_playwright_fallback: bool = True
    user_agents: list[str] = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ]

    # Analysis
    min_confidence_threshold: float = 0.3
    high_confidence_threshold: float = 0.7

    # GUI
    window_width: int = 900
    window_height: int = 700
    appearance_mode: str = "dark"
    color_theme: str = "blue"

    model_config = {"env_prefix": "TOS_"}
