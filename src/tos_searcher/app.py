import logging
from pathlib import Path

import customtkinter

from tos_searcher.config import Settings
from tos_searcher.gui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("tos_searcher.log"),
            logging.StreamHandler(),
        ],
    )

    settings = Settings()

    # Ensure db_path is absolute
    if not settings.db_path.is_absolute():
        settings.db_path = Path.cwd() / settings.db_path

    customtkinter.set_appearance_mode(settings.appearance_mode)
    customtkinter.set_default_color_theme(settings.color_theme)

    app = MainWindow(settings)
    app.mainloop()


if __name__ == "__main__":
    main()
