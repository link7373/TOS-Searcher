from __future__ import annotations

import queue
import threading
from tkinter import messagebox
from typing import Callable

import customtkinter

from tos_searcher.config import Settings
from tos_searcher.search.pipeline import SearchPipeline
from tos_searcher.storage.database import Database
from tos_searcher.storage.models import SearchProgress

POLL_INTERVAL_MS = 100


class SearchFrame(customtkinter.CTkFrame):
    def __init__(
        self,
        master: customtkinter.CTkBaseClass,
        settings: Settings,
        db: Database,
        on_results_updated: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._settings = settings
        self._db = db
        self._on_results_updated = on_results_updated
        self._progress_queue: queue.Queue[SearchProgress] = queue.Queue()
        self._pipeline: SearchPipeline | None = None
        self._worker_thread: threading.Thread | None = None

        self._build_ui()
        self._show_existing_stats()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Row 0: Buttons
        btn_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self._begin_btn = customtkinter.CTkButton(
            btn_frame,
            text="Begin Search",
            command=self._start_search,
            width=180,
            height=40,
            font=customtkinter.CTkFont(size=15, weight="bold"),
        )
        self._begin_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = customtkinter.CTkButton(
            btn_frame,
            text="Stop",
            command=self.stop_search,
            width=80,
            height=40,
            state="disabled",
            fg_color="gray",
            hover_color="darkgray",
        )
        self._stop_btn.pack(side="left", padx=(0, 10))

        self._reset_btn = customtkinter.CTkButton(
            btn_frame,
            text="Reset Database",
            command=self._reset_database,
            width=140,
            height=40,
            fg_color="#8B0000",
            hover_color="#A52A2A",
        )
        self._reset_btn.pack(side="right")

        # Row 1: Status label
        self._status_label = customtkinter.CTkLabel(
            self,
            text="Status: Ready",
            font=customtkinter.CTkFont(size=13),
            anchor="w",
        )
        self._status_label.grid(row=1, column=0, sticky="ew")

        # Row 2: Progress bar
        self._progress_bar = customtkinter.CTkProgressBar(self, width=400)
        self._progress_bar.grid(row=2, column=0, sticky="ew", pady=(5, 5))
        self._progress_bar.set(0)

        # Row 3: Stats labels
        self._stats_label = customtkinter.CTkLabel(
            self,
            text="Found: 0 docs | Fetched: 0 | Analyzed: 0 | Potential finds: 0",
            font=customtkinter.CTkFont(size=12),
            anchor="w",
        )
        self._stats_label.grid(row=3, column=0, sticky="ew")

    def _show_existing_stats(self) -> None:
        """Show stats from any previous runs on startup."""
        stats = self._db.get_stats()
        if stats["total"] > 0:
            results = self._db.get_all_results(self._settings.min_confidence_threshold)
            self._stats_label.configure(
                text=(
                    f"Found: {stats['total']} docs | "
                    f"Fetched: {stats['fetched'] + stats['analyzed']} | "
                    f"Analyzed: {stats['analyzed']} | "
                    f"Potential finds: {len(results)}"
                )
            )
            self._status_label.configure(text="Status: Ready (previous results loaded)")

    def _start_search(self) -> None:
        self._begin_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._reset_btn.configure(state="disabled")

        self._pipeline = SearchPipeline(
            settings=self._settings,
            db=self._db,
            progress_callback=self._enqueue_progress,
        )

        self._worker_thread = threading.Thread(
            target=self._run_pipeline, daemon=True
        )
        self._worker_thread.start()
        self._poll_progress()

    def _run_pipeline(self) -> None:
        """Runs in background thread."""
        assert self._pipeline is not None
        try:
            self._pipeline.run()
        except Exception as e:
            self._enqueue_progress(
                SearchProgress(
                    phase="error",
                    current_action=f"Error: {e}",
                    is_running=False,
                )
            )

    def _enqueue_progress(self, progress: SearchProgress) -> None:
        """Thread-safe: called from background thread."""
        self._progress_queue.put(progress)

    def _poll_progress(self) -> None:
        """Runs on main thread via .after()."""
        try:
            while True:
                progress = self._progress_queue.get_nowait()
                self._update_ui(progress)
        except queue.Empty:
            pass

        if self._worker_thread and self._worker_thread.is_alive():
            self.after(POLL_INTERVAL_MS, self._poll_progress)
        else:
            self._search_finished()

    def _update_ui(self, progress: SearchProgress) -> None:
        self._status_label.configure(text=f"Status: {progress.current_action}")
        self._progress_bar.set(progress.percent_complete)
        self._stats_label.configure(
            text=(
                f"Found: {progress.total_discovered} docs | "
                f"Fetched: {progress.total_fetched} | "
                f"Analyzed: {progress.total_analyzed} | "
                f"Potential finds: {progress.total_results}"
            )
        )

    def _search_finished(self) -> None:
        self._begin_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._reset_btn.configure(state="normal")

        # Get final stats
        stats = self._db.get_stats()
        results = self._db.get_all_results(self._settings.min_confidence_threshold)
        if stats["analyzed"] > 0:
            self._status_label.configure(
                text=(
                    f"Status: Complete - {len(results)} potential find(s) "
                    f"in {stats['analyzed']} documents"
                )
            )
        self._progress_bar.set(1.0)
        self._on_results_updated()

    def stop_search(self) -> None:
        if self._pipeline:
            self._pipeline.request_stop()

    def _reset_database(self) -> None:
        if messagebox.askyesno(
            "Confirm Reset",
            "This will delete ALL stored documents and results.\n\n"
            "The next search will start from scratch, re-scanning everything.\n\n"
            "Continue?",
        ):
            self._db.reset()
            self._status_label.configure(text="Status: Database reset - ready")
            self._stats_label.configure(
                text="Found: 0 docs | Fetched: 0 | Analyzed: 0 | Potential finds: 0"
            )
            self._progress_bar.set(0)
            self._on_results_updated()
