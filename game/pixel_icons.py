"""Ícones de item e habilidade em pixel art (experimental).

Cada ícone é desenhado num quadro de 16×16 e ampliado por um fator inteiro
(2×, 3× ou 4×), então fica sempre nítido e no mesmo "tamanho de pixel" da arte
do mundo. Só entra com **Configurações -> Vídeo -> Arte pixel** ligada.
"""
from __future__ import annotations

import math
from typing import Sequence

import pygame

CONTORNO = (20, 18, 26)
DOURADO = (232, 192, 112)
MADEIRA = (146, 104, 62)
MADEIRA_ESCURA = (104, 70, 40)
ACO = (206, 212, 226)
ACO_CLARO = (242, 246, 255)
VIDRO = (206, 224, 232)

_cache: dict[tuple[str, tuple[int, int, int]], pygame.Surface] = {}


def _tom(cor: Sequence[int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c) + delta)) for c in cor[:3])


def _encolher(pontos: Sequence[Sequence[float]], d: float = 1.0) -> list[tuple[int, int]]:
    """Move cada vértice um pixel para dentro, deixando a borda escura."""
    cx = sum(p[0] for p in pontos) / len(pontos)
    cy = sum(p[1] for p in pontos) / len(pontos)
    saida = []
    for x, y in pontos:
        dx, dy = x - cx, y - cy
        dist = max(1.0, math.hypot(dx, dy))
        saida.append((int(round(x - dx / dist * d)), int(round(y - dy / dist * d))))
    return saida


def _poly(img: pygame.Surface, cor: Sequence[int], pontos: Sequence[Sequence[float]], borda: bool = True) -> None:
    pts = [(int(round(x)), int(round(y))) for x, y in pontos]
    if borda:
        pygame.draw.polygon(img, CONTORNO, pts)
        pygame.draw.polygon(img, tuple(cor[:3]), _encolher(pts))
    else:
        pygame.draw.polygon(img, tuple(cor[:3]), pts)


def _bloco(img: pygame.Surface, cor: Sequence[int], rect: Sequence[int], borda: bool = True) -> None:
    r = pygame.Rect(rect)
    if borda:
        pygame.draw.rect(img, CONTORNO, r.inflate(2, 2))
    pygame.draw.rect(img, tuple(cor[:3]), r)


def _linha(
    img: pygame.Surface, cor: Sequence[int], inicio: Sequence[float], fim: Sequence[float],
    grossura: int = 3,
) -> None:
    """Linha com contorno: pincel grosso escuro e miolo claro."""
    a = (int(inicio[0]), int(inicio[1]))
    b = (int(fim[0]), int(fim[1]))
    pygame.draw.line(img, CONTORNO, a, b, grossura)
    pygame.draw.line(img, tuple(cor[:3]), a, b, max(1, grossura - 2))


# ------------------------------------------------------------------ desenhos
def _espada(img: pygame.Surface, cor) -> None:
    claro = _tom(cor, 60)
    _poly(img, cor, [(7, 2), (8, 0), (10, 2), (10, 9), (7, 9)])
    pygame.draw.line(img, claro, (7, 3), (7, 8))
    _bloco(img, DOURADO, (4, 10, 9, 2))
    _bloco(img, MADEIRA, (7, 12, 3, 3))
    _bloco(img, DOURADO, (6, 15, 5, 1))


def _arco(img: pygame.Surface, cor) -> None:
    # limbo em três segmentos, para curvar sem depender de arco
    for a, b in (((9, 1), (4, 4)), ((4, 4), (3, 8)), ((3, 8), (4, 12)), ((4, 12), (9, 15))):
        _linha(img, cor, a, b, 3)
    pygame.draw.line(img, (232, 226, 200), (9, 1), (9, 15))
    pygame.draw.line(img, (232, 226, 200), (3, 8), (11, 8))
    _poly(img, cor, [(14, 8), (10, 5), (10, 11)])


def _cajado(img: pygame.Surface, cor) -> None:
    _linha(img, MADEIRA, (4, 15), (9, 4), 3)
    pygame.draw.circle(img, CONTORNO, (11, 4), 4)
    pygame.draw.circle(img, tuple(cor[:3]), (11, 4), 3)
    pygame.draw.rect(img, (255, 255, 255), (10, 2, 1, 1))
    pygame.draw.rect(img, _tom(cor, -60), (12, 5, 2, 1))


def _armadura(img: pygame.Surface, cor) -> None:
    _poly(img, cor, [(2, 4), (5, 1), (10, 1), (13, 4), (12, 11), (8, 14), (4, 11)])
    pygame.draw.rect(img, CONTORNO, (6, 1, 4, 2))
    pygame.draw.line(img, _tom(cor, 55), (8, 3), (8, 12))
    pygame.draw.line(img, _tom(cor, -50), (4, 6), (4, 10))
    pygame.draw.line(img, _tom(cor, -50), (12, 6), (12, 10))


