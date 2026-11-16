"""Desenho vetorial do personagem, com animação procedural por classe."""
from __future__ import annotations

import math
from typing import Any, Sequence

import pygame

import pixel_arte
import pixel_player
from utils import Camera, halo_suave, sombra

CONTORNO = (26, 24, 34)
PELE = (242, 202, 170)
PELE_SOMBRA = (206, 162, 132)


def _c(base: Sequence[int], flash: bool) -> tuple[int, int, int]:
    return (255, 255, 255) if flash else tuple(base[:3])


def _misturar(a: Sequence[int], b: Sequence[int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1.0 - t) + b[i] * t) for i in range(3))


def _capsula(surf: pygame.Surface, cor: Sequence[int], p1: Sequence[float], p2: Sequence[float], largura: int) -> None:
    x1, y1 = int(p1[0]), int(p1[1])
    x2, y2 = int(p2[0]), int(p2[1])
    pygame.draw.line(surf, tuple(cor[:3]), (x1, y1), (x2, y2), max(1, largura))
    pygame.draw.circle(surf, tuple(cor[:3]), (x1, y1), max(1, largura // 2))
    pygame.draw.circle(surf, tuple(cor[:3]), (x2, y2), max(1, largura // 2))


def _capsula_borda(
    surf: pygame.Surface, cor: Sequence[int], borda: Sequence[int],
    p1: Sequence[float], p2: Sequence[float], largura: int,
) -> None:
    _capsula(surf, borda, p1, p2, largura + 3)
    _capsula(surf, cor, p1, p2, largura)


def _poly(surf: pygame.Surface, cor: Sequence[int], pontos: Sequence[Sequence[float]], borda: Sequence[int] | None = None, largura: int = 2) -> None:
    pts = [(int(x), int(y)) for x, y in pontos]
    pygame.draw.polygon(surf, tuple(cor[:3]), pts)
    if borda is not None:
        pygame.draw.polygon(surf, tuple(borda[:3]), pts, max(1, largura))


def _pernas(
    surf: pygame.Surface, sx: float, sy: float, fase: float, andando: bool,
    cor: Sequence[int], cor_bota: Sequence[int], flash: bool, largura: int = 8,
) -> None:
    swing = math.sin(fase) * 6.5 if andando else 0.0
    contorno = _c(CONTORNO, flash)
    # perna de trás
    _capsula_borda(surf, _c(cor, flash), contorno, (sx - 5, sy - 22), (sx - 5 + swing, sy - 3), largura)
    _capsula_borda(surf, _c(cor_bota, flash), contorno, (sx - 5 + swing, sy - 7), (sx - 5 + swing, sy - 1), largura + 2)
    # perna da frente
    _capsula_borda(surf, _c(cor, flash), contorno, (sx + 5, sy - 22), (sx + 5 - swing, sy - 3), largura)
    _capsula_borda(surf, _c(cor_bota, flash), contorno, (sx + 5 - swing, sy - 7), (sx + 5 - swing, sy - 1), largura + 2)


def _cabeca(
    surf: pygame.Surface, sx: float, sy: float, olhar: str, lado: int,
    cabelo: Sequence[int], flash: bool, chapeu: str = "",
) -> None:
    contorno = _c(CONTORNO, flash)
    pele = _c(PELE, flash)
    cabelo_c = _c(cabelo, flash)
    cx = sx + (lado * 2.5 if olhar in ("esquerda", "direita") else 0)
    cy = sy - 64
    # pescoço
    _capsula(surf, _c(PELE_SOMBRA, flash), (cx, cy + 12), (cx, cy + 18), 9)
    # cabelo/trás
    pygame.draw.circle(surf, contorno, (int(cx), int(cy)), 16)
    pygame.draw.circle(surf, cabelo_c, (int(cx), int(cy)), 14)
    # rosto
    if olhar != "cima":
        pygame.draw.circle(surf, contorno, (int(cx), int(cy + 2)), 13)
        pygame.draw.circle(surf, pele, (int(cx), int(cy + 2)), 12)
        # bochecha
        pygame.draw.circle(surf, _c((236, 156, 146), flash), (int(cx - 7), int(cy + 6)), 2)
        pygame.draw.circle(surf, _c((236, 156, 146), flash), (int(cx + 7), int(cy + 6)), 2)
        # olhos
        olho = _c((48, 40, 48), flash)
        if olhar == "esquerda":
            pygame.draw.circle(surf, olho, (int(cx - 6), int(cy + 1)), 2)
        elif olhar == "direita":
            pygame.draw.circle(surf, olho, (int(cx + 6), int(cy + 1)), 2)
        else:
            pygame.draw.circle(surf, olho, (int(cx - 5), int(cy + 1)), 2)
            pygame.draw.circle(surf, olho, (int(cx + 5), int(cy + 1)), 2)
        # boca
        pygame.draw.line(surf, _c((168, 104, 96), flash), (cx - 3, cy + 8), (cx + 3, cy + 8), 1)
    else:
        # nuca: cabelo cobre o rosto
        pygame.draw.circle(surf, cabelo_c, (int(cx), int(cy + 2)), 12)
        pygame.draw.circle(surf, _c(tuple(max(0, c - 24) for c in cabelo), flash), (int(cx), int(cy + 2)), 8)

    # franja
    if olhar != "cima":
        _poly(
            surf, cabelo_c,
            [(cx - 12, cy - 5), (cx - 4, cy - 13), (cx + 7, cy - 11), (cx + 12, cy - 4),
             (cx + 8, cy - 7), (cx + 1, cy - 4), (cx - 5, cy - 8)],
            contorno, 1,
        )
    # chapéu / elmo
    if chapeu == "maga":
        brim = pygame.Rect(int(cx - 26), int(cy - 16), 52, 10)
        pygame.draw.ellipse(surf, contorno, brim.inflate(3, 3))
        pygame.draw.ellipse(surf, _c((96, 62, 158), flash), brim)
        cone = [(cx - 16, cy - 15), (cx + 16, cy - 15), (cx + 6, cy - 54), (cx - 3, cy - 58)]
        _poly(surf, _c((128, 88, 196), flash), cone, contorno, 2)
        pygame.draw.line(surf, _c((224, 186, 108), flash), (cx - 13, cy - 18), (cx + 13, cy - 18), 3)
        pygame.draw.circle(surf, _c((248, 218, 120), flash), (int(cx + 2), int(cy - 54)), 5)
        for ox, oy in ((-7, -28), (5, -38), (9, -24)):
            pygame.draw.circle(surf, _c((248, 218, 120), flash), (int(cx + ox), int(cy + oy)), 2)
    elif chapeu == "cavaleiro":
        # elmo aberto com guarda-malas, nasal e crista
        pygame.draw.circle(surf, contorno, (int(cx), int(cy - 2)), 16)
        pygame.draw.circle(surf, _c((150, 160, 182), flash), (int(cx), int(cy - 2)), 14)
        pygame.draw.circle(surf, _c((104, 116, 140), flash), (int(cx), int(cy - 2)), 11)
        # abertura do rosto
        pygame.draw.ellipse(
            surf, _c((52, 46, 54), flash),
            (int(cx - 9), int(cy - 5), 18, 15),
        )
        # guardas laterais
        for sinal in (-1, 1):
            _poly(
                surf, _c((176, 186, 204), flash),
                [(cx + sinal * 13, cy - 6), (cx + sinal * 10, cy + 11),
                 (cx + sinal * 5, cy + 13), (cx + sinal * 6, cy - 3)],
                contorno, 1,
            )
        # nasal
        pygame.draw.line(surf, contorno, (cx, cy - 8), (cx, cy + 6), 4)
        pygame.draw.line(surf, _c((206, 214, 230), flash), (cx, cy - 8), (cx, cy + 5), 2)
        # sobrancelha e rivetes
        pygame.draw.line(surf, _c((226, 232, 244), flash), (cx - 10, cy - 8), (cx + 10, cy - 8), 2)
        # olhos dentro da abertura
        olho = _c((250, 226, 170), flash)
        if olhar == "esquerda":
            pygame.draw.circle(surf, olho, (int(cx - 5), int(cy + 1)), 2)
        elif olhar == "direita":
            pygame.draw.circle(surf, olho, (int(cx + 5), int(cy + 1)), 2)
        else:
            pygame.draw.circle(surf, olho, (int(cx - 4), int(cy + 1)), 2)
            pygame.draw.circle(surf, olho, (int(cx + 4), int(cy + 1)), 2)
        pygame.draw.line(surf, _c((140, 100, 96), flash), (cx - 3, cy + 6), (cx + 3, cy + 6), 1)
        for ox in (-11, 11):
            pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(cx + ox), int(cy - 2)), 2)
        # crista de crina
        for i in range(4):
            ox = -3 + i * 2
            pygame.draw.line(
                surf, _c((196, 64, 76), flash),
                (cx + ox, cy - 15), (cx + ox - 7, cy - 27 - i), 2,
            )
        pygame.draw.circle(surf, _c((240, 208, 120), flash), (int(cx), int(cy - 15)), 2)
    elif chapeu == "arqueira":
        # capuz
        capuz = [
            (cx - 17, cy + 6), (cx - 16, cy - 10), (cx - 6, cy - 20), (cx + 8, cy - 18),
            (cx + 17, cy - 6), (cx + 16, cy + 8), (cx + 10, cy + 2), (cx + 9, cy - 8),
            (cx - 9, cy - 8), (cx - 10, cy + 2),
        ]
        _poly(surf, _c((62, 142, 92), flash), capuz, contorno, 2)
        pygame.draw.line(surf, _c((92, 178, 116), flash), (cx - 13, cy - 8), (cx - 4, cy - 17), 2)
        # sombra interna do capuz
        pygame.draw.ellipse(
            surf, _c((34, 74, 50), flash),
            (int(cx - 10), int(cy - 10), 20, 10),
        )
        # pena dourada no capuz
        pygame.draw.line(surf, _c((228, 190, 108), flash), (cx + 12, cy - 14), (cx + 24, cy - 30), 2)
        pygame.draw.polygon(
            surf, _c((240, 220, 150), flash),
            [(cx + 24, cy - 30), (cx + 18, cy - 26), (cx + 26, cy - 22)],
        )


def _capa(
    surf: pygame.Surface, sx: float, sy: float, fase: float, andando: bool,
    cor: Sequence[int], cor_escura: Sequence[int], flash: bool, comprimento: float = 1.0,
) -> None:
    sway = math.sin(fase * 0.9 + 0.4) * (5.0 if andando else 2.0)
    topo = sy - 50
    base = sy - 10 + (6 if andando else 0)
    pts = [
        (sx - 14, topo), (sx + 14, topo),
        (sx + 20 + sway, base - 8), (sx + 12 + sway, base),
        (sx + sway * 1.4, base + 2), (sx - 12 + sway, base),
        (sx - 20 + sway, base - 8),
    ]
    pts = [(sx + (x - sx) * comprimento, sy + (y - sy) * comprimento) for x, y in pts]
    _poly(surf, _c(cor, flash), pts, _c(cor_escura, flash), 2)
    pygame.draw.line(surf, _c(tuple(min(255, c + 30) for c in cor), flash), (sx - 8, topo + 4), (sx - 4 + sway, base - 8), 1)
    # acabamento dourado na barra da capa
    pygame.draw.lines(
        surf, _c((228, 190, 108), flash), False,
        [(int(x), int(y)) for x, y in pts[2:7]], 1,
    )
    # dobras do tecido
    pygame.draw.line(surf, _c(cor_escura, flash), (sx - 4, topo + 8), (sx - 2 + sway * 0.6, base - 4), 1)
    pygame.draw.line(surf, _c(cor_escura, flash), (sx + 5, topo + 8), (sx + 4 + sway * 0.6, base - 4), 1)


def _espada(
    surf: pygame.Surface, mao: tuple[float, float], angulo: float, flash: bool,
    brilho: float = 0.0, cor: Sequence[int] | None = None,
) -> None:
    contorno = _c(CONTORNO, flash)
    cor_lamina = cor or (210, 218, 236)
    comprimento = 48
    ponta = (mao[0] + math.cos(angulo) * comprimento, mao[1] + math.sin(angulo) * comprimento)
    base = (mao[0] + math.cos(angulo) * 6, mao[1] + math.sin(angulo) * 6)
    # lâmina
    perp = angulo + math.pi / 2
    largura = 4.0
    pts = [
        (base[0] + math.cos(perp) * largura, base[1] + math.sin(perp) * largura),
        (ponta[0], ponta[1]),
        (base[0] - math.cos(perp) * largura, base[1] - math.sin(perp) * largura),
    ]
    _poly(surf, _c(cor_lamina, flash), pts, contorno, 2)
    pygame.draw.line(
        surf, _c(tuple(min(255, c + 40) for c in cor_lamina), flash),
        base, (ponta[0] - math.cos(angulo) * 4, ponta[1] - math.sin(angulo) * 4), 1,
    )
    # guarda
    guarda = (mao[0] + math.cos(angulo) * 6, mao[1] + math.sin(angulo) * 6)
    pygame.draw.line(
        surf, _c((228, 190, 108), flash),
        (guarda[0] + math.cos(perp) * 7, guarda[1] + math.sin(perp) * 7),
        (guarda[0] - math.cos(perp) * 7, guarda[1] - math.sin(perp) * 7), 3,
    )
    pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(mao[0]), int(mao[1])), 3)
    if brilho > 0:
        pygame.draw.circle(surf, (255, 250, 210), (int(ponta[0]), int(ponta[1])), int(3 + 3 * brilho))


