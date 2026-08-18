from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.core.version import APP_NAME, ORGANIZATION_NAME, VERSION
from app.desktop.error_handler import install_global_exception_handler
from app.desktop.main_window import MainWindow
from app.desktop.theme import apply_theme
from app.packaging import resource_path


def _arg_value(args: list[str], flag: str) -> str | None:
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return args[index + 1]
    return None


def _show_fatal(title: str, message: str) -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    box = QMessageBox()
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def _startup_config_error(exc: Exception) -> int:
    """Present a friendly message when configuration is missing or invalid."""
    print(f"ERROR: application configuration could not be loaded: {exc}", file=sys.stderr)
    _show_fatal(
        "Configuration Error",
        "The application could not read its configuration.\n\n"
        f"{exc}\n\n"
        "Create a .env file next to LMS.exe with a DATABASE_URL setting and try again. "
        "See the installation guide for details.",
    )
    return 1


def main() -> int:
    args = sys.argv[1:]

    if "--self-check" in args:
        from app.packaging import run_self_check

        return run_self_check(_arg_value(args, "--report"))

    if "--migrate" in args:
        from app.packaging import run_database_migrations

        return run_database_migrations()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationVersion(VERSION)

    icon_path = resource_path("assets/app.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    try:
        setup_logging()
        settings = get_settings()
    except Exception as exc:  # noqa: BLE001 - configuration failures use the fatal dialog
        return _startup_config_error(exc)

    logger = get_logger(__name__)
    logger.info(
        "Starting application",
        extra={
            "extra_fields": {
                "app_name": settings.app_name,
                "environment": settings.app_env,
                "version": VERSION,
            }
        },
    )

    install_global_exception_handler()

    apply_theme(app)

    window = MainWindow()
    window.show()

    logger.info("Application started successfully")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
