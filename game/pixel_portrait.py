"""Retratos de classe em pixel art (experimental).

O rosto vem do próprio charset do herói (recorte da cabeça e dos ombros),
então o retrato combina com o personagem que anda no mapa. Só entra com
**Configurações -> Vídeo -> Arte pixel** ligada.
"""
from __future__ import annotations

from typing import Sequence

import pygame

import pixel_arte
import pixel_player
from settings import CLASSES

RECORTE = pygame.Rect(2, 0, 20, 20)
LADO = RECORTE.width

_cache: dict[tuple[str, int], pygame.Surface] = {}


def _rosto(classe: str, escala: int) -> pygame.Surface:
    chave = (classe, escala)
    img = _cache.get(chave)
    if img is None:
        arquivo = pixel_player.ARQUIVOS.get(classe, pixel_player.ARQUIVOS["Cavaleiro"])
        linhas = pixel_arte.charset(pixel_player.PASTA / arquivo)
        quadro = pygame.transform.scale(linhas[pixel_arte.FRENTE][1], (24, 32))
        recorte = quadro.subsurface(RECORTE).copy()
        img = pygame.transform.scale(recorte, (LADO * escala, LADO * escala))
        if len(_cache) > 24:
            _cache.clear()
        _cache[chave] = img
    return img


def desenhar(
    surf: pygame.Surface, classe: str, rect: pygame.Rect | Sequence[int],
    estado: str = "normal", tempo: float = 0.0,
) -> None:
    r = pygame.Rect(rect)
    if r.width < 12 or r.height < 12:
        return
    dados = CLASSES.get(classe, CLASSES["Cavaleiro"])
    cor = tuple(int(c) for c in dados["cor"])
    cor2 = tuple(int(c) for c in dados["cor2"])
    escala = max(1, min(r.width, r.height) // LADO)

    fundo = tuple(int(c * 0.22 + 14) for c in cor)
    faixa = tuple(int(c * 0.30 + 18) for c in cor)
    base = tuple(int(c * 0.15 + 10) for c in cor)
    surf.fill(fundo, r)
    pygame.draw.rect(surf, faixa, (r.x, r.y + r.height // 2, r.width, r.height - r.height // 2))
    pygame.draw.rect(surf, base, (r.x, r.y + r.height - max(2, r.height // 8), r.width, max(2, r.height // 8)))

    rosto = _rosto(classe, escala)
    x = r.centerx - rosto.get_width() // 2
    y = r.centery - rosto.get_height() // 2 + 2
    surf.blit(rosto, (x, y))

    # expressões: ferido escurece e vermelha; morto dessatura e escurece
    if estado == "ferido":
        camada = pygame.Surface(r.size, pygame.SRCALPHA)
        camada.fill((180, 40, 40, 55))
        surf.blit(camada, r.topleft)
        pygame.draw.rect(surf, (220, 80, 80), r, 1)
    elif estado == "morto":
        surf.fill((128, 128, 128), r, pygame.BLEND_MULT)
        camada = pygame.Surface(r.size, pygame.SRCALPHA)
        camada.fill((20, 20, 30, 110))
        surf.blit(camada, r.topleft)

    # piscada: fecha os olhos por 0,12 s a cada 4 s
    if estado != "morto":
        ciclo = tempo % 4.0
        if 3.0 < ciclo < 3.12:
            for ex, ey in ((7, 6), (11, 6)):
                pygame.draw.rect(
                    surf, (20, 18, 26),
                    (r.x + (ex + 1) * escala, r.y + (ey + 1) * escala, 2 * escala, 1 * escala),
                )

    pygame.draw.rect(surf, (20, 18, 26), r, 1)
    if r.width >= 24 and r.height >= 24:
        pygame.draw.rect(surf, cor2, r.inflate(-2, -2), 1)