def _escudo(surf: pygame.Surface, centro: tuple[float, float], flash: bool) -> None:
    contorno = _c(CONTORNO, flash)
    r = pygame.Rect(int(centro[0] - 12), int(centro[1] - 17), 24, 34)
    pygame.draw.ellipse(surf, contorno, r.inflate(4, 4))
    pygame.draw.ellipse(surf, _c((72, 112, 182), flash), r)
    pygame.draw.ellipse(surf, _c((218, 186, 108), flash), r, 2)
    for ox, oy in ((0, -11), (0, 11), (-8, 0), (8, 0)):
        pygame.draw.circle(surf, _c((232, 200, 120), flash), (int(centro[0] + ox), int(centro[1] + oy)), 1)
    pygame.draw.line(
        surf, _c((150, 196, 238), flash),
        (centro[0] - 4, centro[1] - 5), (centro[0] + 4, centro[1] - 5), 1,
    )
    pygame.draw.polygon(
        surf, _c((228, 194, 118), flash),
        [(centro[0], centro[1] - 9), (centro[0] + 5, centro[1]), (centro[0], centro[1] + 9), (centro[0] - 5, centro[1])],
    )


def _arco(
    surf: pygame.Surface, mao: tuple[float, float], lado: int, flash: bool, puxando: bool,
    cor: Sequence[int] | None = None,
) -> None:
    contorno = _c(CONTORNO, flash)
    cor_madeira = _c(cor or (150, 104, 62), flash)
    cx, cy = mao[0] + lado * 2, mao[1]
    rect = pygame.Rect(int(cx - 17), int(cy - 27), 34, 54)
    pygame.draw.arc(surf, contorno, rect.inflate(3, 3), -1.25, 1.25, 4)
    pygame.draw.arc(surf, cor_madeira, rect, -1.25, 1.25, 3)
    topo = (cx + math.cos(-1.25) * 17, cy + math.sin(-1.25) * 27)
    base = (cx + math.cos(1.25) * 17, cy + math.sin(1.25) * 27)
    pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(topo[0]), int(topo[1])), 2)
    pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(base[0]), int(base[1])), 2)
    corda_x = cx - lado * (14 if puxando else 2)
    pygame.draw.line(surf, _c((228, 220, 190), flash), topo, (corda_x, cy), 1)
    pygame.draw.line(surf, _c((228, 220, 190), flash), (corda_x, cy), base, 1)
    if puxando:
        pygame.draw.line(surf, _c((236, 240, 220), flash), (corda_x, cy), (cx + lado * 20, cy), 2)
        pygame.draw.polygon(
            surf, _c((210, 232, 200), flash),
            [(cx + lado * 20, cy), (cx + lado * 14, cy - 3), (cx + lado * 14, cy + 3)],
        )


