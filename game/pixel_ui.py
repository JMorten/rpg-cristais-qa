"""UI em pixel art (experimental).

Troca os painéis arredondados e as barras com brilho suave por molduras de
cantos retos, bisel de 1 px e barras em blocos — o visual "8/16 bits" que
combina com a arte do mundo.

Só entra com **Configurações -> Vídeo -> Arte pixel** ligada; sem isso o jogo
usa os painéis vetoriais de sempre.
"""
from __future__ import annotations

from typing import Sequence

import pygame

PAINEL = (22, 26, 36)
BORDA = (86, 74, 58)
DOURADO = (232, 192, 112)


def _tom(cor: Sequence[int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + delta)) for c in cor[:3])


def _rgba(cor: Sequence[int], alpha: int) -> tuple[int, int, int, int]:
    return (int(cor[0]), int(cor[1]), int(cor[2]), max(0, min(255, int(alpha))))


def painel(
    surf: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    alpha: int = 228,
    cor: Sequence[int] = PAINEL,
    borda: Sequence[int] | None = BORDA,
    raio: int = 14,
    largura_borda: int = 2,
) -> pygame.Rect:
    """Moldura de pixel: cantos retos, bisel de 1 px e rebites nos cantos."""
    r = pygame.Rect(rect)
    if r.width < 6 or r.height < 6:
        return r
    w, h = r.size
    temp = pygame.Surface((w, h), pygame.SRCALPHA)
    base = tuple(cor[:3])
    claro = _tom(base, 30)
    escuro = _tom(base, -26)
    linha = tuple(borda[:3]) if borda is not None else _tom(base, -60)

    pygame.draw.rect(temp, _rgba(base, alpha), (0, 0, w, h))
    # bisel: topo/esquerda claros, base/direita escuros
    pygame.draw.rect(temp, _rgba(claro, min(255, alpha + 24)), (1, 1, w - 2, 1))
    pygame.draw.rect(temp, _rgba(claro, min(255, alpha + 24)), (1, 1, 1, h - 2))
    pygame.draw.rect(temp, _rgba(escuro, 255), (1, h - 2, w - 2, 1))
    pygame.draw.rect(temp, _rgba(escuro, 255), (w - 2, 1, 1, h - 2))
    # contorno duro
    pygame.draw.rect(temp, _rgba(linha, 255), (0, 0, w, h), 1)
    # rebites nos cantos
    if w >= 20 and h >= 20:
        for cx, cy in ((1, 1), (w - 4, 1), (1, h - 4), (w - 4, h - 4)):
            pygame.draw.rect(temp, _rgba(DOURADO, 210), (cx, cy, 3, 3))
    surf.blit(temp, r.topleft)
    return r


def cantos_ornamentados(
    surf: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    cor: Sequence[int] = DOURADO,
    tamanho: int = 14,
) -> None:
    """Cantos em L de pixel (quadrados, sem curvas)."""
    r = pygame.Rect(rect)
    c = tuple(cor[:3])
    for cx, cy, dx, dy in (
        (r.x + 5, r.y + 5, 1, 1),
        (r.right - 6, r.y + 5, -1, 1),
        (r.x + 5, r.bottom - 6, 1, -1),
        (r.right - 6, r.bottom - 6, -1, -1),
    ):
        pygame.draw.line(surf, c, (cx, cy), (cx + tamanho * dx, cy), 2)
        pygame.draw.line(surf, c, (cx, cy), (cx, cy + (tamanho - 4) * dy), 2)


def barra(
    surf: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    valor: float,
    maximo: float,
    cor: Sequence[int],
    fundo: Sequence[int] = (18, 22, 30),
    borda: Sequence[int] = (0, 0, 0),
    rotulo: str | None = None,
    tamanho_fonte: int = 12,
    raio: int | None = None,
) -> pygame.Rect:
    """Barra em blocos, com 1 px de brilho no topo e contorno duro."""
    from utils import BRANCO, clamp, texto

    r = pygame.Rect(rect)
    pygame.draw.rect(surf, tuple(fundo[:3]), r)
    if maximo > 0 and valor > 0:
        w = int(r.width * clamp(valor / maximo, 0.0, 1.0))
        if w >= 2:
            preenchimento = pygame.Rect(r.x, r.y, w, r.height)
            pygame.draw.rect(surf, tuple(cor[:3]), preenchimento)
            if r.height >= 5:
                pygame.draw.rect(
                    surf, _tom(cor, 52), (r.x + 1, r.y + 1, max(1, w - 2), 1)
                )
            if r.height >= 7:
                pygame.draw.rect(
                    surf, _tom(cor, -38), (r.x + 1, r.bottom - 2, max(1, w - 2), 1)
                )
    pygame.draw.rect(surf, tuple(borda[:3]), r, width=1)
    if rotulo:
        texto(
            surf, rotulo, (r.centerx, r.centery - tamanho_fonte // 2),
            tamanho_fonte, BRANCO, negrito=True, alinhamento="center", sombra=True,
        )
    return r