def _anel(img: pygame.Surface, cor) -> None:
    pygame.draw.circle(img, CONTORNO, (8, 9), 5, 3)
    pygame.draw.circle(img, tuple(cor[:3]), (8, 9), 5, 1)
    pygame.draw.polygon(img, CONTORNO, [(8, 0), (11, 4), (8, 8), (5, 4)])
    pygame.draw.polygon(img, (232, 250, 255), [(8, 2), (9, 4), (8, 6), (7, 4)])


def _amuleto(img: pygame.Surface, cor) -> None:
    # corrente em V
    pygame.draw.lines(img, (226, 200, 120), False, [(2, 1), (5, 4), (8, 5), (11, 4), (14, 1)], 1)
    pygame.draw.rect(img, CONTORNO, (7, 5, 3, 3))
    pygame.draw.rect(img, DOURADO, (8, 6, 1, 2))
    # pingente
    pygame.draw.polygon(img, CONTORNO, [(8, 7), (12, 10), (8, 15), (4, 10)])
    pygame.draw.polygon(img, tuple(cor[:3]), [(8, 9), (10, 10), (8, 13), (6, 10)])
    pygame.draw.rect(img, (250, 232, 160), (7, 9, 1, 2))


def _cristal(img: pygame.Surface, cor) -> None:
    _poly(img, cor, [(8, 1), (12, 6), (10, 14), (6, 14), (4, 6)])
    pygame.draw.polygon(img, (255, 255, 255), [(8, 2), (10, 6), (8, 12)], 1)
    pygame.draw.line(img, _tom(cor, -70), (9, 8), (10, 13))


def _pocao(img: pygame.Surface, cor) -> None:
    _bloco(img, MADEIRA_ESCURA, (6, 0, 4, 2))
    _bloco(img, VIDRO, (6, 2, 4, 3))
    _poly(img, VIDRO, [(4, 5), (12, 5), (12, 12), (10, 14), (6, 14), (4, 12)])
    _poly(img, cor, [(5, 7), (11, 7), (11, 12), (10, 13), (6, 13), (5, 12)], borda=False)
    pygame.draw.line(img, (255, 255, 255), (6, 8), (6, 10))
    pygame.draw.rect(img, _tom(cor, -70), (5, 12, 6, 1))


def _giro(img: pygame.Surface, cor) -> None:
    pygame.draw.arc(img, tuple(cor[:3]), (2, 2, 12, 12), 0.9, 5.5, 2)
    pygame.draw.polygon(img, tuple(cor[:3]), [(14, 1), (15, 7), (10, 5)])


def _dash(img: pygame.Surface, cor) -> None:
    for x in (1, 5, 9):
        _linha(img, cor, (x, 3), (x + 4, 8), 3)
        _linha(img, cor, (x + 4, 8), (x, 13), 3)


def _brado(img: pygame.Surface, cor) -> None:
    # megafone com ondas de som
    _poly(img, cor, [(2, 6), (8, 3), (8, 13), (2, 10)])
    _bloco(img, _tom(cor, -60), (3, 10, 4, 3))
    for x, y0, y1 in ((10, 6, 10), (12, 4, 12), (14, 2, 14)):
        pygame.draw.line(img, tuple(cor[:3]), (x, y0), (x, y1), 1)


def _duplo(img: pygame.Surface, cor) -> None:
    for ox in (0, 4):
        _linha(img, cor, (3 + ox, 13), (10 + ox, 3), 3)
        _poly(img, cor, [(11 + ox, 2), (8 + ox, 4), (10 + ox, 6)])


def _chuva(img: pygame.Surface, cor) -> None:
    pygame.draw.rect(img, (150, 160, 182), (0, 0, 16, 3))
    pygame.draw.rect(img, (108, 118, 140), (0, 2, 16, 1))
    for x in (3, 8, 13):
        _linha(img, cor, (x, 5), (x, 10), 3)
        _poly(img, cor, [(x, 15), (x - 2, 10), (x + 2, 10)])


def _certeiro(img: pygame.Surface, cor) -> None:
    pygame.draw.circle(img, tuple(cor[:3]), (8, 8), 5, 1)
    pygame.draw.line(img, tuple(cor[:3]), (8, 0), (8, 3))
    pygame.draw.line(img, tuple(cor[:3]), (8, 13), (8, 15))
    pygame.draw.line(img, tuple(cor[:3]), (0, 8), (3, 8))
    pygame.draw.line(img, tuple(cor[:3]), (13, 8), (15, 8))
    pygame.draw.rect(img, (255, 255, 255), (8, 8, 1, 1))


def _fogo(img: pygame.Surface, cor) -> None:
    _poly(img, cor, [(8, 0), (11, 4), (12, 8), (11, 12), (8, 14), (5, 12), (4, 8), (5, 4)])
    _poly(img, (255, 226, 130), [(8, 5), (10, 9), (9, 12), (7, 12), (6, 9)], borda=False)
    pygame.draw.rect(img, (255, 250, 210), (8, 9, 1, 2))


