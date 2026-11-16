"""Chão em pixel art por bioma (experimental).

A Clareira de Lumen e a Vila de Veyra têm superfícies montadas de uma vez (são
pequenas). Os biomas abertos usam *pedaços* de 8x8 tiles gerados sob demanda e
guardados num cache pequeno: pré-renderizar o mundo inteiro em pixel art
custaria dezenas de MB de RAM.

A grama vem do kit **Pixel Art Top Down - Basic** (Cainos, uso livre), em 32x32
ampliada 2x para bater com o TILE de 64 px. Pedra, terra e trilhas são geradas
por código, para não repetir o mesmo tijolo em todo o mapa. Só entra com
**Configurações -> Vídeo -> Arte pixel**.
"""
from __future__ import annotations

import math
import random
from collections import OrderedDict
from dataclasses import dataclass, field

import pygame

import pixel_arte

CENARIO = pixel_arte.CENARIO
TILE = 64
LADO = 8                       # tiles por lado de um pedaço
PEDACO = TILE * LADO           # 512 px
MAX_PEDACOS = 24

GRAMA = ((0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1))
FLORES = ((4, 0), (5, 0), (6, 0), (7, 0), (4, 1), (5, 1))

# (base, claro, escuro)
Paleta = tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]

TOM_CLAREIRA = (196, 224, 188)
PALETA_VEYRA: Paleta = ((186, 152, 114), (212, 180, 138), (158, 126, 92))
PALETA_PRACA_VEYRA: Paleta = ((150, 140, 132), (176, 166, 156), (120, 112, 106))

_folha_cache: pygame.Surface | None = None
_conjuntos: dict[tuple, tuple[list[pygame.Surface], list[pygame.Surface]]] = {}
_superficies: dict[tuple[str, int, int], pygame.Surface] = {}
_pedacos: OrderedDict[tuple[str, int, int, int, int], pygame.Surface] = OrderedDict()


@dataclass(frozen=True)
class Tema:
    """Aparência do chão de um bioma."""

    familia: str = "grama"                      # grama | pedra | terra
    tom: tuple[int, int, int] = (255, 255, 255)  # multiplicado sobre a grama
    luz: tuple[int, int, int] = (0, 0, 0)        # somado depois, para abrir o tom
    paleta: Paleta | None = None                 # usada por pedra/terra
    caminho: Paleta | None = None                # trilha de terra
    detalhe: str = ""                            # flor | musgo
    chance_detalhe: float = 0.08
    brilho: tuple[int, int, int] | None = None
    chance_brilho: float = 0.0


TEMAS: dict[str, Tema] = {
    "floresta": Tema(
        familia="grama", tom=(150, 190, 150), luz=(6, 34, 44),
        caminho=((124, 98, 66), (148, 120, 84), (100, 78, 52)),
        detalhe="flor", chance_detalhe=0.09,
        brilho=(150, 206, 150), chance_brilho=0.03,
    ),
    "ruinas": Tema(
        familia="pedra", paleta=((112, 110, 118), (138, 136, 144), (86, 84, 92)),
        caminho=((104, 100, 100), (124, 120, 120), (84, 80, 82)),
        detalhe="musgo", chance_detalhe=0.12,
        brilho=(120, 178, 130), chance_brilho=0.03,
    ),
    "caverna": Tema(
        familia="pedra", paleta=((62, 54, 84), (84, 74, 110), (44, 38, 62)),
        caminho=((66, 58, 84), (86, 76, 104), (50, 44, 66)),
        brilho=(150, 190, 255), chance_brilho=0.06,
    ),
    "pantano": Tema(
        familia="grama", tom=(110, 130, 110), luz=(0, 14, 22),
        caminho=((110, 92, 64), (132, 112, 80), (88, 72, 50)),
        detalhe="flor", chance_detalhe=0.04,
        brilho=(120, 170, 130), chance_brilho=0.03,
    ),
    "desfiladeiro": Tema(
        familia="pedra", paleta=((72, 60, 64), (94, 78, 82), (52, 42, 46)),
        caminho=((82, 70, 72), (102, 88, 90), (64, 54, 56)),
        brilho=(240, 140, 90), chance_brilho=0.05,
    ),
    "fenda": Tema(
        familia="pedra", paleta=((74, 56, 98), (96, 74, 126), (54, 40, 74)),
        caminho=((78, 62, 100), (100, 80, 124), (58, 44, 76)),
        brilho=(206, 158, 255), chance_brilho=0.07,
    ),
    "coracao": Tema(
        familia="pedra", paleta=((148, 162, 186), (176, 190, 212), (120, 134, 158)),
        caminho=((140, 154, 178), (164, 178, 200), (116, 130, 152)),
        brilho=(236, 248, 255), chance_brilho=0.06,
    ),
    "veyra": Tema(
        familia="terra", paleta=PALETA_VEYRA,
        caminho=((176, 144, 108), (200, 170, 130), (150, 120, 88)),
        brilho=(150, 138, 110), chance_brilho=0.03,
    ),
}


