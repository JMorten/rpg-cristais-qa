"""Casas, vegetação e props em pixel art (experimental).

Casas: kit **Shabby Chic Exterior Tiles** (cyanowl, CC0), montadas em
`assets/pixel/casas/`.
Props: kit **Pixel Art Top Down - Basic** (Cainos), recortados de
`assets/pixel/cainos/props.png`, `plant.png` e `struct.png`.
Coluna: **0x72 - DungeonTileset II** (CC0).
Estruturas da vila (fonte, altar, jardim, bandeira, bigorna, banca e fogueira):
desenhadas à mão em pixel, porque nenhum dos packs tem essas peças.

Tudo em escala 1x, que é o tamanho em que os props batem com os obstáculos
que o mundo já usa. Só entra com **Configurações -> Vídeo -> Arte pixel**.
"""
from __future__ import annotations

import math

import pygame

import pixel_arte
from utils import halo_suave, sombra

CASAS = pixel_arte.RAIZ / "assets" / "pixel" / "casas"
CAINOS = pixel_arte.CAINOS
OX72 = pixel_arte.RAIZ / "assets" / "pixel" / "ox72" / "props"

# recortes no props.png do Cainos (x, y, largura, altura)
RECORTES: dict[str, tuple[int, int, int, int]] = {
    "caixote": (96, 76, 32, 49),
    "barril": (162, 153, 28, 36),
    "banco": (292, 19, 56, 41),
    "placa": (99, 160, 27, 32),
    "vaso": (165, 217, 21, 34),
}

# recortes no plant.png do Cainos
ARVORES: tuple[tuple[int, int, int, int], ...] = (
    (24, 14, 113, 139),
    (161, 17, 95, 136),
    (295, 31, 79, 120),
)
ARBUSTOS: tuple[tuple[int, int, int, int], ...] = (
    (156, 190, 38, 32),
    (216, 185, 47, 42),
    (282, 186, 39, 45),
    (346, 190, 40, 35),
)

# recortes no struct.png do Cainos
PAREDES: tuple[tuple[int, int, int, int], ...] = (
    (32, 32, 64, 96),
    (128, 32, 65, 96),
    (224, 32, 65, 96),
    (32, 160, 64, 96),
    (128, 160, 65, 96),
    (224, 160, 65, 96),
)
ARCOS: tuple[tuple[int, int, int, int], ...] = (
    (408, 27, 80, 64),
    (416, 128, 64, 64),
)

_cache: dict[tuple[str, object], pygame.Surface] = {}
_folhas: dict[str, pygame.Surface] = {}


def _folha(nome: str) -> pygame.Surface:
    if nome not in _folhas:
        _folhas[nome] = pygame.image.load(str(CAINOS / nome)).convert_alpha()
    return _folhas[nome]


def _casa(nome: str) -> pygame.Surface:
    chave = ("casa", nome)
    if chave not in _cache:
        _cache[chave] = pygame.image.load(str(CASAS / f"{nome}.png")).convert_alpha()
    return _cache[chave]


def _recorte(nome: str) -> pygame.Surface:
    chave = ("recorte", nome)
    if chave not in _cache:
        folha = _folha("props.png")
        _cache[chave] = folha.subsurface(pygame.Rect(RECORTES[nome])).copy()
    return _cache[chave]


def _planta(nome: str, indice: int) -> pygame.Surface:
    chave = (nome, indice)
    if chave not in _cache:
        recortes = ARVORES if nome == "arvore" else ARBUSTOS
        folha = _folha("plant.png")
        _cache[chave] = folha.subsurface(pygame.Rect(recortes[indice % len(recortes)])).copy()
    return _cache[chave]


def _estrutura(nome: str, indice: int) -> pygame.Surface:
    chave = (nome, indice)
    if chave not in _cache:
        recortes = PAREDES if nome == "parede" else ARCOS
        folha = _folha("struct.png")
        _cache[chave] = folha.subsurface(pygame.Rect(recortes[indice % len(recortes)])).copy()
    return _cache[chave]


def _ox72(nome: str, escala: int = 2) -> pygame.Surface:
    chave = ("ox72", nome)
    if chave not in _cache:
        img = pygame.image.load(str(OX72 / f"{nome}.png")).convert_alpha()
        img = pygame.transform.scale(img, (img.get_width() * escala, img.get_height() * escala))
        _cache[chave] = img
    return _cache[chave]


# ------------------------------------------------------------------ desenhos
def _lampiao_pixel() -> pygame.Surface:
    """Lampião desenhado à mão em pixel: o kit do Cainos não tem poste de luz."""
    chave = ("prop", "lampiao")
    if chave in _cache:
        return _cache[chave]
    largura, altura = 20, 68
    img = pygame.Surface((largura, altura), pygame.SRCALPHA)
    metal = (54, 52, 64)
    metal_claro = (92, 90, 106)
    vidro = (250, 214, 130)
    brilho = (255, 244, 200)
    # telhadinho
    pygame.draw.polygon(img, metal, [(1, 8), (19, 8), (10, 1)])
    pygame.draw.polygon(img, metal_claro, [(4, 8), (16, 8), (10, 4)])
    # lanterna
    pygame.draw.rect(img, metal, (3, 8, 14, 18))
    pygame.draw.rect(img, vidro, (5, 10, 10, 14))
    pygame.draw.rect(img, brilho, (7, 12, 6, 10))
    pygame.draw.rect(img, metal, (9, 10, 2, 14))
    # poste e base
    pygame.draw.rect(img, metal, (8, 26, 4, 32))
    pygame.draw.rect(img, metal_claro, (9, 26, 1, 32))
    pygame.draw.rect(img, metal, (2, 56, 16, 4))
    pygame.draw.rect(img, metal, (5, 60, 10, 8))
    pygame.draw.rect(img, metal_claro, (6, 60, 8, 2))
    _cache[chave] = img
    return img