def _cajado(
    surf: pygame.Surface, mao: tuple[float, float], lado: int, flash: bool, brilho: float,
    cor: Sequence[int] | None = None,
) -> None:
    contorno = _c(CONTORNO, flash)
    cor_orbe = cor or (198, 146, 250)
    topo = (mao[0] + lado * 3, mao[1] - 60)
    pygame.draw.line(surf, contorno, (int(mao[0]), int(mao[1] + 6)), (int(topo[0]), int(topo[1])), 6)
    pygame.draw.line(surf, _c((146, 104, 62), flash), (int(mao[0]), int(mao[1] + 6)), (int(topo[0]), int(topo[1])), 4)
    # orbe
    r = 8
    halo = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
    pygame.draw.circle(halo, (168, 120, 240, int(60 + 80 * brilho)), (r * 3, r * 3), int(r * 2.4))
    pygame.draw.circle(halo, (220, 190, 255, int(50 + 60 * brilho)), (r * 3, r * 3), int(r * 1.4))
    surf.blit(halo, (int(topo[0] - r * 3), int(topo[1] - r * 3)))
    pygame.draw.circle(surf, contorno, (int(topo[0]), int(topo[1])), r + 2)
    pygame.draw.circle(surf, _c(cor_orbe, flash), (int(topo[0]), int(topo[1])), r)
    pygame.draw.circle(surf, (246, 232, 255), (int(topo[0] - 2), int(topo[1] - 2)), 2)


