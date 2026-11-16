"""Preferências persistentes do jogador."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.paths import settings_path

LOGGER = logging.getLogger(__name__)
SETTINGS_VERSION = 1

# Escalas de texto suportadas pela interface. Manter poucas opções evita
# que os painéis de layout fixo se sobreponham.
ESCALA_TEXTO_OPCOES: tuple[float, ...] = (0.9, 1.0, 1.15)
ESCALA_TEXTO_ROTULOS = {0.9: "Compacto", 1.0: "Normal", 1.15: "Grande"}


def normalizar_escala_texto(valor: Any) -> float:
    """Aceita apenas as escalas suportadas; qualquer outro valor volta para 1,0."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return 1.0
    for opcao in ESCALA_TEXTO_OPCOES:
        if abs(numero - opcao) < 1e-6:
            return opcao
    return 1.0


def proxima_escala_texto(atual: float) -> float:
    """Avança para a próxima escala da lista, em ciclo."""
    atual = normalizar_escala_texto(atual)
    indice = ESCALA_TEXTO_OPCOES.index(atual)
    return ESCALA_TEXTO_OPCOES[(indice + 1) % len(ESCALA_TEXTO_OPCOES)]


def limitar_volume(valor: Any, padrao: float = 0.8) -> float:
    """Volume entre 0 e 1; valor inválido mantém o padrão."""
    try:
        return max(0.0, min(1.0, float(valor)))
    except (TypeError, ValueError):
        return padrao


def proximo_volume(atual: float) -> float:
    """Avança o volume de 10 em 10 por cento, voltando a zero depois de 100%."""
    atual = limitar_volume(atual, 0.0)
    proximo = round(atual + 0.1, 2)
    return 0.0 if proximo > 1.0001 else proximo


@dataclass
class Preferencias:
    """Opções que sobrevivem entre sessões."""

    tela_cheia: bool = False
    tremer_tela: bool = True
    numeros_dano: bool = True
    mostrar_fps: bool = False
    dicas_tutorial: bool = True
    escala_texto: float = 1.0
    volume_geral: float = 0.8
    volume_musica: float = 0.6
    volume_efeitos: float = 0.8
    mudo: bool = False
    parada_impacto: bool = True
    bloom: bool = True
    luz_avancada: bool = True
    arte_pixel: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"versao": SETTINGS_VERSION, **asdict(self)}

    @classmethod
    def from_dict(cls, dados: dict[str, Any] | None) -> "Preferencias":
        prefs = cls()
        if not isinstance(dados, dict):
            return prefs

        try:
            versao = int(dados.get("versao", SETTINGS_VERSION))
        except (TypeError, ValueError):
            versao = SETTINGS_VERSION
        if versao > SETTINGS_VERSION:
            LOGGER.warning(
                "Preferências de versão %s são mais novas que o jogo (%s). "
                "As opções conhecidas serão carregadas.",
                versao,
                SETTINGS_VERSION,
            )

        for campo in prefs.__dataclass_fields__:
            valor = dados.get(campo)
            if campo == "escala_texto":
                prefs.escala_texto = normalizar_escala_texto(valor)
            elif campo.startswith("volume_"):
                setattr(prefs, campo, limitar_volume(valor, getattr(prefs, campo)))
            elif isinstance(valor, bool):
                setattr(prefs, campo, valor)
        return prefs

    def resetar(self) -> None:
        padrao = Preferencias()
        for campo in self.__dataclass_fields__:
            setattr(self, campo, getattr(padrao, campo))


def carregar_preferencias(caminho: Path | None = None) -> Preferencias:
    caminho = caminho or settings_path()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return Preferencias()
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Não foi possível ler as preferências: %s", exc)
        return Preferencias()
    return Preferencias.from_dict(dados)


def salvar_preferencias(prefs: Preferencias, caminho: Path | None = None) -> bool:
    caminho = caminho or settings_path()
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(caminho.name + ".tmp")
        with temporario.open("w", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(prefs.to_dict(), ensure_ascii=False, indent=2))
            arquivo.flush()
            try:
                os.fsync(arquivo.fileno())
            except OSError:
                pass
        temporario.replace(caminho)
        return True
    except OSError as exc:
        LOGGER.warning("Não foi possível salvar as preferências: %s", exc)
        return False