def _rocha_pixel(variacao: int) -> pygame.Surface:
    chave = ("rocha", variacao)
    if chave in _cache:
        return _cache[chave]
    formas = (
        ((2, 29), (0, 20), (4, 10), (13, 3), (27, 2), (36, 9), (39, 18), (35, 27), (20, 29)),
        ((1, 29), (3, 16), (11, 7), (24, 4), (34, 12), (38, 22), (30, 29), (14, 30)),
        ((4, 29), (0, 22), (6, 12), (18, 6), (30, 8), (39, 17), (34, 28), (18, 30)),
    )
    pontos = formas[variacao % len(formas)]
    img = pygame.Surface((40, 31), pygame.SRCALPHA)
    pygame.draw.polygon(img, (86, 90, 102), pontos)
    n = len(pontos)
    cx = sum(p[0] for p in pontos) / n
    cy = sum(p[1] for p in pontos) / n
    claro = [(int(cx + (x - cx) * 0.6) - 1, int(cy + (y - cy) * 0.6) - 2) for x, y in pontos]
    pygame.draw.polygon(img, (118, 124, 138), claro)
    pygame.draw.polygon(img, (56, 60, 72), pontos, 2)
    # facetas e rachaduras
    pygame.draw.line(img, (44, 48, 58), (10, 22), (22, 8), 1)
    pygame.draw.line(img, (44, 48, 58), (22, 8), (34, 20), 1)
    pygame.draw.line(img, (44, 48, 58), (22, 8), (24, 26), 1)
    pygame.draw.rect(img, (138, 144, 156), (16, 7, 6, 2))
    # musgo
    if variacao % 2 == 0:
        pygame.draw.rect(img, (74, 120, 74), (26, 14, 8, 3))
        pygame.draw.rect(img, (94, 146, 84), (28, 13, 4, 2))
    _cache[chave] = img
    return img


def _cristal_pixel(cor: tuple[int, int, int], variacao: int) -> pygame.Surface:
    chave = ("cristal", (cor, variacao % 3))
    if chave in _cache:
        return _cache[chave]
    claro = tuple(min(255, c + 70) for c in cor)
    escuro = tuple(max(0, c - 60) for c in cor)
    contorno = tuple(max(0, c - 110) for c in cor)
    img = pygame.Surface((46, 66), pygame.SRCALPHA)
    shards = (
        ((23, 2), (12, 30), (23, 60), (34, 30)),
        ((7, 24), (0, 44), (12, 60), (16, 38)),
        ((39, 20), (46, 40), (34, 60), (30, 36)),
    )
    deslocamento = variacao % 3
    for i, pts in enumerate(shards):
        pts = tuple((x, min(64, y + deslocamento)) for x, y in pts)
        pygame.draw.polygon(img, cor, pts)
        pygame.draw.polygon(img, claro, (pts[0], pts[1], pts[2]))
        pygame.draw.polygon(img, escuro, (pts[2], pts[3], (pts[3][0], pts[3][1] - 6)))
        pygame.draw.polygon(img, contorno, pts, 1)
    # pedriscos na base
    pygame.draw.ellipse(img, escuro, (6, 56, 34, 9))
    for ox, oy, r in ((10, 60, 2), (24, 62, 2), (36, 59, 2)):
        pygame.draw.rect(img, contorno, (ox, oy, r + 2, r + 1))
    _cache[chave] = img
    return img


def _tronco_pixel(variacao: int) -> pygame.Surface:
    chave = ("tronco", variacao)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((34, 27), pygame.SRCALPHA)
    pygame.draw.rect(img, (92, 62, 42), (3, 10, 28, 15))
    pygame.draw.rect(img, (66, 44, 30), (3, 10, 28, 15), 2)
    pygame.draw.ellipse(img, (128, 92, 60), (3, 3, 28, 14))
    pygame.draw.ellipse(img, (86, 58, 38), (3, 3, 28, 14), 2)
    pygame.draw.ellipse(img, (150, 112, 74), (10, 6, 8, 5))
    if variacao % 2 == 0:
        pygame.draw.rect(img, (74, 118, 74), (7, 4, 6, 3))
    _cache[chave] = img
    return img


def _arvore_morta_pixel(variacao: int) -> pygame.Surface:
    chave = ("arvore_morta", variacao)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((66, 94), pygame.SRCALPHA)
    tronco = ((28, 93), (26, 64), (23, 42), (21, 22), (26, 15), (31, 24), (33, 46), (35, 66), (37, 93))
    pygame.draw.polygon(img, (66, 54, 44), tronco)
    pygame.draw.polygon(img, (40, 32, 26), tronco, 1)
    galhos = (
        ((27, 62), (8, 46)), ((28, 54), (48, 34)), ((25, 40), (10, 20)),
        ((30, 30), (50, 14)), ((30, 72), (46, 64)), ((24, 50), (4, 34)),
    )
    for (ax, ay), (bx, by) in galhos:
        pygame.draw.line(img, (58, 46, 36), (ax, ay), (bx, by), 2)
        pygame.draw.line(img, (36, 28, 22), (ax, ay), (bx, by), 1)
    # musgo luminoso
    pygame.draw.rect(img, (74, 116, 68), (22, 44, 8, 5))
    pygame.draw.rect(img, (112, 164, 88), (24, 43, 4, 3))
    _cache[chave] = img
    return img


