"""Carregamento e validação do conteúdo externalizado em `data/*.json`.

Os dados do JSON são mesclados sobre os padrões do código: adicionar um cristal,
poção ou nome novo não exige editar Python. Se o arquivo estiver ausente ou
inválido, o jogo continua com os padrões e registra o problema no log.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

STATS_VALIDOS = {
    "ataque", "defesa", "hp_max", "mp_max", "stamina_max",
    "critico", "velocidade", "regen_hp", "regen_mp",
}


def base_dir() -> Path:
    """Raiz dos dados, tanto no código quanto no executável congelado."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def caminho_dados(nome: str) -> Path:
    return base_dir() / "data" / nome


def _erro(mensagem: str) -> None:
    raise ValueError(mensagem)


def _cor(valor: Any, campo: str) -> list[int]:
    if not isinstance(valor, (list, tuple)) or len(valor) != 3:
        _erro(f"{campo}: cor deve ser uma lista com 3 números")
    try:
        cor = [int(c) for c in valor]
    except (TypeError, ValueError):
        _erro(f"{campo}: cor inválida")
    if any(c < 0 or c > 255 for c in cor):
        _erro(f"{campo}: cor fora do intervalo 0..255")
    return cor


def _texto(valor: Any, campo: str, permitir_vazio: bool = False) -> str:
    if not isinstance(valor, str) or (not permitir_vazio and not valor.strip()):
        _erro(f"{campo}: texto obrigatório")
    return valor


def _lista_textos(valor: Any, campo: str) -> list[str]:
    if not isinstance(valor, list) or not valor:
        _erro(f"{campo}: lista de textos obrigatória")
    for i, item in enumerate(valor):
        _texto(item, f"{campo}[{i}]", permitir_vazio=True)
    return [str(item) for item in valor]


def _validar_cristais(dados: Any) -> None:
    if not isinstance(dados, dict):
        _erro("cristais: deve ser um objeto")
    for chave, cristal in dados.items():
        campo = f"cristais.{chave}"
        if not isinstance(cristal, dict):
            _erro(f"{campo}: deve ser um objeto")
        stat = _texto(cristal.get("stat"), f"{campo}.stat")
        if stat not in STATS_VALIDOS:
            _erro(f"{campo}.stat: '{stat}' não é um atributo válido")
        cristal["cor"] = _cor(cristal.get("cor"), f"{campo}.cor")
        try:
            cristal["base"] = float(cristal["base"])
        except (KeyError, TypeError, ValueError):
            _erro(f"{campo}.base: número obrigatório")
        _texto(cristal.get("nome"), f"{campo}.nome")
        _texto(cristal.get("descricao"), f"{campo}.descricao")


def _validar_pocoes(dados: Any) -> None:
    if not isinstance(dados, dict):
        _erro("pocoes: deve ser um objeto")
    for chave, pocao in dados.items():
        campo = f"pocoes.{chave}"
        if not isinstance(pocao, dict):
            _erro(f"{campo}: deve ser um objeto")
        _texto(pocao.get("nome"), f"{campo}.nome")
        pocao["cor"] = _cor(pocao.get("cor"), f"{campo}.cor")
        _texto(pocao.get("icone"), f"{campo}.icone")
        _texto(pocao.get("descricao"), f"{campo}.descricao")


def _validar_tabela(dados: Any, nome: str) -> None:
    if not isinstance(dados, dict):
        _erro(f"{nome}: deve ser um objeto")
    for chave, lista in dados.items():
        _lista_textos(lista, f"{nome}.{chave}")


def validar_itens(dados: Any) -> dict[str, Any]:
    """Valida o schema e devolve os dados normalizados. Levanta ValueError."""
    if not isinstance(dados, dict):
        _erro("items.json: raiz deve ser um objeto")
    for secao, validador in (
        ("cristais", _validar_cristais),
        ("pocoes", _validar_pocoes),
        ("bases_arma", lambda d: _validar_tabela(d, "bases_arma")),
        ("prefixos", lambda d: _validar_tabela(d, "prefixos")),
        ("sufixos", lambda d: _validar_tabela(d, "sufixos")),
    ):
        if secao in dados:
            validador(dados[secao])
    return dados


def carregar_itens(estrito: bool = False) -> dict[str, Any]:
    """Lê `data/items.json`; em erro, usa os padrões do código."""
    caminho = caminho_dados("items.json")
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        return validar_itens(dados)
    except FileNotFoundError:
        if estrito:
            raise
        LOGGER.info("data/items.json ausente; usando os dados padrão do código.")
        return {}
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        if estrito:
            raise
        LOGGER.error("Conteúdo de itens inválido (%s); usando os padrões.", exc)
        return {}