@dataclass
class Bioma:
    """Região do mundo com chão de um tema e suas trilhas (em pixels)."""

    nome: str
    rect: pygame.Rect
    caminhos: tuple[tuple[tuple[float, float], ...], ...] = field(default_factory=tuple)
    largura_caminho: float = 2.1 * TILE


# ------------------------------------------------------------------ tiles
def _folha() -> pygame.Surface:
    global _folha_cache
    if _folha_cache is None:
        _folha_cache = pygame.image.load(str(CENARIO / "tileset_grass.png")).convert_alpha()
    return _folha_cache


def _recortar(coluna: int, linha: int) -> pygame.Surface:
    folha = _folha()
    tile = folha.subsurface(pygame.Rect(coluna * 32, linha * 32, 32, 32)).copy()
    return pygame.transform.scale(tile, (TILE, TILE))


def _tingir(tile: pygame.Surface, tema: Tema) -> pygame.Surface:
    novo = tile.copy()
    novo.fill((*tema.tom, 255), special_flags=pygame.BLEND_RGBA_MULT)
    if tema.luz != (0, 0, 0):
        novo.fill((*tema.luz, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return novo


def _tile_procedural(rnd: random.Random, paleta: Paleta, tipo: str) -> pygame.Surface:
    base, claro, escuro = paleta
    img = pygame.Surface((32, 32))
    img.fill(base)
    if tipo == "terra":
        for _ in range(6):
            x, y = rnd.randrange(-4, 32), rnd.randrange(-4, 32)
            w, h = rnd.randrange(4, 11), rnd.randrange(2, 5)
            pygame.draw.ellipse(img, rnd.choice((claro, escuro)), (x, y, w, h))
        for _ in range(26):
            img.set_at((rnd.randrange(32), rnd.randrange(32)), rnd.choice((claro, escuro)))
        for _ in range(3):
            x, y = rnd.randrange(2, 28), rnd.randrange(2, 28)
            pygame.draw.rect(img, escuro, (x, y, 3, 2))
            img.set_at((x, y), claro)
    else:
        # placas de rocha com lascas, sem formar grade
        for _ in range(4):
            x, y = rnd.randrange(0, 24), rnd.randrange(0, 24)
            w, h = rnd.randrange(6, 14), rnd.randrange(5, 11)
            pygame.draw.polygon(img, rnd.choice((claro, escuro)), [
                (x, y + h // 2), (x + w // 3, y), (x + w, y + h // 4),
                (x + w - 2, y + h), (x + 2, y + h - 2),
            ])
        for _ in range(22):
            img.set_at((rnd.randrange(32), rnd.randrange(32)), rnd.choice((claro, escuro)))
        for _ in range(2):
            x, y = rnd.randrange(2, 24), rnd.randrange(2, 26)
            pygame.draw.line(
                img, escuro, (x, y), (x + rnd.randrange(3, 9), y + rnd.randrange(-3, 4)),
            )
    return pygame.transform.scale(img, (TILE, TILE))


def _conjunto(tema: Tema) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
    """(chão, detalhes) já no tom do bioma. Índice 0 do chão é o tile base."""
    if tema.familia == "grama":
        chave: tuple = ("grama", tema.tom, tema.luz)
    else:
        chave = (tema.familia, tema.paleta)
    if chave in _conjuntos:
        return _conjuntos[chave]

    if tema.familia == "grama":
        chao = [_tingir(_recortar(c, lin), tema) for c, lin in GRAMA]
        detalhes = [_tingir(_recortar(c, lin), tema) for c, lin in FLORES]
    else:
        assert tema.paleta is not None
        rnd = random.Random(f"{tema.familia}:{tema.paleta}")
        chao = [_tile_procedural(rnd, tema.paleta, tema.familia) for _ in range(6)]
        detalhes = []
    _conjuntos[chave] = (chao, detalhes)
    return chao, detalhes


def _musgo(paleta: Paleta) -> list[pygame.Surface]:
    """Pedra com manchas verdes, usada nas Ruínas."""
    chave: tuple = ("musgo", paleta)
    if chave in _conjuntos:
        return _conjuntos[chave][0]
    rnd = random.Random(f"musgo:{paleta}")
    tiles = []
    for _ in range(4):
        img = _tile_procedural(rnd, paleta, "pedra")
        for _ in range(5):
            x, y = rnd.randrange(0, 26), rnd.randrange(0, 28)
            pygame.draw.rect(img, (86, 128, 82), (x, y, rnd.randrange(3, 8), rnd.randrange(2, 4)))
            pygame.draw.rect(img, (108, 154, 96), (x, y, 3, 2))
        tiles.append(img)
    _conjuntos[chave] = (tiles, [])
    return tiles


# ------------------------------------------------------------------ desenho
def _esfumar(surf: pygame.Surface, borda: int = 56) -> None:
    """Apaga as bordas aos poucos para o chão entrar no bioma vizinho."""
    largura, altura = surf.get_size()
    mascara = pygame.Surface((largura, altura), pygame.SRCALPHA)
    mascara.fill((255, 255, 255, 255))
    for i in range(borda):
        alpha = int(255 * (i / borda) ** 1.6)
        pygame.draw.rect(
            mascara, (255, 255, 255, alpha),
            (i, i, largura - 2 * i, altura - 2 * i), 1,
        )
    surf.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


def _preencher(
    surf: pygame.Surface,
    rnd: random.Random,
    chao: list[pygame.Surface],
    detalhes: list[pygame.Surface],
    chance_detalhe: float,
    chance_variante: float,
) -> None:
    largura, altura = surf.get_size()
    variantes = chao[1:] or chao
    for y in range(0, altura, TILE):
        for x in range(0, largura, TILE):
            if detalhes and rnd.random() < chance_detalhe:
                tile = rnd.choice(detalhes)
            elif rnd.random() < chance_variante:
                tile = rnd.choice(variantes)
            else:
                tile = chao[0]
            surf.blit(tile, (x, y))


def superficie(largura: int, altura: int) -> pygame.Surface:
    """Chão completo da Clareira, com praça de pedras e bordas esfumadas."""
    chave = ("clareira", largura, altura)
    if chave in _superficies:
        return _superficies[chave]

    rnd = random.Random(20261026)
    tema = Tema(familia="grama", tom=TOM_CLAREIRA)
    chao, flores = _conjunto(tema)
    pedra, _ = _conjunto(Tema(familia="pedra", paleta=PALETA_PRACA_VEYRA))

    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    _preencher(surf, rnd, chao, flores, 0.08, 0.22)

    # praça de pedras no centro
    cx, cy = largura // 2, altura // 2
    rx, ry = int(largura * 0.34), int(altura * 0.30)
    for y in range(0, altura, TILE):
        for x in range(0, largura, TILE):
            px, py = x + TILE / 2, y + TILE / 2
            dist = ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2
            if dist > 1.12:
                continue
            surf.blit(rnd.choice(pedra), (x, y))

    # caminho horizontal atravessando a clareira
    for x in range(0, largura, TILE):
        for y in (cy - TILE, cy + TILE):
            surf.blit(rnd.choice(pedra), (x, y))

    _esfumar(surf, 56)
    _superficies[chave] = surf
    return surf


def superficie_vila(largura: int, altura: int) -> pygame.Surface:
    """Chão da Vila de Veyra: terra batida com praça de pedra no centro."""
    chave = ("veyra", largura, altura)
    if chave in _superficies:
        return _superficies[chave]

    rnd = random.Random(20261027)
    chao, _ = _conjunto(TEMAS["veyra"])
    pedra, _ = _conjunto(Tema(familia="pedra", paleta=PALETA_PRACA_VEYRA))

    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    _preencher(surf, rnd, chao, [], 0.0, 0.34)

    cx, cy = largura // 2, altura // 2
    raio = min(largura, altura) * 0.46
    for y in range(0, altura, TILE):
        for x in range(0, largura, TILE):
            px, py = x + TILE / 2, y + TILE / 2
            if math.hypot(px - cx, py - cy) > raio:
                continue
            surf.blit(rnd.choice(pedra), (x, y))

    _esfumar(surf, 44)
    _superficies[chave] = surf
    return surf


# ------------------------------------------------------------------ biomas
def _camada_caminho(
    bioma: Bioma, coluna: int, linha: int, tema: Tema,
) -> pygame.Surface | None:
    """Estrada contínua, desenhada em 1/4 da resolução e ampliada 4x."""
    if tema.caminho is None or not bioma.caminhos:
        return None
    base, claro, escuro = tema.caminho
    x0, y0 = coluna * PEDACO, linha * PEDACO
    baixa = pygame.Surface((PEDACO // 4, PEDACO // 4), pygame.SRCALPHA)
    largura = max(3, int(bioma.largura_caminho / 4))
    desenhou = False
    for pontos in bioma.caminhos:
        pts = [((px - x0) / 4.0, (py - y0) / 4.0) for px, py in pontos]
        if len(pts) < 2:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) < -largura or min(xs) > baixa.get_width() + largura:
            continue
        if max(ys) < -largura or min(ys) > baixa.get_height() + largura:
            continue
        for cor, esp in ((escuro, largura), (base, max(2, largura - 3)), (claro, max(1, largura // 3))):
            pygame.draw.lines(baixa, cor, False, pts, esp)
            for px, py in pts:
                pygame.draw.circle(baixa, cor, (int(px), int(py)), esp // 2)
        desenhou = True
    if not desenhou:
        return None

    # grãos de terra para a estrada não ficar chapada
    rnd = random.Random(f"estrada:{bioma.nome}:{coluna}:{linha}")
    largura_baixa, altura_baixa = baixa.get_size()
    for _ in range(120):
        x, y = rnd.randrange(largura_baixa), rnd.randrange(altura_baixa)
        if baixa.get_at((x, y)).a == 0:
            continue
        baixa.set_at((x, y), rnd.choice((base, claro, escuro)))
    return pygame.transform.scale(baixa, (PEDACO, PEDACO))


def _gerar_pedaco(bioma: Bioma, coluna: int, linha: int) -> pygame.Surface:
    tema = TEMAS[bioma.nome]
    chao, detalhes = _conjunto(tema)
    if tema.detalhe == "musgo" and tema.paleta is not None:
        detalhes = _musgo(tema.paleta)
    elif tema.detalhe != "flor":
        detalhes = []

    surf = pygame.Surface((PEDACO, PEDACO))
    rnd = random.Random(f"{bioma.nome}:{coluna}:{linha}")
    base_x, base_y = coluna * PEDACO, linha * PEDACO

    for j in range(LADO):
        for i in range(LADO):
            tx, ty = base_x + i * TILE, base_y + j * TILE
            if not bioma.rect.colliderect((tx, ty, TILE, TILE)):
                continue
            if detalhes and rnd.random() < tema.chance_detalhe:
                tile = rnd.choice(detalhes)
            elif rnd.random() < 0.32:
                tile = rnd.choice(chao[1:] or chao)
            else:
                tile = chao[0]
            surf.blit(tile, (i * TILE, j * TILE))

    estrada = _camada_caminho(bioma, coluna, linha, tema)
    if estrada is not None:
        surf.blit(estrada, (0, 0))

    if tema.brilho is not None and tema.chance_brilho > 0.0:
        for j in range(LADO):
            for i in range(LADO):
                if rnd.random() < tema.chance_brilho:
                    x = i * TILE + 4 * rnd.randrange(0, 16)
                    y = j * TILE + 4 * rnd.randrange(0, 16)
                    surf.fill(tema.brilho, (x, y, 4, 4))
    return surf


def _obter_pedaco(bioma: Bioma, coluna: int, linha: int) -> pygame.Surface:
    chave = (
        bioma.nome, bioma.rect.left, bioma.rect.top,
        bioma.rect.w, bioma.rect.h, coluna, linha,
    )
    img = _pedacos.get(chave)
    if img is None:
        img = _gerar_pedaco(bioma, coluna, linha)
        _pedacos[chave] = img
        while len(_pedacos) > MAX_PEDACOS:
            _pedacos.popitem(last=False)
    else:
        _pedacos.move_to_end(chave)
    return img


def desenhar(surf: pygame.Surface, camera: object, bioma: Bioma) -> None:
    """Desenha só os pedaços visíveis do bioma, recortados no retângulo dele."""
    largura, altura = surf.get_size()
    ox, oy = camera.aplicar((0.0, 0.0))
    # Só os pedaços que encostam na tela: pedir vizinhos de margem estourava o
    # cache (24 pedaços) e obrigava a regerar tudo a cada quadro.
    x0 = max(bioma.rect.left, int(-ox))
    x1 = min(bioma.rect.right, int(-ox) + largura)
    y0 = max(bioma.rect.top, int(-oy))
    y1 = min(bioma.rect.bottom, int(-oy) + altura)
    if x1 <= x0 or y1 <= y0:
        return

    tela = pygame.Rect(int(bioma.rect.left + ox), int(bioma.rect.top + oy), bioma.rect.w, bioma.rect.h)
    anterior = surf.get_clip()
    # respeita um clip que já esteja ativo (mini-mapas, transições etc.)
    recorte = tela.clip(anterior)
    if recorte.width <= 0 or recorte.height <= 0:
        return

    surf.set_clip(recorte)
    try:
        for linha in range(y0 // PEDACO, (y1 - 1) // PEDACO + 1):
            for coluna in range(x0 // PEDACO, (x1 - 1) // PEDACO + 1):
                img = _obter_pedaco(bioma, coluna, linha)
                surf.blit(img, (int(coluna * PEDACO + ox), int(linha * PEDACO + oy)))
    finally:
        surf.set_clip(anterior)


def limpar_cache() -> None:
    """Usado pelos testes e ao trocar de mundo."""
    _pedacos.clear()