def _cogumelo_pixel(cor: tuple[int, int, int], variacao: int) -> pygame.Surface:
    chave = ("cogumelo", (cor, variacao % 2))
    if chave in _cache:
        return _cache[chave]
    claro = tuple(min(255, c + 50) for c in cor)
    escuro = tuple(max(0, c - 60) for c in cor)
    img = pygame.Surface((32, 28), pygame.SRCALPHA)
    for ox, altura, raio in ((5, 12, 6), (14, 17, 8), (25, 9, 5)):
        pygame.draw.rect(img, (214, 204, 182), (ox, 27 - altura, 3, altura))
        pygame.draw.rect(img, (168, 158, 138), (ox + 2, 27 - altura, 1, altura))
        pygame.draw.ellipse(img, escuro, (ox - raio, 26 - altura - raio, raio * 2, raio + 4))
        pygame.draw.ellipse(img, cor, (ox - raio, 27 - altura - raio, raio * 2, raio + 2))
        pygame.draw.rect(img, claro, (ox - 2, 27 - altura - raio + 2, 3, 2))
    _cache[chave] = img
    return img


# ------------------------------------------------------------------ API
def desenhar_casa(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    nome = "casa_pequena" if getattr(d, "variacao", 0) == 1 else "casa_grande"
    img = _casa(nome)
    sombra(surf, sx, sy - 3, img.get_width() * 0.42, 14, 95)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height()))


def desenhar_prop(nome: str, surf: pygame.Surface, sx: float, sy: float) -> None:
    img = _recorte(nome)
    sombra(surf, sx, sy - 2, img.get_width() * 0.42, 6, 65)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height()))


def desenhar_lampiao(surf: pygame.Surface, sx: float, sy: float, tempo: float, fase: float) -> None:
    pulso = 0.7 + 0.3 * math.sin(tempo * 2.4 + fase)
    halo_suave(surf, (sx, sy - 52), 34, (250, 206, 120), int(42 * pulso))
    img = _lampiao_pixel()
    sombra(surf, sx, sy - 2, 13, 5, 70)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height()))


def desenhar_arvore(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _planta("arvore", getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 4, img.get_width() * 0.30, 11, 85)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 6))