def _efeito_ataque(surf: pygame.Surface, j: Any, sx: float, sy: float, olhar: str, lado: int) -> None:
    if j.ataque_anim <= 0:
        return
    t = 1.0 - j.ataque_anim / 0.24
    ang = j.angulo_ataque
    if j.classe == "Cavaleiro":
        temp = pygame.Surface((180, 180), pygame.SRCALPHA)
        centro = (90, 90)
        pts = [centro]
        for i in range(9):
            a = ang - 0.95 + 1.9 * i / 8
            pts.append((90 + math.cos(a) * (46 + 26 * t), 90 + math.sin(a) * (46 + 26 * t)))
        pygame.draw.polygon(temp, (255, 238, 178, int(110 * (1 - t))), pts)
        pygame.draw.lines(temp, (255, 252, 230, int(220 * (1 - t))), False, pts[1:], 3)
        surf.blit(temp, (int(sx - 90), int(sy - 34 - 90)))
    elif j.classe == "Arqueira":
        mao = (sx + lado * 20, sy - 34)
        pygame.draw.circle(surf, (240, 252, 220), (int(mao[0]), int(mao[1])), int(4 + 4 * (1 - t)))
        pygame.draw.line(
            surf, (220, 244, 190),
            (mao[0], mao[1]),
            (mao[0] + math.cos(ang) * 34, mao[1] + math.sin(ang) * 34), 2,
        )
    else:
        topo = (sx + lado * 21, sy - 88)
        pygame.draw.circle(surf, (236, 210, 255), (int(topo[0]), int(topo[1])), int(5 + 7 * (1 - t)))
        pygame.draw.circle(surf, (186, 128, 250), (int(topo[0]), int(topo[1])), int(3 + 3 * (1 - t)))


