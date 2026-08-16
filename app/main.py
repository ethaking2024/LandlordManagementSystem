from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.desktop.error_handler import install_global_exception_handler
from app.desktop.main_window import MainWindow
from app.desktop.theme import apply_theme


def main() -> int:
    setup_logging()
    logger = get_logger(__name__)

    settings = get_settings()
    logger.info(
        "Starting application",
        extra={"extra_fields": {"app_name": settings.app_name, "environment": settings.app_env}},
    )

    install_global_exception_handler()

    app = QApplication(sys.argv)
    app.setApplicationName(settings.app_name)
    app.setOrganizationName("LMS")
    apply_theme(app)

    window = MainWindow()
    window.show()

    logger.info("Application started successfully")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