def desenhar_arbusto(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _planta("arbusto", getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 1, img.get_width() * 0.42, 6, 60)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def desenhar_junco(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    base_x, base_y = int(sx), int(sy)
    sway = int(round(math.sin(tempo * 1.3 + getattr(d, "fase", 0.0)) * 2))
    for i, (ox, altura) in enumerate(((-8, 26), (-3, 35), (3, 31), (8, 22))):
        cor = (86, 110, 64) if i % 2 == 0 else (64, 86, 48)
        topo = base_x + ox + sway
        pygame.draw.line(surf, cor, (base_x + ox, base_y), (topo, base_y - altura), 2)
        if i % 2 == 0:
            pygame.draw.rect(surf, (132, 102, 58), (topo - 2, base_y - altura - 7, 5, 8))
            pygame.draw.rect(surf, (168, 132, 74), (topo - 1, base_y - altura - 7, 2, 8))


def desenhar_arvore_morta(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _arvore_morta_pixel(getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 3, img.get_width() * 0.30, 9, 80)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def desenhar_rocha(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _rocha_pixel(getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 2, img.get_width() * 0.42, 8, 80)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def desenhar_tronco(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _tronco_pixel(getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 2, img.get_width() * 0.40, 7, 70)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def desenhar_cristal(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    cor = tuple(getattr(d, "cor", None) or (150, 200, 250))
    img = _cristal_pixel(cor, getattr(d, "variacao", 0))
    pulso = 0.75 + 0.25 * math.sin(tempo * 2.2 + getattr(d, "fase", 0.0))
    halo_suave(surf, (sx, sy - 34), 34, cor, alpha=int(38 + 22 * pulso))
    sombra(surf, sx, sy - 1, img.get_width() * 0.34, 8, 110)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 3))


def desenhar_cogumelo(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    cor = tuple(getattr(d, "cor", None) or (140, 200, 150))
    img = _cogumelo_pixel(cor, getattr(d, "variacao", 0))
    pulso = 0.6 + 0.4 * math.sin(tempo * 3 + getattr(d, "fase", 0.0))
    halo_suave(surf, (sx, sy - 16), 22, cor, alpha=int(24 + 18 * pulso))
    sombra(surf, sx, sy - 1, 11, 4, 55)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def _cone(img: pygame.Surface, cx: int, altura: int, base: int, topo: int) -> None:
    """Estalagmite sombreada linha a linha, com a luz vindo da esquerda."""
    corpo = (108, 98, 138)
    claro = (154, 144, 184)
    realce = (196, 186, 222)
    escuro = (72, 64, 98)
    contorno = (44, 38, 60)
    for y in range(topo, altura + 1):
        f = (y - topo) / max(1, altura - topo)
        meia = max(1, int(base * 0.5 * f))
        x0, x1 = cx - meia, cx + meia
        pygame.draw.line(img, corpo, (x0, y), (x1, y))
        if meia >= 2:
            pygame.draw.line(img, claro, (x0, y), (x0 + max(1, int(meia * 0.55)), y))
        if meia >= 5:
            pygame.draw.line(img, realce, (x0 + 1, y), (x0 + max(1, meia // 3), y))
        if meia >= 3:
            pygame.draw.line(img, escuro, (x1 - max(1, meia // 4), y), (x1, y))
        img.set_at((x0, y), contorno)
        img.set_at((x1, y), contorno)
    img.set_at((cx, topo), realce)


def _estalagmite_pixel(variacao: int) -> pygame.Surface:
    chave = ("estalagmite", variacao % 3)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((42, 80), pygame.SRCALPHA)
    if variacao % 3 == 0:
        _cone(img, 21, 76, 26, 4)
    elif variacao % 3 == 1:
        _cone(img, 15, 74, 22, 8)
        _cone(img, 31, 42, 12, 22)
    else:
        _cone(img, 12, 46, 12, 22)
        _cone(img, 27, 74, 24, 10)
    # pedriscos soltos na base
    for ox, oy, w in ((4, 77, 7), (20, 78, 9), (33, 77, 6)):
        pygame.draw.rect(img, (74, 68, 96), (ox, oy, w, 2))
        pygame.draw.rect(img, (48, 42, 66), (ox, oy + 1, w, 1))
    _cache[chave] = img
    return img


def desenhar_estalagmite(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _estalagmite_pixel(getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 1, img.get_width() * 0.34, 6, 90)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def _obelisco_pixel() -> pygame.Surface:
    chave = ("obelisco", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((32, 108), pygame.SRCALPHA)
    claro, base, escuro, contorno = (168, 174, 200), (128, 134, 164), (86, 90, 118), (54, 58, 80)
    # pedestal em dois degraus
    pygame.draw.rect(img, base, (0, 98, 32, 10))
    pygame.draw.rect(img, claro, (0, 98, 32, 2))
    pygame.draw.rect(img, contorno, (0, 98, 32, 10), 1)
    pygame.draw.rect(img, base, (3, 90, 26, 8))
    pygame.draw.rect(img, claro, (3, 90, 26, 2))
    pygame.draw.rect(img, contorno, (3, 90, 26, 8), 1)
    # fuste afunilado
    fuste = [(10, 90), (12, 30), (16, 14), (20, 30), (22, 90)]
    pygame.draw.polygon(img, base, fuste)
    pygame.draw.polygon(img, claro, [(10, 90), (12, 30), (16, 14), (16, 90)])
    pygame.draw.polygon(img, escuro, [(16, 14), (20, 30), (22, 90), (16, 90)])
    pygame.draw.polygon(img, contorno, fuste, 1)
    # runas acesas ao longo do fuste
    for y in (36, 54, 72):
        pygame.draw.rect(img, (120, 200, 250), (14, y, 4, 8))
        pygame.draw.rect(img, (212, 242, 255), (15, y + 1, 2, 5))
    # gema no topo
    pygame.draw.polygon(img, (150, 226, 255), [(16, 0), (21, 8), (16, 14), (11, 8)])
    pygame.draw.polygon(img, (228, 250, 255), [(16, 2), (18, 8), (16, 11)])
    pygame.draw.polygon(img, (70, 120, 170), [(16, 0), (21, 8), (16, 14), (11, 8)], 1)
    _cache[chave] = img
    return img


def desenhar_obelisco(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _obelisco_pixel()
    pulso = 0.7 + 0.3 * math.sin(tempo * 1.8 + getattr(d, "fase", 0.0))
    halo_suave(surf, (sx, sy - 48), 26, (140, 200, 255), alpha=int(30 + 22 * pulso))
    sombra(surf, sx, sy - 2, 16, 7, 90)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def _estatua_pixel(variacao: int) -> pygame.Surface:
    chave = ("estatua", variacao % 2)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((42, 76), pygame.SRCALPHA)
    claro, base, escuro = (150, 148, 158), (116, 114, 124), (78, 76, 86)
    # pedestal
    pygame.draw.rect(img, base, (2, 62, 38, 14))
    pygame.draw.rect(img, claro, (2, 62, 38, 3))
    pygame.draw.rect(img, escuro, (2, 62, 38, 14), 1)
    # manto
    pygame.draw.polygon(img, base, [(12, 62), (14, 30), (28, 30), (30, 62)])
    pygame.draw.polygon(img, claro, [(14, 60), (16, 32), (21, 32), (20, 60)])
    pygame.draw.polygon(img, escuro, [(12, 62), (14, 30), (28, 30), (30, 62)], 1)
    # ombros, braços e cabeça
    pygame.draw.rect(img, base, (11, 24, 20, 8))
    pygame.draw.rect(img, escuro, (11, 24, 20, 8), 1)
    pygame.draw.rect(img, base, (8, 28, 5, 16))
    pygame.draw.rect(img, base, (29, 28, 5, 16))
    pygame.draw.rect(img, escuro, (8, 28, 5, 16), 1)
    pygame.draw.rect(img, escuro, (29, 28, 5, 16), 1)
    pygame.draw.rect(img, claro, (16, 12, 10, 12))
    pygame.draw.rect(img, base, (16, 12, 10, 12), 1)
    pygame.draw.rect(img, escuro, (14, 10, 14, 3))
    # musgo
    pygame.draw.rect(img, (88, 124, 88), (26, 34, 4, 3))
    _cache[chave] = img
    return img


def desenhar_estatua(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _estatua_pixel(getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 2, 20, 7, 85)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def _coluna_quebrada() -> pygame.Surface:
    """Coluna de pedra partida ao meio, sem grama, para servir em qualquer bioma."""
    chave = ("coluna_quebrada", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((46, 72), pygame.SRCALPHA)
    base, claro, escuro, contorno = (118, 116, 126), (150, 148, 158), (82, 80, 90), (52, 50, 60)
    # três tambores empilhados, cada um um pouco fora de prumo
    for i, (ox, oy, altura) in enumerate(((0, 26, 22), (-2, 46, 22), (1, 64, 8))):
        x = 8 + ox
        pygame.draw.rect(img, base, (x, oy, 20, altura))
        pygame.draw.rect(img, claro, (x, oy, 20, 3))
        pygame.draw.rect(img, escuro, (x, oy + altura - 2, 20, 2))
        pygame.draw.rect(img, contorno, (x, oy, 20, altura), 1)
        if i < 2:
            pygame.draw.line(img, escuro, (x + 3, oy + 4), (x + 8, oy + altura - 5), 1)
    # topo partido, em diagonal
    pygame.draw.polygon(img, base, [(7, 28), (11, 8), (26, 12), (28, 28)])
    pygame.draw.polygon(img, claro, [(11, 8), (26, 12), (27, 16), (11, 13)])
    pygame.draw.polygon(img, contorno, [(7, 28), (11, 8), (26, 12), (28, 28)], 1)
    # entulho na base
    for x, y, w, h in ((2, 68, 7, 3), (30, 66, 9, 5), (36, 70, 7, 2)):
        pygame.draw.rect(img, base, (x, y, w, h))
        pygame.draw.rect(img, claro, (x, y, w, 1))
        pygame.draw.rect(img, contorno, (x, y, w, h), 1)
    _cache[chave] = img
    return img


def desenhar_ruina(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    variacao = getattr(d, "variacao", 0)
    if variacao % 2 == 0:
        img = _ox72("column")
        sombra(surf, sx, sy - 2, 18, 7, 90)
        surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))
        # capitel caído ao lado
        bloco = pygame.Rect(int(sx) + 14, int(sy) - 12, 30, 11)
        pygame.draw.rect(surf, (124, 120, 126), bloco)
        pygame.draw.rect(surf, (74, 72, 80), bloco, 2)
        pygame.draw.rect(surf, (148, 144, 148), (bloco.left + 2, bloco.top + 1, 26, 2))
    else:
        img = _coluna_quebrada()
        sombra(surf, sx, sy - 2, img.get_width() * 0.40, 8, 90)
        surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def desenhar_muro(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _estrutura("parede", getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 2, img.get_width() * 0.44, 8, 90)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))


def desenhar_arco(surf: pygame.Surface, sx: float, sy: float, d: object) -> None:
    img = _estrutura("arco", getattr(d, "variacao", 0))
    sombra(surf, sx, sy - 1, img.get_width() * 0.44, 9, 100)
    surf.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() + 2))

# ------------------------------------------------------- estruturas da vila
def _fonte_pixel() -> pygame.Surface:
    chave = ("fonte", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((112, 92), pygame.SRCALPHA)
    pedra, claro, escuro, contorno = (114, 112, 124), (150, 148, 160), (72, 70, 84), (46, 44, 56)
    agua, agua_clara, agua_escura = (54, 118, 158), (96, 172, 204), (36, 86, 124)

    # parede da bacia, com juntas de pedra
    parede = [(2, 62), (110, 62), (108, 88), (4, 88)]
    pygame.draw.polygon(img, pedra, parede)
    for x in range(14, 104, 16):
        pygame.draw.line(img, escuro, (x, 64), (x, 87), 1)
        pygame.draw.line(img, claro, (x + 1, 64), (x + 1, 84), 1)
    pygame.draw.rect(img, claro, (4, 62, 104, 3))
    pygame.draw.polygon(img, contorno, parede, 2)

    # borda superior
    pygame.draw.ellipse(img, escuro, (2, 44, 108, 36))
    pygame.draw.ellipse(img, pedra, (4, 45, 104, 33))
    pygame.draw.ellipse(img, claro, (6, 46, 100, 7))

    # água
    pygame.draw.ellipse(img, agua, (16, 54, 80, 21))
    pygame.draw.ellipse(img, agua_escura, (16, 62, 80, 13))
    pygame.draw.ellipse(img, agua_clara, (24, 56, 30, 6))

    # blocos da borda
    for i in range(10):
        ang = i * math.tau / 10
        bx = int(56 + math.cos(ang) * 47)
        by = int(63 + math.sin(ang) * 15)
        pygame.draw.rect(img, pedra, (bx - 4, by - 3, 8, 5))
        pygame.draw.rect(img, claro, (bx - 4, by - 3, 8, 1))
        pygame.draw.rect(img, escuro, (bx - 4, by + 1, 8, 1))
        pygame.draw.rect(img, contorno, (bx - 4, by - 3, 8, 5), 1)

    # runas de ouro na borda
    for i in range(4):
        ang = i * math.tau / 4 + math.pi / 4
        px = int(56 + math.cos(ang) * 38)
        py = int(63 + math.sin(ang) * 11)
        pygame.draw.rect(img, (176, 156, 116), (px - 1, py - 1, 3, 3))

    # coluna central
    pygame.draw.rect(img, escuro, (46, 50, 20, 8))
    pygame.draw.rect(img, pedra, (50, 22, 12, 32))
    pygame.draw.rect(img, claro, (50, 22, 4, 32))
    pygame.draw.rect(img, contorno, (50, 22, 12, 32), 1)

    # taça do topo
    pygame.draw.ellipse(img, escuro, (36, 12, 40, 14))
    pygame.draw.ellipse(img, pedra, (36, 11, 40, 13))
    pygame.draw.ellipse(img, claro, (38, 11, 36, 5))
    pygame.draw.ellipse(img, agua, (42, 15, 28, 6))
    pygame.draw.ellipse(img, agua_clara, (46, 16, 12, 3))
    _cache[chave] = img
    return img


def desenhar_fonte(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _fonte_pixel()
    sombra(surf, sx, sy - 4, 56, 16, 85)
    surf.blit(img, (int(sx) - 56, int(sy) - 90))

    # ondinhas na água
    for i in range(3):
        ox = int(math.sin(tempo * 1.4 + i * 2.1) * 10)
        pygame.draw.ellipse(
            surf, (120, 196, 224), (int(sx) - 20 + ox, int(sy) - 34 + i * 4, 22, 4),
        )
    # jatos do topo
    for i in range(3):
        ang = -math.pi / 2 + (i - 1) * 0.45
        comprimento = 16 + 4 * math.sin(tempo * 3 + i)
        px = int(sx + math.cos(ang) * comprimento)
        py = int(sy - 76 + math.sin(ang) * comprimento)
        pygame.draw.line(surf, (190, 232, 246), (int(sx), int(sy - 76)), (px, py), 1)
        pygame.draw.rect(surf, (232, 250, 255), (px, py, 2, 2))


def _altar_pixel() -> pygame.Surface:
    chave = ("altar", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((48, 64), pygame.SRCALPHA)
    pedra, claro, escuro, contorno = (124, 122, 134), (162, 160, 174), (82, 80, 94), (50, 48, 60)
    # base
    pygame.draw.rect(img, escuro, (2, 50, 44, 12))
    pygame.draw.rect(img, pedra, (3, 49, 42, 12))
    pygame.draw.rect(img, claro, (3, 49, 42, 3))
    pygame.draw.rect(img, contorno, (2, 49, 44, 13), 1)
    # degrau
    pygame.draw.rect(img, escuro, (7, 41, 34, 9))
    pygame.draw.rect(img, pedra, (8, 40, 32, 9))
    pygame.draw.rect(img, claro, (8, 40, 32, 2))
    pygame.draw.rect(img, contorno, (7, 40, 34, 10), 1)
    # mesa
    pygame.draw.rect(img, pedra, (12, 30, 24, 12))
    pygame.draw.rect(img, claro, (12, 30, 6, 12))
    pygame.draw.rect(img, contorno, (12, 30, 24, 12), 1)
    # tampo
    pygame.draw.rect(img, escuro, (7, 23, 34, 8))
    pygame.draw.rect(img, claro, (8, 23, 32, 7))
    pygame.draw.rect(img, pedra, (8, 27, 32, 3))
    pygame.draw.rect(img, contorno, (7, 23, 34, 8), 1)
    # braseiro no tampo
    pygame.draw.ellipse(img, contorno, (16, 19, 16, 8))
    pygame.draw.ellipse(img, escuro, (17, 20, 14, 6))
    pygame.draw.ellipse(img, (36, 34, 46), (18, 21, 12, 4))
    # runas acesas na base
    for x in (14, 24, 34):
        pygame.draw.rect(img, (120, 200, 250), (x, 54, 2, 4))
        pygame.draw.rect(img, (212, 242, 255), (x, 54, 1, 2))
    _cache[chave] = img
    return img


def desenhar_altar(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _altar_pixel()
    fase = getattr(d, "fase", 0.0)
    pulso = 0.5 + 0.5 * math.sin(tempo * 6 + fase)
    halo_suave(surf, (sx, sy - 46), 16, (110, 190, 250), int(42 + 30 * pulso))
    sombra(surf, sx, sy - 2, 20, 7, 85)
    surf.blit(img, (int(sx) - 24, int(sy) - 62))
    # orbe flutuando sobre a mesa
    cy = int(sy - 46 - 2 * pulso)
    pygame.draw.circle(surf, (70, 130, 200), (int(sx), cy), 7)
    pygame.draw.circle(surf, (120, 196, 250), (int(sx), cy), 5)
    pygame.draw.circle(surf, (226, 248, 255), (int(sx) - 1, cy - 1), 2)


def _jardim_pixel() -> pygame.Surface:
    chave = ("jardim", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((58, 26), pygame.SRCALPHA)
    madeira, claro, escuro, contorno = (124, 88, 56), (158, 116, 74), (78, 54, 36), (44, 30, 20)
    # canteiro de madeira, baixo como um canteiro de chão
    pygame.draw.rect(img, escuro, (2, 10, 54, 15))
    pygame.draw.rect(img, madeira, (3, 11, 52, 13))
    pygame.draw.rect(img, claro, (3, 11, 52, 3))
    pygame.draw.rect(img, contorno, (2, 10, 54, 15), 1)
    # terra
    pygame.draw.rect(img, (58, 42, 30), (5, 14, 48, 8))
    pygame.draw.rect(img, (84, 62, 42), (5, 14, 48, 4))
    # torrões
    for x, y in ((10, 19), (24, 21), (38, 19), (46, 21)):
        pygame.draw.rect(img, (44, 32, 24), (x, y, 5, 2))
        pygame.draw.rect(img, (96, 72, 50), (x, y, 3, 1))
    # postes nos cantos
    for x in (2, 52):
        pygame.draw.rect(img, claro, (x, 8, 4, 6))
        pygame.draw.rect(img, contorno, (x, 8, 4, 6), 1)
    _cache[chave] = img
    return img


def desenhar_jardim(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _jardim_pixel()
    fase = getattr(d, "fase", 0.0)
    sombra(surf, sx, sy - 1, 30, 7, 55)
    surf.blit(img, (int(sx) - 29, int(sy) - 24))
    # folhagem de fundo
    for ox, oy in ((-22, 0), (-8, 1), (8, 0), (20, 1), (0, -2)):
        pygame.draw.rect(surf, (38, 88, 48), (int(sx) + ox, int(sy) - 11 + oy, 6, 4))
        pygame.draw.rect(surf, (54, 112, 60), (int(sx) + ox + 1, int(sy) - 11 + oy, 4, 2))
    cores = (
        ((240, 180, 200), (252, 216, 228)),
        ((250, 220, 120), (255, 240, 176)),
        ((200, 150, 240), (224, 190, 250)),
        ((240, 120, 120), (252, 164, 156)),
    )
    posicoes = (
        (-20, 2), (-13, 0), (-6, 4), (1, 1), (8, 3), (15, 0),
        (-16, 6), (-1, 6), (12, 6), (20, 4),
    )
    for i, (ox, dy) in enumerate(posicoes):
        sway = int(round(math.sin(tempo * 1.4 + i + fase)))
        base_y = int(sy) - 8 - dy
        topo = base_y - 7
        x = int(sx) + ox
        pygame.draw.line(surf, (52, 120, 64), (x, base_y), (x + sway, topo), 1)
        pygame.draw.rect(surf, (70, 146, 78), (x + (1 if sway >= 0 else -2), base_y - 3, 2, 2))
        cor, claro = cores[i % 4]
        pygame.draw.rect(surf, cor, (x + sway - 2, topo - 4, 5, 5))
        pygame.draw.rect(surf, claro, (x + sway - 2, topo - 4, 5, 1))
        pygame.draw.rect(surf, (250, 246, 210), (x + sway, topo - 2, 1, 1))


def _bandeira_pixel() -> pygame.Surface:
    chave = ("bandeira", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((44, 86), pygame.SRCALPHA)
    # base de pedra
    pygame.draw.rect(img, (76, 72, 78), (10, 78, 24, 7))
    pygame.draw.rect(img, (112, 108, 114), (10, 78, 24, 2))
    pygame.draw.rect(img, (48, 46, 52), (10, 78, 24, 7), 1)
    # mastro
    pygame.draw.rect(img, (92, 70, 48), (20, 10, 4, 70))
    pygame.draw.rect(img, (132, 104, 70), (20, 10, 1, 70))
    pygame.draw.rect(img, (58, 42, 28), (20, 10, 4, 70), 1)
    # pináculo dourado
    pygame.draw.rect(img, (228, 190, 108), (19, 6, 6, 5))
    pygame.draw.rect(img, (250, 226, 150), (20, 6, 2, 3))
    pygame.draw.rect(img, (150, 118, 60), (19, 6, 6, 5), 1)
    _cache[chave] = img
    return img


def desenhar_bandeira(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _bandeira_pixel()
    cor = tuple(getattr(d, "cor", None) or (196, 150, 90))
    claro = tuple(min(255, c + 44) for c in cor)
    escuro = tuple(max(0, c - 60) for c in cor)
    fase = getattr(d, "fase", 0.0)
    sombra(surf, sx, sy - 1, 9, 4, 60)
    surf.blit(img, (int(sx) - 21, int(sy) - 84))

    sway = math.sin(tempo * 2 + fase) * 3
    x0, y0 = int(sx) + 2, int(sy) - 74
    # bandeira com entalhe na ponta (rabo de andorinha)
    pts = [
        (x0, y0), (x0 + 32, int(y0 - 3 + sway)),
        (x0 + 25, int(y0 + 9 + sway)), (x0 + 32, int(y0 + 21 + sway)),
        (x0, y0 + 23),
    ]
    pygame.draw.polygon(surf, cor, pts)
    pygame.draw.polygon(surf, claro, [pts[0], pts[1], (pts[1][0] - 4, pts[1][1] + 10), (x0 + 3, y0 + 11)])
    # dobras
    pygame.draw.line(surf, escuro, (x0 + 6, y0 + 6), (x0 + 26, int(y0 + 3 + sway)), 1)
    pygame.draw.line(surf, escuro, (x0 + 5, y0 + 15), (x0 + 24, int(y0 + 13 + sway)), 1)
    pygame.draw.polygon(surf, escuro, pts, 1)
    # emblema
    pygame.draw.rect(surf, (250, 226, 150), (x0 + 12, y0 + 8, 3, 3))
    pygame.draw.rect(surf, (255, 244, 196), (x0 + 13, y0 + 8, 1, 1))


def _bigorna_pixel() -> pygame.Surface:
    chave = ("bigorna", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((50, 46), pygame.SRCALPHA)
    metal, claro, escuro, contorno = (104, 100, 108), (148, 144, 152), (62, 60, 68), (36, 34, 42)
    # base de pedra
    pygame.draw.rect(img, (64, 60, 62), (5, 36, 40, 9))
    pygame.draw.rect(img, (96, 92, 94), (5, 36, 40, 2))
    pygame.draw.rect(img, (40, 38, 40), (5, 36, 40, 9), 1)
    # cintura
    pygame.draw.rect(img, escuro, (18, 27, 14, 10))
    pygame.draw.rect(img, metal, (19, 27, 12, 9))
    # corpo
    pygame.draw.rect(img, metal, (7, 15, 34, 13))
    # chifre
    pygame.draw.polygon(img, metal, [(41, 15), (49, 21), (41, 26)])
    # face superior
    pygame.draw.rect(img, claro, (7, 15, 34, 3))
    pygame.draw.rect(img, contorno, (7, 15, 34, 13), 1)
    pygame.draw.polygon(img, contorno, [(41, 15), (49, 21), (41, 26)], 1)
    # talão
    pygame.draw.rect(img, escuro, (4, 20, 4, 8))
    pygame.draw.rect(img, contorno, (4, 20, 4, 8), 1)
    _cache[chave] = img
    return img


def desenhar_bigorna(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _bigorna_pixel()
    fase = getattr(d, "fase", 0.0)
    sombra(surf, sx, sy - 2, 24, 8, 75)
    surf.blit(img, (int(sx) - 25, int(sy) - 43))
    # brasas na bigorna
    for i in range(3):
        brilho = 0.5 + 0.5 * math.sin(tempo * 5 + fase + i * 2.0)
        if brilho > 0.35:
            cor = (250, 160, 70) if brilho > 0.6 else (206, 110, 48)
            pygame.draw.rect(surf, cor, (int(sx) - 5 + i * 6, int(sy) - 27, 2, 2))


def _banca_pixel() -> pygame.Surface:
    chave = ("banca", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((78, 78), pygame.SRCALPHA)
    madeira, claro, escuro, contorno = (126, 88, 56), (162, 118, 76), (78, 52, 36), (44, 30, 22)
    # postes
    for x in (10, 62):
        pygame.draw.rect(img, escuro, (x, 20, 5, 34))
        pygame.draw.rect(img, claro, (x, 20, 2, 34))
        pygame.draw.rect(img, contorno, (x, 20, 5, 34), 1)
    # balcão
    pygame.draw.rect(img, escuro, (6, 48, 66, 28))
    pygame.draw.rect(img, madeira, (7, 47, 64, 28))
    pygame.draw.rect(img, claro, (7, 47, 64, 4))
    for x in (26, 46):
        pygame.draw.line(img, escuro, (x, 52), (x, 74), 1)
    pygame.draw.line(img, escuro, (7, 62), (71, 62), 1)
    pygame.draw.rect(img, contorno, (6, 47, 66, 29), 1)
    # tampo
    pygame.draw.rect(img, claro, (4, 43, 70, 5))
    pygame.draw.rect(img, contorno, (4, 43, 70, 5), 1)
    # toldo listrado com barrado
    pygame.draw.rect(img, (232, 214, 180), (3, 8, 72, 18))
    for i in range(6):
        x = 3 + i * 12
        cor = (176, 72, 74) if i % 2 == 0 else (232, 214, 180)
        if i % 2 == 0:
            pygame.draw.rect(img, cor, (x, 8, 12, 18))
        pygame.draw.rect(img, cor, (x + 1, 26, 10, 2))
        pygame.draw.rect(img, cor, (x + 3, 28, 6, 1))
    pygame.draw.rect(img, contorno, (3, 8, 72, 18), 1)
    # mercadorias
    for x, cor in ((20, (214, 84, 96)), (38, (86, 148, 232)), (56, (236, 202, 96))):
        pygame.draw.rect(img, cor, (x, 36, 7, 7))
        pygame.draw.rect(img, (250, 246, 226), (x + 1, 37, 2, 2))
        pygame.draw.rect(img, contorno, (x, 36, 7, 7), 1)
    _cache[chave] = img
    return img


def desenhar_banca(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _banca_pixel()
    sombra(surf, sx, sy - 2, 30, 10, 80)
    surf.blit(img, (int(sx) - 39, int(sy) - 76))


def _fogueira_pixel() -> pygame.Surface:
    chave = ("fogueira", 0)
    if chave in _cache:
        return _cache[chave]
    img = pygame.Surface((52, 50), pygame.SRCALPHA)
    # cinza
    pygame.draw.ellipse(img, (44, 38, 36), (8, 34, 36, 13))
    # lenha
    pygame.draw.line(img, (56, 38, 26), (13, 37), (39, 29), 4)
    pygame.draw.line(img, (82, 56, 36), (13, 36), (39, 28), 2)
    pygame.draw.line(img, (56, 38, 26), (13, 29), (39, 37), 4)
    pygame.draw.line(img, (74, 50, 32), (13, 28), (39, 36), 2)
    # pedras ao redor, na frente da lenha
    for i in range(8):
        ang = i * math.tau / 8
        px = int(26 + math.cos(ang) * 17)
        py = int(41 + math.sin(ang) * 5)
        pygame.draw.rect(img, (66, 62, 62), (px - 4, py - 3, 8, 6))
        pygame.draw.rect(img, (102, 96, 94), (px - 4, py - 3, 8, 2))
        pygame.draw.rect(img, (36, 32, 32), (px - 4, py - 3, 8, 6), 1)
    _cache[chave] = img
    return img


def _chama_pixel(
    surf: pygame.Surface, cx: int, base: int, altura: int, largura: int,
    tempo: float, fase: float, cor: tuple[int, int, int],
    realce: tuple[int, int, int] | None = None,
) -> None:
    """Chama desenhada linha a linha, para manter a silhueta em degraus."""
    for y in range(base - altura, base + 1):
        f = (base - y) / max(1, altura)
        meia = int(largura * (1.0 - f ** 1.7))
        if meia <= 0:
            continue
        desvio = int(math.sin(tempo * 5.0 + fase + f * 3.0) * 2 * f)
        x0, x1 = cx - meia + desvio, cx + meia + desvio
        pygame.draw.line(surf, cor, (x0, y), (x1, y))
        if realce is not None and meia >= 3:
            pygame.draw.line(surf, realce, (x0 + 1, y), (x0 + max(2, meia // 2), y))


def desenhar_fogueira(surf: pygame.Surface, sx: float, sy: float, d: object, tempo: float) -> None:
    img = _fogueira_pixel()
    fase = getattr(d, "fase", 0.0)
    pulso = 0.5 + 0.5 * math.sin(tempo * 7.0 + fase)
    halo_suave(surf, (sx, sy - 16), 22, (255, 168, 86), 36)
    sombra(surf, sx, sy - 2, 24, 8, 80)
    surf.blit(img, (int(sx) - 26, int(sy) - 46))

    base = int(sy) - 10
    altura = 20 + 7 * pulso
    largura = 11 + 3 * pulso
    cx = int(sx)
    _chama_pixel(surf, cx, base, int(altura), int(largura), tempo, fase, (232, 92, 40))
    _chama_pixel(
        surf, cx, base, int(altura * 0.70), int(largura * 0.62),
        tempo, fase + 1.1, (250, 150, 56), (255, 196, 104),
    )
    _chama_pixel(
        surf, cx, base, int(altura * 0.40), int(largura * 0.32),
        tempo, fase + 2.2, (255, 232, 158),
    )

    # fagulhas
    for i in range(4):
        f = tempo * (1.4 + i * 0.2) + fase + i
        px = int(sx + math.sin(f * 2.2) * 10)
        py = int(sy - 22 - (f % 1.0) * 24)
        pygame.draw.rect(surf, (255, 190, 100), (px, py, 2, 2))
