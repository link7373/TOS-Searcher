from typing import Protocol


class SearchProvider(Protocol):
    @property
    def name(self) -> str: ...

    def search(self, query: str, max_results: int = 50) -> list[str]:
        """Return a list of URLs matching the query."""
        ...
