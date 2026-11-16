"""Caminhos persistentes do jogo (save, logs e dados do usuário)."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_NAME = "CristaisDeAether"
_ENV_OVERRIDE = "CRISTAIS_DATA_DIR"


def em_web() -> bool:
    """Verdadeiro quando o jogo está rodando no navegador (pygbag ou Pyodide)."""
    return os.environ.get("CRISTAIS_WEB") == "1" or sys.platform == "emscripten"


def _default_base() -> Path:
    if em_web():
        return Path("/data")
    if os.name == "nt":
        return Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def app_data_dir() -> Path:
    """Pasta de dados do usuário, com override para testes e builds portáveis."""
    override = os.environ.get(_ENV_OVERRIDE)
    base = Path(override).expanduser() if override else _default_base() / APP_NAME
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path(tempfile.gettempdir()) / APP_NAME
        base.mkdir(parents=True, exist_ok=True)
    return base


def save_path() -> Path:
    return app_data_dir() / "save.json"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def audio_dir() -> Path:
    """Cache dos sons gerados por código."""
    path = app_data_dir() / "audio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def legacy_save_path() -> Path:
    """Save antigo, gravado ao lado do código/protótipo."""
    return Path(__file__).resolve().parents[1] / "save.json"
