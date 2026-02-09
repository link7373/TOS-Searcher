from __future__ import annotations

import customtkinter

from tos_searcher.config import Settings
from tos_searcher.gui.results_frame import ResultsFrame
from tos_searcher.gui.search_frame import SearchFrame
from tos_searcher.storage.database import Database


class MainWindow(customtkinter.CTk):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

        self.title("TOS Searcher - Hidden Contest Finder")
        self.geometry(f"{settings.window_width}x{settings.window_height}")
        self.minsize(700, 500)

        # Initialize database
        self._db = Database(settings.db_path)
        self._db.connect()

        # Layout: two main frames stacked vertically
        self.grid_rowconfigure(1, weight=1)  # results frame expands
        self.grid_columnconfigure(0, weight=1)

        # Search controls + progress (top)
        self._search_frame = SearchFrame(
            self,
            settings=settings,
            db=self._db,
            on_results_updated=self._refresh_results,
        )
        self._search_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        # Results display (bottom, expandable)
        self._results_frame = ResultsFrame(self, db=self._db)
        self._results_frame.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")

        # Load any existing results from previous runs
        self._refresh_results()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _refresh_results(self) -> None:
        self._results_frame.load_results()

    def _on_close(self) -> None:
        self._search_frame.stop_search()
        self._db.close()
        self.destroy()
