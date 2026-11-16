"""Mapa, biomas, colisão, decoração e zonas de spawn."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Sequence

import pygame

import pixel_agua
import pixel_arte
import pixel_props
import pixel_terreno
from settings import (
    ALTURA, LARGURA, MUNDO_ALTURA,
    MUNDO_LARGURA, TILE, VERDE,
)
from npc import NPC
from utils import Camera, clamp, distancia, halo_suave, lerp, sombra

QUALIDADE_ARTE = 1.0


# --------------------------------------------------------------------------
# estruturas
# --------------------------------------------------------------------------


@dataclass
class Obstaculo:
    tipo: str  # "rect" | "circle" | "ellipse"
    rect: pygame.Rect | None = None
    x: float = 0.0
    y: float = 0.0
    raio: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    # None = vale nos dois modos; True = só na arte pixel; False = só no vetor.
    pixel: bool | None = None
    bounds: pygame.Rect = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Caixa envolvente, para descartar obstáculos distantes sem teste exato."""
        if self.tipo == "rect" and self.rect is not None:
            self.bounds = self.rect.copy()
        elif self.tipo == "circle":
            r = int(self.raio) + 1
            self.bounds = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)
        elif self.tipo == "ellipse":
            rx, ry = int(self.rx) + 1, int(self.ry) + 1
            self.bounds = pygame.Rect(int(self.x) - rx, int(self.y) - ry, rx * 2, ry * 2)
        else:
            self.bounds = pygame.Rect(0, 0, 0, 0)

    def colide_rect(self, r: pygame.Rect) -> bool:
        if self.tipo == "rect" and self.rect is not None:
            return r.colliderect(self.rect)
        if self.tipo == "circle":
            px = clamp(self.x, r.left, r.right)
            py = clamp(self.y, r.top, r.bottom)
            return (px - self.x) ** 2 + (py - self.y) ** 2 < self.raio ** 2
        if self.tipo == "ellipse":
            rx = max(1.0, self.rx)
            ry = max(1.0, self.ry)
            for px, py in (
                (r.left, r.top), (r.right, r.top),
                (r.left, r.bottom), (r.right, r.bottom),
                (r.centerx, r.centery),
            ):
                if ((px - self.x) / rx) ** 2 + ((py - self.y) / ry) ** 2 <= 1.0:
                    return True
            return r.left <= self.x <= r.right and r.top <= self.y <= r.bottom
        return False

    def colide_circulo(self, cx: float, cy: float, cr: float) -> bool:
        if self.tipo == "rect" and self.rect is not None:
            px = clamp(cx, self.rect.left, self.rect.right)
            py = clamp(cy, self.rect.top, self.rect.bottom)
            return (px - cx) ** 2 + (py - cy) ** 2 < cr ** 2
        if self.tipo == "circle":
            return (cx - self.x) ** 2 + (cy - self.y) ** 2 < (cr + self.raio) ** 2
        if self.tipo == "ellipse":
            rx = max(1.0, self.rx + cr)
            ry = max(1.0, self.ry + cr)
            return ((cx - self.x) / rx) ** 2 + ((cy - self.y) / ry) ** 2 <= 1.0
        return False


@dataclass
class Zona:
    nome: str
    rect: pygame.Rect
    nivel_min: int
    nivel_max: int
    inimigos: list[str]
    max_inimigos: int
    boss: str | None
    chance_boss: float
    cor: tuple[int, int, int]
    seguro: bool = False

    def sortear_nivel(self) -> int:
        return random.randint(self.nivel_min, self.nivel_max)


@dataclass
class Decoracao:
    tipo: str
    x: float
    y: float
    escala: float = 1.0
    variacao: int = 0
    fase: float = 0.0
    cor: tuple[int, int, int] = VERDE
    solido: bool = False
    # None = aparece nos dois modos; True = só na arte pixel; False = só no vetor.
    pixel: bool | None = None

    def desenhar(self, surf: pygame.Surface, camera: Camera, tempo: float) -> None:
        if self.pixel is not None and self.pixel != pixel_arte.ATIVO:
            return
        sx, sy = camera.aplicar((self.x, self.y))
        if sx < -220 or sy < -260 or sx > LARGURA + 220 or sy > ALTURA + 160:
            return
        desenhar = {
            "arvore": _arvore,
            "rocha": _rocha,
            "ruina": _ruina,
            "cristal": _cristal,
            "estatua": _estatua,
            "altar": _altar,
            "estalagmite": _estalagmite,
            "cogumelo": _cogumelo,
            "bandeira": _bandeira,
            "casa": _casa,
            "fonte": _fonte,
            "obelisco": _obelisco,
            "tronco": _tronco,
            "arvore_morta": _arvore_morta,
            "junco": _junco,
            "lampiao": _lampiao,
            "banco": _banco,
            "jardim": _jardim,
            "placa": _placa,
            "caixote": _caixote,
            "barril": _barril,
            "vaso": _vaso,
            "bigorna": _bigorna,
            "banca": _banca,
            "fogueira": _fogueira,
            "arbusto": _arbusto,
            "arco": _arco,
            "muro": _muro,
        }.get(self.tipo)
        if desenhar:
            desenhar(surf, sx, sy, self, tempo)


# --------------------------------------------------------------------------
# desenho das decorações
# --------------------------------------------------------------------------


def _bloco_elevado(
    surf: pygame.Surface, r: pygame.Rect, cor: tuple[int, int, int],
    *, raio: int = 4, com_sombra: bool = True, alpha_sombra: int = 125,
) -> None:
    """Massa de pedra com sombra de contato e contorno escuro.

    É o que faz a parede ler como obstáculo e não como textura de chão:
    sombra deslocada embaixo, topo iluminado e contorno próprio.
    """
    if com_sombra:
        sombra(surf, r.centerx, r.bottom + 3, r.width * 0.68 + 6, max(6, r.height * 0.13), alpha_sombra)
    pygame.draw.rect(surf, (44, 42, 50), r.inflate(7, 7), border_radius=raio + 2)
    pygame.draw.rect(surf, cor, r, border_radius=raio)
    altura_topo = max(3, int(r.height * 0.2))
    pygame.draw.rect(
        surf, tuple(min(255, c + 30) for c in cor),
        (r.x + 2, r.y + 2, max(1, r.width - 4), altura_topo),
        border_radius=max(2, raio - 1),
    )
    pygame.draw.rect(surf, (38, 36, 44), r, 2, border_radius=raio)


