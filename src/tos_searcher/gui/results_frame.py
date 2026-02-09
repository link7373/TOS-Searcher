from __future__ import annotations

import webbrowser

import customtkinter

from tos_searcher.storage.database import Database


class ResultCard(customtkinter.CTkFrame):
    """A single result card showing a potential hidden contest."""

    def __init__(
        self,
        master: customtkinter.CTkBaseClass,
        url: str,
        domain: str,
        confidence: float,
        matched_text: str,
        context: str,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._url = url

        # Confidence badge
        if confidence >= 0.7:
            badge_color = "#2ecc71"
            badge_text = f"HIGH ({confidence:.0%})"
        elif confidence >= 0.4:
            badge_color = "#f39c12"
            badge_text = f"MEDIUM ({confidence:.0%})"
        else:
            badge_color = "#95a5a6"
            badge_text = f"LOW ({confidence:.0%})"

        # Row 0: Badge + domain
        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(8, 0))

        customtkinter.CTkLabel(
            header,
            text=badge_text,
            fg_color=badge_color,
            corner_radius=6,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            text_color="white",
            padx=8,
            pady=2,
        ).pack(side="left")

        customtkinter.CTkLabel(
            header,
            text=domain,
            font=customtkinter.CTkFont(size=14, weight="bold"),
        ).pack(side="left", padx=(10, 0))

        # Row 1: URL (clickable)
        url_label = customtkinter.CTkLabel(
            self,
            text=url,
            font=customtkinter.CTkFont(size=11),
            text_color="#3498db",
            anchor="w",
            cursor="hand2",
        )
        url_label.pack(fill="x", padx=12, pady=(4, 0))
        url_label.bind("<Button-1>", self._open_url)

        # Row 2: Matched text (the key finding)
        customtkinter.CTkLabel(
            self,
            text=f'"{matched_text}"',
            font=customtkinter.CTkFont(size=12),
            wraplength=700,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=12, pady=(6, 0))

        # Row 3: Context snippet
        truncated = context[:400] + "..." if len(context) > 400 else context
        customtkinter.CTkLabel(
            self,
            text=truncated,
            font=customtkinter.CTkFont(size=10),
            text_color="gray",
            wraplength=700,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=12, pady=(4, 10))

    def _open_url(self, event=None) -> None:
        webbrowser.open(self._url)


class ResultsFrame(customtkinter.CTkFrame):
    def __init__(
        self,
        master: customtkinter.CTkBaseClass,
        db: Database,
    ) -> None:
        super().__init__(master)
        self._db = db

        # Header
        customtkinter.CTkLabel(
            self,
            text="Results",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        # Scrollable area for result cards
        self._scroll_frame = customtkinter.CTkScrollableFrame(
            self, corner_radius=8
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Placeholder
        self._placeholder = customtkinter.CTkLabel(
            self._scroll_frame,
            text="No results yet. Click 'Begin Search' to start scanning.",
            font=customtkinter.CTkFont(size=13),
            text_color="gray",
        )
        self._placeholder.pack(pady=40)

        self._cards: list[ResultCard] = []

    def load_results(self) -> None:
        """Reload results from database and rebuild cards."""
        for card in self._cards:
            card.destroy()
        self._cards.clear()

        try:
            self._placeholder.pack_forget()
        except Exception:
            pass

        pairs = self._db.get_results_with_documents()

        if not pairs:
            self._placeholder.pack(pady=40)
            return

        # Sort by confidence descending
        pairs.sort(key=lambda p: p[0].confidence, reverse=True)

        for result, doc in pairs:
            card = ResultCard(
                self._scroll_frame,
                url=doc.url,
                domain=doc.domain,
                confidence=result.confidence,
                matched_text=result.matched_text,
                context=result.context,
                corner_radius=8,
                border_width=1,
            )
            card.pack(fill="x", padx=5, pady=5)
            self._cards.append(card)