# --------------------------------------------------------------------------
# classes
# --------------------------------------------------------------------------


def _cavaleiro(
    j: Any, surf: pygame.Surface, sx: float, sy: float, olhar: str, lado: int,
    fase: float, flash: bool, cor_arma: Sequence[int] | None = None,
    cor_armadura: Sequence[int] | None = None,
) -> None:
    base_armadura = (84, 132, 212)
    armadura = _misturar(base_armadura, cor_armadura, 0.50) if cor_armadura else base_armadura
    armadura_clara = tuple(min(255, c + 44) for c in armadura)
    armadura_escura = tuple(max(0, c - 36) for c in armadura)
    perna = (58, 70, 104)
    bota = (70, 54, 46)
    contorno = _c(CONTORNO, flash)
    andando = j.andando
    swing = math.sin(fase) * 4.0 if andando else 0.0
    cor_capa = _misturar((186, 62, 72), cor_armadura, 0.35) if cor_armadura else (186, 62, 72)
    cor_capa_escura = tuple(max(0, c - 70) for c in cor_capa)

    # capa
    if olhar != "cima":
        _capa(surf, sx, sy, fase, andando, cor_capa, cor_capa_escura, flash)

    # braço de trás
    _capsula_borda(surf, _c(armadura_escura, flash), contorno, (sx - 15, sy - 46), (sx - 20 + swing, sy - 28), 7)
    # pernas
    _pernas(surf, sx, sy, fase, andando, perna, bota, flash, 8)

    # torso
    _capsula_borda(surf, _c(armadura, flash), contorno, (sx, sy - 52), (sx, sy - 24), 30)
    _poly(surf, _c(armadura_clara, flash), [(sx - 11, sy - 49), (sx + 11, sy - 49), (sx + 8, sy - 30), (sx - 8, sy - 30)], contorno, 1)
    pygame.draw.line(surf, _c((236, 242, 252), flash), (sx - 7, sy - 46), (sx - 7, sy - 32), 2)
    for ox, oy in ((-6, -44), (6, -44), (0, -36)):
        pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(sx + ox), int(sy + oy)), 1)
    # cinto
    pygame.draw.rect(surf, contorno, (int(sx - 15), int(sy - 29), 30, 7), border_radius=2)
    pygame.draw.rect(surf, _c((88, 62, 44), flash), (int(sx - 13), int(sy - 28), 26, 5), border_radius=2)
    pygame.draw.rect(surf, _c((228, 190, 108), flash), (int(sx - 4), int(sy - 29), 8, 7), border_radius=2)
    # emblema no peito
    pygame.draw.polygon(
        surf, _c((240, 208, 120), flash),
        [(sx, sy - 45), (sx + 4, sy - 41), (sx, sy - 37), (sx - 4, sy - 41)],
    )
    # ombreiras
    for ox in (-17, 17):
        pygame.draw.circle(surf, contorno, (int(sx + ox), int(sy - 47)), 11)
        pygame.draw.circle(surf, _c(armadura_clara, flash), (int(sx + ox), int(sy - 47)), 8)
        pygame.draw.circle(surf, _c(armadura_escura, flash), (int(sx + ox), int(sy - 47)), 5)

    # cabeça
    _cabeca(surf, sx, sy, olhar, lado, (92, 64, 48), flash, "cavaleiro")

    # braço da frente + espada
    mao = (sx + lado * (20 + swing * 0.4), sy - 32)
    _capsula_borda(surf, _c(armadura, flash), contorno, (sx + 15, sy - 46), mao, 7)
    ang = -1.25 if lado > 0 else -1.89
    if j.ataque_anim > 0:
        ang = j.angulo_ataque - 0.25
    _espada(surf, mao, ang, flash, 1.0 if j.ataque_anim > 0 else 0.0, cor=cor_arma)
    # tassets / saia de placas
    for ox in (-10, 0, 10):
        _poly(
            surf, _c(armadura_clara, flash),
            [(sx + ox - 4, sy - 27), (sx + ox + 4, sy - 27),
             (sx + ox + 2, sy - 15), (sx + ox - 2, sy - 15)],
            contorno, 1,
        )
    # manopla
    pygame.draw.circle(surf, contorno, (int(mao[0]), int(mao[1])), 6)
    pygame.draw.circle(surf, _c(armadura_clara, flash), (int(mao[0]), int(mao[1])), 4)
    pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(mao[0]), int(mao[1])), 2)
    # escudo
    _escudo(surf, (sx - lado * 21, sy - 36), flash)

    if olhar == "cima":
        _capa(surf, sx, sy, fase, andando, cor_capa, cor_capa_escura, flash)


