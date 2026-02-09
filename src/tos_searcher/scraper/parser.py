from __future__ import annotations

from bs4 import BeautifulSoup, Tag

NOISE_TAGS = frozenset({
    "nav", "header", "footer", "aside", "script", "style",
    "noscript", "iframe", "svg", "form", "button",
})

NOISE_PATTERNS = [
    "nav", "menu", "sidebar", "footer", "header", "cookie",
    "banner", "popup", "modal", "ad-", "social", "share",
    "newsletter", "subscribe",
]


class DocumentParser:
    def extract_text(self, html: str) -> str:
        """Extract main content text from HTML, removing navigation noise."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove noise elements by tag name
        for tag_name in NOISE_TAGS:
            for el in soup.find_all(tag_name):
                el.decompose()

        # Remove elements with noise-related classes/IDs
        for el in soup.find_all(True):
            if isinstance(el, Tag):
                classes = " ".join(el.get("class", []))
                el_id = el.get("id", "") or ""
                combined = f"{classes} {el_id}".lower()
                if any(p in combined for p in NOISE_PATTERNS):
                    el.decompose()

        # Try to find main content area
        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"role": "main"})
            or soup.find(
                "div",
                class_=lambda c: c and "content" in " ".join(c).lower()
                if c
                else False,
            )
            or soup.body
            or soup
        )

        text = main.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def extract_title(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.find("title")
        return title.get_text(strip=True) if title else ""