def _arvore(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_arvore(surf, sx, sy, d)
        return
    e = d.escala
    if QUALIDADE_ARTE < 0.6:
        sombra(surf, sx, sy - 4 * e, 34 * e, 12 * e, 90)
        tronco = pygame.Rect(int(sx - 7 * e), int(sy - 56 * e), int(14 * e), int(56 * e))
        pygame.draw.rect(surf, (86, 58, 40), tronco, border_radius=int(4 * e))
        pygame.draw.rect(surf, (56, 38, 26), tronco, width=max(1, int(2 * e)), border_radius=int(4 * e))
        sway = math.sin(tempo * 1.1 + d.fase) * 2.5 * e
        for ox, oy, r, cor in (
            (0, -92, 38, (28, 74, 48)),
            (-24, -80, 28, (38, 100, 62)),
            (24, -82, 27, (38, 100, 62)),
        ):
            pygame.draw.circle(surf, cor, (int(sx + ox * e + sway), int(sy + oy * e)), int(r * e))
        return
    sway = math.sin(tempo * 1.1 + d.fase) * 2.8 * e
    sombra(surf, sx, sy - 4 * e, 38 * e, 14 * e, 85)

    # raízes
    for ox, largura in ((-12, 4), (-5, 3), (5, 3), (12, 4)):
        pygame.draw.line(
            surf, (62, 42, 28),
            (sx + ox * e, sy - 2 * e), (sx + ox * 1.9 * e, sy - 9 * e),
            max(1, int(largura * e)),
        )

    # tronco com casca
    tronco = pygame.Rect(int(sx - 8 * e), int(sy - 60 * e), int(16 * e), int(60 * e))
    pygame.draw.rect(surf, (94, 64, 44), tronco, border_radius=int(5 * e))
    pygame.draw.rect(surf, (58, 38, 26), tronco, width=max(1, int(2 * e)), border_radius=int(5 * e))
    for ox, cor in ((-3, (72, 48, 32)), (1, (112, 80, 54)), (4, (78, 52, 36))):
        pygame.draw.line(
            surf, cor,
            (sx + ox * e, sy - 54 * e), (sx + ox * 1.1 * e, sy - 10 * e), 1,
        )
    pygame.draw.ellipse(surf, (66, 92, 56), (int(sx - 9 * e), int(sy - 12 * e), int(18 * e), int(7 * e)))

    # galhos
    for gx, gy, tx, ty in (
        (sx - 2 * e, sy - 44 * e, sx - 27 * e, sy - 72 * e),
        (sx + 3 * e, sy - 50 * e, sx + 25 * e, sy - 78 * e),
        (sx - 1 * e, sy - 58 * e, sx - 17 * e, sy - 88 * e),
        (sx + 2 * e, sy - 34 * e, sx + 21 * e, sy - 50 * e),
    ):
        pygame.draw.line(surf, (78, 52, 36), (gx, gy), (tx, ty), max(2, int(3 * e)))
        pygame.draw.line(surf, (120, 86, 58), (gx, gy - 1), (tx, ty - 1), 1)

    # copa em três camadas
    variacao = d.variacao % 4
    centros = [
        (sx + sway, sy - 100 * e, 43 * e),
        (sx - 31 * e + sway * 0.7, sy - 84 * e, 31 * e),
        (sx + 30 * e + sway * 0.7, sy - 87 * e, 32 * e),
        (sx - 8 * e + sway * 0.4, sy - 121 * e, 29 * e),
        (sx + 12 * e + sway * 0.5, sy - 111 * e, 25 * e),
        (sx - 22 * e + sway * 0.5, sy - 108 * e, 24 * e),
    ]
    tons_escuros = [(20, 54, 36), (24, 62, 40), (22, 58, 38)]
    tons_medios = [(38, 100, 62), (44, 112, 68), (50, 122, 74)]
    tons_claros = [(76, 160, 96), (88, 174, 104), (66, 148, 88)]
    for i, (cx, cy, r) in enumerate(centros):
        pygame.draw.circle(surf, tons_escuros[i % 3], (int(cx), int(cy)), int(r))
        pygame.draw.circle(surf, tons_medios[(i + variacao) % 3], (int(cx), int(cy)), int(r - 3 * e))
    # cachos de folhas e luz de topo
    for i, (cx, cy, r) in enumerate(centros):
        pygame.draw.circle(
            surf, tons_claros[(i + variacao) % 3],
            (int(cx - r * 0.22), int(cy - r * 0.28)), int(r * 0.42),
        )
        pygame.draw.circle(
            surf, (116, 190, 112),
            (int(cx - r * 0.36), int(cy - r * 0.42)), int(r * 0.18),
        )
    # folhas soltas / cipós
    for i in range(3):
        ox = (i - 1) * 12 * e + sway
        pygame.draw.line(
            surf, (44, 108, 62),
            (sx + ox, sy - 78 * e), (sx + ox * 1.2, sy - 66 * e), 1,
        )
    # folhas caindo
    for i in range(2):
        fase = (tempo * 0.35 + d.fase + i * 0.5) % 1.0
        px = sx + math.sin(fase * 6 + i) * 24 * e
        py = sy - 70 * e + fase * 58 * e
        pygame.draw.ellipse(
            surf, (120, 178, 92),
            (int(px), int(py), max(2, int(3 * e)), max(1, int(2 * e))),
        )


def _arvore_morta(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_arvore_morta(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy - 3 * e, 30 * e, 11 * e, 80)
    sway = math.sin(tempo * 0.8 + d.fase) * 2.0 * e
    # tronco retorcido
    pts = [
        (sx - 9 * e, sy), (sx - 6 * e, sy - 30 * e), (sx - 10 * e + sway, sy - 58 * e),
        (sx - 4 * e + sway, sy - 76 * e), (sx + 2 * e + sway, sy - 78 * e),
        (sx + 6 * e, sy - 54 * e), (sx + 3 * e, sy - 28 * e), (sx + 9 * e, sy),
    ]
    pygame.draw.polygon(surf, (58, 46, 36), pts)
    pygame.draw.polygon(surf, (34, 28, 24), pts, 2)
    pygame.draw.line(surf, (78, 62, 46), (sx - 2 * e, sy - 8 * e), (sx - 5 * e + sway, sy - 62 * e), max(1, int(2 * e)))
    # galhos secos
    for gx, gy, tx, ty in (
        (sx - 7 * e, sy - 54 * e, sx - 28 * e, sy - 74 * e),
        (sx + 3 * e, sy - 62 * e, sx + 26 * e, sy - 84 * e),
        (sx - 5 * e, sy - 68 * e, sx - 18 * e, sy - 92 * e),
        (sx + 2 * e, sy - 44 * e, sx + 22 * e, sy - 54 * e),
    ):
        pygame.draw.line(surf, (50, 40, 32), (gx, gy), (tx + sway * 0.6, ty), max(1, int(3 * e)))
    # musgo luminoso
    pygame.draw.circle(surf, (86, 132, 74), (int(sx - 6 * e + sway), int(sy - 58 * e)), max(2, int(3 * e)))
    pygame.draw.circle(surf, (128, 178, 96), (int(sx - 7 * e + sway), int(sy - 59 * e)), max(1, int(1.6 * e)))


def _junco(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_junco(surf, sx, sy, d, tempo)
        return
    e = d.escala
    sway = math.sin(tempo * 1.4 + d.fase) * 3.0 * e
    for i in range(5):
        ox = (i - 2) * 4.5 * e
        altura = (16 + (i % 3) * 7) * e
        cor = (74, 104, 58) if i % 2 == 0 else (92, 122, 66)
        pygame.draw.line(surf, cor, (sx + ox, sy), (sx + ox + sway * 0.4, sy - altura), max(1, int(2 * e)))
        if i % 2 == 0:
            pygame.draw.ellipse(
                surf, (118, 92, 52),
                (int(sx + ox + sway * 0.4 - 2 * e), int(sy - altura - 5 * e), int(4 * e), int(9 * e)),
            )


def _tronco(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_tronco(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy - 3 * e, 22 * e, 8 * e, 70)
    pygame.draw.rect(surf, (86, 58, 40), (int(sx - 8 * e), int(sy - 26 * e), int(16 * e), int(26 * e)), border_radius=int(4 * e))
    pygame.draw.circle(surf, (104, 72, 48), (int(sx), int(sy - 26 * e)), int(8 * e))
    pygame.draw.circle(surf, (72, 48, 34), (int(sx), int(sy - 26 * e)), int(8 * e), max(1, int(2 * e)))


def _rocha(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_rocha(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy - 2 * e, 26 * e, 10 * e, 75)
    base = d.variacao % 3
    if base == 0:
        pts = [(sx - 24 * e, sy), (sx - 16 * e, sy - 20 * e), (sx - 4 * e, sy - 30 * e),
               (sx + 12 * e, sy - 26 * e), (sx + 24 * e, sy - 8 * e), (sx + 18 * e, sy)]
    elif base == 1:
        pts = [(sx - 20 * e, sy), (sx - 12 * e, sy - 14 * e), (sx + 2 * e, sy - 24 * e),
               (sx + 18 * e, sy - 18 * e), (sx + 22 * e, sy - 4 * e), (sx + 12 * e, sy)]
    else:
        pts = [(sx - 26 * e, sy), (sx - 18 * e, sy - 24 * e), (sx - 2 * e, sy - 34 * e),
               (sx + 14 * e, sy - 22 * e), (sx + 26 * e, sy - 10 * e), (sx + 20 * e, sy)]
    pygame.draw.polygon(surf, (78, 82, 92), pts)
    pygame.draw.polygon(surf, (52, 56, 66), pts, max(1, int(2 * e)))
    # facetas
    pygame.draw.polygon(surf, (106, 112, 124), [pts[1], pts[2], (sx - 2 * e, sy - 10 * e)])
    pygame.draw.polygon(surf, (94, 100, 112), [pts[2], pts[3], (sx + 6 * e, sy - 12 * e)])
    # rachaduras e brilho
    pygame.draw.line(surf, (46, 50, 60), (sx - 8 * e, sy - 24 * e), (sx + 2 * e, sy - 10 * e), max(1, int(2 * e)))
    pygame.draw.line(surf, (46, 50, 60), (sx + 6 * e, sy - 22 * e), (sx + 14 * e, sy - 12 * e), 1)
    pygame.draw.circle(surf, (120, 126, 138), (int(sx - 6 * e), int(sy - 20 * e)), max(1, int(2 * e)))
    if d.variacao % 2 == 0:
        pygame.draw.ellipse(surf, (58, 108, 66), (int(sx - 14 * e), int(sy - 30 * e), int(20 * e), int(8 * e)))
    # liquen, pedriscos e luz de topo
    for ox, oy, r in ((-18, -2, 3), (14, -3, 2), (7, -1, 2)):
        pygame.draw.circle(surf, (74, 78, 86), (int(sx + ox * e), int(sy + oy * e)), max(1, int(r * e)))
    pygame.draw.line(
        surf, (142, 148, 158),
        (int(pts[1][0] + 3 * e), int(pts[1][1] + 2 * e)),
        (int(pts[2][0] - 2 * e), int(pts[2][1] + 2 * e)), 1,
    )
    pygame.draw.ellipse(surf, (64, 112, 66), (int(sx + 4 * e), int(sy - 26 * e), int(12 * e), int(5 * e)))


def _ruina(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_ruina(surf, sx, sy, d)
        return
    e = d.escala
    if QUALIDADE_ARTE < 0.6:
        sombra(surf, sx, sy - 3 * e, 26 * e, 9 * e, 90)
        altura = 64 * e if d.variacao % 2 == 0 else 42 * e
        bloco = pygame.Rect(int(sx - 14 * e), int(sy - altura), int(28 * e), int(altura))
        pygame.draw.rect(surf, (118, 114, 120), bloco)
        pygame.draw.rect(surf, (66, 64, 72), bloco, max(1, int(2 * e)))
        pygame.draw.ellipse(surf, (58, 106, 66), (int(sx - 16 * e), int(sy - 7 * e), int(24 * e), int(6 * e)))
        return
    if d.variacao % 2 == 0:
        # coluna quebrada
        altura = 74 * e if d.variacao % 4 == 0 else 50 * e
        _bloco_elevado(
            surf, pygame.Rect(int(sx - 15 * e), int(sy - altura), int(30 * e), int(altura)), (126, 122, 126),
        )
        pygame.draw.line(surf, (70, 68, 76), (sx - 6 * e, sy - altura * 0.72), (sx + 8 * e, sy - altura * 0.44), max(1, int(2 * e)))
        pygame.draw.line(surf, (86, 84, 92), (sx - 10 * e, sy - altura * 0.55), (sx - 4 * e, sy - altura * 0.35), 1)
        # capitel caído no chão
        _bloco_elevado(
            surf, pygame.Rect(int(sx - 19 * e), int(sy - 12 * e), int(38 * e), int(10 * e)), (140, 136, 138),
        )
    else:
        # arco de pé
        _bloco_elevado(surf, pygame.Rect(int(sx - 34 * e), int(sy - 66 * e), int(18 * e), int(66 * e)), (118, 114, 120))
        _bloco_elevado(surf, pygame.Rect(int(sx + 16 * e), int(sy - 66 * e), int(18 * e), int(66 * e)), (118, 114, 120))
        _bloco_elevado(
            surf, pygame.Rect(int(sx - 34 * e), int(sy - 78 * e), int(68 * e), int(16 * e)), (130, 126, 130),
            com_sombra=False,
        )
    # musgo
    pygame.draw.ellipse(surf, (54, 104, 64), (int(sx - 18 * e), int(sy - 8 * e), int(26 * e), int(7 * e)))
    # entulho e trepadeiras
    for ox, oy, largura, altura in ((-28, -4, 12, 7), (20, -3, 15, 8), (-4, -2, 9, 5)):
        pygame.draw.rect(
            surf, (96, 92, 98),
            (int(sx + ox * e), int(sy + oy * e), int(largura * e), int(altura * e)),
            border_radius=max(1, int(2 * e)),
        )
        pygame.draw.rect(
            surf, (66, 64, 72),
            (int(sx + ox * e), int(sy + oy * e), int(largura * e), int(altura * e)),
            max(1, int(e)), border_radius=max(1, int(2 * e)),
        )
    pygame.draw.line(surf, (48, 98, 58), (sx - 10 * e, sy - 6 * e), (sx - 14 * e, sy - 30 * e), 1)
    pygame.draw.line(surf, (62, 118, 68), (sx + 8 * e, sy - 4 * e), (sx + 13 * e, sy - 24 * e), 1)
    pygame.draw.circle(surf, (78, 140, 82), (int(sx - 14 * e), int(sy - 30 * e)), max(1, int(2 * e)))


def _arco(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_arco(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy + 2, 52 * e, 13 * e, 120)
    for ox in (-34, 34):
        r = pygame.Rect(int(sx + ox * e - 9 * e), int(sy - 74 * e), int(18 * e), int(74 * e))
        _bloco_elevado(surf, r, (112, 108, 118), com_sombra=False)
        for i in range(1, 5):
            yy = r.top + int(i * r.height / 5)
            pygame.draw.line(surf, (82, 80, 88), (r.left + 2, yy), (r.right - 2, yy), 1)
    # lintel quebrado
    _bloco_elevado(
        surf, pygame.Rect(int(sx - 46 * e), int(sy - 86 * e), int(62 * e), int(14 * e)), (118, 114, 122),
        com_sombra=False,
    )
    # runa suspensa
    pulso = 0.65 + 0.35 * math.sin(tempo * 2.1 + d.fase)
    halo_suave(surf, (sx, sy - 52 * e), 20 * e, (80, 160, 220), alpha=int(50 + 30 * pulso))
    pygame.draw.circle(surf, (120, 200, 240), (int(sx), int(sy - 52 * e)), max(1, int(4 * e)))
    pygame.draw.circle(surf, (170, 230, 255), (int(sx), int(sy - 52 * e)), max(1, int(1.5 * e)))
    pygame.draw.ellipse(surf, (54, 104, 64), (int(sx - 24 * e), int(sy - 8 * e), int(34 * e), int(7 * e)))


def _muro(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_muro(surf, sx, sy, d)
        return
    e = d.escala
    w, h = 74 * e, 44 * e
    bloco = pygame.Rect(int(sx - w / 2), int(sy - h), int(w), int(h))
    _bloco_elevado(surf, bloco, (108, 104, 112), raio=3)
    # fiadas de tijolo, só na face
    for linha in range(1, 3):
        yy = bloco.top + int(h * linha / 3)
        pygame.draw.line(surf, (62, 60, 68), (bloco.left + 3, yy), (bloco.right - 3, yy), 2)
    for coluna in (1, 2):
        xx = bloco.left + int(w * coluna / 3)
        pygame.draw.line(surf, (62, 60, 68), (xx, bloco.top + 4), (xx, bloco.centery), 2)
    # rachadura e lasca
    pygame.draw.line(
        surf, (50, 48, 56),
        (bloco.left + int(w * 0.2), bloco.top + 6),
        (bloco.left + int(w * 0.32), bloco.bottom - 6), 1,
    )
    pygame.draw.polygon(
        surf, (78, 76, 84),
        [(bloco.right - 10, bloco.top + 2), (bloco.right - 2, bloco.top + 2), (bloco.right - 2, bloco.top + 10)],
    )
    # ameias quebradas no topo
    pygame.draw.ellipse(surf, (54, 104, 64), (int(sx - w / 2), int(sy - 8 * e), int(w * 0.45), int(6 * e)))
    if d.variacao % 2 == 0:
        halo_suave(surf, (sx, sy - h * 0.55), 18 * e, (80, 160, 220), alpha=55)
        pygame.draw.circle(surf, (110, 190, 230), (int(sx), int(sy - h * 0.55)), max(1, int(4 * e)), 1)


def _cristal(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_cristal(surf, sx, sy, d, tempo)
        return
    e = d.escala
    cor = d.cor
    if QUALIDADE_ARTE < 0.6:
        sombra(surf, sx, sy - 1 * e, 24 * e, 8 * e, 90)
        halo_suave(surf, (sx, sy - 26 * e), 44 * e, cor, 45)
        for ox, altura in ((-10, 42), (0, 58), (10, 38)):
            pts = [
                (sx + (ox - 8) * e, sy),
                (sx + ox * e, sy - altura * e),
                (sx + (ox + 8) * e, sy),
            ]
            pygame.draw.polygon(surf, cor, pts)
            pygame.draw.polygon(surf, (24, 20, 34), pts, max(1, int(2 * e)))
        return
    pulso = 0.75 + 0.25 * math.sin(tempo * 2.2 + d.fase)

    # Sombra de contato forte: ancora a peça no chão.
    sombra(surf, sx, sy - 1 * e, 27 * e, 9 * e, 125)

    # Poça de luz rente ao solo: o cristal ilumina a própria base.
    halo_suave(surf, (sx, sy - 5 * e), 28 * e, cor, alpha=int(38 + 20 * pulso))

    # Brilho ao redor da pedra (antes dos shards, para não lavar a silhueta).
    halo_suave(surf, (sx, sy - 34 * e), 40 * e, cor, alpha=int(42 + 24 * pulso))

    # Shards: a base desce abaixo da linha do chão para ficar enterrada.
    shards = [
        [(sx, sy - 60 * e), (sx - 11 * e, sy - 16 * e), (sx, sy + 7 * e), (sx + 11 * e, sy - 16 * e)],
        [(sx - 18 * e, sy - 36 * e), (sx - 27 * e, sy - 8 * e), (sx - 16 * e, sy + 7 * e), (sx - 9 * e, sy - 18 * e)],
        [(sx + 18 * e, sy - 40 * e), (sx + 10 * e, sy - 16 * e), (sx + 18 * e, sy + 7 * e), (sx + 28 * e, sy - 10 * e)],
    ]
    for pts in shards:
        pygame.draw.polygon(surf, cor, pts)
        claro = tuple(min(255, c + 55) for c in cor)
        pygame.draw.polygon(surf, claro, [pts[0], pts[1], (pts[0][0] + 2 * e, pts[1][1] + 6 * e)])
        pygame.draw.polygon(surf, tuple(max(0, c - 55) for c in cor), pts, max(1, int(2 * e)))

    # Base de rocha: cobre o pé dos shards e dá contato com o terreno.
    pedras = (
        (-18, 3, 13, 7, (58, 53, 74)),
        (-3, 6, 16, 8, (68, 62, 86)),
        (15, 3, 12, 6, (52, 48, 68)),
    )
    for ox, oy, rx, ry, tom in pedras:
        r = pygame.Rect(
            int(sx + (ox - rx) * e), int(sy + (oy - ry) * e),
            int(rx * 2 * e), int(ry * 2 * e),
        )
        pygame.draw.ellipse(surf, tom, r)
        pygame.draw.ellipse(surf, tuple(min(255, c + 26) for c in tom), r, max(1, int(2 * e)))

    # Fragmentos pequenos saindo da base: reforçam a leitura de formação rochosa.
    for ox, oy, h, w in ((-21, 3, 13, 4), (20, 4, 10, 3), (-7, 9, 8, 3)):
        pts = [
            (sx + ox * e, sy + (oy - h) * e),
            (sx + (ox - w) * e, sy + oy * e),
            (sx + (ox + w) * e, sy + oy * e),
        ]
        pygame.draw.polygon(surf, tuple(max(0, c - 30) for c in cor), pts)

    # Pedriscos soltos ao redor, para quebrar a silhueta.
    for ox, oy, r in ((-28, 6, 4), (26, 7, 3), (-12, 10, 3), (12, 11, 2)):
        pygame.draw.circle(surf, (34, 31, 46), (int(sx + ox * e), int(sy + oy * e)), max(1, int(r * e)))


def _estatua(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_estatua(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy - 2 * e, 24 * e, 8 * e, 80)
    pygame.draw.rect(surf, (86, 84, 90), (int(sx - 18 * e), int(sy - 18 * e), int(36 * e), int(18 * e)), border_radius=3)
    pygame.draw.rect(surf, (112, 110, 118), (int(sx - 18 * e), int(sy - 18 * e), int(36 * e), int(4 * e)))
    pygame.draw.rect(surf, (104, 102, 110), (int(sx - 10 * e), int(sy - 56 * e), int(20 * e), int(38 * e)), border_radius=6)
    pygame.draw.circle(surf, (118, 116, 124), (int(sx), int(sy - 62 * e)), int(9 * e))
    pygame.draw.line(surf, (94, 92, 100), (sx - 8 * e, sy - 48 * e), (sx - 18 * e, sy - 40 * e), max(2, int(5 * e)))
    pygame.draw.ellipse(surf, (70, 92, 70), (int(sx - 12 * e), int(sy - 22 * e), int(14 * e), int(6 * e)))
    pygame.draw.ellipse(surf, (70, 92, 70), (int(sx + 2 * e), int(sy - 58 * e), int(8 * e), int(4 * e)))


def _altar(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_altar(surf, sx, sy, d, tempo)
        return
    e = d.escala
    pulso = 0.5 + 0.5 * math.sin(tempo * 6 + d.fase)
    sombra(surf, sx, sy - 2 * e, 18 * e, 7 * e, 80)
    pygame.draw.rect(surf, (76, 74, 84), (int(sx - 16 * e), int(sy - 16 * e), int(32 * e), int(16 * e)), border_radius=3)
    pygame.draw.rect(surf, (100, 98, 110), (int(sx - 16 * e), int(sy - 16 * e), int(32 * e), int(4 * e)))
    pygame.draw.ellipse(surf, (50, 48, 58), (int(sx - 10 * e), int(sy - 24 * e), int(20 * e), int(10 * e)))
    for i in range(3):
        r = (8 - i * 2) * e
        pygame.draw.circle(surf, (90, 170, 250), (int(sx), int(sy - 30 * e - i * 4 * e)), int(r))
    pygame.draw.circle(surf, (215, 242, 255), (int(sx), int(sy - 34 * e)), max(2, int((2 + 2 * pulso) * e)))


def _estalagmite(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_estalagmite(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy - 1 * e, 12 * e, 5 * e, 80)
    pts = [
        (sx - 10 * e, sy), (sx - 4 * e, sy - 50 * e), (sx, sy - 70 * e),
        (sx + 5 * e, sy - 44 * e), (sx + 11 * e, sy),
    ]
    pygame.draw.polygon(surf, (58, 50, 76), [(int(x), int(y)) for x, y in pts])
    pygame.draw.polygon(
        surf, (82, 72, 102),
        [(int(sx - 6 * e), int(sy)), (int(sx), int(sy - 66 * e)), (int(sx + 2 * e), int(sy))],
    )
    pygame.draw.polygon(surf, (36, 30, 48), [(int(x), int(y)) for x, y in pts], 2)


def _cogumelo(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_cogumelo(surf, sx, sy, d, tempo)
        return
    e = d.escala
    cor = d.cor
    pulso = 0.6 + 0.4 * math.sin(tempo * 3 + d.fase)
    sombra(surf, sx, sy - 1 * e, 12 * e, 4 * e, 60)
    for ox, h, r in ((-8, 14, 6), (2, 20, 8), (10, 10, 5)):
        pygame.draw.line(
            surf, (206, 196, 176),
            (sx + ox * e, sy), (sx + ox * e, sy - h * e), max(1, int(2 * e)),
        )
        pygame.draw.ellipse(
            surf, cor,
            (int(sx + (ox - r) * e), int(sy - (h + r * 0.5) * e), int(r * 2 * e), int(r * 1.2 * e)),
        )
        pygame.draw.ellipse(
            surf, (250, 255, 255),
            (int(sx + (ox - r * 0.5) * e), int(sy - (h + r * 0.3) * e), int(r * 0.8 * e), int(r * 0.4 * e)),
        )
    halo_suave(surf, (sx, sy - 18 * e), 26 * e, cor, alpha=int(28 + 22 * pulso))


def _bandeira(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_bandeira(surf, sx, sy, d, tempo)
        return
    e = d.escala
    cor = d.cor
    sombra(surf, sx, sy - 1 * e, 8 * e, 4 * e, 60)
    pygame.draw.line(surf, (90, 70, 50), (sx, sy), (sx, sy - 70 * e), max(2, int(3 * e)))
    sway = math.sin(tempo * 2 + d.fase) * 3 * e
    pts = [
        (sx, sy - 68 * e), (sx + 28 * e, sy - 64 * e + sway),
        (sx + 24 * e, sy - 44 * e + sway), (sx, sy - 48 * e),
    ]
    pygame.draw.polygon(surf, cor, [(int(x), int(y)) for x, y in pts])
    pygame.draw.polygon(surf, (30, 26, 34), [(int(x), int(y)) for x, y in pts], 1)
    pygame.draw.circle(surf, (228, 190, 108), (int(sx), int(sy - 70 * e)), max(2, int(3 * e)))


def _casa(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_casa(surf, sx, sy, d)
        return
    e = d.escala
    if QUALIDADE_ARTE < 0.6:
        sombra(surf, sx, sy - 4 * e, 56 * e, 16 * e, 90)
        parede = pygame.Rect(int(sx - 42 * e), int(sy - 70 * e), int(84 * e), int(70 * e))
        pygame.draw.rect(surf, (206, 188, 154), parede)
        pygame.draw.rect(surf, (110, 88, 68), parede, max(1, int(2 * e)))
        telhado = [(sx - 54 * e, sy - 68 * e), (sx, sy - 112 * e), (sx + 54 * e, sy - 68 * e)]
        pygame.draw.polygon(surf, (156, 68, 62), telhado)
        pygame.draw.polygon(surf, (96, 40, 40), telhado, max(2, int(3 * e)))
        porta = pygame.Rect(int(sx - 10 * e), int(sy - 30 * e), int(20 * e), int(30 * e))
        pygame.draw.rect(surf, (86, 60, 42), porta)
        for ox in (-28, 22):
            pygame.draw.rect(surf, (240, 204, 120), (int(sx + ox * e), int(sy - 48 * e), int(10 * e), int(10 * e)))
        return
    sombra(surf, sx, sy - 4 * e, 58 * e, 18 * e, 85)
    # paredes
    parede = pygame.Rect(int(sx - 44 * e), int(sy - 74 * e), int(88 * e), int(74 * e))
    pygame.draw.rect(surf, (214, 196, 160), parede, border_radius=int(4 * e))
    pygame.draw.rect(surf, (120, 98, 76), parede, max(1, int(2 * e)), border_radius=int(4 * e))
    # madeira
    for i in range(3):
        x = parede.left + 12 * e + i * 26 * e
        pygame.draw.line(surf, (176, 150, 112), (x, parede.top + 6 * e), (x, parede.bottom - 4 * e), max(1, int(2 * e)))
    # telhado
    telhado = [(sx - 56 * e, sy - 70 * e), (sx, sy - 116 * e), (sx + 56 * e, sy - 70 * e)]
    pygame.draw.polygon(surf, (166, 74, 66), telhado)
    pygame.draw.polygon(surf, (104, 44, 42), telhado, max(2, int(3 * e)))
    pygame.draw.polygon(surf, (196, 94, 80), [(sx - 44 * e, sy - 76 * e), (sx, sy - 108 * e), (sx + 6 * e, sy - 96 * e), (sx - 30 * e, sy - 76 * e)])
    # porta
    porta = pygame.Rect(int(sx - 12 * e), int(sy - 42 * e), int(24 * e), int(42 * e))
    pygame.draw.rect(surf, (94, 64, 44), porta, border_top_left_radius=int(10 * e), border_top_right_radius=int(10 * e))
    pygame.draw.circle(surf, (236, 200, 112), (int(sx + 6 * e), int(sy - 20 * e)), max(1, int(3 * e)))
    # janelas
    for wx in (sx - 32 * e, sx + 22 * e):
        janela = pygame.Rect(int(wx), int(sy - 58 * e), int(14 * e), int(14 * e))
        pygame.draw.rect(surf, (250, 214, 120), janela)
        pygame.draw.rect(surf, (92, 70, 52), janela, max(1, int(2 * e)))
        pygame.draw.line(surf, (92, 70, 52), (wx + 7 * e, sy - 58 * e), (wx + 7 * e, sy - 44 * e), max(1, int(2 * e)))
    # base de pedra, telhas, chaminé e floreira
    pygame.draw.rect(
        surf, (116, 112, 108),
        (int(sx - 46 * e), int(sy - 12 * e), int(92 * e), int(12 * e)),
        border_radius=max(1, int(3 * e)),
    )
    for i in range(1, 5):
        f = i / 5.0
        y_telha = sy - 116 * e + 46 * e * f
        pygame.draw.line(
            surf, (122, 52, 50),
            (sx - 52 * e + 52 * e * f, y_telha),
            (sx + 52 * e - 52 * e * f, y_telha), 1,
        )
    chamine = pygame.Rect(int(sx + 24 * e), int(sy - 108 * e), int(13 * e), int(30 * e))
    pygame.draw.rect(surf, (96, 62, 48), chamine)
    pygame.draw.rect(surf, (62, 40, 32), chamine, max(1, int(2 * e)))
    for i in range(3):
        fase = (tempo * 0.35 + i * 0.3) % 1.0
        pygame.draw.circle(
            surf, (150, 150, 156),
            (int(sx + 31 * e + math.sin(fase * 5) * 5 * e), int(sy - 112 * e - fase * 30 * e)),
            max(2, int((4 - i) * e)),
        )
    for wx in (sx - 32 * e, sx + 22 * e):
        pygame.draw.rect(
            surf, (72, 108, 64),
            (int(wx - 2 * e), int(sy - 42 * e), int(18 * e), int(5 * e)),
            border_radius=2,
        )
        for i in range(3):
            pygame.draw.circle(
                surf, (226, 120, 120),
                (int(wx + i * 6 * e), int(sy - 44 * e)), max(1, int(2 * e)),
            )


def _fonte(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_fonte(surf, sx, sy, d, tempo)
        return
    e = d.escala
    sombra(surf, sx, sy - 4 * e, 54 * e, 18 * e, 80)
    pygame.draw.ellipse(surf, (122, 118, 122), (int(sx - 50 * e), int(sy - 34 * e), int(100 * e), int(38 * e)))
    pygame.draw.ellipse(surf, (82, 80, 88), (int(sx - 50 * e), int(sy - 34 * e), int(100 * e), int(38 * e)), max(1, int(3 * e)))
    pygame.draw.ellipse(surf, (58, 128, 168), (int(sx - 40 * e), int(sy - 28 * e), int(80 * e), int(24 * e)))
    for i in range(3):
        ox = math.sin(tempo * 1.4 + i * 2.1) * 12 * e
        pygame.draw.ellipse(surf, (110, 190, 220), (int(sx - 22 * e + ox), int(sy - 24 * e + i * 5 * e), int(24 * e), int(5 * e)))
    pygame.draw.rect(surf, (142, 138, 140), (int(sx - 7 * e), int(sy - 62 * e), int(14 * e), int(36 * e)), border_radius=int(4 * e))
    pygame.draw.circle(surf, (176, 220, 240), (int(sx), int(sy - 66 * e)), int(10 * e))
    pygame.draw.circle(surf, (220, 244, 252), (int(sx - 3 * e), int(sy - 69 * e)), int(4 * e))
    # runas na borda
    for i in range(8):
        ang = i * math.tau / 8
        px = sx + math.cos(ang) * 42 * e
        py = sy - 15 * e + math.sin(ang) * 14 * e
        pygame.draw.polygon(
            surf, (176, 156, 116),
            [(int(px), int(py - 2 * e)), (int(px + 2 * e), int(py)),
             (int(px), int(py + 2 * e)), (int(px - 2 * e), int(py))],
        )
    # jatos d'água
    for i in range(3):
        ang = -math.pi / 2 + (i - 1) * 0.45
        comprimento = (18 + 4 * math.sin(tempo * 3 + i)) * e
        px = sx + math.cos(ang) * comprimento
        py = sy - 66 * e + math.sin(ang) * comprimento
        pygame.draw.line(surf, (190, 232, 246), (int(sx), int(sy - 66 * e)), (int(px), int(py)), 1)
        pygame.draw.circle(surf, (226, 248, 255), (int(px), int(py)), max(1, int(2 * e)))
    # musgo
    pygame.draw.ellipse(surf, (62, 108, 66), (int(sx - 46 * e), int(sy - 6 * e), int(28 * e), int(5 * e)))


def _obelisco(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_obelisco(surf, sx, sy, d, tempo)
        return
    e = d.escala
    pulso = 0.65 + 0.35 * math.sin(tempo * 2.6)
    sombra(surf, sx, sy - 3 * e, 24 * e, 9 * e, 80)
    pygame.draw.rect(surf, (72, 78, 94), (int(sx - 16 * e), int(sy - 12 * e), int(32 * e), int(12 * e)), border_radius=int(3 * e))
    pygame.draw.polygon(surf, (58, 64, 82), [(sx - 12 * e, sy - 10 * e), (sx - 8 * e, sy - 92 * e), (sx + 8 * e, sy - 92 * e), (sx + 12 * e, sy - 10 * e)])
    pygame.draw.polygon(surf, (90, 100, 124), [(sx - 8 * e, sy - 92 * e), (sx + 8 * e, sy - 92 * e), (sx + 3 * e, sy - 84 * e), (sx - 3 * e, sy - 84 * e)])
    cor = (120, 220, 236)
    halo = pygame.Surface((int(46 * e), int(46 * e)), pygame.SRCALPHA)
    pygame.draw.circle(halo, (*cor, int(60 * pulso)), (int(23 * e), int(23 * e)), int(21 * e))
    surf.blit(halo, (int(sx - 23 * e), int(sy - 64 * e)))
    pygame.draw.circle(surf, cor, (int(sx), int(sy - 58 * e)), int(5 * e))
    pygame.draw.line(surf, (170, 240, 250), (sx, sy - 64 * e), (sx, sy - 52 * e), max(1, int(2 * e)))


def _arbusto(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_arbusto(surf, sx, sy, d)
        return
    e = d.escala
    sombra(surf, sx, sy - 1, 20 * e, 6 * e, 55)
    tons = ((44, 112, 68), (56, 132, 78), (68, 150, 86))
    for i, (ox, oy, r) in enumerate(((-9, -10, 13), (8, -12, 14), (0, -20, 15), (12, -4, 10), (-12, -3, 10))):
        pygame.draw.circle(surf, (26, 68, 44), (int(sx + ox * e), int(sy + oy * e)), int(r * e))
        pygame.draw.circle(surf, tons[i % 3], (int(sx + ox * e), int(sy + oy * e)), int((r - 2) * e))
    if d.variacao % 2 == 0:
        for ox, oy in ((-6, -18), (9, -10), (2, -24)):
            pygame.draw.circle(surf, (236, 120, 130), (int(sx + ox * e), int(sy + oy * e)), max(1, int(2 * e)))


def _lampiao(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_lampiao(surf, sx, sy, tempo, d.fase)
        return
    e = d.escala
    pulso = 0.7 + 0.3 * math.sin(tempo * 2.4 + d.fase)
    sombra(surf, sx, sy - 2, 13 * e, 5 * e, 70)
    pygame.draw.rect(surf, (52, 50, 58), (int(sx - 8 * e), int(sy - 6 * e), int(16 * e), int(6 * e)), border_radius=int(2 * e))
    pygame.draw.line(surf, (62, 60, 68), (int(sx), int(sy - 5 * e)), (int(sx), int(sy - 54 * e)), max(2, int(4 * e)))
    halo = pygame.Surface((int(60 * e), int(60 * e)), pygame.SRCALPHA)
    pygame.draw.circle(halo, (250, 206, 120, int(46 * pulso)), (int(30 * e), int(30 * e)), int(27 * e))
    pygame.draw.circle(halo, (255, 232, 170, int(60 * pulso)), (int(30 * e), int(30 * e)), int(15 * e))
    surf.blit(halo, (int(sx - 30 * e), int(sy - 78 * e)))
    pygame.draw.rect(surf, (40, 38, 44), (int(sx - 8 * e), int(sy - 68 * e), int(16 * e), int(18 * e)), border_radius=int(3 * e))
    pygame.draw.rect(surf, (250, 214, 130), (int(sx - 5 * e), int(sy - 65 * e), int(10 * e), int(12 * e)), border_radius=int(2 * e))
    pygame.draw.polygon(surf, (52, 50, 58), [(sx - 10 * e, sy - 68 * e), (sx, sy - 76 * e), (sx + 10 * e, sy - 68 * e)])
    pygame.draw.circle(surf, (255, 246, 210), (int(sx - 1 * e), int(sy - 60 * e)), max(1, int(2 * e)))


def _banco(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_prop("banco", surf, sx, sy)
        return
    e = d.escala
    sombra(surf, sx, sy - 2, 30 * e, 8 * e, 60)
    # pernas
    for ox in (-22, 22):
        pygame.draw.rect(surf, (74, 52, 36), (int(sx + ox * e - 3 * e), int(sy - 16 * e), int(6 * e), int(16 * e)), border_radius=2)
    # assento
    pygame.draw.rect(surf, (52, 36, 26), (int(sx - 28 * e), int(sy - 22 * e), int(56 * e), int(9 * e)), border_radius=3)
    pygame.draw.rect(surf, (150, 104, 64), (int(sx - 27 * e), int(sy - 21 * e), int(54 * e), int(7 * e)), border_radius=3)
    # encosto
    pygame.draw.rect(surf, (52, 36, 26), (int(sx - 28 * e), int(sy - 44 * e), int(56 * e), int(8 * e)), border_radius=3)
    pygame.draw.rect(surf, (138, 94, 58), (int(sx - 27 * e), int(sy - 43 * e), int(54 * e), int(6 * e)), border_radius=3)
    for ox in (-20, 20):
        pygame.draw.line(surf, (74, 52, 36), (sx + ox * e, sy - 38 * e), (sx + ox * e, sy - 22 * e), max(2, int(3 * e)))
    pygame.draw.line(surf, (188, 138, 88), (sx - 24 * e, sy - 19 * e), (sx + 24 * e, sy - 19 * e), 1)


def _jardim(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_jardim(surf, sx, sy, d, tempo)
        return
    e = d.escala
    terra = pygame.Rect(int(sx - 24 * e), int(sy - 10 * e), int(48 * e), int(14 * e))
    pygame.draw.ellipse(surf, (52, 42, 32), terra.inflate(4, 4))
    pygame.draw.ellipse(surf, (104, 76, 50), terra)
    for i in range(7):
        ox = (i - 3) * 6 * e
        oy = math.sin(tempo * 1.4 + i + d.fase) * 1.5 * e
        pygame.draw.line(surf, (56, 130, 70), (sx + ox, sy - 8 * e), (sx + ox, sy - 16 * e + oy), max(1, int(2 * e)))
        cor = ((240, 180, 200), (250, 220, 120), (200, 150, 240), (240, 120, 120))[i % 4]
        pygame.draw.circle(surf, cor, (int(sx + ox), int(sy - 18 * e + oy)), max(1, int(3 * e)))
        pygame.draw.circle(surf, (250, 246, 210), (int(sx + ox), int(sy - 18 * e + oy)), max(1, int(1 * e)))


def _placa(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_prop("placa", surf, sx, sy)
        return
    e = d.escala
    sombra(surf, sx, sy - 1, 16 * e, 5 * e, 60)
    pygame.draw.line(surf, (66, 46, 32), (int(sx), int(sy)), (int(sx), int(sy - 40 * e)), max(3, int(5 * e)))
    pygame.draw.rect(surf, (48, 34, 24), (int(sx - 22 * e), int(sy - 58 * e), int(44 * e), int(20 * e)), border_radius=3)
    pygame.draw.rect(surf, (150, 106, 66), (int(sx - 21 * e), int(sy - 57 * e), int(42 * e), int(18 * e)), border_radius=3)
    # seta
    pygame.draw.polygon(surf, (72, 48, 30), [(sx - 13 * e, sy - 48 * e), (sx + 8 * e, sy - 48 * e), (sx + 8 * e, sy - 53 * e), (sx + 18 * e, sy - 46 * e), (sx + 8 * e, sy - 39 * e), (sx + 8 * e, sy - 44 * e), (sx - 13 * e, sy - 44 * e)])


def _bigorna(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_bigorna(surf, sx, sy, d, tempo)
        return
    e = d.escala
    sombra(surf, sx, sy - 2, 22 * e, 8 * e, 70)
    base = pygame.Rect(int(sx - 18 * e), int(sy - 12 * e), int(36 * e), int(12 * e))
    pygame.draw.rect(surf, (58, 52, 54), base, border_radius=3)
    pygame.draw.rect(surf, (96, 88, 86), base.inflate(-4, -4), border_radius=2)
    pygame.draw.rect(surf, (44, 40, 44), (int(sx - 10 * e), int(sy - 24 * e), int(20 * e), int(12 * e)), border_radius=3)
    pygame.draw.rect(surf, (120, 112, 108), (int(sx - 14 * e), int(sy - 30 * e), int(28 * e), int(8 * e)), border_radius=2)
    for i in range(3):
        pygame.draw.circle(surf, (250, 160, 70), (int(sx - 6 * e + i * 6 * e), int(sy - 18 * e)), 2)


def _banca(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_banca(surf, sx, sy, d, tempo)
        return
    e = d.escala
    sombra(surf, sx, sy - 2, 30 * e, 10 * e, 75)
    # balcão
    pygame.draw.rect(surf, (70, 48, 34), (int(sx - 26 * e), int(sy - 26 * e), int(52 * e), int(26 * e)), border_radius=4)
    pygame.draw.rect(surf, (126, 88, 56), (int(sx - 26 * e), int(sy - 30 * e), int(52 * e), int(8 * e)), border_radius=3)
    # toldo
    for i in range(4):
        cor = (170, 70, 72) if i % 2 == 0 else (226, 206, 170)
        pygame.draw.polygon(
            surf, cor,
            [
                (sx - 30 * e + i * 15 * e, sy - 58 * e),
                (sx - 15 * e + i * 15 * e, sy - 58 * e),
                (sx - 18 * e + i * 15 * e, sy - 42 * e),
                (sx - 33 * e + i * 15 * e, sy - 42 * e),
            ],
        )
    pygame.draw.line(surf, (74, 54, 40), (sx - 28 * e, sy - 58 * e), (sx - 28 * e, sy - 30 * e), 2)
    pygame.draw.line(surf, (74, 54, 40), (sx + 28 * e, sy - 58 * e), (sx + 28 * e, sy - 30 * e), 2)
    # mercadorias
    for ox, cor in ((-14, (232, 82, 96)), (0, (82, 148, 244)), (14, (244, 206, 92))):
        pygame.draw.circle(surf, cor, (int(sx + ox * e), int(sy - 34 * e)), max(2, int(3 * e)))


def _fogueira(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_fogueira(surf, sx, sy, d, tempo)
        return
    e = d.escala
    sombra(surf, sx, sy - 2, 26 * e, 9 * e, 80)
    halo_suave(surf, (sx, sy - 16 * e), 42 * e, (255, 168, 86), 70)
    # pedras ao redor
    for i in range(7):
        ang = i * math.tau / 7
        px = sx + math.cos(ang) * 16 * e
        py = sy - 2 + math.sin(ang) * 5 * e
        pygame.draw.circle(surf, (58, 54, 54), (int(px), int(py)), max(2, int(4 * e)))
    # lenha
    pygame.draw.line(surf, (72, 48, 32), (sx - 12 * e, sy - 2), (sx + 12 * e, sy - 8 * e), max(2, int(4 * e)))
    pygame.draw.line(surf, (88, 58, 36), (sx - 11 * e, sy - 8 * e), (sx + 12 * e, sy - 2), max(2, int(4 * e)))
    # chama
    pulso = 0.5 + 0.5 * math.sin(tempo * 7.0 + d.fase)
    altura = (16 + 6 * pulso) * e
    largura = (10 + 3 * pulso) * e
    pygame.draw.polygon(
        surf, (250, 120, 52),
        [(sx - largura, sy - 6 * e), (sx, sy - 6 * e - altura), (sx + largura, sy - 6 * e)],
    )
    pygame.draw.polygon(
        surf, (255, 194, 92),
        [(sx - largura * 0.55, sy - 6 * e), (sx, sy - 6 * e - altura * 0.68), (sx + largura * 0.55, sy - 6 * e)],
    )
    pygame.draw.polygon(
        surf, (255, 240, 190),
        [(sx - largura * 0.22, sy - 6 * e), (sx, sy - 6 * e - altura * 0.35), (sx + largura * 0.22, sy - 6 * e)],
    )
    # fagulhas
    for i in range(4):
        fase = tempo * (1.4 + i * 0.2) + d.fase + i
        px = sx + math.sin(fase * 2.2) * 10 * e
        py = sy - 18 * e - (fase % 1.0) * 28 * e
        pygame.draw.circle(surf, (255, 190, 100), (int(px), int(py)), max(1, int(1.6 * e)))


def _caixote(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_prop("caixote", surf, sx, sy)
        return
    e = d.escala
    sombra(surf, sx, sy - 2, 18 * e, 6 * e, 65)
    r = pygame.Rect(int(sx - 16 * e), int(sy - 30 * e), int(32 * e), int(30 * e))
    pygame.draw.rect(surf, (48, 34, 24), r.inflate(3, 3), border_radius=3)
    pygame.draw.rect(surf, (150, 106, 64), r, border_radius=3)
    pygame.draw.rect(surf, (116, 78, 46), (int(sx - 14 * e), int(sy - 28 * e), int(28 * e), int(6 * e)), border_radius=2)
    pygame.draw.line(surf, (92, 62, 38), (r.left + 4, r.top + 8), (r.right - 4, r.bottom - 6), max(1, int(2 * e)))
    pygame.draw.line(surf, (92, 62, 38), (r.right - 4, r.top + 8), (r.left + 4, r.bottom - 6), max(1, int(2 * e)))
    for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1)):
        pygame.draw.rect(surf, (78, 82, 92), (r.left + ox * (r.w - 5), r.top + oy * (r.h - 5), 5, 5))


def _barril(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_prop("barril", surf, sx, sy)


def _vaso(surf: pygame.Surface, sx: float, sy: float, d: Decoracao, tempo: float) -> None:
    if pixel_arte.ATIVO:
        pixel_props.desenhar_prop("vaso", surf, sx, sy)


# Lagoas do Pântano de Veyra: centro em tiles e raios em tiles.
LAGOAS_PANTANO: tuple[tuple[float, float, float, float], ...] = (
    (68.0, 7.5, 3.4, 2.2),
    (76.0, 34.5, 3.8, 2.4),
    (80.5, 12.0, 2.9, 2.0),
    (69.6, 33.0, 2.4, 1.8),
    (80.2, 29.5, 2.2, 1.6),
)

# Caminho do pântano, ligando a Caverna à nascente de Veyra.
CAMINHO_PANTANO: tuple[tuple[float, float], ...] = (
    (64.0, 23.0), (68.0, 24.2), (72.0, 22.6), (76.5, 23.8), (80.5, 22.8), (83.0, 23.0),
)


def em_lagoa_pantano(x: float, y: float, folga: float = 0.0) -> bool:
    for cx, cy, rx, ry in LAGOAS_PANTANO:
        rx = max(0.1, rx + folga)
        ry = max(0.1, ry + folga)
        if ((x / TILE - cx) / rx) ** 2 + ((y / TILE - cy) / ry) ** 2 <= 1.0:
            return True
    return False


# --------------------------------------------------------------------------
# mundo
# --------------------------------------------------------------------------

# Clareiras da Floresta de Lumen: centro em tiles e raio em tiles.
CLAREIRAS_FLORESTA: tuple[tuple[float, float, float], ...] = (
    (4.5, 14.0, 3.2),    # Clareira do Lago
    (17.2, 12.6, 3.0),   # Clareira das Pedras
    (5.0, 33.0, 3.4),    # Clareira do Sul
    (16.6, 35.0, 3.0),   # Clareira Leste
)

# Trilhas de terra da floresta: listas de pontos em tiles.
TRILHAS_FLORESTA: tuple[tuple[tuple[float, float], ...], ...] = (
    # praça → margem do lago
    ((9.0, 20.2), (7.4, 17.6), (6.4, 14.2), (6.0, 11.8)),
    # praça → norte da mata (passa a leste do lago)
    ((11.4, 19.4), (11.7, 15.5), (12.2, 11.0), (12.1, 6.0), (11.8, 2.5)),
    # praça → sul da mata
    ((11.8, 26.8), (11.6, 31.0), (12.2, 35.5), (11.8, 40.0), (11.6, 43.2)),
    # praça → trilha principal (leste)
    ((15.0, 21.9), (17.0, 21.2), (19.6, 21.6), (20.8, 22.0)),
    # desvios para as clareiras
    ((10.2, 11.0), (13.0, 11.4), (15.6, 12.2)),
    ((6.4, 14.2), (5.4, 14.1)),
    ((11.6, 31.0), (8.2, 32.4), (5.6, 32.9)),
    ((12.2, 35.5), (14.4, 35.2), (16.0, 35.0)),
)

# Estrada principal: atravessa o mundo inteiro na altura da praça (em tiles).
CAMINHO_PRINCIPAL: tuple[tuple[float, float], ...] = (
    (11.0, 23.0), (16.0, 23.0), (21.0, 22.0), (26.0, 23.0),
    (33.0, 22.0), (39.0, 24.0), (44.0, 22.0), (50.0, 23.0),
    (57.0, 22.0), (62.0, 23.0), (64.0, 23.0), (68.0, 24.2),
    (72.0, 22.6), (76.5, 23.8), (80.5, 22.8), (83.0, 23.0),
    (86.0, 23.0), (90.5, 22.5), (95.0, 23.0), (100.0, 22.5),
    (103.0, 23.0), (107.0, 22.8), (112.0, 23.4),
    (118.0, 22.6), (122.0, 23.0),
)


def _distancia_segmento(ponto: Sequence[float], a: Sequence[float], b: Sequence[float]) -> float:
    """Distância de um ponto ao segmento de reta ab."""
    px, py = float(ponto[0]), float(ponto[1])
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])
    dx, dy = bx - ax, by - ay
    tam = dx * dx + dy * dy
    if tam <= 0.0:
        return math.hypot(px - ax, py - ay)
    f = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / tam))
    return math.hypot(px - (ax + dx * f), py - (ay + dy * f))


def em_clareira_floresta(x: float, y: float, folga: float = 0.0) -> bool:
    for cx, cy, raio in CLAREIRAS_FLORESTA:
        if math.hypot(x - cx * TILE, y - cy * TILE) < (raio + folga) * TILE:
            return True
    return False


def na_trilha_floresta(x: float, y: float, folga: float = 1.1) -> bool:
    for pontos in TRILHAS_FLORESTA:
        for i in range(len(pontos) - 1):
            a = (pontos[i][0] * TILE, pontos[i][1] * TILE)
            b = (pontos[i + 1][0] * TILE, pontos[i + 1][1] * TILE)
            if _distancia_segmento((x, y), a, b) < folga * TILE:
                return True
    return False


class Mundo:
    @property
    def qualidade(self) -> float:
        return self._qualidade

    @qualidade.setter
    def qualidade(self, valor: float) -> None:
        global QUALIDADE_ARTE
        self._qualidade = float(valor)
        QUALIDADE_ARTE = self._qualidade

    def __init__(self) -> None:
        self.largura = MUNDO_LARGURA
        self.altura = MUNDO_ALTURA
        self.tempo = 0.0
        self.obstaculos: list[Obstaculo] = []
        self.decoracoes: list[Decoracao] = []
        self.ambientais: list[dict] = []

        t = TILE
        self.vila = Zona(
            nome="Clareira de Lumen",
            rect=pygame.Rect(7 * t, 18 * t, 9 * t, 10 * t),
            nivel_min=1, nivel_max=1, inimigos=[], max_inimigos=0,
            boss=None, chance_boss=0.0, cor=(126, 196, 138), seguro=True,
        )
        self.vila_veyra = Zona(
            nome="Vila de Veyra",
            rect=pygame.Rect(86 * t, 15 * t, 9 * t, 15 * t),
            nivel_min=1, nivel_max=1, inimigos=[], max_inimigos=0,
            boss=None, chance_boss=0.0, cor=(196, 158, 108), seguro=True,
        )
        self.zonas = [
            Zona(
                nome="Floresta de Lumen",
                rect=pygame.Rect(0, 0, 22 * t, self.altura),
                nivel_min=1, nivel_max=5,
                inimigos=["slime", "goblin", "lobo"],
                max_inimigos=9,
                boss="Rei Slime",
                chance_boss=0.045,
                cor=(62, 138, 88),
            ),
            Zona(
                nome="Ruínas de Aether",
                rect=pygame.Rect(22 * t, 0, 22 * t, self.altura),
                nivel_min=6, nivel_max=10,
                inimigos=["goblin", "wisp", "golem", "morcego", "aranha"],
                max_inimigos=10,
                boss="Golem Ancião",
                chance_boss=0.04,
                cor=(128, 124, 132),
            ),
            Zona(
                nome="Caverna de Cristal",
                rect=pygame.Rect(44 * t, 0, 20 * t, self.altura),
                nivel_min=11, nivel_max=16,
                inimigos=["wisp", "golem", "slime_cristal", "morcego", "elemental_cristal", "serpente"],
                max_inimigos=11,
                boss="Senhor dos Fragmentos",
                chance_boss=0.035,
                cor=(92, 62, 132),
            ),
            Zona(
                nome="Pântano de Veyra",
                rect=pygame.Rect(64 * t, 0, 20 * t, self.altura),
                nivel_min=17, nivel_max=22,
                inimigos=["sapo", "mosquito", "lodo"],
                max_inimigos=10,
                boss="Rainha do Lodo",
                chance_boss=0.035,
                cor=(64, 94, 70),
            ),
            Zona(
                nome="Desfiladeiro de Obsidiana",
                rect=pygame.Rect(84 * t, 0, 20 * t, self.altura),
                nivel_min=23, nivel_max=29,
                inimigos=["golem", "elemental_cristal", "serpente", "escorpiao", "golem_obsidiana"],
                max_inimigos=10,
                boss="Colosso de Obsidiana",
                chance_boss=0.035,
                cor=(92, 56, 62),
            ),
            Zona(
                nome="Fenda do Eclipse",
                rect=pygame.Rect(104 * t, 0, 20 * t, 12 * t),
                nivel_min=38, nivel_max=44,
                inimigos=["sombra_eclipse", "ceifador_espelhado", "serpente_vazio"],
                max_inimigos=8,
                boss="Guardião do Eclipse",
                chance_boss=0.05,
                cor=(80, 48, 104),
            ),
            Zona(
                nome="Coração de Aether",
                rect=pygame.Rect(104 * t, 0, 20 * t, self.altura),
                nivel_min=30, nivel_max=36,
                inimigos=["sentinela_aether", "espectro_aether", "serpente_aether"],
                max_inimigos=10,
                boss="Avatar de Aether",
                chance_boss=0.03,
                cor=(164, 198, 240),
            ),
        ]
        self.spawn_jogador = (11.5 * t, 25.8 * t)
        self.npc = NPC("Mestre Aldrin", 13.55 * t, 25.05 * t)
        self.npcs: list[NPC] = [
            self.npc,
            NPC("Mercadora Sela", 88.2 * t, 21.4 * t, cor=(196, 138, 92), estilo="mercadora"),
            NPC("Ferreiro Durin", 92.0 * t, 24.2 * t, cor=(150, 120, 96), estilo="ferreiro"),
            NPC("Encantadora Yara", 89.0 * t, 26.6 * t, cor=(156, 118, 196), estilo="encantadora"),
        ]
        self.fogueiras: list[tuple[float, float]] = [
            (15.4 * t, 26.6 * t),
            (91.5 * t, 26.2 * t),
            (85.4 * t, 23.2 * t),
            (106.5 * t, 23.2 * t),
            (114.0 * t, 13.5 * t),
        ]
        self.aguas: list[tuple[str, float, float, float, float]] = [
            ("lago", 6.75 * t, 8.6 * t, 3.25 * t, 2.1 * t),
            *[("pantano", cx * t, cy * t, rx * t, ry * t) for cx, cy, rx, ry in LAGOAS_PANTANO],
        ]
        self.grama: list[tuple[float, float, tuple[int, int, int], float, float, str]] = []
        self.detalhes: list[tuple[str, float, float, tuple[int, int, int], float, float]] = []
        self.nevoa: list[tuple[str, float, float, float, float, float]] = []
        self.particulas: list[tuple[str, float, float, float, float, tuple[int, int, int]]] = []
        self.noite = 0.0
        self.qualidade = 1.0
        self._nevoa_overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        self._biomas_pixel: list[pixel_terreno.Bioma] | None = None

        self.terreno = self._gerar_terreno()
        self._gerar_decoracoes()
        self._gerar_grama()
        self._gerar_detalhes()
        self._gerar_ambientais()
        self._gerar_atmosfera()
        self.camada_longe = self._gerar_camada_fundo(777, 30, 30)
        self.camada_perto = self._gerar_camada_fundo(778, 20, 16)

    # ------------------------------------------------------------------ terreno
    def _gerar_terreno(self) -> pygame.Surface:
        t = TILE
        w, h = self.largura, self.altura
        surf = pygame.Surface((w, h))
        rnd = random.Random(20261023)

        # base floresta
        surf.fill((44, 88, 60))
        # manchas amplas de tom, para quebrar a repetição do tapete
        for _ in range(150):
            x = rnd.randrange(0, 22 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(70, 170)
            cor = rnd.choice(((52, 100, 68), (38, 78, 54), (60, 112, 74), (46, 92, 62)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # textura fina da mata
        for _ in range(2600):
            x = rnd.randrange(0, 22 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(7, 26)
            cor = rnd.choice(((48, 96, 64), (40, 80, 56), (54, 104, 68), (36, 74, 52)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # clareiras: manchas abertas de grama clara, com bordas irregulares
        for cx, cy, raio in CLAREIRAS_FLORESTA:
            px, py = int(cx * t), int(cy * t)
            for _ in range(int(raio * 26)):
                ang = rnd.uniform(0, math.tau)
                dist = raio * t * math.sqrt(rnd.random()) * 0.9
                ox = px + math.cos(ang) * dist
                oy = py + math.sin(ang) * dist
                r = rnd.randint(int(t * 0.5), int(t * 1.5))
                cor = rnd.choice(((64, 106, 68), (72, 114, 72), (78, 122, 76), (84, 128, 80)))
                pygame.draw.ellipse(surf, cor, (int(ox - r), int(oy - r * 0.6), r * 2, int(r * 1.2)))
            for _ in range(int(raio * 150)):
                ang = rnd.uniform(0, math.tau)
                dist = raio * t * math.sqrt(rnd.random())
                gx = px + math.cos(ang) * dist
                gy = py + math.sin(ang) * dist
                if rnd.random() < 0.5:
                    pygame.draw.line(surf, rnd.choice(((72, 124, 78), (82, 134, 84), (62, 112, 70))),
                                     (int(gx), int(gy)), (int(gx + rnd.randint(-2, 2)), int(gy - rnd.randint(3, 9))), 1)
                else:
                    pygame.draw.circle(surf, rnd.choice(((236, 224, 128), (244, 190, 208), (222, 242, 240))),
                                       (int(gx), int(gy)), rnd.randint(1, 3))


        # ruínas
        pygame.draw.rect(surf, (78, 76, 82), (22 * t, 0, 22 * t, h))
        for _ in range(900):
            x = rnd.randrange(22 * t, 44 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(16, 70)
            cor = rnd.choice(((80, 78, 84), (74, 72, 78), (84, 82, 88), (70, 68, 74)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # placas de pedra do chão: sem contorno e com pouco contraste, para não
        # competir com os obstáculos (que têm sombra e relevo)
        for gx in range(22, 44):
            for gy in range(0, 44, 2):
                if rnd.random() < 0.5:
                    r = pygame.Rect(gx * t + rnd.randint(-6, 6), gy * t + rnd.randint(-6, 6), t - 4, t - 4)
                    cor = rnd.choice(((84, 82, 88), (79, 77, 83), (88, 86, 90), (76, 74, 80)))
                    pygame.draw.rect(surf, cor, r, border_radius=3)
                    if rnd.random() < 0.3:
                        pygame.draw.line(surf, (71, 70, 75), (r.left + 3, r.bottom - 2), (r.right - 3, r.bottom - 2), 1)
        # rachaduras discretas
        for _ in range(70):
            x = rnd.randrange(22 * t, 44 * t)
            y = rnd.randrange(0, h)
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 5)):
                x += rnd.randint(-28, 28)
                y += rnd.randint(-20, 20)
                pts.append((x, y))
            pygame.draw.lines(surf, (64, 63, 68), False, pts, 1)

        # círculos de runas no chão das ruínas
        for _ in range(22):
            x = rnd.randrange(23 * t, 43 * t)
            y = rnd.randrange(2 * t, 42 * t)
            if abs(y - 23 * t) < t * 1.6:
                continue
            raio = rnd.randint(18, 30)
            halo_suave(surf, (x, y), raio, (70, 150, 200), alpha=55)
            pygame.draw.circle(surf, (86, 166, 206), (x, y), raio, 1)
            pygame.draw.circle(surf, (108, 190, 230), (x, y), max(3, raio // 3), 1)
            for k in range(4):
                ang = k * math.tau / 4 + 0.4
                px = x + math.cos(ang) * raio * 0.68
                py = y + math.sin(ang) * raio * 0.68
                pygame.draw.circle(surf, (128, 208, 238), (int(px), int(py)), 2)

        # caverna
        pygame.draw.rect(surf, (34, 28, 46), (44 * t, 0, 20 * t, h))
        for _ in range(900):
            x = rnd.randrange(44 * t, 64 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(18, 80)
            cor = rnd.choice(((38, 32, 52), (30, 24, 42), (44, 36, 60), (26, 22, 38)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # veios de cristal no chão (fracos: os cristais obstáculo é que brilham)
        for _ in range(90):
            x = rnd.randrange(44 * t, 64 * t)
            y = rnd.randrange(0, h)
            cor = rnd.choice(((62, 44, 88), (50, 36, 74), (72, 52, 100)))
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 4)):
                x += rnd.randint(-34, 34)
                y += rnd.randint(-24, 24)
                pts.append((x, y))
            pygame.draw.lines(surf, cor, False, pts, rnd.randint(1, 3))

        # pântano de Veyra
        pygame.draw.rect(surf, (56, 64, 46), (64 * t, 0, 20 * t, h))
        for _ in range(760):
            x = rnd.randrange(64 * t, 84 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(20, 92)
            cor = rnd.choice(((60, 70, 50), (50, 58, 42), (66, 74, 52), (46, 54, 40)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # lama e grama morta
        for _ in range(340):
            x = rnd.randrange(64 * t, 84 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(10, 40)
            cor = rnd.choice(((78, 68, 46), (70, 62, 42), (86, 76, 52), (62, 60, 42)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 3, r * 2, r // 2))
        for _ in range(900):
            x = rnd.randrange(64 * t, 84 * t)
            y = rnd.randrange(0, h)
            if rnd.random() < 0.65:
                pygame.draw.line(
                    surf, rnd.choice(((74, 88, 56), (84, 96, 60), (64, 78, 50))),
                    (x, y), (x + rnd.randint(-2, 2), y - rnd.randint(4, 10)), 1,
                )
            else:
                pygame.draw.circle(
                    surf, rnd.choice(((150, 148, 92), (130, 120, 84), (110, 118, 82))),
                    (x, y), rnd.randint(1, 3),
                )
        # lagoas escuras com margem de lama e vitórias-régias
        for cx, cy, rx, ry in LAGOAS_PANTANO:
            area = pygame.Rect(
                int(cx * t - rx * t), int(cy * t - ry * t),
                int(rx * 2 * t), int(ry * 2 * t),
            )
            pygame.draw.ellipse(surf, (74, 66, 44), area.inflate(26, 20))
            pygame.draw.ellipse(surf, (36, 70, 62), area)
            pygame.draw.ellipse(surf, (46, 88, 76), area.inflate(-18, -14))
            pygame.draw.ellipse(surf, (58, 106, 90), area.inflate(-46, -34))
            for _ in range(22):
                ang = rnd.uniform(0, math.tau)
                dist = rnd.uniform(0.15, 0.85)
                px = area.centerx + math.cos(ang) * area.w * 0.5 * dist
                py = area.centery + math.sin(ang) * area.h * 0.5 * dist
                pygame.draw.ellipse(
                    surf, rnd.choice(((70, 120, 96), (56, 104, 84), (82, 134, 108))),
                    (int(px), int(py), rnd.randint(8, 30), rnd.randint(2, 6)),
                )
            for _ in range(10):
                ang = rnd.uniform(0, math.tau)
                dist = rnd.uniform(0.2, 0.7)
                px = area.centerx + math.cos(ang) * area.w * 0.5 * dist
                py = area.centery + math.sin(ang) * area.h * 0.5 * dist
                r = rnd.randint(5, 11)
                pygame.draw.ellipse(surf, (76, 132, 88), (int(px - r), int(py - r // 2), r * 2, r))
                pygame.draw.line(surf, (48, 96, 62), (int(px), int(py)), (int(px + r), int(py - r // 2)), 1)
                if rnd.random() < 0.3:
                    pygame.draw.circle(surf, (226, 198, 128), (int(px), int(py - 1)), max(2, r // 3))

        # Desfiladeiro de Obsidiana
        pygame.draw.rect(surf, (46, 38, 48), (84 * t, 0, 20 * t, h))
        for _ in range(760):
            x = rnd.randrange(84 * t, 104 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(18, 88)
            cor = rnd.choice(((52, 42, 54), (40, 34, 44), (60, 48, 58), (36, 30, 40)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # veios de obsidiana e brasas
        for _ in range(110):
            x = rnd.randrange(84 * t, 104 * t)
            y = rnd.randrange(0, h)
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 5)):
                x += rnd.randint(-40, 40)
                y += rnd.randint(-26, 26)
                pts.append((x, y))
            pygame.draw.lines(
                surf, rnd.choice(((86, 42, 58), (120, 58, 48), (68, 48, 72))),
                False, pts, rnd.randint(1, 3),
            )
        # Coração de Aether: santuário de cristal além do Desfiladeiro
        pygame.draw.rect(surf, (58, 60, 82), (104 * t, 0, 20 * t, h))
        for _ in range(980):
            x = rnd.randrange(104 * t, 124 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(16, 92)
            cor = rnd.choice(((70, 72, 98), (84, 86, 112), (50, 52, 72), (96, 94, 126), (64, 68, 92)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # veios de energia e ouro
        for _ in range(170):
            x = rnd.randrange(104 * t, 124 * t)
            y = rnd.randrange(0, h)
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 5)):
                x += rnd.randint(-46, 46)
                y += rnd.randint(-28, 28)
                pts.append((x, y))
            pygame.draw.lines(
                surf, rnd.choice(((110, 180, 224), (188, 160, 94), (158, 140, 220))),
                False, pts, rnd.randint(1, 3),
            )
        # runas e poças de luz no chão
        for _ in range(46):
            x = rnd.randrange(105 * t, 123 * t)
            y = rnd.randrange(13 * t, 42 * t)
            raio = rnd.randint(16, 34)
            halo_suave(surf, (x, y), raio, (170, 220, 255), alpha=48)
            pygame.draw.circle(surf, (150, 200, 236), (x, y), raio, 1)
            pygame.draw.circle(surf, (214, 240, 255), (x, y), max(3, raio // 3), 1)
        # Fenda do Eclipse: topo do Coração sob um eclipse eterno
        fenda_h = int(12 * t)
        pygame.draw.rect(surf, (28, 20, 40), (104 * t, 0, 20 * t, fenda_h))
        for _ in range(420):
            x = rnd.randrange(104 * t, 124 * t)
            y = rnd.randrange(0, fenda_h)
            r = rnd.randint(16, 76)
            cor = rnd.choice(((42, 30, 56), (56, 38, 72), (34, 24, 48), (68, 46, 86), (24, 18, 36)))
            pygame.draw.ellipse(surf, cor, (x - r, y - r // 2, r * 2, r))
        # veios de eclipse
        for _ in range(70):
            x = rnd.randrange(104 * t, 124 * t)
            y = rnd.randrange(0, fenda_h)
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 4)):
                x += rnd.randint(-40, 40)
                y += rnd.randint(-22, 22)
                pts.append((x, y))
            pygame.draw.lines(
                surf, rnd.choice(((132, 74, 168), (90, 54, 120), (176, 96, 120))),
                False, pts, rnd.randint(1, 3),
            )
        # círculo do eclipse no santuário
        pygame.draw.circle(surf, (18, 12, 28), (int(120 * t), int(5 * t)), int(2.4 * t))
        pygame.draw.circle(surf, (170, 120, 220), (int(120 * t), int(5 * t)), int(2.4 * t), 3)
        pygame.draw.circle(surf, (240, 210, 150), (int(120 * t), int(5 * t)), int(1.7 * t), 2)
        # transição suave na borda inferior da fenda
        faixa = max(1, int(1.6 * t))
        for i in range(faixa):
            f = i / max(1, faixa - 1)
            cor = (
                int(28 + (58 - 28) * (1 - f)),
                int(20 + (60 - 20) * (1 - f)),
                int(40 + (82 - 40) * (1 - f)),
            )
            pygame.draw.line(surf, cor, (104 * t, fenda_h - i), (124 * t, fenda_h - i))
        # caminho de entrada da Fenda
        pygame.draw.line(surf, (54, 38, 68), (114 * t, fenda_h - 2), (114 * t, 23 * t), int(t * 0.9))
        pygame.draw.line(surf, (76, 52, 92), (114 * t, fenda_h - 2), (114 * t, 23 * t), int(t * 0.35))
        # chão da Vila de Veyra: terra batida e grama seca (integra a praça ao bioma)
        vcx, vcy = 90.5 * t, 22.5 * t
        vrx, vry = 6.2 * t, 9.0 * t
        patch = pygame.Surface((int(vrx * 2), int(vry * 2)), pygame.SRCALPHA)
        for i in range(22):
            f = i / 21.0
            rx_i = vrx * (1.0 - 0.5 * f)
            ry_i = vry * (1.0 - 0.5 * f)
            alpha = int(14 + 210 * (f ** 2.2))
            pygame.draw.ellipse(
                patch, (104, 94, 68, alpha),
                (int(vrx - rx_i), int(vry - ry_i), int(rx_i * 2), int(ry_i * 2)),
            )
        surf.blit(patch, (int(vcx - vrx), int(vcy - vry)))
        # textura: grama seca, pedriscos e manchas de terra
        for _ in range(420):
            ang = rnd.uniform(0, math.tau)
            dist = math.sqrt(rnd.random()) * 0.92
            x = vcx + math.cos(ang) * vrx * dist
            y = vcy + math.sin(ang) * vry * dist
            if rnd.random() < 0.55:
                pygame.draw.line(
                    surf, rnd.choice(((84, 104, 60), (96, 116, 66), (76, 96, 56))),
                    (int(x), int(y)), (int(x + rnd.randint(-2, 2)), int(y - rnd.randint(4, 9))), 1,
                )
            elif rnd.random() < 0.5:
                pygame.draw.circle(surf, rnd.choice(((122, 110, 86), (108, 98, 78))), (int(x), int(y)), rnd.randint(1, 2))
            else:
                pygame.draw.ellipse(
                    surf, rnd.choice(((94, 86, 62), (112, 100, 74))),
                    (int(x), int(y), rnd.randint(8, 22), rnd.randint(3, 7)),
                )
        # praça de pedra da Vila de Veyra
        cx_v, cy_v = 90.5 * t, 22.5 * t
        pygame.draw.circle(surf, (122, 110, 96), (int(cx_v), int(cy_v)), int(4.6 * t))
        pygame.draw.circle(surf, (98, 88, 78), (int(cx_v), int(cy_v)), int(4.6 * t), 5)
        for _ in range(420):
            ang = rnd.uniform(0, math.tau)
            dist = rnd.uniform(0.8 * t, 4.3 * t)
            px = cx_v + math.cos(ang) * dist
            py = cy_v + math.sin(ang) * dist
            cor = rnd.choice(((132, 118, 100), (114, 102, 90), (142, 126, 108), (104, 94, 84)))
            pygame.draw.ellipse(surf, cor, (int(px), int(py), rnd.randint(4, 14), rnd.randint(2, 6)))
        for i in range(12):
            ang = i * math.tau / 12
            px = cx_v + math.cos(ang) * 3.6 * t
            py = cy_v + math.sin(ang) * 3.6 * t
            pygame.draw.circle(surf, (168, 146, 104), (int(px), int(py)), 5)
            pygame.draw.circle(surf, (116, 156, 160), (int(px), int(py)), 2)

        # transições suaves
        self._faixa_transicao(surf, 22 * t - t, t * 2, (44, 88, 60), (78, 76, 82))
        self._faixa_transicao(surf, 44 * t - t, t * 2, (78, 76, 82), (34, 28, 46))
        self._faixa_transicao(surf, 64 * t - t, t * 2, (34, 28, 46), (56, 64, 46))
        self._faixa_transicao(surf, 84 * t - t, t * 2, (56, 64, 46), (46, 38, 48))
        self._faixa_transicao(surf, 104 * t - t, t * 2, (46, 38, 48), (58, 60, 82))

        # caminho principal com transição de cor entre os biomas
        caminho = [(x * t, y * t) for x, y in CAMINHO_PRINCIPAL]
        marrom, marrom_claro = (108, 88, 66), (128, 106, 80)
        pedra, pedra_clara = (84, 82, 88), (104, 100, 106)
        caverna, caverna_clara = (62, 52, 78), (86, 74, 106)
        pantano, pantano_claro = (70, 62, 44), (92, 82, 56)
        obsidiana, obsidiana_clara = (70, 58, 64), (96, 80, 84)
        coracao, coracao_claro = (88, 90, 118), (122, 122, 154)

        def _misturar(a: tuple[int, int, int], b: tuple[int, int, int], f: float) -> tuple[int, int, int]:
            return tuple(int(lerp(a[c], b[c], f)) for c in range(3))

        def cor_caminho(x: float, claro: bool = False) -> tuple[int, int, int]:
            if x < 21 * t:
                return marrom_claro if claro else marrom
            if x < 23 * t:
                f = (x - 21 * t) / (2 * t)
                return _misturar(marrom_claro if claro else marrom, pedra_clara if claro else pedra, f)
            if x < 43 * t:
                return pedra_clara if claro else pedra
            if x < 45 * t:
                f = (x - 43 * t) / (2 * t)
                return _misturar(pedra_clara if claro else pedra, caverna_clara if claro else caverna, f)
            if x < 63 * t:
                return caverna_clara if claro else caverna
            if x < 65 * t:
                f = (x - 63 * t) / (2 * t)
                return _misturar(caverna_clara if claro else caverna, pantano_claro if claro else pantano, f)
            if x < 83 * t:
                return pantano_claro if claro else pantano
            if x < 85 * t:
                f = (x - 83 * t) / (2 * t)
                return _misturar(pantano_claro if claro else pantano, obsidiana_clara if claro else obsidiana, f)
            if x < 103 * t:
                return obsidiana_clara if claro else obsidiana
            if x < 105 * t:
                f = (x - 103 * t) / (2 * t)
                return _misturar(obsidiana_clara if claro else obsidiana, coracao_claro if claro else coracao, f)
            return coracao_claro if claro else coracao

        for i in range(len(caminho) - 1):
            x1, y1 = caminho[i]
            x2, y2 = caminho[i + 1]
            passos = max(1, int(math.hypot(x2 - x1, y2 - y1) / 12))
            for k in range(passos):
                xa = x1 + (x2 - x1) * k / passos
                ya = y1 + (y2 - y1) * k / passos
                xb = x1 + (x2 - x1) * (k + 1) / passos
                yb = y1 + (y2 - y1) * (k + 1) / passos
                pygame.draw.line(surf, cor_caminho((xa + xb) / 2), (xa, ya), (xb, yb), int(t * 2.1))
        for p in caminho:
            pygame.draw.circle(surf, cor_caminho(p[0]), (int(p[0]), int(p[1])), int(t * 1.05))
        for i in range(len(caminho) - 1):
            x1, y1 = caminho[i]
            x2, y2 = caminho[i + 1]
            passos = max(1, int(math.hypot(x2 - x1, y2 - y1) / 14))
            for k in range(passos):
                xa = x1 + (x2 - x1) * k / passos
                ya = y1 + (y2 - y1) * k / passos
                xb = x1 + (x2 - x1) * (k + 1) / passos
                yb = y1 + (y2 - y1) * (k + 1) / passos
                pygame.draw.line(surf, cor_caminho((xa + xb) / 2, True), (xa, ya), (xb, yb), int(t * 0.95))
        # pedrinhas no caminho
        for _ in range(240):
            x = rnd.randrange(0, w)
            y = rnd.randrange(0, h)
            if min(abs(y - 23 * t), abs(y - 22 * t)) < t * 1.15:
                base = cor_caminho(x)
                variacao = rnd.choice((-18, 0, 22, 40))
                cor = tuple(max(0, min(255, c + variacao)) for c in base)
                pygame.draw.circle(surf, cor, (x, y), rnd.randint(1, 4))

        # praça da vila
        pygame.draw.circle(surf, (150, 142, 126), (int(11.5 * t), int(23 * t)), int(t * 3.4))
        pygame.draw.circle(surf, (128, 120, 108), (int(11.5 * t), int(23 * t)), int(t * 3.4), 4)
        for i in range(8):
            ang = i * math.tau / 8
            x = 11.5 * t + math.cos(ang) * t * 2.5
            y = 23 * t + math.sin(ang) * t * 2.5
            pygame.draw.circle(surf, (168, 158, 138), (int(x), int(y)), 6)

        # textura de pedra da praça
        cx, cy = 11.5 * t, 23 * t
        for _ in range(420):
            ang = rnd.uniform(0, math.tau)
            dist = rnd.uniform(0.8 * t, 3.15 * t)
            x = cx + math.cos(ang) * dist
            y = cy + math.sin(ang) * dist
            cor = rnd.choice(((142, 134, 120), (158, 150, 132), (136, 128, 116), (166, 158, 140)))
            pygame.draw.ellipse(surf, cor, (int(x), int(y), rnd.randint(4, 15), rnd.randint(2, 7)))
        # juntas radiais e anéis concêntricos
        for i in range(14):
            ang = i * math.tau / 14 + 0.08
            p1 = (cx + math.cos(ang) * 0.9 * t, cy + math.sin(ang) * 0.9 * t)
            p2 = (cx + math.cos(ang) * 3.3 * t, cy + math.sin(ang) * 3.3 * t)
            pygame.draw.line(surf, (128, 120, 108), p1, p2, 1)
        pygame.draw.circle(surf, (130, 122, 110), (int(cx), int(cy)), int(1.55 * t), 1)
        pygame.draw.circle(surf, (126, 118, 106), (int(cx), int(cy)), int(2.85 * t), 2)
        # runas ao redor da fonte
        for i in range(12):
            ang = i * math.tau / 12 + math.tau / 24
            rx = cx + math.cos(ang) * 1.15 * t
            ry = cy + math.sin(ang) * 1.15 * t
            cor = (176, 154, 104) if i % 2 == 0 else (116, 158, 166)
            pygame.draw.polygon(surf, cor, [
                (rx, ry - 5), (rx + 5, ry), (rx, ry + 5), (rx - 5, ry),
            ])
            pygame.draw.circle(surf, cor, (int(rx), int(ry)), 1)
        # musgo e rachaduras
        for _ in range(46):
            ang = rnd.uniform(0, math.tau)
            dist = rnd.uniform(2.4 * t, 3.35 * t)
            x = cx + math.cos(ang) * dist
            y = cy + math.sin(ang) * dist
            pygame.draw.ellipse(surf, rnd.choice(((110, 128, 94), (98, 118, 86), (122, 136, 100))),
                                (int(x), int(y), rnd.randint(6, 18), rnd.randint(3, 8)))
        for _ in range(9):
            x = cx + rnd.uniform(-2.9 * t, 2.9 * t)
            y = cy + rnd.uniform(-2.9 * t, 2.9 * t)
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 4)):
                x += rnd.randint(-22, 22)
                y += rnd.randint(-16, 16)
                pts.append((x, y))
            pygame.draw.lines(surf, (112, 104, 94), False, pts, 1)

        # lago
        lago = pygame.Rect(int(3.5 * t), int(6.5 * t), int(6.5 * t), int(4.2 * t))
        pygame.draw.ellipse(surf, (196, 178, 132), lago.inflate(18, 14))
        pygame.draw.ellipse(surf, (40, 96, 132), lago)
        pygame.draw.ellipse(surf, (52, 118, 154), lago.inflate(-20, -16))
        pygame.draw.ellipse(surf, (72, 148, 180), (lago.x + 26, lago.y + 18, lago.w // 2, lago.h // 3))
        for _ in range(30):
            x = rnd.randrange(lago.left + 10, lago.right - 10)
            y = rnd.randrange(lago.top + 10, lago.bottom - 10)
            pygame.draw.ellipse(surf, (110, 190, 216), (x, y, rnd.randint(8, 28), rnd.randint(2, 5)))

        # juncos na margem
        for _ in range(46):
            ang = rnd.uniform(0, math.tau)
            fator = rnd.uniform(0.98, 1.08)
            px = lago.centerx + math.cos(ang) * (lago.w / 2) * fator
            py = lago.centery + math.sin(ang) * (lago.h / 2) * fator
            if not (0 <= px < w and 0 <= py < h):
                continue
            for _ in range(3):
                bx = px + rnd.randint(-5, 5)
                by = py + rnd.randint(-2, 2)
                altura = rnd.randint(8, 22)
                pygame.draw.line(
                    surf, rnd.choice(((58, 112, 64), (70, 128, 72), (48, 96, 58))),
                    (bx, by), (bx + rnd.randint(-3, 3), by - altura), 2,
                )
                pygame.draw.circle(surf, (132, 100, 58), (int(bx), int(by - altura)), 2)

        # vitórias-régias e flores
        for _ in range(16):
            ang = rnd.uniform(0, math.tau)
            fator = rnd.uniform(0.35, 0.8)
            px = lago.centerx + math.cos(ang) * (lago.w / 2) * fator
            py = lago.centery + math.sin(ang) * (lago.h / 2) * fator
            r = rnd.randint(5, 11)
            pygame.draw.ellipse(surf, (70, 138, 86), (int(px - r), int(py - r // 2), r * 2, r))
            pygame.draw.line(surf, (40, 96, 60), (int(px), int(py)), (int(px + r), int(py - r // 2)), 1)
            if rnd.random() < 0.35:
                pygame.draw.circle(surf, (238, 210, 120), (int(px), int(py - 1)), max(2, r // 3))
                pygame.draw.circle(surf, (250, 236, 190), (int(px), int(py - 1)), max(1, r // 5))

        # textura de grama e flores
        for _ in range(2200):
            x = rnd.randrange(0, 22 * t)
            y = rnd.randrange(0, h)
            if rnd.random() < 0.7:
                pygame.draw.line(surf, rnd.choice(((60, 118, 72), (70, 132, 80), (52, 104, 64))), (x, y), (x + rnd.randint(-2, 2), y - rnd.randint(3, 8)), 1)
            else:
                pygame.draw.circle(surf, rnd.choice(((232, 220, 120), (240, 180, 200), (220, 240, 240))), (x, y), rnd.randint(1, 3))
        for _ in range(500):
            x = rnd.randrange(44 * t, 64 * t)
            y = rnd.randrange(0, h)
            pygame.draw.circle(surf, rnd.choice(((120, 90, 160), (80, 60, 120), (150, 110, 190))), (x, y), rnd.randint(1, 3))

        # trilhas de terra por cima da grama, para ler o caminho
        for pontos in TRILHAS_FLORESTA:
            self._desenhar_trilha(surf, pontos, rnd)

        # detalhes de chão nas Ruínas: musgo e rachaduras
        for _ in range(80):
            x = rnd.randrange(22 * t, 44 * t)
            y = rnd.randrange(0, h)
            r = rnd.randint(12, 36)
            pygame.draw.ellipse(surf, (70, 78, 64), (x - r, y - r // 3, r * 2, r // 2))
        for _ in range(60):
            x = rnd.randrange(22 * t, 44 * t)
            y = rnd.randrange(0, h)
            pts = [(x, y)]
            for _ in range(rnd.randint(2, 4)):
                x += rnd.randint(-18, 18)
                y += rnd.randint(-12, 12)
                pts.append((x, y))
            pygame.draw.lines(surf, (52, 50, 58), False, pts, 1)

        # pedriscos na Caverna
        for _ in range(320):
            x = rnd.randrange(44 * t, 64 * t)
            y = rnd.randrange(0, h)
            pygame.draw.circle(
                surf,
                rnd.choice(((40, 34, 58), (58, 48, 78), (30, 26, 44))),
                (x, y), rnd.randint(1, 4),
            )

        return surf

    @staticmethod
    def _desenhar_trilha(
        surf: pygame.Surface, pontos: tuple[tuple[float, float], ...], rnd: random.Random,
    ) -> None:
        """Trilha de terra estreita, com desvio suave e bordas desgastadas."""
        t = TILE

        # serpenteia de leve, para não ficar uma reta artificial
        curva: list[tuple[float, float]] = []
        for i in range(len(pontos) - 1):
            x1, y1 = pontos[i][0] * t, pontos[i][1] * t
            x2, y2 = pontos[i + 1][0] * t, pontos[i + 1][1] * t
            comprimento = math.hypot(x2 - x1, y2 - y1)
            passos = max(2, int(comprimento / (t * 0.35)))
            nx, ny = -(y2 - y1), (x2 - x1)
            norma = max(1e-3, math.hypot(nx, ny))
            for k in range(passos):
                f = k / passos
                desvio = math.sin((i * 2.3 + f * 3.1) * math.pi) * 0.28 * t
                curva.append((x1 + (x2 - x1) * f + nx / norma * desvio,
                              y1 + (y2 - y1) * f + ny / norma * desvio))
        curva.append((pontos[-1][0] * t, pontos[-1][1] * t))

        terra, terra_clara = (104, 84, 62), (126, 104, 78)
        largura = max(2, int(t * 0.9))
        for i in range(len(curva) - 1):
            pygame.draw.line(surf, terra, curva[i], curva[i + 1], largura)
        for px, py in curva:
            pygame.draw.circle(surf, terra, (int(px), int(py)), largura // 2)
        # manchas mais claras e pedrinhas, para quebrar a uniformidade
        for i in range(len(curva) - 1):
            x1, y1 = curva[i]
            x2, y2 = curva[i + 1]
            nx, ny = -(y2 - y1), (x2 - x1)
            norma = max(1e-3, math.hypot(nx, ny))
            for _ in range(2):
                off = rnd.uniform(-0.3, 0.3) * t
                px = x1 + nx / norma * off
                py = y1 + ny / norma * off
                if rnd.random() < 0.5:
                    pygame.draw.ellipse(surf, terra_clara,
                                        (int(px - 8), int(py - 5), rnd.randint(10, 22), rnd.randint(5, 10)))
                else:
                    pygame.draw.ellipse(surf, (92, 78, 58),
                                        (int(px - 7), int(py - 4), rnd.randint(8, 18), rnd.randint(4, 8)))
        for i in range(0, len(curva), 3):
            px, py = curva[i]
            for _ in range(2):
                off = rnd.uniform(-0.75, 0.75) * t
                nx, ny = -(curva[min(i + 1, len(curva) - 1)][1] - py), (curva[min(i + 1, len(curva) - 1)][0] - px)
                norma = max(1e-3, math.hypot(nx, ny))
                cor = rnd.choice(((96, 82, 62), (120, 100, 76), (86, 76, 60), (74, 68, 56)))
                pygame.draw.circle(surf, cor, (int(px + nx / norma * off), int(py + ny / norma * off)), rnd.randint(1, 3))


    @staticmethod
    def _faixa_transicao(
        surf: pygame.Surface, x_inicio: int, largura: int,
        cor_a: tuple[int, int, int], cor_b: tuple[int, int, int],
    ) -> None:
        for i in range(largura):
            t = i / max(1, largura - 1)
            cor = tuple(int(lerp(cor_a[c], cor_b[c], t)) for c in range(3))
            pygame.draw.line(surf, cor, (x_inicio + i, 0), (x_inicio + i, surf.get_height()))

    # ------------------------------------------------------------------ decoração
    def _gerar_decoracoes(self) -> None:
        t = TILE
        rnd = random.Random(7788)
        self.obstaculos.clear()
        self.decoracoes.clear()

        # o lago é intransponível
        self.obstaculos.append(
            Obstaculo("ellipse", x=6.75 * t, y=8.6 * t, rx=3.25 * t + 8, ry=2.1 * t + 6)
        )
        # as lagoas do pântano também
        for cx, cy, rx, ry in LAGOAS_PANTANO:
            self.obstaculos.append(
                Obstaculo("ellipse", x=cx * t, y=cy * t, rx=rx * t + 6, ry=ry * t + 4)
            )

        # lago (área) — evita repetir a checagem em cada laço
        def no_lago(x: float, y: float) -> bool:
            return 3.3 * t < x < 10.2 * t and 6.3 * t < y < 10.9 * t

        def livre_floresta(x: float, y: float, folga_clareira: float = 0.2) -> bool:
            if self.vila.rect.inflate(t * 2, t * 2).collidepoint(x, y):
                return False
            if abs(y - 23 * t) < t * 1.5:
                return False
            if no_lago(x, y):
                return False
            if em_clareira_floresta(x, y, folga_clareira):
                return False
            return not na_trilha_floresta(x, y)

        # árvores da floresta: bosques densos e árvores soltas entre eles
        bosques = (
            (4.2, 16.5, 4.6), (17.6, 16.0, 4.8), (4.6, 29.5, 4.4),
            (17.4, 30.5, 4.6), (10.4, 7.0, 4.2), (10.6, 39.5, 4.4),
            (4.4, 40.0, 3.6), (18.0, 41.0, 3.4),
        )
        for _ in range(168):
            if rnd.random() < 0.74:
                bx, by, br = rnd.choice(bosques)
                ang = rnd.uniform(0, math.tau)
                dist = br * t * math.sqrt(rnd.random())
                x = bx * t + math.cos(ang) * dist
                y = by * t + math.sin(ang) * dist
            else:
                x = rnd.uniform(1 * t, 21 * t)
                y = rnd.uniform(1 * t, 43 * t)
            if not (0.2 * t < x < 21.8 * t and 0.2 * t < y < 43.8 * t):
                continue
            if not livre_floresta(x, y):
                continue
            escala = rnd.uniform(0.72, 1.28)
            self.decoracoes.append(Decoracao("arvore", x, y, escala, rnd.randint(0, 3), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=12 * escala))

        # troncos caídos, de preferência perto das trilhas
        for _ in range(40):
            if rnd.random() < 0.45:
                pontos = rnd.choice(TRILHAS_FLORESTA)
                i = rnd.randrange(len(pontos) - 1)
                f = rnd.random()
                x = (pontos[i][0] + (pontos[i + 1][0] - pontos[i][0]) * f) * t + rnd.uniform(-1.4, 1.4) * t
                y = (pontos[i][1] + (pontos[i + 1][1] - pontos[i][1]) * f) * t + rnd.uniform(-1.1, 1.1) * t
            else:
                x = rnd.uniform(1 * t, 21 * t)
                y = rnd.uniform(1 * t, 43 * t)
            if not livre_floresta(x, y, folga_clareira=-0.4):
                continue
            self.decoracoes.append(Decoracao("tronco", x, y, rnd.uniform(0.7, 1.15), rnd.randint(0, 3), rnd.uniform(0, 6.28)))

        # arbustos floridos: mais concentrados na orla das clareiras
        for _ in range(86):
            if rnd.random() < 0.5:
                cx, cy, raio = rnd.choice(CLAREIRAS_FLORESTA)
                ang = rnd.uniform(0, math.tau)
                dist = raio * t * rnd.uniform(0.75, 1.15)
                x = cx * t + math.cos(ang) * dist
                y = cy * t + math.sin(ang) * dist
            else:
                x = rnd.uniform(1.5 * t, 21 * t)
                y = rnd.uniform(1.5 * t, 42.5 * t)
            if not livre_floresta(x, y, folga_clareira=-0.5):
                continue
            self.decoracoes.append(Decoracao("arbusto", x, y, rnd.uniform(0.55, 1.05), rnd.randint(0, 3), rnd.uniform(0, 6.28)))

        # círculo de pedras na Clareira das Pedras: marco visual do bioma
        cx_pedras, cy_pedras, _raio_pedras = CLAREIRAS_FLORESTA[1]
        for i in range(9):
            ang = i * math.tau / 9
            x = cx_pedras * t + math.cos(ang) * 1.7 * t
            y = cy_pedras * t + math.sin(ang) * 1.7 * t
            e = rnd.uniform(0.55, 0.75)
            self.decoracoes.append(Decoracao("rocha", x, y, e, rnd.randint(0, 5), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=13 * e))
        for dx, dy, e in ((0.0, 0.0, 0.5), (0.9, -0.7, 0.4)):
            x = cx_pedras * t + dx * t
            y = cy_pedras * t + dy * t
            self.decoracoes.append(Decoracao("tronco", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28)))


        # rochas na floresta e ruínas
        for _ in range(34):
            x = rnd.uniform(2 * t, 43 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if self.vila.rect.inflate(t, t).collidepoint(x, y) or abs(y - 23 * t) < t * 1.2:
                continue
            e = rnd.uniform(0.7, 1.2)
            self.decoracoes.append(Decoracao("rocha", x, y, e, rnd.randint(0, 5), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=16 * e))

        # ruínas
        for _ in range(26):
            x = rnd.uniform(23 * t, 43 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if abs(y - 23 * t) < t * 1.4:
                continue
            e = rnd.uniform(0.8, 1.2)
            self.decoracoes.append(Decoracao("ruina", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 20 * e), int(y - 26 * e), int(40 * e), int(26 * e))))

        # arcos e muros quebrados dão verticalidade às ruínas
        for _ in range(7):
            x = rnd.uniform(24 * t, 42.5 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if abs(y - 23 * t) < t * 1.8:
                continue
            e = rnd.uniform(0.8, 1.15)
            self.decoracoes.append(Decoracao("arco", x, y, e, rnd.randint(0, 2), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 43 * e), int(y - 78 * e), int(18 * e), int(78 * e))))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x + 25 * e), int(y - 78 * e), int(18 * e), int(78 * e))))
        for _ in range(11):
            x = rnd.uniform(24 * t, 42.5 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if abs(y - 23 * t) < t * 1.8:
                continue
            e = rnd.uniform(0.8, 1.2)
            self.decoracoes.append(Decoracao("muro", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 37 * e), int(y - 44 * e), int(74 * e), int(44 * e))))

        # cristais azuis entre as ruínas
        for _ in range(12):
            x = rnd.uniform(23.5 * t, 42.5 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if abs(y - 23 * t) < t * 1.5:
                continue
            e = rnd.uniform(0.5, 0.9)
            cor = rnd.choice(((90, 160, 220), (120, 200, 240), (80, 140, 210)))
            self.decoracoes.append(Decoracao("cristal", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28), cor))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=8 * e))

        # cristais na caverna
        for _ in range(44):
            x = rnd.uniform(45 * t, 63 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if abs(y - 23 * t) < t * 1.1:
                continue
            e = rnd.uniform(0.7, 1.3)
            cor = rnd.choice(((120, 86, 200), (86, 150, 230), (200, 92, 190), (86, 210, 200)))
            self.decoracoes.append(Decoracao("cristal", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28), cor))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=12 * e))

        # pântano de Veyra: árvores mortas, juncos e ruínas afundadas
        def livre_pantano(x: float, y: float, folga_lagoa: float = 0.15) -> bool:
            if abs(y - 23 * t) < t * 1.7:
                return False
            return not em_lagoa_pantano(x, y, folga_lagoa)

        for _ in range(52):
            x = rnd.uniform(65 * t, 83 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if not livre_pantano(x, y):
                continue
            e = rnd.uniform(0.8, 1.35)
            self.decoracoes.append(Decoracao("arvore_morta", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=11 * e))

        for _ in range(96):
            x = rnd.uniform(64.4 * t, 83.6 * t)
            y = rnd.uniform(1.5 * t, 42.5 * t)
            if not livre_pantano(x, y, folga_lagoa=-0.05):
                continue
            self.decoracoes.append(Decoracao("junco", x, y, rnd.uniform(0.6, 1.25), rnd.randint(0, 3), rnd.uniform(0, 6.28)))

        for _ in range(26):
            x = rnd.uniform(65 * t, 83 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if not livre_pantano(x, y):
                continue
            e = rnd.uniform(0.6, 1.1)
            self.decoracoes.append(Decoracao("rocha", x, y, e, rnd.randint(0, 5), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=14 * e))

        for _ in range(7):
            x = rnd.uniform(66 * t, 82 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if not livre_pantano(x, y, folga_lagoa=0.4):
                continue
            e = rnd.uniform(0.75, 1.05)
            self.decoracoes.append(Decoracao("ruina", x, y, e, rnd.randint(0, 3), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 20 * e), int(y - 26 * e), int(40 * e), int(26 * e))))

        for i in range(16):
            x = rnd.uniform(65 * t, 83 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if not livre_pantano(x, y, folga_lagoa=0.0):
                continue
            cor = rnd.choice(((150, 220, 130), (110, 200, 160), (200, 220, 120)))
            self.decoracoes.append(Decoracao("cogumelo", x, y, rnd.uniform(0.7, 1.15), i, rnd.uniform(0, 6.28), cor))

        for i in range(8):
            x = rnd.uniform(66 * t, 82 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if not livre_pantano(x, y, folga_lagoa=0.2):
                continue
            e = rnd.uniform(0.5, 0.85)
            cor = rnd.choice(((120, 210, 140), (170, 220, 110), (90, 190, 170)))
            self.decoracoes.append(Decoracao("cristal", x, y, e, i, rnd.uniform(0, 6.28), cor))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=8 * e))

        # Vila de Veyra: praça, casas, mercado, forja e altar
        for cx, cy in ((87.4, 18.6), (93.6, 18.6), (87.4, 27.4), (93.6, 27.4)):
            self.decoracoes.append(Decoracao("casa", cx * t, cy * t, 0.9, 0, 0))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(
                int(cx * t - 40), int(cy * t - 68), 80, 68,
            )))
        self.decoracoes.append(Decoracao("fonte", 90.5 * t, 22.5 * t, 1.1, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=90.5 * t, y=22.5 * t, raio=46))
        for lx, ly, e in ((86.6, 20.2, 0.9), (94.4, 20.2, 0.9), (86.6, 25.6, 0.9), (94.4, 25.6, 0.9)):
            self.decoracoes.append(Decoracao("lampiao", lx * t, ly * t, e, 0, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=lx * t, y=ly * t - 4, raio=6 * e))
        for bx, by in ((88.4, 20.6), (92.6, 20.6)):
            self.decoracoes.append(Decoracao("banco", bx * t, by * t, 1.0, 0, 0))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(bx * t - 30), int(by * t - 24), 60, 20)))
        for gx, gy, e in ((87.8, 23.4, 0.9), (93.2, 23.4, 0.9), (88.8, 18.0, 0.8), (92.2, 18.0, 0.8)):
            self.decoracoes.append(Decoracao("jardim", gx * t, gy * t, e, 0, rnd.uniform(0, 6.28)))
        self.decoracoes.append(Decoracao("banca", 87.4 * t, 21.4 * t, 1.0, 0, 0))
        self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(87.4 * t - 32), int(21.4 * t - 60), 64, 60)))
        self.decoracoes.append(Decoracao("bigorna", 92.6 * t, 24.2 * t, 1.0, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=92.6 * t, y=24.2 * t - 4, raio=18))
        self.decoracoes.append(Decoracao("altar", 89.7 * t, 26.6 * t, 1.0, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=89.7 * t, y=26.6 * t - 4, raio=16))
        for i, (bx, by) in enumerate(((86.4, 17.0), (94.6, 17.0), (86.4, 28.8), (94.6, 28.8))):
            self.decoracoes.append(Decoracao("bandeira", bx * t, by * t, 0.9, i, rnd.uniform(0, 6.28), (196, 150, 90)))
        for npc in self.npcs[1:]:
            self.obstaculos.append(Obstaculo("circle", x=npc.x, y=npc.y - 4, raio=13))

        # Desfiladeiro de Obsidiana: cristais escuros, rochas e ruínas
        for i in range(52):
            x = rnd.uniform(84.5 * t, 103.5 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if self.vila_veyra.rect.inflate(t * 2, t * 2).collidepoint(x, y):
                continue
            e = rnd.uniform(0.6, 1.25)
            cor = rnd.choice(((126, 44, 74), (92, 38, 58), (160, 64, 86), (108, 52, 90)))
            self.decoracoes.append(Decoracao("cristal", x, y, e, i, rnd.uniform(0, 6.28), cor))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=10 * e))
        for _ in range(34):
            x = rnd.uniform(84.5 * t, 103.5 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if self.vila_veyra.rect.inflate(t * 2, t * 2).collidepoint(x, y):
                continue
            e = rnd.uniform(0.6, 1.1)
            self.decoracoes.append(Decoracao("rocha", x, y, e, rnd.randint(0, 5), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=14 * e))
        for _ in range(18):
            x = rnd.uniform(85 * t, 103 * t)
            y = rnd.uniform(2 * t, 42 * t)
            if self.vila_veyra.rect.inflate(t * 2, t * 2).collidepoint(x, y):
                continue
            self.decoracoes.append(Decoracao("arvore_morta", x, y, rnd.uniform(0.7, 1.1), 0, rnd.uniform(0, 6.28)))
        for _ in range(8):
            x = rnd.uniform(86 * t, 102 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if self.vila_veyra.rect.inflate(t * 2, t * 2).collidepoint(x, y):
                continue
            e = rnd.uniform(0.7, 1.0)
            self.decoracoes.append(Decoracao("ruina", x, y, e, 0, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 20 * e), int(y - 26 * e), int(40 * e), int(26 * e))))

        # Coração de Aether: cristais claros, obeliscos e santuário
        for i in range(52):
            x = rnd.uniform(104.5 * t, 123.5 * t)
            y = rnd.uniform(13 * t, 42 * t)
            if abs(y - 23 * t) < 1.5 * t:
                continue
            e = rnd.uniform(0.65, 1.35)
            cor = rnd.choice((
                (176, 238, 255), (208, 248, 255), (232, 220, 154),
                (150, 202, 250), (200, 176, 250),
            ))
            self.decoracoes.append(Decoracao("cristal", x, y, e, i, rnd.uniform(0, 6.28), cor))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=10 * e))
        for _ in range(24):
            x = rnd.uniform(104.5 * t, 123.5 * t)
            y = rnd.uniform(13 * t, 42 * t)
            if abs(y - 23 * t) < 1.5 * t:
                continue
            e = rnd.uniform(0.6, 1.15)
            self.decoracoes.append(Decoracao("rocha", x, y, e, rnd.randint(0, 5), rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=14 * e))
        for i in range(12):
            x = rnd.uniform(105 * t, 123 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if abs(y - 23 * t) < 2.0 * t:
                continue
            e = rnd.uniform(0.8, 1.15)
            self.decoracoes.append(Decoracao("obelisco", x, y, e, i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=15 * e))
        for i in range(8):
            x = rnd.uniform(106 * t, 122 * t)
            y = rnd.uniform(4 * t, 40 * t)
            if abs(y - 23 * t) < 2.0 * t:
                continue
            self.decoracoes.append(Decoracao("estatua", x, y, rnd.uniform(0.9, 1.2), i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=16))
        for _ in range(10):
            x = rnd.uniform(105 * t, 123 * t)
            y = rnd.uniform(3 * t, 41 * t)
            if abs(y - 23 * t) < 1.8 * t:
                continue
            e = rnd.uniform(0.7, 1.0)
            self.decoracoes.append(Decoracao("ruina", x, y, e, 1, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 20 * e), int(y - 26 * e), int(40 * e), int(26 * e))))
        for gx, gy, e in ((108.0, 26.2, 0.9), (116.0, 19.0, 0.85), (121.0, 27.0, 0.8)):
            self.decoracoes.append(Decoracao("jardim", gx * t, gy * t, e, 0, rnd.uniform(0, 6.28)))
        # santuário no fim do caminho
        self.decoracoes.append(Decoracao("altar", 120.0 * t, 22.5 * t, 1.25, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=120.0 * t, y=22.5 * t - 4, raio=22))
        for bx, by in ((106.8, 19.5), (106.8, 26.5)):
            self.decoracoes.append(Decoracao("bandeira", bx * t, by * t, 1.0, 0, rnd.uniform(0, 6.28), (180, 220, 250)))

        # Fenda do Eclipse: cristais escuros, obeliscos e santuário
        for i in range(28):
            x = rnd.uniform(104.5 * t, 123.5 * t)
            y = rnd.uniform(1.5 * t, 10.5 * t)
            if abs(x - 114 * t) < 1.5 * t and y > 8 * t:
                continue
            if abs(x - 120 * t) < 2.5 * t and abs(y - 5 * t) < 2.5 * t:
                continue
            e = rnd.uniform(0.6, 1.25)
            cor = rnd.choice(((120, 70, 180), (90, 50, 140), (170, 90, 200), (70, 44, 110)))
            self.decoracoes.append(Decoracao("cristal", x, y, e, i, rnd.uniform(0, 6.28), cor))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=10 * e))
        for i in range(8):
            x = rnd.uniform(105.5 * t, 122.5 * t)
            y = rnd.uniform(2 * t, 10 * t)
            if abs(x - 114 * t) < 2.0 * t:
                continue
            if abs(x - 120 * t) < 2.5 * t and abs(y - 5 * t) < 2.5 * t:
                continue
            e = rnd.uniform(0.8, 1.15)
            self.decoracoes.append(Decoracao("obelisco", x, y, e, i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=15 * e))
        for i in range(5):
            x = rnd.uniform(106 * t, 122 * t)
            y = rnd.uniform(2.5 * t, 9.5 * t)
            if abs(x - 114 * t) < 2.0 * t:
                continue
            if abs(x - 120 * t) < 2.5 * t and abs(y - 5 * t) < 2.5 * t:
                continue
            self.decoracoes.append(Decoracao("estatua", x, y, rnd.uniform(0.9, 1.2), i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=16))
        for _ in range(6):
            x = rnd.uniform(105 * t, 123 * t)
            y = rnd.uniform(2 * t, 10 * t)
            if abs(x - 114 * t) < 1.8 * t:
                continue
            if abs(x - 120 * t) < 2.5 * t and abs(y - 5 * t) < 2.5 * t:
                continue
            e = rnd.uniform(0.7, 1.0)
            self.decoracoes.append(Decoracao("ruina", x, y, e, 1, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(x - 20 * e), int(y - 26 * e), int(40 * e), int(26 * e))))
        self.decoracoes.append(Decoracao("altar", 120.0 * t, 5.0 * t, 1.35, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=120.0 * t, y=5.0 * t - 4, raio=24))
        for bx, by in ((116.5, 3.0), (123.0, 7.0)):
            self.decoracoes.append(Decoracao("bandeira", bx * t, by * t, 1.0, 0, rnd.uniform(0, 6.28), (180, 120, 230)))

        # fogueiras de descanso
        for i, (fx, fy) in enumerate(self.fogueiras):
            self.decoracoes.append(Decoracao("fogueira", fx, fy, 1.0, i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=fx, y=fy - 4, raio=12))

        # vila: casas, fonte e obelisco
        # Casa 1: no vetor é ~97 px de largura; na arte pixel vira 192 px (kit
        # Shabby Chic), então cada modo tem o seu próprio obstáculo.
        self.decoracoes.append(Decoracao("casa", 9.4 * t, 20.2 * t, 0.9, 0, 0))
        self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(9.4 * t - 40), int(20.2 * t - 68), 80, 68), pixel=False))
        self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(9.4 * t - 74), int(20.2 * t - 44), 148, 44), pixel=True))
        self.decoracoes.append(Decoracao("casa", 13.8 * t, 20.4 * t, 0.85, 1, 0))
        self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(13.8 * t - 38), int(20.4 * t - 64), 76, 64), pixel=False))
        self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(13.8 * t - 48), int(20.4 * t - 44), 96, 44), pixel=True))
        # Casa 3: fica só no modo vetorial — a versão pixel (192 px) bateria no
        # lampião, no banco e no caminho até Aldrin.
        self.decoracoes.append(Decoracao("casa", 9.2 * t, 26.4 * t, 0.8, 2, 0, pixel=False))
        self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(9.2 * t - 36), int(26.4 * t - 60), 72, 60), pixel=False))
        self.decoracoes.append(Decoracao("fonte", 11.5 * t, 23.0 * t, 1.0, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=11.5 * t, y=23.0 * t, raio=44))
        self.decoracoes.append(Decoracao("obelisco", 14.6 * t, 24.8 * t, 1.0, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=14.6 * t, y=24.8 * t, raio=14))
        # o cronista fica ao lado da praça, virado para a fonte
        self.obstaculos.append(Obstaculo("circle", x=self.npc.x, y=self.npc.y - 4, raio=13))

        # detalhes da vila: lâmpadas, bancos, canteiros, placa e caixotes
        for lx, ly, e in ((8.6, 21.6, 0.9), (14.4, 21.6, 0.9), (8.6, 24.8, 0.9), (12.9, 26.1, 0.85)):
            self.decoracoes.append(Decoracao("lampiao", lx * t, ly * t, e, 0, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=lx * t, y=ly * t - 4, raio=6 * e))
        for bx, by in ((9.9, 24.3), (13.1, 24.3)):
            self.decoracoes.append(Decoracao("banco", bx * t, by * t, 1.0, 0, 0))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(bx * t - 30), int(by * t - 24), 60, 20)))
        for gx, gy, e in ((8.9, 22.8, 0.9), (14.1, 22.8, 0.9), (10.4, 21.0, 0.8), (12.6, 21.0, 0.8)):
            self.decoracoes.append(Decoracao("jardim", gx * t, gy * t, e, 0, rnd.uniform(0, 6.28)))
        self.decoracoes.append(Decoracao("placa", 16.3 * t, 23.0 * t, 1.0, 0, 0))
        self.obstaculos.append(Obstaculo("circle", x=16.3 * t, y=23.0 * t - 4, raio=6))
        for kx, ky, e in ((10.6, 21.5, 0.9), (12.5, 21.5, 0.85)):
            self.decoracoes.append(Decoracao("caixote", kx * t, ky * t, e, 0, 0))
            self.obstaculos.append(Obstaculo("rect", rect=pygame.Rect(int(kx * t - 16 * e), int(ky * t - 30 * e), int(32 * e), int(30 * e))))
        # quintal no canto onde a casa 3 fica no modo vetorial
        for bx, by in ((9.35, 26.55), (10.0, 26.85)):
            self.decoracoes.append(Decoracao("barril", bx * t, by * t, 1.0, 0, 0, pixel=True))
            self.obstaculos.append(Obstaculo("circle", x=bx * t, y=by * t - 8, raio=10, pixel=True))
        self.decoracoes.append(Decoracao("vaso", 10.65 * t, 26.35 * t, 1.0, 0, 0, pixel=True))
        self.obstaculos.append(Obstaculo("circle", x=10.65 * t, y=26.35 * t - 4, raio=7, pixel=True))

        # pedras delimitando a praça
        for i in range(14):
            ang = i * math.tau / 14
            x = 11.5 * t + math.cos(ang) * 4.4 * t
            y = 23 * t + math.sin(ang) * 4.4 * t
            self.decoracoes.append(Decoracao("rocha", x, y, 0.45, i, rnd.uniform(0, 6.28)))

        # estátuas e altares nas Ruínas
        for i in range(7):
            x = rnd.uniform(24 * t, 42 * t)
            y = rnd.uniform(4 * t, 40 * t)
            self.decoracoes.append(Decoracao("estatua", x, y, rnd.uniform(0.8, 1.1), i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 6, raio=16))
        for i in range(4):
            x = rnd.uniform(24 * t, 42 * t)
            y = rnd.uniform(4 * t, 40 * t)
            self.decoracoes.append(Decoracao("altar", x, y, rnd.uniform(0.9, 1.1), i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=14))

        # estalagmites e cogumelos luminosos na Caverna
        for i in range(18):
            x = rnd.uniform(45 * t, 63 * t)
            y = rnd.uniform(2 * t, 42 * t)
            self.decoracoes.append(Decoracao("estalagmite", x, y, rnd.uniform(0.7, 1.2), i, rnd.uniform(0, 6.28)))
            self.obstaculos.append(Obstaculo("circle", x=x, y=y - 4, raio=10))
        for i in range(14):
            x = rnd.uniform(45 * t, 63 * t)
            y = rnd.uniform(2 * t, 42 * t)
            cor = rnd.choice(((120, 220, 255), (180, 120, 255), (120, 240, 190)))
            self.decoracoes.append(Decoracao("cogumelo", x, y, rnd.uniform(0.7, 1.1), i, rnd.uniform(0, 6.28), cor))

        # bandeiras na vila e nas ruínas
        for i, (bx, by) in enumerate(((8.2, 20.6), (14.8, 20.6), (8.2, 25.4), (14.8, 25.4))):
            self.decoracoes.append(Decoracao("bandeira", bx * t, by * t, 0.9, i, rnd.uniform(0, 6.28), (150, 60, 70)))
        for i in range(5):
            x = rnd.uniform(24 * t, 42 * t)
            y = rnd.uniform(4 * t, 40 * t)
            self.decoracoes.append(Decoracao("bandeira", x, y, rnd.uniform(0.7, 1.0), i, rnd.uniform(0, 6.28), (90, 120, 180)))

        self.decoracoes.sort(key=lambda d: d.y)

    # ------------------------------------------------------------------ grama
    def _em_agua(self, x: float, y: float) -> bool:
        for tipo, cx, cy, rx, ry in self.aguas:
            if ((x - cx) / max(1.0, rx)) ** 2 + ((y - cy) / max(1.0, ry)) ** 2 <= 1.0:
                return True
        return False

    def _gerar_grama(self) -> None:
        """Tufos animados por bioma; são desenhados por cima do terreno."""
        rnd = random.Random(9091)
        t = TILE
        self.grama.clear()

        def adicionar(
            x0: float, x1: float, y0: float, y1: float, quantidade: int,
            cores: tuple[tuple[int, int, int], ...],
            flores: tuple[tuple[int, int, int], ...] = (),
            tipo: str = "grama", evitar_vila: bool = False,
        ) -> None:
            for _ in range(quantidade):
                x = rnd.uniform(x0, x1)
                y = rnd.uniform(y0, y1)
                if self._em_agua(x, y):
                    continue
                if evitar_vila and self.vila.rect.inflate(t * 1.2, t * 1.2).collidepoint(x, y):
                    continue
                if self.colidir_circulo(x, y, 4):
                    continue
                if flores and rnd.random() < 0.12:
                    self.grama.append((x, y, rnd.choice(flores), rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.25), "flor"))
                else:
                    self.grama.append((x, y, rnd.choice(cores), rnd.uniform(0, 6.28), rnd.uniform(0.6, 1.3), tipo))

        adicionar(
            0.5 * t, 21.5 * t, 1.5 * t, 42.5 * t, 260,
            ((58, 128, 72), (74, 146, 82), (48, 110, 64), (88, 158, 92)),
            ((236, 222, 120), (230, 150, 180), (220, 240, 240)),
            evitar_vila=True,
        )
        adicionar(
            22.5 * t, 43.5 * t, 1.5 * t, 42.5 * t, 120,
            ((96, 108, 72), (112, 120, 82), (82, 98, 68)),
            ((214, 200, 130), (190, 180, 150)),
        )
        adicionar(
            44.5 * t, 63.5 * t, 1.5 * t, 42.5 * t, 90,
            ((86, 190, 214), (150, 120, 230), (92, 214, 180)),
            tipo="sporo",
        )
        adicionar(
            64.5 * t, 83.5 * t, 1.5 * t, 42.5 * t, 180,
            ((66, 104, 60), (88, 126, 70), (54, 92, 54)),
            ((206, 220, 120), (180, 230, 140)),
        )
        adicionar(
            84.5 * t, 103.5 * t, 1.5 * t, 42.5 * t, 120,
            ((118, 76, 68), (146, 88, 78), (96, 64, 62)),
            ((240, 120, 60), (250, 170, 80)),
            tipo="sporo",
        )
        adicionar(
            104.5 * t, 123.5 * t, 13 * t, 42.5 * t, 150,
            ((132, 214, 224), (176, 214, 248), (146, 174, 236)),
            ((244, 240, 190), (224, 250, 255), (214, 206, 250)),
            tipo="sporo",
        )
        adicionar(
            104.5 * t, 123.5 * t, 1.5 * t, 11.5 * t, 90,
            ((90, 60, 130), (120, 80, 170), (70, 46, 110)),
            ((180, 120, 220), (220, 160, 200), (140, 100, 190)),
            tipo="sporo",
        )
        adicionar(
            5.5 * t, 17.5 * t, 16.5 * t, 29.5 * t, 80,
            ((74, 140, 78), (90, 158, 88)),
            ((236, 222, 120), (230, 150, 180), (220, 240, 240)),
            evitar_vila=True,
        )
        adicionar(
            84.5 * t, 86.0 * t, 15.0 * t, 30.0 * t, 24,
            ((78, 110, 66), (96, 128, 76)),
            ((226, 210, 120),),
        )
        adicionar(
            95.0 * t, 103.0 * t, 15.0 * t, 30.0 * t, 36,
            ((82, 112, 68), (100, 132, 78)),
            ((226, 210, 120), (210, 160, 120)),
        )

    # ------------------------------------------------------------------ água
    def desenhar_grama(self, surf: pygame.Surface, camera: Camera, passo: int = 1) -> None:
        for i in range(0, len(self.grama), max(1, passo)):
            x, y, cor, fase, escala, tipo = self.grama[i]
            sx, sy = camera.aplicar((x, y))
            if sx < -12 or sy < -12 or sx > LARGURA + 12 or sy > ALTURA + 12:
                continue
            sway = math.sin(self.tempo * 1.5 + fase) * 2.0 * escala
            if tipo == "flor":
                pygame.draw.line(surf, (54, 104, 58), (int(sx), int(sy)), (int(sx + sway * 0.3), int(sy - 7 * escala)), 1)
                px, py = int(sx + sway * 0.3), int(sy - 8 * escala)
                for i in range(4):
                    ang = i * math.tau / 4
                    pygame.draw.circle(surf, cor, (int(px + math.cos(ang) * 2 * escala), int(py + math.sin(ang) * 2 * escala)), max(1, int(1.6 * escala)))
                pygame.draw.circle(surf, (250, 230, 140), (px, py), max(1, int(1.2 * escala)))
            elif tipo == "sporo":
                pygame.draw.circle(surf, cor, (int(sx + sway), int(sy - 5 * escala)), max(1, int(2 * escala)))
                pygame.draw.circle(surf, (240, 255, 250), (int(sx + sway - 1), int(sy - 6 * escala)), 1)
            else:
                for i in range(3):
                    ox = (i - 1) * 2.4 * escala
                    altura = (6 + i * 1.8) * escala
                    pygame.draw.line(
                        surf, cor,
                        (int(sx + ox), int(sy)),
                        (int(sx + ox + sway * 0.5), int(sy - altura)), 1,
                    )

    def desenhar_agua(self, surf: pygame.Surface, camera: Camera) -> None:
        if pixel_arte.ATIVO:
            pixel_agua.desenhar(surf, camera, self.aguas, self.tempo)
            return
        for i, (tipo, cx, cy, rx, ry) in enumerate(self.aguas):
            sx, sy = camera.aplicar((cx, cy))
            if sx + rx < -20 or sy + ry < -20 or sx - rx > LARGURA + 20 or sy - ry > ALTURA + 20:
                continue
            cor = (120, 210, 230) if tipo == "lago" else (104, 176, 118)
            for k in range(2):
                f = ((self.tempo * 0.16 + i * 0.21 + k / 2.0) % 1.0)
                rx_k = rx * (0.18 + 0.72 * f)
                ry_k = ry * (0.18 + 0.72 * f)
                pygame.draw.ellipse(
                    surf, cor,
                    (int(sx - rx_k), int(sy - ry_k), int(rx_k * 2), int(ry_k * 2)), 1,
                )
            for k in range(7):
                ang = k * math.tau / 7 + self.tempo * 0.08 + i
                px = sx + math.cos(ang) * rx * 0.58
                py = sy + math.sin(ang) * ry * 0.58
                pygame.draw.line(surf, (210, 244, 250), (int(px - 3), int(py)), (int(px + 3), int(py)), 1)
            # espuma na margem
            for k in range(10):
                ang = k * math.tau / 10 + i * 0.4
                px = sx + math.cos(ang) * rx * 0.97
                py = sy + math.sin(ang) * ry * 0.97
                pygame.draw.circle(surf, (200, 232, 224), (int(px), int(py)), 1)

    # ------------------------------------------------------------------ detalhes de chão
    def _gerar_detalhes(self) -> None:
        """Pedrinhas, ossos, gravetos e brasas: quebram o tapete do terreno."""
        rnd = random.Random(7731)
        t = TILE
        self.detalhes.clear()

        def area(
            x0: float, x1: float, y0: float, y1: float, quantidade: int,
            tipos: tuple[tuple[str, tuple[int, int, int], float], ...],
        ) -> None:
            for _ in range(quantidade):
                x = rnd.uniform(x0, x1)
                y = rnd.uniform(y0, y1)
                if self._em_agua(x, y):
                    continue
                if self.vila.rect.collidepoint(x, y) or self.vila_veyra.rect.collidepoint(x, y):
                    continue
                if self.colidir_circulo(x, y, 8):
                    continue
                tipo, cor, escala = rnd.choice(tipos)
                self.detalhes.append((tipo, x, y, cor, rnd.uniform(0, 6.28), escala * rnd.uniform(0.75, 1.3)))

        area(
            0.5 * t, 21.5 * t, 1.5 * t, 42.5 * t, 150,
            (
                ("pedra", (96, 100, 92), 0.9),
                ("folhas", (150, 138, 74), 0.8),
                ("graveto", (92, 70, 48), 0.9),
                ("cogumelo", (222, 204, 150), 0.7),
            ),
        )
        area(
            22.5 * t, 43.5 * t, 1.5 * t, 42.5 * t, 170,
            (
                ("pedra", (128, 124, 126), 1.0),
                ("rachadura", (58, 58, 64), 1.2),
                ("osso", (208, 198, 168), 0.9),
                ("cranio", (216, 206, 176), 0.8),
                ("pedra", (100, 96, 100), 0.8),
            ),
        )
        area(
            44.5 * t, 63.5 * t, 1.5 * t, 42.5 * t, 160,
            (
                ("cogumelo", (122, 226, 210), 1.0),
                ("estilhaco", (166, 132, 236), 0.9),
                ("pedra", (72, 62, 94), 0.9),
                ("rachadura", (52, 42, 72), 1.1),
            ),
        )
        area(
            64.5 * t, 83.5 * t, 1.5 * t, 42.5 * t, 180,
            (
                ("osso", (196, 188, 158), 0.9),
                ("graveto", (78, 70, 48), 1.0),
                ("pedra", (84, 92, 72), 0.8),
                ("cranio", (202, 194, 164), 0.75),
                ("cogumelo", (206, 224, 140), 0.7),
            ),
        )
        area(
            84.5 * t, 103.5 * t, 1.5 * t, 42.5 * t, 190,
            (
                ("brasa", (250, 138, 70), 1.0),
                ("estilhaco", (206, 92, 96), 1.0),
                ("pedra", (78, 64, 70), 0.9),
                ("rachadura", (96, 52, 60), 1.3),
                ("osso", (188, 168, 148), 0.85),
            ),
        )
        area(
            104.5 * t, 123.5 * t, 13 * t, 42.5 * t, 180,
            (
                ("estilhaco", (186, 232, 250), 1.0),
                ("pedra", (150, 164, 196), 0.9),
                ("cogumelo", (154, 240, 236), 0.8),
                ("rachadura", (88, 110, 160), 1.1),
            ),
        )
        area(
            104.5 * t, 123.5 * t, 1.5 * t, 11.5 * t, 110,
            (
                ("estilhaco", (170, 120, 220), 1.0),
                ("pedra", (90, 70, 120), 0.9),
                ("cogumelo", (150, 90, 190), 0.8),
                ("rachadura", (70, 40, 100), 1.1),
            ),
        )

    def desenhar_detalhes(self, surf: pygame.Surface, camera: Camera, passo: int = 1) -> None:
        for i in range(0, len(self.detalhes), max(1, passo)):
            tipo, x, y, cor, fase, escala = self.detalhes[i]
            sx, sy = camera.aplicar((x, y))
            if sx < -24 or sy < -24 or sx > LARGURA + 24 or sy > ALTURA + 24:
                continue
            ix, iy = int(sx), int(sy)
            e = escala
            if tipo == "pedra":
                pygame.draw.ellipse(surf, (34, 32, 38), (ix - int(4 * e), iy - int(2 * e), int(9 * e), int(5 * e)))
                pygame.draw.ellipse(surf, cor, (ix - int(3 * e), iy - int(3 * e), int(7 * e), int(4 * e)))
                pygame.draw.line(surf, tuple(min(255, c + 30) for c in cor), (ix - int(2 * e), iy - int(2 * e)), (ix + int(2 * e), iy - int(2 * e)), 1)
            elif tipo == "folhas":
                for i in range(3):
                    ox = (i - 1) * 4 * e
                    pygame.draw.ellipse(
                        surf, cor if i != 1 else tuple(max(0, c - 26) for c in cor),
                        (ix + int(ox), iy + int((i % 2) * 2 * e), max(2, int(4 * e)), max(1, int(2 * e))),
                    )
            elif tipo == "graveto":
                pygame.draw.line(surf, (46, 34, 24), (ix - int(7 * e), iy + int(2 * e)), (ix + int(7 * e), iy - int(2 * e)), max(1, int(2 * e)))
                pygame.draw.line(surf, cor, (ix - int(6 * e), iy + int(1 * e)), (ix + int(6 * e), iy - int(2 * e)), 1)
                pygame.draw.line(surf, (58, 44, 30), (ix + int(2 * e), iy - int(1 * e)), (ix + int(5 * e), iy - int(5 * e)), 1)
            elif tipo == "cogumelo":
                brilho = 0.5 + 0.5 * math.sin(self.tempo * 2.2 + fase)
                halo_suave(surf, (sx, sy - 2 * e), 11 * e, cor, alpha=int(24 + 22 * brilho))
                for ox, altura in ((-3, 4), (2, 6), (5, 3)):
                    px = ix + int(ox * e)
                    pygame.draw.line(surf, (216, 210, 190), (px, iy), (px, iy - int(altura * e)), 1)
                    pygame.draw.circle(surf, cor, (px, iy - int(altura * e)), max(2, int(2.4 * e)))
            elif tipo == "rachadura":
                pts = [(ix, iy)]
                ox, oy = 0.0, 0.0
                for i in range(4):
                    ox += math.cos(fase + i * 1.7) * 6 * e
                    oy += math.sin(fase + i * 1.3) * 3 * e
                    pts.append((int(ix + ox), int(iy + oy)))
                pygame.draw.lines(surf, cor, False, pts, max(1, int(e)))
            elif tipo == "osso":
                ang = fase
                dx, dy = math.cos(ang) * 7 * e, math.sin(ang) * 3 * e
                pygame.draw.line(surf, (48, 44, 38), (int(ix - dx), int(iy - dy)), (int(ix + dx), int(iy + dy)), max(2, int(3 * e)))
                pygame.draw.line(surf, cor, (int(ix - dx), int(iy - dy)), (int(ix + dx), int(iy + dy)), max(1, int(2 * e)))
                for sinal in (-1, 1):
                    pygame.draw.circle(surf, cor, (int(ix + dx * sinal), int(iy + dy * sinal)), max(1, int(2 * e)))
            elif tipo == "cranio":
                pygame.draw.circle(surf, (48, 44, 38), (ix, iy - int(3 * e)), max(3, int(5 * e)))
                pygame.draw.circle(surf, cor, (ix, iy - int(3 * e)), max(2, int(4 * e)))
                pygame.draw.circle(surf, (34, 30, 28), (ix - int(2 * e), iy - int(3 * e)), max(1, int(e)))
                pygame.draw.circle(surf, (34, 30, 28), (ix + int(2 * e), iy - int(3 * e)), max(1, int(e)))
                pygame.draw.line(surf, (34, 30, 28), (ix - int(2 * e), iy, ), (ix + int(2 * e), iy), max(1, int(e)))
            elif tipo == "estilhaco":
                brilho = 0.5 + 0.5 * math.sin(self.tempo * 1.8 + fase)
                pts = [
                    (ix, iy - int(7 * e)), (ix + int(4 * e), iy - int(2 * e)),
                    (ix + int(2 * e), iy + int(3 * e)), (ix - int(3 * e), iy + int(2 * e)),
                ]
                pygame.draw.polygon(surf, (34, 26, 40), pts)
                pygame.draw.polygon(surf, cor, pts)
                pygame.draw.line(surf, (250, 226, 240), (ix, iy - int(5 * e)), (ix + int(2 * e), iy - int(2 * e)), 1)
                if brilho > 0.72:
                    pygame.draw.circle(surf, (255, 236, 246), (ix + int(1 * e), iy - int(3 * e)), 1)
            elif tipo == "brasa":
                pulso = 0.5 + 0.5 * math.sin(self.tempo * 3.0 + fase)
                halo_suave(surf, (sx, sy), (9 + 4 * pulso) * e, cor, alpha=int(30 + 40 * pulso))
                pygame.draw.circle(surf, (60, 28, 26), (ix, iy), max(2, int(3 * e)))
                pygame.draw.circle(surf, cor, (ix, iy - 1), max(1, int(2 * e)))
                pygame.draw.circle(surf, (255, 220, 150), (ix, iy - 1), 1)

    # ------------------------------------------------------------------ ambiente
    def _gerar_ambientais(self) -> None:
        rnd = random.Random(4455)
        self.ambientais.clear()
        for _ in range(170):
            x = rnd.uniform(0, self.largura)
            y = rnd.uniform(0, self.altura)
            if x >= 104 * TILE and y < 12 * TILE:
                cor = rnd.choice(((170, 110, 220), (120, 80, 180), (220, 140, 200)))
            elif x < 22 * TILE:
                cor = rnd.choice(((220, 230, 130), (180, 240, 150), (240, 220, 120)))
            elif x < 44 * TILE:
                cor = rnd.choice(((170, 170, 190), (200, 196, 180), (140, 140, 160)))
            elif x < 64 * TILE:
                cor = rnd.choice(((150, 110, 220), (110, 180, 240), (210, 120, 210)))
            elif x < 84 * TILE:
                cor = rnd.choice(((190, 230, 120), (130, 220, 160), (230, 210, 120)))
            elif x < 104 * TILE:
                cor = rnd.choice(((240, 130, 90), (220, 90, 110), (250, 190, 110)))
            else:
                cor = rnd.choice(((180, 240, 255), (230, 236, 255), (244, 220, 160)))
            self.ambientais.append({
                "x": x, "y": y, "fase": rnd.uniform(0, 6.28),
                "vel": rnd.uniform(0.3, 1.0), "raio": rnd.uniform(1.5, 3.4),
                "cor": cor, "amp": rnd.uniform(6, 24),
            })

    # ------------------------------------------------------------------ atmosfera viva
    def _gerar_atmosfera(self) -> None:
        """Névoa baixa e partículas por bioma, animadas a partir de self.tempo."""
        rnd = random.Random(5150)
        t = TILE
        self.nevoa.clear()
        self.particulas.clear()

        # névoa baixa: pântano, caverna e clareiras da floresta
        for _ in range(18):
            self.nevoa.append((
                "pantano",
                rnd.uniform(64.5 * t, 83.5 * t),
                rnd.uniform(1.5 * t, 42.5 * t),
                rnd.uniform(80, 170),
                rnd.uniform(26, 54),
                rnd.uniform(0, math.tau),
            ))
        for _ in range(9):
            self.nevoa.append((
                "caverna",
                rnd.uniform(44.5 * t, 63.5 * t),
                rnd.uniform(1.5 * t, 42.5 * t),
                rnd.uniform(70, 140),
                rnd.uniform(24, 46),
                rnd.uniform(0, math.tau),
            ))
        for _ in range(7):
            self.nevoa.append((
                "floresta",
                rnd.uniform(1.0 * t, 21.0 * t),
                rnd.uniform(1.5 * t, 42.5 * t),
                rnd.uniform(90, 180),
                rnd.uniform(26, 48),
                rnd.uniform(0, math.tau),
            ))

        def adicionar(
            tipo: str, x0: float, x1: float, y0: float, y1: float, quantidade: int,
            cores: tuple[tuple[int, int, int], ...], vel: tuple[float, float] = (0.2, 0.6),
        ) -> None:
            for _ in range(quantidade):
                x = rnd.uniform(x0, x1)
                y = rnd.uniform(y0, y1)
                self.particulas.append((
                    tipo, x, y, rnd.uniform(0, math.tau),
                    rnd.uniform(*vel), rnd.choice(cores),
                ))

        # floresta/clareira: pólen de dia e vaga-lumes à noite
        adicionar(
            "polem", 1.0 * t, 21.0 * t, 2.0 * t, 42.0 * t, 90,
            ((236, 224, 150), (224, 238, 170), (246, 232, 190)), (0.25, 0.6),
        )
        adicionar(
            "vaga_lume", 1.0 * t, 21.0 * t, 2.0 * t, 42.0 * t, 55,
            ((240, 232, 120), (190, 250, 150), (250, 240, 160)), (0.4, 1.0),
        )
        # pântano: bolhas nas lagoas e esporos
        for cx, cy, rx, ry in LAGOAS_PANTANO:
            for _ in range(18):
                ang = rnd.uniform(0, math.tau)
                dist = math.sqrt(rnd.random()) * 0.85
                self.particulas.append((
                    "bolha",
                    (cx + math.cos(ang) * rx * dist) * t,
                    (cy + math.sin(ang) * ry * dist) * t,
                    rnd.uniform(0, math.tau), rnd.uniform(0.35, 0.8),
                    rnd.choice(((170, 220, 180), (140, 210, 170), (200, 236, 190))),
                ))
        adicionar(
            "esporo", 64.5 * t, 83.5 * t, 2.0 * t, 42.0 * t, 80,
            ((190, 230, 130), (150, 220, 160), (220, 240, 150)), (0.2, 0.55),
        )
        # ruínas: poeira suspensa
        adicionar(
            "poeira", 22.5 * t, 43.5 * t, 2.0 * t, 42.0 * t, 60,
            ((196, 194, 180), (170, 172, 178), (210, 206, 190)), (0.15, 0.4),
        )
        # caverna: motes de cristal e gotas
        adicionar(
            "mote", 44.5 * t, 63.5 * t, 2.0 * t, 42.0 * t, 70,
            ((140, 220, 250), (180, 150, 250), (130, 240, 220)), (0.25, 0.7),
        )
        adicionar(
            "gota", 44.5 * t, 63.5 * t, 3.0 * t, 40.0 * t, 20,
            ((170, 220, 245), (200, 236, 255)), (0.5, 0.9),
        )
        # desfiladeiro: fagulhas subindo
        adicionar(
            "brasa", 84.5 * t, 103.5 * t, 3.0 * t, 41.0 * t, 90,
            ((250, 150, 80), (255, 110, 70), (255, 190, 110)), (0.35, 0.9),
        )
        # coração de Aether: motes de luz subindo
        adicionar(
            "mote", 104.5 * t, 123.5 * t, 13.0 * t, 42.0 * t, 90,
            ((176, 240, 255), (224, 236, 255), (232, 216, 160)), (0.25, 0.7),
        )
        # fenda do eclipse: motes escuros
        adicionar(
            "mote", 104.5 * t, 123.5 * t, 1.5 * t, 11.0 * t, 70,
            ((170, 110, 220), (120, 80, 180), (220, 140, 200)), (0.2, 0.6),
        )

    def desenhar_atmosfera(self, surf: pygame.Surface, camera: Camera) -> None:
        if self.qualidade < 0.55:
            return
        centro = (camera.x + LARGURA / 2, camera.y + ALTURA / 2)
        zona = self.zona_em(*centro)
        nome_zona = zona.nome if zona else ""
        if nome_zona in ("Pântano de Veyra", "Caverna de Cristal", "Floresta de Lumen", "Clareira de Lumen"):
            self._nevoa_overlay.fill((0, 0, 0, 0))
            cores = {
                "pantano": (128, 168, 124),
                "caverna": (110, 92, 158),
                "floresta": (188, 214, 186),
            }
            for tipo, x, y, rx, ry, fase in self.nevoa:
                sx, sy = camera.aplicar((x, y))
                if sx < -220 or sy < -120 or sx > LARGURA + 220 or sy > ALTURA + 120:
                    continue
                ox = math.sin(self.tempo * 0.11 + fase) * 34
                oy = math.cos(self.tempo * 0.08 + fase) * 9
                alpha = int(18 + 10 * math.sin(self.tempo * 0.5 + fase) + 8 * self.noite)
                pygame.draw.ellipse(
                    self._nevoa_overlay, (*cores[tipo], max(6, alpha)),
                    (int(sx + ox - rx), int(sy + oy - ry), int(rx * 2), int(ry * 2)),
                )
            surf.blit(self._nevoa_overlay, (0, 0))

        noite = self.noite
        for tipo, x, y, fase, vel, cor in self.particulas:
            sx, sy = camera.aplicar((x, y))
            if sx < -24 or sy < -24 or sx > LARGURA + 24 or sy > ALTURA + 24:
                continue
            ciclo = (self.tempo * vel + fase) % 1.0
            if tipo == "polem":
                px = sx + math.sin(self.tempo * 0.4 + fase) * 14
                py = sy + math.cos(self.tempo * 0.3 + fase) * 8 - ciclo * 12
                pygame.draw.circle(surf, cor, (int(px), int(py)), 1)
            elif tipo == "vaga_lume":
                brilho = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(self.tempo * 2.2 + fase))
                brilho *= 0.25 + 0.75 * noite
                px = sx + math.sin(self.tempo * 0.5 + fase) * 18
                py = sy + math.cos(self.tempo * 0.4 + fase) * 10
                c = tuple(int(v * brilho) for v in cor)
                pygame.draw.circle(surf, c, (int(px), int(py)), 2)
                if brilho > 0.55:
                    pygame.draw.circle(surf, tuple(min(255, int(v * 1.2)) for v in cor), (int(px), int(py)), 1)
            elif tipo == "bolha":
                px = sx + math.sin(self.tempo * 0.8 + fase) * 3
                py = sy - ciclo * 26
                c = tuple(int(v * (0.55 + 0.45 * (1.0 - ciclo))) for v in cor)
                pygame.draw.circle(surf, c, (int(px), int(py)), 2, 1)
                if ciclo < 0.7:
                    pygame.draw.circle(surf, c, (int(px - 1), int(py - 1)), 1)
            elif tipo == "esporo":
                px = sx + math.sin(self.tempo * 0.35 + fase) * 16
                py = sy - ciclo * 20
                pygame.draw.circle(surf, cor, (int(px), int(py)), 1)
            elif tipo == "poeira":
                px = sx + math.sin(self.tempo * 0.25 + fase) * 20
                py = sy + math.cos(self.tempo * 0.2 + fase) * 12
                pygame.draw.circle(surf, cor, (int(px), int(py)), 1)
            elif tipo == "mote":
                px = sx + math.sin(self.tempo * 0.5 + fase) * 12
                py = sy + math.cos(self.tempo * 0.35 + fase) * 14
                brilho = 0.5 + 0.5 * math.sin(self.tempo * 2.6 + fase)
                c = tuple(int(v * (0.5 + 0.5 * brilho)) for v in cor)
                pygame.draw.circle(surf, c, (int(px), int(py)), 1 + int(brilho))
            elif tipo == "gota":
                px = sx + math.sin(fase) * 4
                py = sy + ciclo * 34
                pygame.draw.line(surf, cor, (int(px), int(py)), (int(px), int(py + 5)), 1)
            elif tipo == "brasa":
                px = sx + math.sin(self.tempo * 1.1 + fase) * 10
                py = sy - ciclo * 44
                brilho = 1.0 - ciclo
                c = tuple(int(v * (0.25 + 0.75 * brilho)) for v in cor)
                pygame.draw.circle(surf, c, (int(px), int(py)), 1 + int(brilho))
                if brilho > 0.75:
                    pygame.draw.circle(surf, (255, 226, 170), (int(px), int(py)), 1)

    # ------------------------------------------------------------------ consultas
    def zona_em(self, x: float, y: float) -> Zona | None:
        if self.vila.rect.collidepoint(x, y):
            return self.vila
        if self.vila_veyra.rect.collidepoint(x, y):
            return self.vila_veyra
        for z in self.zonas:
            if z.rect.collidepoint(x, y):
                return z
        return None

    def colidir_rect(self, rect: pygame.Rect) -> bool:
        for o in self.obstaculos:
            if o.pixel is not None and o.pixel != pixel_arte.ATIVO:
                continue
            if not rect.colliderect(o.bounds):
                continue
            if o.colide_rect(rect):
                return True
        return False

    def colidir_circulo(self, x: float, y: float, raio: float) -> bool:
        caixa = pygame.Rect(int(x - raio) - 1, int(y - raio) - 1, int(raio * 2) + 2, int(raio * 2) + 2)
        for o in self.obstaculos:
            if o.pixel is not None and o.pixel != pixel_arte.ATIVO:
                continue
            if not caixa.colliderect(o.bounds):
                continue
            if o.colide_circulo(x, y, raio):
                return True
        return False

    def ponto_spawn(self, zona: Zona, longe_de: Sequence[float] | None = None, dist_min: float = 320.0) -> tuple[float, float] | None:
        for _ in range(50):
            x = random.uniform(zona.rect.left + 48, zona.rect.right - 48)
            y = random.uniform(zona.rect.top + 48, zona.rect.bottom - 48)
            if longe_de is not None and distancia((x, y), longe_de) < dist_min:
                continue
            if self.colidir_circulo(x, y, 22):
                continue
            if self.vila.rect.collidepoint(x, y):
                continue
            if self.vila_veyra.rect.collidepoint(x, y):
                continue
            return x, y
        return None

    # ------------------------------------------------------------------ desenho
    def _gerar_camada_fundo(self, semente: int, alpha_base: int, tamanho: int) -> pygame.Surface:
        """Névoa atmosférica gerada em 1/4 de resolução e suavizada ao subir de escala."""
        rnd = random.Random(semente)
        w, h = self.largura // 4, ALTURA // 4
        pequena = pygame.Surface((w, h), pygame.SRCALPHA)
        cores = {
            "Clareira de Lumen": (210, 230, 190),
            "Floresta de Lumen": (120, 205, 150),
            "Ruínas de Aether": (160, 170, 200),
            "Caverna de Cristal": (130, 100, 190),
            "Pântano de Veyra": (120, 160, 110),
            "Vila de Veyra": (220, 190, 140),
            "Desfiladeiro de Obsidiana": (190, 120, 120),
            "Coração de Aether": (190, 220, 255),
            "Fenda do Eclipse": (190, 140, 240),
        }
        padrao = (150, 150, 170)
        for x in range(0, w, 24):
            zona = self.zona_em(x * 4 + 48, ALTURA // 2)
            cor = (*cores.get(zona.nome if zona else "", padrao), alpha_base)
            for _ in range(2):
                cx = x + rnd.randrange(-12, 12)
                cy = rnd.randrange(8, h - 8)
                rx = rnd.randrange(tamanho, tamanho * 2)
                ry = rnd.randrange(max(4, tamanho // 3), tamanho)
                pygame.draw.ellipse(pequena, cor, (cx - rx, cy - ry, rx * 2, ry * 2))
        grande = pygame.Surface((self.largura, ALTURA), pygame.SRCALPHA)
        pygame.transform.smoothscale(pequena, (self.largura, ALTURA), grande)
        return grande

    def desenhar_fundo(self, surf: pygame.Surface, camera: Camera) -> None:
        """Duas camadas de névoa movendo mais devagar que o chão (parallax)."""
        if self.qualidade < 0.55:
            return
        for camada, fator in ((self.camada_longe, 0.25), (self.camada_perto, 0.55)):
            desloc = int(camera.x * fator) % max(1, self.largura - LARGURA)
            surf.blit(camada, (0, 0), pygame.Rect(desloc, 0, LARGURA, ALTURA))

    def desenhar_terreno(self, surf: pygame.Surface, camera: Camera) -> None:
        x = int(clamp(camera.x, 0, max(0, self.largura - LARGURA)))
        y = int(clamp(camera.y, 0, max(0, self.altura - ALTURA)))
        surf.blit(self.terreno, (0, 0), pygame.Rect(x, y, LARGURA, ALTURA))
        if pixel_arte.ATIVO:
            self._desenhar_chao_pixel(surf, camera)

    def _desenhar_chao_pixel(self, surf: pygame.Surface, camera: Camera) -> None:
        """Sobrepõe o chão em pixel art nos biomas (experimental)."""
        if self._biomas_pixel is None:
            self._biomas_pixel = self._montar_biomas_pixel()
        for bioma in self._biomas_pixel:
            pixel_terreno.desenhar(surf, camera, bioma)

        # Vila de Veyra tem superfície própria, com a praça de pedra no centro.
        rect = self.vila_veyra.rect
        sx, sy = camera.aplicar((rect.left, rect.top))
        if not (sx > LARGURA or sy > ALTURA or sx + rect.w < 0 or sy + rect.h < 0):
            surf.blit(pixel_terreno.superficie_vila(rect.w, rect.h), (int(sx), int(sy)))

        # A Clareira de Lumen entra por cima da floresta, com bordas esfumadas.
        rect = self.vila.rect
        sx, sy = camera.aplicar((rect.left, rect.top))
        if not (sx > LARGURA or sy > ALTURA or sx + rect.w < 0 or sy + rect.h < 0):
            surf.blit(pixel_terreno.superficie(rect.w, rect.h), (int(sx), int(sy)))

    def _montar_biomas_pixel(self) -> list[pixel_terreno.Bioma]:
        """Chão de cada bioma, com as trilhas que o jogador já conhece."""
        t = TILE
        estrada = tuple((x * t, y * t) for x, y in CAMINHO_PRINCIPAL)
        trilhas = tuple(
            tuple((x * t, y * t) for x, y in pontos) for pontos in TRILHAS_FLORESTA
        )
        pantano = tuple((x * t, y * t) for x, y in CAMINHO_PANTANO)
        return [
            pixel_terreno.Bioma(
                "floresta", pygame.Rect(0, 0, 22 * t, self.altura), (estrada, *trilhas),
            ),
            pixel_terreno.Bioma(
                "ruinas", pygame.Rect(22 * t, 0, 22 * t, self.altura), (estrada,),
            ),
            pixel_terreno.Bioma(
                "caverna", pygame.Rect(44 * t, 0, 20 * t, self.altura), (estrada,),
            ),
            pixel_terreno.Bioma(
                "pantano", pygame.Rect(64 * t, 0, 20 * t, self.altura), (estrada, pantano),
            ),
            pixel_terreno.Bioma(
                "desfiladeiro", pygame.Rect(84 * t, 0, 20 * t, self.altura), (estrada,),
            ),
            pixel_terreno.Bioma(
                "coracao", pygame.Rect(104 * t, 0, 20 * t, self.altura), (estrada,),
            ),
            # a Fenda cobre o norte do Coração: desenha por último
            pixel_terreno.Bioma(
                "fenda", pygame.Rect(104 * t, 0, 20 * t, 12 * t), (estrada,),
            ),
        ]

    def desenhar_ambiente(self, surf: pygame.Surface, camera: Camera) -> None:
        self.desenhar_atmosfera(surf, camera)
        passo = 1 if self.qualidade >= 0.9 else 2
        for i in range(0, len(self.ambientais), passo):
            p = self.ambientais[i]
            sx, sy = camera.aplicar((p["x"], p["y"]))
            if sx < -10 or sy < -10 or sx > LARGURA + 10 or sy > ALTURA + 10:
                continue
            ox = math.sin(self.tempo * p["vel"] + p["fase"]) * p["amp"]
            oy = math.cos(self.tempo * p["vel"] * 0.7 + p["fase"]) * p["amp"] * 0.5
            alpha = 0.45 + 0.35 * math.sin(self.tempo * 2 + p["fase"])
            cor = tuple(int(c * alpha) for c in p["cor"])
            pygame.draw.circle(surf, cor, (int(sx + ox), int(sy + oy)), int(p["raio"]))

    def atualizar(self, dt: float) -> None:
        self.tempo += dt