def _arqueira(
    j: Any, surf: pygame.Surface, sx: float, sy: float, olhar: str, lado: int,
    fase: float, flash: bool, cor_arma: Sequence[int] | None = None,
    cor_armadura: Sequence[int] | None = None,
) -> None:
    base_verde = (72, 162, 104)
    verde = _misturar(base_verde, cor_armadura, 0.45) if cor_armadura else base_verde
    verde_claro = tuple(min(255, c + 36) for c in verde)
    verde_escuro = tuple(max(0, c - 30) for c in verde)
    couro = (154, 112, 70)
    couro_escuro = (104, 74, 48)
    perna = (76, 92, 74)
    bota = (92, 64, 46)
    contorno = _c(CONTORNO, flash)
    andando = j.andando
    swing = math.sin(fase) * 4.0 if andando else 0.0
    cor_capa = _misturar((52, 128, 84), cor_armadura, 0.35) if cor_armadura else (52, 128, 84)
    cor_capa_escura = tuple(max(0, c - 50) for c in cor_capa)

    if olhar != "cima":
        _capa(surf, sx, sy, fase, andando, cor_capa, cor_capa_escura, flash, 0.82)

    # braço de trás
    _capsula_borda(surf, _c(verde_escuro, flash), contorno, (sx - 14, sy - 46), (sx - 19 + swing, sy - 30), 6)
    # pernas
    _pernas(surf, sx, sy, fase, andando, perna, bota, flash, 7)

    # aljava
    aljava = pygame.Rect(int(sx - lado * 22 - 7), int(sy - 58), 14, 30)
    pygame.draw.rect(surf, contorno, aljava.inflate(3, 3), border_radius=4)
    pygame.draw.rect(surf, _c(couro_escuro, flash), aljava, border_radius=4)
    for i in range(3):
        x = aljava.x + 3 + i * 4
        pygame.draw.line(surf, _c((214, 204, 160), flash), (x, aljava.y + 4), (x - 2, aljava.y - 8), 2)
        pygame.draw.polygon(surf, _c((180, 60, 60), flash), [(x - 4, aljava.y - 8), (x, aljava.y - 14), (x + 2, aljava.y - 8)])

    # torso
    _capsula_borda(surf, _c(verde, flash), contorno, (sx, sy - 52), (sx, sy - 24), 26)
    # peitoral de couro com costura
    _poly(
        surf, _c(couro, flash),
        [(sx - 9, sy - 47), (sx + 9, sy - 47), (sx + 7, sy - 31), (sx - 7, sy - 31)],
        contorno, 1,
    )
    _poly(
        surf, _c(couro_escuro, flash),
        [(sx - 7, sy - 45), (sx + 7, sy - 45), (sx + 5, sy - 34), (sx - 5, sy - 34)],
    )
    for i in range(3):
        pygame.draw.line(
            surf, _c((196, 156, 104), flash),
            (sx - 5 + i * 5, sy - 43), (sx - 5 + i * 5, sy - 36), 1,
        )
    pygame.draw.line(surf, _c(verde_claro, flash), (sx - 8, sy - 48), (sx + 8, sy - 48), 1)
    for ox, oy in ((-5, -45), (5, -45), (0, -38)):
        pygame.draw.circle(surf, _c(couro, flash), (int(sx + ox), int(sy + oy)), 1)
    # alça de couro
    pygame.draw.line(surf, _c(couro, flash), (sx - 10, sy - 49), (sx + 10, sy - 32), 4)
    # cinto
    pygame.draw.rect(surf, contorno, (int(sx - 13), int(sy - 29), 26, 6), border_radius=2)
    pygame.draw.rect(surf, _c(couro, flash), (int(sx - 11), int(sy - 28), 22, 4), border_radius=2)
    pygame.draw.circle(surf, _c((228, 190, 108), flash), (int(sx), int(sy - 26)), 2)
    # emblema no peito
    pygame.draw.polygon(
        surf, _c((240, 208, 120), flash),
        [(sx, sy - 45), (sx + 4, sy - 41), (sx, sy - 37), (sx - 4, sy - 41)],
    )
    # ombreiras de couro
    for ox in (-13, 13):
        pygame.draw.circle(surf, contorno, (int(sx + ox), int(sy - 47)), 6)
        pygame.draw.circle(surf, _c(couro, flash), (int(sx + ox), int(sy - 47)), 4)

    # cabeça
    _cabeca(surf, sx, sy, olhar, lado, (168, 96, 54), flash, "arqueira")

    # braço da frente + arco
    mao = (sx + lado * (18 + swing * 0.4), sy - 34)
    _capsula_borda(surf, _c(verde, flash), contorno, (sx + 13, sy - 46), mao, 6)
    # braçadeira de couro
    pygame.draw.line(
        surf, _c(couro_escuro, flash),
        (sx + lado * 15, sy - 43), (sx + lado * 17, sy - 38), 5,
    )
    pygame.draw.line(
        surf, _c((214, 176, 112), flash),
        (sx + lado * 15, sy - 42), (sx + lado * 17, sy - 38), 1,
    )
    pygame.draw.rect(
        surf, _c(couro, flash),
        (int(mao[0] - 4), int(mao[1] - 2), 8, 6), border_radius=2,
    )
    _arco(surf, mao, lado, flash, j.ataque_anim > 0, cor=cor_arma)

    if olhar == "cima":
        _capa(surf, sx, sy, fase, andando, cor_capa, cor_capa_escura, flash, 0.82)


