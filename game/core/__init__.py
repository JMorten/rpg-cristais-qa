"""Infraestrutura compartilhada do jogo (caminhos, save e logs)."""
from __future__ import annotations

from core.paths import app_data_dir, legacy_save_path, log_dir, save_path, settings_path
from core.preferences import (
    Preferencias,
    carregar_preferencias,
    salvar_preferencias,
)
from core.save import SAVE_VERSION, SaveError, read_save, write_save
from core.tutorial import Tutorial

__all__ = [
    "SAVE_VERSION",
    "Preferencias",
    "SaveError",
    "Tutorial",
    "app_data_dir",
    "carregar_preferencias",
    "legacy_save_path",
    "log_dir",
    "read_save",
    "save_path",
    "salvar_preferencias",
    "settings_path",
    "write_save",
]
