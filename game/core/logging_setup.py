"""Configuração de logs e tratamento de erros fatais."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.paths import log_dir

LOGGER_NAME = "cristais"


def setup_logging(level: int = logging.INFO) -> Path:
    """Configura log rotativo em arquivo e, se houver console, também no stderr."""
    log_path = log_dir() / "game.log"
    root = logging.getLogger()
    root.setLevel(level)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler(sys.stderr)
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    return log_path


def install_exception_hook(log_path: Path | None = None) -> None:
    """Registra exceções não tratadas e mostra um diálogo no Windows sem console."""

    def handle(exc_type, exc_value, exc_tb) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        logger.exception("Erro não tratado", exc_info=(exc_type, exc_value, exc_tb))
        if sys.stderr is not None:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        else:
            _show_error_dialog(exc_value, log_path)

    sys.excepthook = handle


def _show_error_dialog(exc: BaseException, log_path: Path | None) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        details = f"{type(exc).__name__}: {exc}"
        if log_path is not None:
            details += f"\n\nLog: {log_path}"
        ctypes.windll.user32.MessageBoxW(0, details, "Cristais de Aether — erro", 0x10)
    except Exception:
        pass