def _maga(
    j: Any, surf: pygame.Surface, sx: float, sy: float, olhar: str, lado: int,
    fase: float, flash: bool, cor_arma: Sequence[int] | None = None,
    cor_armadura: Sequence[int] | None = None,
) -> None:
    base_roxo = (128, 88, 196)
    roxo = _misturar(base_roxo, cor_armadura, 0.45) if cor_armadura else base_roxo
    roxo_claro = tuple(min(255, c + 44) for c in roxo)
    roxo_escuro = tuple(max(0, c - 36) for c in roxo)
    dourado = (228, 190, 108)
    perna = (72, 56, 104)
    bota = (62, 46, 82)
    contorno = _c(CONTORNO, flash)
    andando = j.andando
    swing = math.sin(fase) * 4.0 if andando else 0.0

    # braço de trás
    _capsula_borda(surf, _c(roxo_escuro, flash), contorno, (sx - 14, sy - 46), (sx - 19 + swing, sy - 30), 6)
    # pernas
    _pernas(surf, sx, sy, fase, andando, perna, bota, flash, 7)

    # manto externo mais escuro (silhueta)
    _poly(
        surf, _c(roxo_escuro, flash),
        [(sx - 15, sy - 53), (sx + 15, sy - 53),
         (sx + 24 + math.sin(fase) * 2, sy - 2), (sx + 12, sy + 2),
         (sx, sy - 1), (sx - 12, sy + 2), (sx - 24 + math.sin(fase) * 2, sy - 2)],
        contorno, 2,
    )
    # manto
    pts = [
        (sx - 13, sy - 52), (sx + 13, sy - 52),
        (sx + 21 + math.sin(fase) * 2, sy - 2), (sx + 10, sy + 1),
        (sx, sy - 2), (sx - 10, sy + 1), (sx - 21 + math.sin(fase) * 2, sy - 2),
    ]
    _poly(surf, _c(roxo, flash), pts, contorno, 2)
    # barra irregular com forro claro
    for i in range(4):
        ox = -16 + i * 9 + math.sin(fase) * 2
        pygame.draw.line(
            surf, _c(roxo_claro, flash),
            (sx + ox, sy - 6), (sx + ox + 3, sy + 1), 2,
        )
    # faixa clara
    _poly(surf, _c(roxo_claro, flash), [(sx - 10, sy - 49), (sx + 10, sy - 49), (sx + 13, sy - 30), (sx - 13, sy - 30)], contorno, 1)
    for ox, oy in ((-6, -44), (6, -44), (0, -37)):
        pygame.draw.circle(surf, _c(dourado, flash), (int(sx + ox), int(sy + oy)), 1)
    # detalhes dourados
    pygame.draw.line(surf, _c(dourado, flash), (sx - 13, sy - 30), (sx + 13, sy - 30), 2)
    pygame.draw.line(surf, _c(dourado, flash), (sx - 16, sy - 8), (sx + 16, sy - 8), 1)
    pygame.draw.circle(surf, _c(dourado, flash), (int(sx), int(sy - 30)), 3)
    # faixa e runas do manto
    pygame.draw.line(surf, _c((96, 62, 158), flash), (sx - 13, sy - 25), (sx + 13, sy - 25), 3)
    for i in range(4):
        ox = -12 + i * 8
        pygame.draw.circle(surf, _c((236, 210, 255), flash), (int(sx + ox), int(sy - 12)), 1)
        pygame.draw.line(
            surf, _c((190, 150, 240), flash),
            (sx + ox, sy - 15), (sx + ox, sy - 9), 1,
        )
    # emblema no peito
    pygame.draw.polygon(
        surf, _c((240, 208, 120), flash),
        [(sx, sy - 45), (sx + 4, sy - 41), (sx, sy - 37), (sx - 4, sy - 41)],
    )
    # ombros e manto de gola
    for ox in (-14, 14):
        pygame.draw.circle(surf, contorno, (int(sx + ox), int(sy - 47)), 8)
        pygame.draw.circle(surf, _c(roxo_claro, flash), (int(sx + ox), int(sy - 47)), 5)
        pygame.draw.circle(surf, _c(dourado, flash), (int(sx + ox), int(sy - 49)), 1)
    _poly(
        surf, _c(roxo_escuro, flash),
        [(sx - 14, sy - 49), (sx + 14, sy - 49), (sx + 10, sy - 42), (sx - 10, sy - 42)],
        contorno, 1,
    )
    pygame.draw.line(surf, _c(dourado, flash), (sx - 11, sy - 44), (sx + 11, sy - 44), 1)

    # cabeça
    _cabeca(surf, sx, sy, olhar, lado, (226, 226, 238), flash, "maga")

    # braço da frente + manga larga + cajado
    mao = (sx + lado * (18 + swing * 0.4), sy - 34)
    _capsula_borda(surf, _c(roxo, flash), contorno, (sx + 13, sy - 46), mao, 6)
    _poly(
        surf, _c(roxo_escuro, flash),
        [(sx + lado * 12, sy - 45), (sx + lado * 19, sy - 41),
         (sx + lado * 16, sy - 31), (sx + lado * 10, sy - 34)],
        contorno, 1,
    )
    pygame.draw.line(
        surf, _c(dourado, flash),
        (sx + lado * 14, sy - 42), (sx + lado * 12, sy - 33), 1,
    )
    _cajado(surf, mao, lado, flash, 1.0 if j.ataque_anim > 0 else 0.35, cor=cor_arma)