def _gelo(img: pygame.Surface, cor) -> None:
    for i in range(3):
        a = i * math.pi / 3
        dx, dy = math.cos(a) * 6, math.sin(a) * 6
        _linha(img, cor, (8 - dx, 8 - dy), (8 + dx, 8 + dy), 3)
    pygame.draw.rect(img, (232, 250, 255), (7, 7, 2, 2))


def _raio(img: pygame.Surface, cor) -> None:
    _poly(img, cor, [(9, 0), (4, 7), (7, 7), (6, 15), (12, 6), (9, 6)])
    pygame.draw.rect(img, _tom(cor, 70), (7, 3, 1, 2))


def _engrenagem(img: pygame.Surface, cor) -> None:
    # centro e 6 dentes
    pygame.draw.circle(img, CONTORNO, (8, 8), 5)
    pygame.draw.circle(img, tuple(cor[:3]), (8, 8), 4)
    pygame.draw.circle(img, (22, 24, 32), (8, 8), 2)
    for i in range(6):
        a = i * math.pi / 3
        dx, dy = math.cos(a) * 6, math.sin(a) * 6
        pygame.draw.rect(img, tuple(cor[:3]), (int(8 + dx - 1), int(8 + dy - 1), 2, 2))
        pygame.draw.rect(img, CONTORNO, (int(8 + dx - 1), int(8 + dy - 1), 2, 2), 1)


def _alto_falante(img: pygame.Surface, cor) -> None:
    # cone do falante
    _poly(img, cor, [(2, 5), (8, 3), (8, 13), (2, 11)])
    # ondas de som
    for r in (3, 5):
        pygame.draw.arc(img, tuple(cor[:3]), (9 - r, 8 - r, r * 2, r * 2), -1.0, 1.0, 1)


def _monitor(img: pygame.Surface, cor) -> None:
    # tela
    _bloco(img, CONTORNO, (2, 2, 12, 9))
    _bloco(img, tuple(cor[:3]), (3, 3, 10, 7), borda=False)
    pygame.draw.rect(img, (255, 255, 255), (5, 4, 2, 2))
    # suporte
    pygame.draw.rect(img, CONTORNO, (7, 11, 2, 2))
    pygame.draw.rect(img, CONTORNO, (4, 13, 8, 2))


DESENHOS = {
    "espada": _espada,
    "arco": _arco,
    "cajado": _cajado,
    "armadura": _armadura,
    "anel": _anel,
    "amuleto": _amuleto,
    "cristal": _cristal,
    "pocao_vida": lambda img, cor: _pocao(img, (232, 82, 96)),
    "pocao_mana": lambda img, cor: _pocao(img, (82, 148, 244)),
    "pocao_stamina": lambda img, cor: _pocao(img, (244, 206, 92)),
    "giro": _giro,
    "dash": _dash,
    "brado": _brado,
    "duplo": _duplo,
    "chuva": _chuva,
    "certeiro": _certeiro,
    "fogo": _fogo,
    "gelo": _gelo,
    "raio": _raio,
    "engrenagem": _engrenagem,
    "alto_falante": _alto_falante,
    "monitor": _monitor,
}


def _padrao(img: pygame.Surface, cor) -> None:
    pygame.draw.circle(img, CONTORNO, (8, 8), 6)
    pygame.draw.circle(img, tuple(cor[:3]), (8, 8), 5)
    pygame.draw.rect(img, _tom(cor, 70), (5, 4, 2, 2))


def _base(tipo: str, cor: Sequence[int]) -> pygame.Surface:
    chave = (tipo, tuple(int(c) for c in cor[:3]))
    img = _cache.get(chave)
    if img is None:
        img = pygame.Surface((16, 16), pygame.SRCALPHA)
        desenho = DESENHOS.get(tipo, _padrao)
        desenho(img, chave[1])
        if len(_cache) > 192:
            _cache.clear()
        _cache[chave] = img
    return img


def desenhar(
    surf: pygame.Surface, tipo: str, rect: pygame.Rect | Sequence[int],
    cor: Sequence[int] | None = None, pulso: float = 1.0,
) -> None:
    """Desenha o ícone ampliado por um fator inteiro, centralizado no retângulo.

    `pulso` (1.0 = tamanho normal) dá um pequeno 'pop' quando a habilidade
    fica pronta, sem mudar a grade de 2 px da arte.
    """
    r = pygame.Rect(rect)
    if r.width < 10 or r.height < 10:
        return
    escala = max(1, min(r.width, r.height) // 16)
    base = _base(tipo, cor or DOURADO)
    lado = 16 * escala
    if pulso != 1.0:
        lado = max(2, int(round(lado * pulso)))
    img = pygame.transform.scale(base, (lado, lado))
    surf.blit(img, (r.centerx - lado // 2, r.centery - lado // 2))
