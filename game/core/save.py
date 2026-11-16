"""Leitura e escrita atômica do save, com backup e versão de schema."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

SAVE_VERSION = 2


class SaveError(RuntimeError):
    """Erro de formato, versão ou leitura do save."""


def read_save(path: Path) -> dict[str, Any]:
    """Lê e valida o save. Levanta SaveError para dados inválidos."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SaveError(f"Save corrompido: {exc}") from exc

    if not isinstance(data, dict):
        raise SaveError("Formato de save inválido: esperado um objeto JSON.")

    try:
        version = int(data.get("versao", 1))
    except (TypeError, ValueError) as exc:
        raise SaveError("Versão de save inválida.") from exc

    if version < 1:
        raise SaveError("Versão de save inválida.")
    if version > SAVE_VERSION:
        raise SaveError(
            f"O save foi criado em uma versão mais nova ({version}) que o jogo ({SAVE_VERSION})."
        )

    data["versao"] = SAVE_VERSION
    return data


def write_save(path: Path, data: dict[str, Any]) -> None:
    """Grava o save de forma atômica e mantém uma cópia .bak da versão anterior."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    backup = path.with_name(path.name + ".bak")
    payload = json.dumps(data, ensure_ascii=False, indent=2)

    with temp.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except OSError:
            pass

    if path.exists():
        shutil.copy2(path, backup)
    temp.replace(path)