# --------------------------------------------------------------------------
# entrada
# --------------------------------------------------------------------------


def desenhar_jogador(j: Any, surf: pygame.Surface, camera: Camera) -> None:
    if pixel_arte.ATIVO:
        pixel_player.desenhar(j, surf, camera)
        return
    sx, sy = camera.aplicar((j.x, j.y))
    if not camera.visivel(j.x, j.y, 160):
        return
    flash = j.hit_flash > 0

    # sombra
    sombra(surf, sx, sy, 20, 7, 95)

    # avanço curto no ataque (a sombra fica no lugar)
    if j.ataque_anim > 0:
        t = 1.0 - j.ataque_anim / 0.24
        lunge = math.sin(max(0.0, min(1.0, t)) * math.pi) * 7
        sx += j.facing[0] * lunge
        sy += j.facing[1] * lunge * 0.6

    # auras
    if j.buffs:
        pulso = 0.6 + 0.4 * math.sin(j.tempo * 4)
        pygame.draw.circle(surf, (246, 206, 112), (int(sx), int(sy)), int(28 + 3 * pulso), 2)
    if j.level_flash > 0:
        t = 1.0 - j.level_flash / 1.6
        raio = int(26 + 70 * t)
        pygame.draw.circle(surf, (252, 226, 140), (int(sx), int(sy)), raio, max(1, int(4 * (1 - t))))

    andando = j.andando
    fase = j.walk_phase
    bob = abs(math.sin(fase)) * 2.2 if andando else math.sin(j.tempo * 2.2) * 1.1
    sy -= bob

    fx, fy = j.facing
    if abs(fx) > abs(fy):
        olhar = "direita" if fx > 0 else "esquerda"
    elif fy < -0.2:
        olhar = "cima"
    else:
        olhar = "baixo"
    lado = -1 if olhar == "esquerda" else 1

    arma = j.equipamentos.get("Arma")
    armadura = j.equipamentos.get("Armadura")
    anel = j.equipamentos.get("Anel")
    amuleto = j.equipamentos.get("Amuleto")
    cor_arma = arma.cor if arma else None
    cor_armadura = armadura.cor if armadura else None

    for equipamento, cor_aura in ((armadura, cor_armadura), (arma, cor_arma)):
        if equipamento is not None and equipamento.raridade in ("Épico", "Lendário"):
            halo_suave(surf, (sx, sy - 34), 34, cor_aura, 28)

    if j.classe == "Cavaleiro":
        _cavaleiro(j, surf, sx, sy, olhar, lado, fase, flash, cor_arma, cor_armadura)
    elif j.classe == "Arqueira":
        _arqueira(j, surf, sx, sy, olhar, lado, fase, flash, cor_arma, cor_armadura)
    else:
        _maga(j, surf, sx, sy, olhar, lado, fase, flash, cor_arma, cor_armadura)

    # gemas de anel e amuleto equipados
    if anel is not None:
        pygame.draw.circle(surf, anel.cor, (int(sx + lado * 20), int(sy - 32)), 4)
        pygame.draw.circle(surf, (255, 255, 255), (int(sx + lado * 20 - 1), int(sy - 33)), 1)
    if amuleto is not None:
        pygame.draw.circle(surf, (26, 24, 34), (int(sx), int(sy - 44)), 6)
        pygame.draw.circle(surf, amuleto.cor, (int(sx), int(sy - 44)), 5)
        pygame.draw.circle(surf, (255, 255, 255), (int(sx - 1), int(sy - 45)), 2)

    _efeito_ataque(surf, j, sx, sy, olhar, lado)

    # luz de contorno suave, para o herói se destacar do cenário
    pygame.draw.arc(
        surf, (255, 244, 210),
        (sx - 13, sy - 58, 26, 26),
        math.pi * 1.05, math.pi * 1.95, 2,
    )
