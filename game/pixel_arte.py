"""Base compartilhada da arte pixel no jogo principal (experimental).

Carrega charsets 24x32 (3 quadros x 4 direções) do pack da Svetlana Kushnariova
e expõe um interruptor global usado pelo herói, pelos NPCs e pelo chão da Clareira.
"""
from __future__ import annotations

from pathlib import Path

import pygame

RAIZ = Path(__file__).resolve().parent
PERSONAGENS = RAIZ / "assets" / "pixel" / "cabbit"
CENARIO = RAIZ / "assets" / "pixel" / "cainos"
CAINOS = CENARIO

QUADRO_L, QUADRO_A = 24, 32
ESCALA = 2
LARGURA, ALTURA = QUADRO_L * ESCALA, QUADRO_A * ESCALA

COSTAS, DIREITA, FRENTE, ESQUERDA = 0, 1, 2, 3

ATIVO = False
_cache: dict[Path, list[list[pygame.Surface]]] = {}


def definir(ativo: bool) -> None:
    global ATIVO
    ATIVO = bool(ativo)


def direcao(facing: tuple[float, float]) -> int:
    fx, fy = facing
    if abs(fx) > abs(fy):
        return DIREITA if fx > 0 else ESQUERDA
    return FRENTE if fy >= -0.2 else COSTAS


def charset(caminho: Path) -> list[list[pygame.Surface]]:
    """4 linhas (direções) x 3 quadros, já ampliados 2x."""
    if caminho not in _cache:
        folha = pygame.image.load(str(caminho)).convert_alpha()
        linhas: list[list[pygame.Surface]] = []
        for linha in range(4):
            quadros = []
            for coluna in range(3):
                rect = pygame.Rect(coluna * QUADRO_L, linha * QUADRO_A, QUADRO_L, QUADRO_A)
                quadro = folha.subsurface(rect).copy()
                quadros.append(pygame.transform.scale(quadro, (LARGURA, ALTURA)))
            linhas.append(quadros)
        _cache[caminho] = linhas
    return _cache[caminho]


def desenhar_charset(
    surf: pygame.Surface,
    x: float,
    y: float,
    linhas: list[list[pygame.Surface]],
    direcao_id: int,
    quadro: int,
    flash: bool = False,
) -> None:
    sprite = linhas[direcao_id][quadro]
    pos = (int(x) - LARGURA // 2, int(y) - ALTURA)
    surf.blit(sprite, pos)
    if flash:
        silhueta = pygame.mask.from_surface(sprite).to_surface(
            setcolor=(255, 255, 255, 210), unsetcolor=(0, 0, 0, 0)
        )
        surf.blit(silhueta, pos)
