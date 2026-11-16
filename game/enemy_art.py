"""Desenho vetorial dos inimigos e bosses."""
from __future__ import annotations

import math
from typing import Any, Sequence

import pygame

import pixel_arte
import pixel_enemy
import settings
from utils import Camera, barra, fonte, halo_suave, sombra, texto

# -------------------------------------------------------------------------- #
# Telegraph (missão 02, protótipo)                                            #
# Cone idêntico ao do golpe real: alcance `ataque_raio + 24`,                  #
# meia-abertura 1.2 rad, janela de preparo 0.34 s (corpo a corpo).            #
# Um único tipo por ora (golem); não altera dano nem balanceamento.           #
# -------------------------------------------------------------------------- #
TIPO_TELEGRAPH = ("golem",)
PREPARO_MEDIDO = 0.34
MEIA_ABERTURA = 1.2
ALCANCE_EXTRA = 24.0

_cone_telegraph: pygame.Surface | None = None
_cone_chave: tuple[float, tuple[float, float, float, float]] | None = None


def _surface_cone(alcance: float, alpha: int) -> pygame.Surface:
    global _cone_telegraph, _cone_chave
    chave = (alcance, (250, 110, 90, alpha))
    if _cone_chave == chave and _cone_telegraph is not None:
        return _cone_telegraph
    lado = int(alcance * 2) + 4
    cone = pygame.Surface((lado, lado), pygame.SRCALPHA)
    c = alcance + 2
    pontos = [(c, c)]
    for i in range(15):
        a = -MEIA_ABERTURA + 2 * MEIA_ABERTURA * i / 14
        pontos.append((c + math.cos(a) * alcance, c + math.sin(a) * alcance))
    pygame.draw.polygon(cone, (250, 110, 90, alpha), pontos)
    pygame.draw.lines(cone, (255, 150, 110, min(255, alpha + 60)), False, pontos, 2)
    _cone_telegraph, _cone_chave = cone, chave
    return _cone_telegraph


def desenhar_telegraph(inimigo: Any, surf: pygame.Surface, sx: float, sy: float) -> None:
    """Aviso sob o inimigo: cone cresce até o instante exato do golpe real."""
    if not settings.TELEGRAPH_COMBATE:
        return
    if getattr(inimigo, "tipo", "") not in TIPO_TELEGRAPH:
        return
    if not getattr(inimigo, "preparando", False):
        return
    if getattr(inimigo, "tipo_preparo", "normal") != "normal":
        return
    if getattr(inimigo, "ranged", False):
        return
    preparo = max(0.0, float(getattr(inimigo, "preparo", 0.0)))
    faltando = min(1.0, preparo / PREPARO_MEDIDO)
    alpha = int(40 + 130 * (1.0 - faltando))
    alcance = float(inimigo.ataque_raio) + ALCANCE_EXTRA
    cone = _surface_cone(alcance, alpha)
    ang = float(getattr(inimigo, "ataque_angulo", 0.0))
    girado = pygame.transform.rotate(cone, -math.degrees(ang)) if ang else cone
    pos = (int(sx) - girado.get_width() // 2, int(sy) - girado.get_height() // 2)
    surf.blit(girado, pos)


CONTORNO = (26, 24, 32)


def _c(cor: Sequence[int], flash: bool) -> tuple[int, int, int]:
    return (255, 255, 255) if flash else tuple(cor[:3])


def _clarear(cor: Sequence[int], q: int) -> tuple[int, int, int]:
    return tuple(min(255, int(c) + q) for c in cor[:3])


def _escurecer(cor: Sequence[int], q: int) -> tuple[int, int, int]:
    return tuple(max(0, int(c) - q) for c in cor[:3])


def _capsula(surf: pygame.Surface, cor: Sequence[int], p1: Sequence[float], p2: Sequence[float], largura: int) -> None:
    x1, y1, x2, y2 = int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1])
    pygame.draw.line(surf, tuple(cor[:3]), (x1, y1), (x2, y2), max(1, largura))
    pygame.draw.circle(surf, tuple(cor[:3]), (x1, y1), max(1, largura // 2))
    pygame.draw.circle(surf, tuple(cor[:3]), (x2, y2), max(1, largura // 2))


def _poly(surf: pygame.Surface, cor: Sequence[int], pts: Sequence[Sequence[float]], borda: Sequence[int] | None = None, largura: int = 2) -> None:
    p = [(int(x), int(y)) for x, y in pts]
    pygame.draw.polygon(surf, tuple(cor[:3]), p)
    if borda is not None:
        pygame.draw.polygon(surf, tuple(borda[:3]), p, max(1, largura))


# --------------------------------------------------------------------------
# tipos
# --------------------------------------------------------------------------


def _slime(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    t = inimigo.tempo
    pulso = 1.0 + math.sin(t * 5.5) * 0.06
    w = r * 2.25 * pulso
    h = r * 1.55 / pulso
    sombra(surf, sx, sy - 2, r * 1.1, r * 0.38, 85)
    if inimigo.estado == "chase":
        sy -= abs(math.sin(inimigo.walk_phase * 0.9)) * 4
    pygame.draw.ellipse(surf, CONTORNO, (int(sx - w / 2 - 2), int(sy - h - 2), int(w + 4), int(h + 4)))
    pygame.draw.ellipse(surf, cor, (int(sx - w / 2), int(sy - h), int(w), int(h)))
    pygame.draw.ellipse(surf, _clarear(cor, 42), (int(sx - w * 0.38), int(sy - h * 0.92), int(w * 0.55), int(h * 0.45)))
    pygame.draw.ellipse(surf, _clarear(cor, 72), (int(sx - w * 0.28), int(sy - h * 0.86), int(w * 0.2), int(h * 0.18)))
    # olhos
    olho_y = int(sy - h * 0.55)
    for ox in (-r * 0.36, r * 0.36):
        pygame.draw.circle(surf, (250, 250, 250), (int(sx + ox), olho_y), max(2, int(r * 0.17)))
        pygame.draw.circle(surf, (30, 30, 40), (int(sx + ox), olho_y), max(1, int(r * 0.09)))
    # boca
    pygame.draw.arc(surf, _escurecer(cor, 70), (int(sx - r * 0.28), int(sy - h * 0.5), int(r * 0.56), int(r * 0.3)), 0.2, math.pi - 0.2, 2)
    if inimigo.tipo == "slime_cristal":
        _cristais_no_corpo(surf, sx, sy, r, inimigo.cor)
    if inimigo.boss:
        _coroa(surf, sx, sy - h - 6, r * 0.7, flash)
        # sobrancelhas de rei
        for ox in (-r * 0.36, r * 0.36):
            pygame.draw.line(surf, (80, 40, 40), (sx + ox - r * 0.14, olho_y - r * 0.28), (sx + ox + r * 0.14, olho_y - r * 0.20), 2)


def _cristais_no_corpo(surf: pygame.Surface, sx: float, sy: float, r: float, cor: Sequence[int]) -> None:
    shards = [
        [(sx - r * 0.5, sy - r * 0.7), (sx - r * 0.72, sy - r * 1.5), (sx - r * 0.25, sy - r * 0.95)],
        [(sx + r * 0.1, sy - r * 0.8), (sx + r * 0.05, sy - r * 1.75), (sx + r * 0.48, sy - r * 0.85)],
        [(sx + r * 0.55, sy - r * 0.6), (sx + r * 0.82, sy - r * 1.15), (sx + r * 0.9, sy - r * 0.55)],
    ]
    for pts in shards:
        _poly(surf, (172, 118, 236), pts, (70, 42, 110), 1)
        pygame.draw.line(surf, (220, 190, 250), (int(pts[0][0]), int(pts[0][1])), (int(pts[1][0]), int(pts[1][1])), 1)


def _coroa(surf: pygame.Surface, sx: float, sy: float, largura: float, flash: bool) -> None:
    pts = [
        (sx - largura, sy), (sx - largura * 0.65, sy - largura * 0.75),
        (sx - largura * 0.3, sy - largura * 0.2), (sx, sy - largura * 0.9),
        (sx + largura * 0.3, sy - largura * 0.2), (sx + largura * 0.65, sy - largura * 0.75),
        (sx + largura, sy),
    ]
    _poly(surf, _c((244, 198, 90), flash), pts, (120, 82, 24), 2)
    for ox in (-largura * 0.65, 0, largura * 0.65):
        pygame.draw.circle(surf, _c((250, 230, 140), flash), (int(sx + ox), int(sy - largura * (0.75 if ox else 0.9))), 3)


def _goblin(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    cor_escura = _escurecer(cor, 45)
    andando = inimigo.estado == "chase" and not inimigo.preparando
    fase = inimigo.walk_phase
    swing = math.sin(fase) * 5 if andando else 0
    sombra(surf, sx, sy - 2, r * 0.9, r * 0.32, 85)
    # pernas
    _capsula(surf, CONTORNO, (sx - 6, sy - 22), (sx - 6 + swing, sy - 2), 9)
    _capsula(surf, cor_escura, (sx - 6, sy - 22), (sx - 6 + swing, sy - 2), 6)
    _capsula(surf, CONTORNO, (sx + 6, sy - 22), (sx + 6 - swing, sy - 2), 9)
    _capsula(surf, cor_escura, (sx + 6, sy - 22), (sx + 6 - swing, sy - 2), 6)
    # corpo
    _capsula(surf, CONTORNO, (sx, sy - 50), (sx, sy - 22), 24)
    _capsula(surf, cor, (sx, sy - 50), (sx, sy - 22), 20)
    # colete
    _poly(surf, (116, 78, 50), [(sx - 9, sy - 48), (sx + 9, sy - 48), (sx + 7, sy - 30), (sx - 7, sy - 30)], CONTORNO, 1)
    # braço com clava
    mao = (sx + 18 + swing * 0.8, sy - 32)
    _capsula(surf, CONTORNO, (sx + 10, sy - 44), mao, 8)
    _capsula(surf, cor, (sx + 10, sy - 44), mao, 5)
    # clava (levanta durante o preparo)
    ang = -0.7
    if inimigo.preparando:
        raise_t = 1.0 - max(0.0, inimigo.preparo) / 0.55
        ang = -0.7 - 0.9 * raise_t
    ponta = (mao[0] + math.cos(ang) * 26, mao[1] + math.sin(ang) * 26)
    pygame.draw.line(surf, CONTORNO, (int(mao[0]), int(mao[1])), (int(ponta[0]), int(ponta[1])), 7)
    pygame.draw.line(surf, (128, 88, 56), (int(mao[0]), int(mao[1])), (int(ponta[0]), int(ponta[1])), 4)
    pygame.draw.circle(surf, CONTORNO, (int(ponta[0]), int(ponta[1])), 9)
    pygame.draw.circle(surf, (146, 104, 66), (int(ponta[0]), int(ponta[1])), 7)
    # cabeça
    cx, cy = sx, sy - 60
    pygame.draw.circle(surf, CONTORNO, (int(cx), int(cy)), int(r * 0.82 + 2))
    pygame.draw.circle(surf, cor, (int(cx), int(cy)), int(r * 0.82))
    # orelhas
    _poly(surf, cor, [(cx - r * 0.72, cy - 2), (cx - r * 1.45, cy - 12), (cx - r * 0.78, cy + 7)], CONTORNO, 1)
    _poly(surf, cor, [(cx + r * 0.72, cy - 2), (cx + r * 1.45, cy - 12), (cx + r * 0.78, cy + 7)], CONTORNO, 1)
    # olhos
    for ox in (-r * 0.3, r * 0.3):
        pygame.draw.circle(surf, (250, 220, 120), (int(cx + ox), int(cy - 1)), max(2, int(r * 0.15)))
        pygame.draw.circle(surf, (50, 30, 20), (int(cx + ox), int(cy - 1)), max(1, int(r * 0.08)))
    # boca
    pygame.draw.line(surf, (60, 40, 30), (cx - 4, cy + 7), (cx + 5, cy + 6), 2)


def _wisp(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    t = inimigo.tempo
    cy = sy - 30 + math.sin(t * 2.2) * 5
    sombra(surf, sx, sy - 2, r * 0.75, r * 0.28, 70)
    # halo
    halo_suave(surf, (sx, cy), r * 2.7, cor, alpha=80)
    # núcleo
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(cy)), int(r * 0.95 + 2))
    pygame.draw.circle(surf, cor, (int(sx), int(cy)), int(r * 0.95))
    pygame.draw.circle(surf, _clarear(cor, 80), (int(sx - r * 0.2), int(cy - r * 0.2)), int(r * 0.35))
    # olhos
    for ox in (-r * 0.3, r * 0.3):
        pygame.draw.circle(surf, (40, 60, 80), (int(sx + ox), int(cy)), max(2, int(r * 0.12)))
    # partículas orbitando
    for i in range(3):
        a = t * 2.4 + i * math.tau / 3
        px = sx + math.cos(a) * r * 1.6
        py = cy + math.sin(a) * r * 0.7
        pygame.draw.circle(surf, _clarear(cor, 60), (int(px), int(py)), max(1, int(r * 0.13)))


def _golem(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    tipo = getattr(inimigo, "tipo", "golem")
    obsidiana = tipo in ("golem_obsidiana", "colosso_obsidiana")
    colosso = tipo == "colosso_obsidiana"
    anciao = tipo == "golem_anciao"
    t = inimigo.tempo
    sombra(surf, sx, sy - 2, r * 1.15, r * 0.4, 100)

    # paleta por variante
    if obsidiana:
        rocha = cor
        rocha_escura = (34, 20, 28) if not flash else (120, 90, 96)
        rocha_clara = _clarear(cor, 30)
        veio = (250, 116, 58)
        veio_claro = (255, 214, 140)
        cor_olho = (255, 178, 90)
    elif anciao:
        rocha = cor
        rocha_escura = _escurecer(cor, 44)
        rocha_clara = _clarear(cor, 30)
        veio = (110, 226, 214)
        veio_claro = (212, 255, 248)
        cor_olho = (252, 176, 92)
    else:
        rocha = cor
        rocha_escura = _escurecer(cor, 44)
        rocha_clara = _clarear(cor, 28)
        veio = (108, 226, 216)
        veio_claro = (214, 255, 250)
        cor_olho = (126, 234, 224)
    if flash:
        rocha, rocha_escura, rocha_clara = (255, 255, 255), (240, 240, 240), (255, 255, 255)

    andando = inimigo.estado == "chase"
    swing = math.sin(inimigo.walk_phase) * 5.0 if andando else 0.0
    if andando:
        sy -= abs(math.sin(inimigo.walk_phase)) * 3.0
    raise_t = 0.0
    if inimigo.preparando:
        raise_t = 1.0 - max(0.0, inimigo.preparo) / 0.55

    contorno = CONTORNO

    # pernas grossas com joelho e pé
    for lado in (-1, 1):
        passo = swing * lado * 0.5
        quadril = (sx + lado * r * 0.42, sy - r * 1.15)
        joelho = (sx + lado * r * 0.55 + passo, sy - r * 0.55)
        pe = (sx + lado * r * 0.62 + passo * 0.6, sy - 2)
        _poly(
            surf, rocha_escura,
            [(quadril[0] - r * 0.2, quadril[1]), (quadril[0] + r * 0.2, quadril[1]),
             (joelho[0] + r * 0.17, joelho[1]), (joelho[0] - r * 0.17, joelho[1])],
            contorno, 2,
        )
        _poly(
            surf, rocha,
            [(joelho[0] - r * 0.17, joelho[1]), (joelho[0] + r * 0.17, joelho[1]),
             (pe[0] + r * 0.2, pe[1]), (pe[0] - r * 0.2, pe[1])],
            contorno, 2,
        )
        pygame.draw.ellipse(
            surf, rocha_clara,
            (int(joelho[0] - r * 0.13), int(joelho[1] - r * 0.08), int(r * 0.26), int(r * 0.16)),
        )
        pygame.draw.ellipse(
            surf, contorno,
            (int(pe[0] - r * 0.26), int(pe[1] - r * 0.12), int(r * 0.52), int(r * 0.2)),
        )
        pygame.draw.ellipse(
            surf, rocha_escura,
            (int(pe[0] - r * 0.23), int(pe[1] - r * 0.13), int(r * 0.46), int(r * 0.16)),
        )

    # torso em placas
    corpo = [
        (sx - r * 0.95, sy - r * 2.55), (sx + r * 0.95, sy - r * 2.55),
        (sx + r * 1.1, sy - r * 1.0), (sx + r * 0.55, sy - r * 0.78),
        (sx - r * 0.55, sy - r * 0.78), (sx - r * 1.1, sy - r * 1.0),
    ]
    _poly(surf, rocha_escura, corpo, contorno, 2)
    _poly(
        surf, rocha,
        [(sx - r * 0.82, sy - r * 2.44), (sx + r * 0.82, sy - r * 2.44),
         (sx + r * 0.94, sy - r * 1.08), (sx + r * 0.5, sy - r * 0.9),
         (sx - r * 0.5, sy - r * 0.9), (sx - r * 0.94, sy - r * 1.08)],
    )
    # placas do peito
    _poly(
        surf, rocha_clara,
        [(sx - r * 0.55, sy - r * 2.36), (sx + r * 0.22, sy - r * 2.36),
         (sx + r * 0.32, sy - r * 1.55), (sx - r * 0.42, sy - r * 1.6)],
        contorno, 1,
    )
    _poly(
        surf, _clarear(rocha, 12),
        [(sx + r * 0.3, sy - r * 2.3), (sx + r * 0.76, sy - r * 2.2),
         (sx + r * 0.82, sy - r * 1.35), (sx + r * 0.36, sy - r * 1.5)],
        contorno, 1,
    )
    # rachaduras com veio luminoso
    veios = [
        [(sx - r * 0.72, sy - r * 2.3), (sx - r * 0.35, sy - r * 1.95), (sx - r * 0.46, sy - r * 1.5)],
        [(sx + r * 0.62, sy - r * 1.9), (sx + r * 0.28, sy - r * 1.62), (sx + r * 0.38, sy - r * 1.15)],
        [(sx - r * 0.1, sy - r * 2.5), (sx + r * 0.05, sy - r * 2.1), (sx - r * 0.12, sy - r * 1.85)],
    ]
    for pts in veios:
        pygame.draw.lines(surf, contorno, False, pts, 4)
        pygame.draw.lines(surf, veio, False, pts, 2)
        pygame.draw.lines(surf, veio_claro, False, pts, 1)
    # núcleo
    pulso = 0.6 + 0.4 * math.sin(t * 3.2)
    cx_core, cy_core = sx, sy - r * 1.55
    halo_suave(surf, (cx_core, cy_core), r * (0.55 + 0.18 * pulso), veio, alpha=int(40 + 40 * pulso))
    pygame.draw.circle(surf, contorno, (int(cx_core), int(cy_core)), int(r * 0.3 + 2))
    pygame.draw.circle(surf, veio, (int(cx_core), int(cy_core)), int(r * 0.28))
    pygame.draw.circle(surf, veio_claro, (int(cx_core - 2), int(cy_core - 2)), int(r * 0.12))
    # runas ao redor do núcleo
    for i in range(6):
        ang = i * math.tau / 6 + t * 0.25
        px = cx_core + math.cos(ang) * r * 0.42
        py = cy_core + math.sin(ang) * r * 0.42
        pygame.draw.circle(surf, veio_claro, (int(px), int(py)), max(1, int(r * 0.045)))

    # ombreiras / espinhos
    for lado in (-1, 1):
        ox = sx + lado * r * 1.0
        oy = sy - r * 2.42
        pygame.draw.circle(surf, contorno, (int(ox), int(oy)), int(r * 0.38))
        pygame.draw.circle(surf, rocha_escura, (int(ox), int(oy)), int(r * 0.34))
        pygame.draw.circle(surf, rocha_clara, (int(ox - lado * r * 0.05), int(oy - r * 0.06)), int(r * 0.2))
        if obsidiana or colosso:
            for k in range(2):
                bx = ox + lado * r * (0.04 + k * 0.18)
                _poly(
                    surf, _clarear(rocha, 16),
                    [(bx - r * 0.09, oy - r * 0.2), (bx + lado * r * 0.1, oy - r * (0.75 + k * 0.2)), (bx + r * 0.1, oy - r * 0.18)],
                    contorno, 1,
                )
        elif anciao:
            pygame.draw.circle(surf, (92, 128, 74), (int(ox + lado * r * 0.1), int(oy - r * 0.12)), int(r * 0.12))

    # braços segmentados com punho enorme
    for lado in (-1, 1):
        ombro = (sx + lado * r * 1.02, sy - r * 2.28)
        cotovelo = (sx + lado * r * 1.34, sy - r * 1.55 + swing * lado * 0.25)
        punho = (sx + lado * r * 1.18 + swing * lado * 0.7, sy - r * 0.92)
        if inimigo.preparando:
            punho = (punho[0], punho[1] - raise_t * r * 0.85)
            cotovelo = (cotovelo[0], cotovelo[1] - raise_t * r * 0.4)
        pygame.draw.line(surf, contorno, ombro, cotovelo, int(r * 0.42))
        pygame.draw.line(surf, rocha_escura, ombro, cotovelo, int(r * 0.32))
        pygame.draw.line(surf, contorno, cotovelo, punho, int(r * 0.4))
        pygame.draw.line(surf, rocha, cotovelo, punho, int(r * 0.3))
        # veio no braço
        pygame.draw.line(surf, veio, (cotovelo[0], cotovelo[1]), (punho[0], punho[1] + r * 0.15), 1)
        # punho
        pygame.draw.circle(surf, contorno, (int(punho[0]), int(punho[1])), int(r * 0.34))
        pygame.draw.circle(surf, rocha_escura, (int(punho[0]), int(punho[1])), int(r * 0.3))
        pygame.draw.circle(surf, rocha_clara, (int(punho[0] - lado * r * 0.05), int(punho[1] - r * 0.08)), int(r * 0.17))
        for dedo in (-1, 0, 1):
            px = punho[0] + lado * r * 0.16 + dedo * r * 0.1
            py = punho[1] + r * 0.22
            pygame.draw.circle(surf, contorno, (int(px), int(py)), max(2, int(r * 0.08)))

    # cabeça angular
    cab_y = sy - r * 2.95
    cab = [
        (sx - r * 0.5, cab_y + r * 0.5), (sx - r * 0.42, cab_y - r * 0.1),
        (sx - r * 0.14, cab_y - r * 0.32), (sx + r * 0.14, cab_y - r * 0.32),
        (sx + r * 0.42, cab_y - r * 0.1), (sx + r * 0.5, cab_y + r * 0.5),
        (sx + r * 0.28, cab_y + r * 0.62), (sx - r * 0.28, cab_y + r * 0.62),
    ]
    _poly(surf, rocha_escura, cab, contorno, 2)
    _poly(
        surf, rocha,
        [(sx - r * 0.4, cab_y + r * 0.42), (sx - r * 0.32, cab_y - r * 0.02),
         (sx - r * 0.1, cab_y - r * 0.2), (sx + r * 0.1, cab_y - r * 0.2),
         (sx + r * 0.32, cab_y - r * 0.02), (sx + r * 0.4, cab_y + r * 0.42),
         (sx + r * 0.22, cab_y + r * 0.5), (sx - r * 0.22, cab_y + r * 0.5)],
    )
    # testa / sobrancelha
    pygame.draw.line(surf, rocha_clara, (sx - r * 0.26, cab_y + r * 0.02), (sx + r * 0.26, cab_y + r * 0.02), max(2, int(r * 0.09)))
    # olhos
    for ox in (-r * 0.19, r * 0.19):
        halo_suave(surf, (sx + ox, cab_y + r * 0.2), r * 0.18, cor_olho, alpha=90)
        pygame.draw.circle(surf, contorno, (int(sx + ox), int(cab_y + r * 0.2)), max(2, int(r * 0.11)))
        pygame.draw.circle(surf, cor_olho, (int(sx + ox), int(cab_y + r * 0.2)), max(1, int(r * 0.07)))
    # mandíbula
    pygame.draw.line(surf, contorno, (sx - r * 0.2, cab_y + r * 0.48), (sx + r * 0.2, cab_y + r * 0.48), 2)
    for i in range(3):
        px = sx - r * 0.12 + i * r * 0.12
        pygame.draw.line(surf, rocha_clara, (px, cab_y + r * 0.36), (px, cab_y + r * 0.48), 1)
    # ornamento de testa
    if colosso:
        _coroa(surf, sx, cab_y - r * 0.34, r * 0.42, flash)
    elif anciao:
        pygame.draw.arc(
            surf, (206, 172, 98),
            pygame.Rect(int(sx - r * 0.4), int(cab_y - r * 0.22), int(r * 0.8), int(r * 0.5)),
            math.pi, math.tau, 2,
        )
        pygame.draw.circle(surf, (120, 168, 92), (int(sx - r * 0.34), int(cab_y + r * 0.3)), max(2, int(r * 0.09)))
    elif obsidiana:
        for lado in (-1, 1):
            _poly(
                surf, _clarear(rocha, 18),
                [(sx + lado * r * 0.34, cab_y - r * 0.12), (sx + lado * r * 0.62, cab_y - r * 0.55), (sx + lado * r * 0.42, cab_y + r * 0.04)],
                contorno, 1,
            )
    # musgo no golem antigo
    if anciao:
        for ox, oy, rr in ((-0.7, -1.2, 0.13), (0.55, -0.95, 0.1), (-0.2, -2.4, 0.09)):
            pygame.draw.ellipse(
                surf, (82, 124, 72),
                (int(sx + r * ox), int(sy + r * oy), int(r * rr * 2), int(r * rr)),
            )
    # coroa de espinhos nas costas do colosso
    if colosso:
        for ox, altura in ((-0.8, 0.55), (-0.35, 0.85), (0.35, 0.85), (0.8, 0.55)):
            bx = sx + r * ox
            _poly(
                surf, _clarear(rocha, 20),
                [(bx - r * 0.13, sy - r * 2.35), (bx + r * 0.02, sy - r * (2.35 + altura)), (bx + r * 0.16, sy - r * 2.35)],
                contorno, 2,
            )



def _senhor_fragmentos(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    t = inimigo.tempo
    sombra(surf, sx, sy - 2, r * 1.2, r * 0.4, 105)
    pulso = 0.6 + 0.4 * math.sin(t * 2.4)
    halo_suave(surf, (sx, sy - r * 1.3), r * 3.2, cor, alpha=int(70 + 25 * pulso))

    # manto externo esfarrapado
    manto = [
        (sx - r * 0.95, sy - r * 2.75), (sx + r * 0.95, sy - r * 2.75),
        (sx + r * 1.5, sy - r * 0.1), (sx + r * 1.05, sy - r * 0.5),
        (sx + r * 0.7, sy + r * 0.05), (sx + r * 0.3, sy - r * 0.45),
        (sx, sy + r * 0.12), (sx - r * 0.35, sy - r * 0.4),
        (sx - r * 0.72, sy + r * 0.02), (sx - r * 1.08, sy - r * 0.52),
        (sx - r * 1.5, sy - r * 0.1),
    ]
    _poly(surf, (40, 26, 64), manto, CONTORNO, 2)
    # manto interno
    _poly(
        surf, (62, 40, 96),
        [(sx - r * 0.7, sy - r * 2.6), (sx + r * 0.7, sy - r * 2.6),
         (sx + r * 0.95, sy - r * 0.8), (sx + r * 0.4, sy - r * 0.45),
         (sx, sy - r * 0.7), (sx - r * 0.4, sy - r * 0.45), (sx - r * 0.95, sy - r * 0.8)],
        CONTORNO, 1,
    )
    # runas no manto
    for i in range(5):
        ry = sy - r * (2.2 - i * 0.32)
        pygame.draw.line(surf, _c((172, 128, 236), flash), (sx - r * 0.35, ry), (sx - r * 0.2, ry), 1)
        pygame.draw.line(surf, _c((172, 128, 236), flash), (sx + r * 0.2, ry), (sx + r * 0.35, ry), 1)
    # gola alta
    _poly(
        surf, (30, 20, 46),
        [(sx - r * 0.7, sy - r * 2.62), (sx - r * 0.95, sy - r * 3.15),
         (sx - r * 0.15, sy - r * 2.8), (sx + r * 0.15, sy - r * 2.8),
         (sx + r * 0.95, sy - r * 3.15), (sx + r * 0.7, sy - r * 2.62)],
        CONTORNO, 2,
    )
    # cabeça encapuzada
    cy = sy - r * 2.95
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(cy)), int(r * 0.68 + 2))
    pygame.draw.circle(surf, (28, 20, 42), (int(sx), int(cy)), int(r * 0.66))
    # rosto vazio com brilho
    halo_suave(surf, (sx, cy), r * 0.55, cor, alpha=int(60 + 30 * pulso))
    pygame.draw.ellipse(
        surf, (16, 12, 26),
        (int(sx - r * 0.34), int(cy - r * 0.2), int(r * 0.68), int(r * 0.55)),
    )
    for ox in (-r * 0.17, r * 0.17):
        pygame.draw.circle(surf, (255, 214, 140), (int(sx + ox), int(cy - r * 0.02)), max(2, int(r * 0.08)))
        pygame.draw.circle(surf, (255, 248, 220), (int(sx + ox), int(cy - r * 0.02)), max(1, int(r * 0.035)))
    # coroa de fragmentos
    for i in range(5):
        ang = -math.pi / 2 + (i - 2) * 0.38
        bx = sx + math.cos(ang) * r * 0.5
        by = cy + math.sin(ang) * r * 0.5
        tx = sx + math.cos(ang) * r * (0.95 + (i % 2) * 0.22)
        ty = cy + math.sin(ang) * r * (0.95 + (i % 2) * 0.22)
        _poly(
            surf, _clarear(cor, 30),
            [(bx - 4, by + 3), (tx, ty), (bx + 4, by + 3)],
            CONTORNO, 1,
        )
        pygame.draw.circle(surf, (255, 240, 255), (int(tx), int(ty)), 1)

    # braços esqueléticos com garras
    for lado in (-1, 1):
        ombro = (sx + lado * r * 0.82, sy - r * 2.2)
        cotovelo = (sx + lado * r * 1.28, sy - r * 1.45 + math.sin(t * 2 + lado) * 3)
        mao = (sx + lado * r * 1.1, sy - r * 0.72)
        pygame.draw.line(surf, CONTORNO, ombro, cotovelo, max(3, int(r * 0.16)))
        pygame.draw.line(surf, (198, 188, 178), ombro, cotovelo, max(2, int(r * 0.09)))
        pygame.draw.line(surf, CONTORNO, cotovelo, mao, max(3, int(r * 0.13)))
        pygame.draw.line(surf, (198, 188, 178), cotovelo, mao, max(2, int(r * 0.07)))
        for dedo in (-1, 0, 1):
            pygame.draw.line(
                surf, (214, 204, 190), mao,
                (mao[0] + lado * r * 0.2 + dedo * 4, mao[1] + r * 0.18 + abs(dedo) * 2),
                1,
            )

    # cristal central no peito
    ccx, ccy = sx, sy - r * 1.7
    _poly(
        surf, _clarear(cor, 42),
        [(ccx, ccy - r * 0.5), (ccx + r * 0.24, ccy - r * 0.08),
         (ccx, ccy + r * 0.52), (ccx - r * 0.24, ccy - r * 0.08)],
        CONTORNO, 2,
    )
    pygame.draw.line(surf, (255, 246, 255), (ccx, ccy - r * 0.38), (ccx, ccy + r * 0.32), 1)

    # fragmentos orbitando
    for i in range(6):
        a = t * 1.4 + i * math.tau / 6
        px = sx + math.cos(a) * r * (1.75 + 0.15 * math.sin(t + i))
        py = sy - r * 1.7 + math.sin(a) * r * 1.0
        tam = 8 + (i % 3) * 3
        _poly(
            surf, _clarear(cor, 26 + (i % 2) * 18),
            [(px, py - tam), (px + tam * 0.55, py), (px, py + tam), (px - tam * 0.55, py)],
            CONTORNO, 1,
        )
        pygame.draw.circle(surf, (255, 236, 255), (int(px), int(py - tam * 0.35)), 1)



def _morcego(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    asa = 0.5 + 0.5 * math.sin(inimigo.tempo * 15)
    sombra(surf, sx, sy - 2, r * 1.2, r * 0.4, 70)

    for lado in (-1, 1):
        pts = [
            (sx, sy - r * 0.9),
            (sx + lado * (r * 1.5 + 5 * asa), sy - r * (1.4 + 0.5 * asa)),
            (sx + lado * (r * 2.0 + 7 * asa), sy - r * 0.3),
            (sx + lado * r * 0.7, sy - r * 0.5),
        ]
        _poly(surf, _escurecer(cor, 25), pts, CONTORNO, 2)

    pygame.draw.ellipse(surf, cor, (int(sx - r * 0.5), int(sy - r * 1.4), int(r), int(r * 1.3)))
    pygame.draw.ellipse(surf, CONTORNO, (int(sx - r * 0.5), int(sy - r * 1.4), int(r), int(r * 1.3)), 2)

    for lado in (-1, 1):
        pts = [
            (sx + lado * r * 0.35, sy - r * 1.25),
            (sx + lado * r * 0.55, sy - r * 1.9),
            (sx + lado * r * 0.05, sy - r * 1.4),
        ]
        pygame.draw.polygon(surf, cor, pts)
        pygame.draw.polygon(surf, CONTORNO, pts, 2)
        pygame.draw.circle(
            surf, (250, 220, 140), (int(sx + lado * r * 0.22), int(sy - r * 0.9)),
            max(2, int(r * 0.14)),
        )

    for lado in (-1, 1):
        pygame.draw.polygon(
            surf, (240, 240, 245),
            [
                (sx + lado * r * 0.18, sy - r * 0.55),
                (sx + lado * r * 0.10, sy - r * 0.15),
                (sx + lado * r * 0.02, sy - r * 0.55),
            ],
        )


def _aranha(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    t = inimigo.tempo
    sombra(surf, sx, sy - 1, r * 1.3, r * 0.5, 70)
    for lado in (-1, 1):
        for i in range(4):
            px = sx + lado * r * 1.6
            py = sy - r * 0.6 + math.sin(t * 8 + i) * 2
            pygame.draw.line(surf, CONTORNO, (sx, sy - r * 0.7), (px, py), 3)
            pygame.draw.line(surf, cor, (sx, sy - r * 0.7), (px, py), 1)
    pygame.draw.ellipse(surf, CONTORNO, (int(sx - r * 0.8), int(sy - r * 1.4), int(r * 1.6), int(r * 1.5)))
    pygame.draw.ellipse(surf, cor, (int(sx - r * 0.65), int(sy - r * 1.3), int(r * 1.3), int(r * 1.2)))
    pygame.draw.polygon(
        surf, _clarear(cor, 40),
        [(sx, sy - r * 1.1), (sx + r * 0.35, sy - r * 0.7), (sx, sy - r * 0.3), (sx - r * 0.35, sy - r * 0.7)],
    )
    for ox in (-0.28, 0.0, 0.28):
        pygame.draw.circle(surf, (250, 80, 90), (int(sx + ox * r), int(sy - r * 1.05)), max(1, int(r * 0.1)))


def _elemental_cristal(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    t = inimigo.tempo
    pulso = 0.6 + 0.4 * math.sin(t * 2.5)
    sombra(surf, sx, sy - 1, r * 1.15, r * 0.4, 80)
    flutua = math.sin(t * 2.0) * 4
    cy = sy - r * 1.15 + flutua
    halo_suave(surf, (sx, cy), r * 2.7, cor, alpha=int(45 + 25 * pulso))

    # base de estilhaços
    for i in range(5):
        ang = i * math.tau / 5 + t * 0.25
        px = sx + math.cos(ang) * r * 0.85
        py = sy - 2 + math.sin(ang) * r * 0.22
        _poly(
            surf, _escurecer(cor, 30),
            [(px - r * 0.12, py), (px, py - r * (0.35 + 0.15 * (i % 2))), (px + r * 0.12, py)],
            CONTORNO, 1,
        )
    # corpo prismático
    corpo = [
        (sx, cy - r * 1.25), (sx + r * 0.62, cy - r * 0.3),
        (sx + r * 0.34, cy + r * 0.95), (sx - r * 0.34, cy + r * 0.95),
        (sx - r * 0.62, cy - r * 0.3),
    ]
    _poly(surf, _escurecer(cor, 18), corpo, CONTORNO, 2)
    _poly(
        surf, cor,
        [(sx, cy - r * 1.05), (sx + r * 0.46, cy - r * 0.25),
         (sx + r * 0.22, cy + r * 0.72), (sx - r * 0.22, cy + r * 0.72),
         (sx - r * 0.46, cy - r * 0.25)],
    )
    # facetas
    pygame.draw.line(surf, _clarear(cor, 70), (sx, cy - r * 1.0), (sx, cy + r * 0.68), 2)
    pygame.draw.line(surf, _clarear(cor, 46), (sx, cy - r * 0.9), (sx + r * 0.4, cy - r * 0.2), 1)
    pygame.draw.line(surf, _clarear(cor, 46), (sx, cy - r * 0.9), (sx - r * 0.4, cy - r * 0.2), 1)
    pygame.draw.line(surf, _escurecer(cor, 30), (sx + r * 0.4, cy - r * 0.2), (sx + r * 0.2, cy + r * 0.6), 1)
    # núcleo
    pygame.draw.circle(surf, (255, 255, 255), (int(sx), int(cy - r * 0.18)), max(2, int(r * 0.14 + pulso * 2)))
    # ombreiras de cristal
    for lado in (-1, 1):
        ox = sx + lado * r * 0.58
        _poly(
            surf, _clarear(cor, 24),
            [(ox - lado * r * 0.1, cy - r * 0.42), (ox + lado * r * 0.34, cy - r * 1.05),
             (ox + lado * r * 0.16, cy - r * 0.2)],
            CONTORNO, 1,
        )
        # braço flutuante
        pygame.draw.line(surf, CONTORNO, (ox, cy - r * 0.1), (ox + lado * r * 0.5, cy + r * 0.55), max(3, int(r * 0.1)))
        pygame.draw.line(surf, _clarear(cor, 20), (ox, cy - r * 0.1), (ox + lado * r * 0.5, cy + r * 0.55), max(1, int(r * 0.05)))
    # cabeça / coroa flutuante
    cab = (sx, cy - r * 1.45)
    _poly(
        surf, _clarear(cor, 30),
        [(cab[0], cab[1] - r * 0.28), (cab[0] + r * 0.24, cab[1]), (cab[0], cab[1] + r * 0.28), (cab[0] - r * 0.24, cab[1])],
        CONTORNO, 1,
    )
    pygame.draw.circle(surf, (255, 255, 255), (int(cab[0]), int(cab[1])), max(1, int(r * 0.08)))
    # estilhaços orbitando
    for i in range(4):
        a = t * 1.6 + i * math.tau / 4
        px = sx + math.cos(a) * r * 1.55
        py = cy - r * 0.2 + math.sin(a) * r * 0.75
        _poly(
            surf, _clarear(cor, 25),
            [(px, py - 7), (px + 4, py), (px, py + 7), (px - 4, py)],
            CONTORNO, 1,
        )



def _lobo(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 40)
    andando = inimigo.estado == "chase"
    swing = math.sin(inimigo.walk_phase) * 5 if andando else 0
    sombra(surf, sx, sy - 2, r * 1.1, r * 0.35, 85)
    pygame.draw.line(surf, CONTORNO, (sx - r * 0.9, sy - r * 0.9), (sx - r * 1.5, sy - r * 1.4), 5)
    pygame.draw.line(surf, cor, (sx - r * 0.9, sy - r * 0.9), (sx - r * 1.5, sy - r * 1.4), 3)
    for lado in (-1, 1):
        pygame.draw.line(
            surf, CONTORNO,
            (sx + lado * r * 0.45, sy - r * 0.7), (sx + lado * r * 0.45 + swing * lado, sy - 2), 6,
        )
        pygame.draw.line(
            surf, escuro,
            (sx + lado * r * 0.45, sy - r * 0.7), (sx + lado * r * 0.45 + swing * lado, sy - 2), 3,
        )
    pygame.draw.ellipse(surf, CONTORNO, (int(sx - r * 0.95), int(sy - r * 1.35), int(r * 1.9), int(r * 0.95)))
    pygame.draw.ellipse(surf, cor, (int(sx - r * 0.88), int(sy - r * 1.3), int(r * 1.76), int(r * 0.82)))
    cx, cy = sx + r * 0.85, sy - r * 1.25
    pygame.draw.circle(surf, CONTORNO, (int(cx), int(cy)), int(r * 0.52 + 2))
    pygame.draw.circle(surf, cor, (int(cx), int(cy)), int(r * 0.5))
    for lado in (-1, 1):
        _poly(
            surf, cor,
            [
                (cx + lado * r * 0.2, cy - r * 0.35),
                (cx + lado * r * 0.45, cy - r * 0.8),
                (cx + lado * r * 0.5, cy - r * 0.3),
            ],
            CONTORNO, 1,
        )
    pygame.draw.circle(surf, escuro, (int(cx + r * 0.35), int(cy + r * 0.15)), max(1, int(r * 0.16)))
    pygame.draw.circle(surf, (250, 220, 120), (int(cx + r * 0.05), int(cy - r * 0.1)), max(1, int(r * 0.1)))
    pygame.draw.circle(surf, (250, 220, 120), (int(cx + r * 0.38), int(cy - r * 0.1)), max(1, int(r * 0.08)))


def _serpente(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    claro = _clarear(cor, 50)
    t = inimigo.tempo
    sway = math.sin(t * 2.2) * 3
    sombra(surf, sx, sy - 2, r * 1.2, r * 0.4, 85)
    for ox, oy, rr in (
        (-r * 0.5, -r * 0.5, r * 0.55),
        (0, -r * 0.35, r * 0.6),
        (r * 0.45, -r * 0.55, r * 0.5),
    ):
        pygame.draw.circle(surf, CONTORNO, (int(sx + ox), int(sy + oy)), int(rr + 2))
        pygame.draw.circle(surf, cor, (int(sx + ox), int(sy + oy)), int(rr))
    cabeca = (sx + r * 0.2 + sway, sy - r * 1.8)
    pygame.draw.line(surf, CONTORNO, (sx, sy - r * 0.8), cabeca, 9)
    pygame.draw.line(surf, cor, (sx, sy - r * 0.8), cabeca, 6)
    pygame.draw.circle(surf, CONTORNO, (int(cabeca[0]), int(cabeca[1])), int(r * 0.45 + 2))
    pygame.draw.circle(surf, cor, (int(cabeca[0]), int(cabeca[1])), int(r * 0.43))
    for i in range(3):
        ox = -r * 0.5 + i * r * 0.45
        pygame.draw.circle(surf, claro, (int(sx + ox), int(sy - r * 0.55)), max(1, int(r * 0.12)))
    for ox in (-r * 0.15, r * 0.15):
        pygame.draw.circle(
            surf, (250, 220, 120), (int(cabeca[0] + ox), int(cabeca[1] - r * 0.1)), max(1, int(r * 0.09))
        )
    pygame.draw.line(
        surf, (240, 90, 110),
        (cabeca[0], cabeca[1] + r * 0.3), (cabeca[0] + r * 0.3, cabeca[1] + r * 0.55), 1,
    )


def _sapo(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    claro = _clarear(cor, 46)
    escuro = _escurecer(cor, 44)
    barriga = _clarear(cor, 74)
    andando = inimigo.estado == "chase"
    pulo = abs(math.sin(inimigo.walk_phase)) * 6 if andando else 0.0
    sombra(surf, sx, sy - 2, r * 1.15, r * 0.4, 95)
    sy -= pulo
    # pernas traseiras dobradas
    for lado in (-1, 1):
        joelho = (sx + lado * r * 0.9, sy - r * 0.55)
        pe = (sx + lado * r * 1.25, sy - 2)
        pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.45, sy - r * 0.8), joelho, 7)
        pygame.draw.line(surf, escuro, (sx + lado * r * 0.45, sy - r * 0.8), joelho, 4)
        pygame.draw.line(surf, CONTORNO, joelho, pe, 6)
        pygame.draw.line(surf, escuro, joelho, pe, 3)
    # corpo
    corpo = pygame.Rect(int(sx - r), int(sy - r * 1.32), int(r * 2), int(r * 1.22))
    pygame.draw.ellipse(surf, CONTORNO, corpo.inflate(5, 5))
    pygame.draw.ellipse(surf, cor, corpo)
    pygame.draw.ellipse(surf, barriga, (corpo.x + 8, corpo.y + int(corpo.h * 0.5), corpo.w - 16, int(corpo.h * 0.45)))
    pygame.draw.ellipse(surf, claro, (corpo.x + 7, corpo.y + 5, int(corpo.w * 0.42), int(corpo.h * 0.3)))
    # manchas
    for ox, oy in ((-0.5, -1.0), (0.45, -0.95), (-0.15, -0.72)):
        pygame.draw.circle(surf, escuro, (int(sx + r * ox), int(sy + r * oy)), max(2, int(r * 0.1)))
    # olhos salientes
    for lado in (-1, 1):
        olho = (sx + lado * r * 0.52, sy - r * 1.45)
        pygame.draw.circle(surf, CONTORNO, (int(olho[0]), int(olho[1])), int(r * 0.34 + 2))
        pygame.draw.circle(surf, (238, 236, 206), (int(olho[0]), int(olho[1])), int(r * 0.32))
        pygame.draw.circle(surf, (38, 30, 30), (int(olho[0] + lado * 2), int(olho[1])), int(r * 0.14))
        pygame.draw.circle(surf, (255, 255, 255), (int(olho[0] + lado * 2 - 1), int(olho[1] - 2)), 1)
    # boca larga
    pygame.draw.arc(
        surf, CONTORNO,
        pygame.Rect(int(sx - r * 0.55), int(sy - r * 1.02), int(r * 1.1), int(r * 0.42)),
        0.25, math.pi - 0.25, 2,
    )
    # braços da frente
    for lado in (-1, 1):
        mao = (sx + lado * r * 0.7, sy - r * 0.18)
        pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.55, sy - r * 0.9), mao, 5)
        pygame.draw.line(surf, claro, (sx + lado * r * 0.55, sy - r * 0.9), mao, 3)


def _mosquito(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 42)
    claro = _clarear(cor, 50)
    t = inimigo.tempo
    flutua = math.sin(t * 4.2) * 5
    sombra(surf, sx, sy - 2, r * 0.8, r * 0.3, 70)
    sy -= 18 + flutua
    # asas
    bater = math.sin(t * 34) * 5
    for lado in (-1, 1):
        _poly(
            surf, (222, 236, 240),
            [
                (sx + lado * r * 0.25, sy - r * 0.35),
                (sx + lado * (r * 1.25 + bater * 0.4), sy - r * 1.0),
                (sx + lado * r * 0.9, sy - r * 0.15),
            ],
            (170, 190, 200), 1,
        )
    # corpo
    pygame.draw.ellipse(surf, CONTORNO, (int(sx - r * 0.34), int(sy - r * 0.75), int(r * 0.68), int(r * 1.35)))
    pygame.draw.ellipse(surf, cor, (int(sx - r * 0.3), int(sy - r * 0.7), int(r * 0.6), int(r * 1.25)))
    pygame.draw.line(surf, escuro, (sx, sy - r * 0.5), (sx, sy + r * 0.4), 2)
    # cabeça
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(sy - r * 0.95)), int(r * 0.42 + 2))
    pygame.draw.circle(surf, claro, (int(sx), int(sy - r * 0.95)), int(r * 0.4))
    for lado in (-1, 1):
        pygame.draw.circle(surf, (196, 60, 70), (int(sx + lado * r * 0.16), int(sy - r * 1.0)), max(2, int(r * 0.11)))
    # tromba
    pygame.draw.line(surf, CONTORNO, (sx, sy - r * 0.72), (sx, sy + r * 0.85), 3)
    pygame.draw.line(surf, (70, 48, 44), (sx, sy - r * 0.72), (sx, sy + r * 0.85), 1)
    # pernas penduradas
    for i, ox in enumerate((-0.22, 0.0, 0.22)):
        yy = sy - r * 0.15 + i * r * 0.28
        for lado in (-1, 1):
            pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.12, yy), (sx + lado * r * 0.55, yy + r * 0.5), 2)


def _lodo(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    claro = _clarear(cor, 44)
    escuro = _escurecer(cor, 36)
    t = inimigo.tempo
    pulso = 1.0 + math.sin(t * 3.2) * 0.05
    w = r * 2.2 * pulso
    h = r * 1.35 / pulso
    sombra(surf, sx, sy - 2, r * 1.15, r * 0.4, 95)
    if inimigo.estado == "chase":
        sy -= abs(math.sin(inimigo.walk_phase * 0.8)) * 2
    pygame.draw.ellipse(surf, CONTORNO, (int(sx - w / 2 - 2), int(sy - h - 2), int(w + 4), int(h + 4)))
    pygame.draw.ellipse(surf, cor, (int(sx - w / 2), int(sy - h), int(w), int(h)))
    pygame.draw.ellipse(surf, claro, (int(sx - w * 0.34), int(sy - h * 0.92), int(w * 0.5), int(h * 0.42)))
    # bolhas e detritos
    for ox, oy, rr in ((-0.3, -0.5, 0.12), (0.25, -0.35, 0.09), (0.05, -0.65, 0.07)):
        pygame.draw.circle(surf, escuro, (int(sx + w * ox), int(sy + h * oy)), max(2, int(r * rr)))
        pygame.draw.circle(surf, claro, (int(sx + w * ox - 1), int(sy + h * oy - 1)), max(1, int(r * rr * 0.4)))
    pygame.draw.line(surf, (78, 62, 40), (sx - w * 0.2, sy - h * 0.95), (sx - w * 0.05, sy - h * 1.2), 2)
    pygame.draw.line(surf, (78, 62, 40), (sx - w * 0.05, sy - h * 1.2), (sx + w * 0.08, sy - h * 1.1), 2)
    # olhos
    olho_y = int(sy - h * 0.6)
    for ox in (-r * 0.34, r * 0.34):
        pygame.draw.circle(surf, (244, 240, 210), (int(sx + ox), olho_y), max(3, int(r * 0.16)))
        pygame.draw.circle(surf, (34, 30, 28), (int(sx + ox + 1), olho_y), max(1, int(r * 0.07)))
    pygame.draw.arc(
        surf, CONTORNO,
        pygame.Rect(int(sx - r * 0.32), int(sy - h * 0.42), int(r * 0.64), int(r * 0.3)),
        math.pi + 0.2, math.tau - 0.2, 2,
    )
    # gosma escorrendo
    for ox in (-0.6, 0.45):
        pygame.draw.line(surf, escuro, (sx + w * ox, sy - h * 0.45), (sx + w * ox, sy - 2), 2)


def _rainha_lodo(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    claro = _clarear(cor, 42)
    escuro = _escurecer(cor, 48)
    barriga = _clarear(cor, 68)
    t = inimigo.tempo
    respira = math.sin(t * 1.8) * 3
    sombra(surf, sx, sy - 2, r * 1.3, r * 0.45, 110)
    sy += respira * 0.3

    # pernas traseiras
    for lado in (-1, 1):
        joelho = (sx + lado * r * 1.0, sy - r * 0.62)
        pe = (sx + lado * r * 1.45, sy - 2)
        pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.5, sy - r * 0.85), joelho, 11)
        pygame.draw.line(surf, escuro, (sx + lado * r * 0.5, sy - r * 0.85), joelho, 7)
        pygame.draw.line(surf, CONTORNO, joelho, pe, 9)
        pygame.draw.line(surf, escuro, joelho, pe, 5)
        for dedo in (-1, 0, 1):
            pygame.draw.line(surf, CONTORNO, pe, (pe[0] + dedo * 7, pe[1] - 2), 3)

    # corpo
    corpo = pygame.Rect(int(sx - r * 1.05), int(sy - r * 1.55), int(r * 2.1), int(r * 1.45))
    pygame.draw.ellipse(surf, CONTORNO, corpo.inflate(6, 6))
    pygame.draw.ellipse(surf, cor, corpo)
    pygame.draw.ellipse(surf, barriga, (corpo.x + 12, corpo.y + int(corpo.h * 0.48), corpo.w - 24, int(corpo.h * 0.46)))
    pygame.draw.ellipse(surf, claro, (corpo.x + 10, corpo.y + 8, int(corpo.w * 0.4), int(corpo.h * 0.3)))

    # verrugas e manchas
    for ox, oy, rr in ((-0.62, -1.15, 0.07), (0.55, -1.2, 0.06), (-0.35, -0.85, 0.05), (0.38, -0.8, 0.06)):
        pygame.draw.circle(surf, escuro, (int(sx + r * ox), int(sy + r * oy)), max(2, int(r * rr * 3)))

    # capa de vitória-régia atrás
    folha = pygame.Rect(int(sx - r * 1.35), int(sy - r * 1.9), int(r * 2.7), int(r * 0.7))
    pygame.draw.ellipse(surf, CONTORNO, folha.inflate(4, 4))
    pygame.draw.ellipse(surf, (64, 124, 82), folha)
    pygame.draw.arc(surf, (44, 96, 64), folha, 0.3, 2.6, 2)
    for i in range(5):
        ang = math.pi + 0.3 + i * (math.pi - 0.6) / 4
        pygame.draw.line(
            surf, (48, 104, 70), folha.center,
            (folha.centerx + math.cos(ang) * folha.w * 0.46, folha.centery + math.sin(ang) * folha.h * 0.42), 1,
        )

    # cabeça e olhos salientes
    cabeca = (sx, sy - r * 1.62)
    pygame.draw.circle(surf, CONTORNO, (int(cabeca[0]), int(cabeca[1])), int(r * 0.62 + 2))
    pygame.draw.circle(surf, cor, (int(cabeca[0]), int(cabeca[1])), int(r * 0.6))
    for lado in (-1, 1):
        olho = (sx + lado * r * 0.4, sy - r * 1.95)
        pygame.draw.circle(surf, CONTORNO, (int(olho[0]), int(olho[1])), int(r * 0.24 + 2))
        pygame.draw.circle(surf, (246, 240, 196), (int(olho[0]), int(olho[1])), int(r * 0.22))
        pygame.draw.circle(surf, (36, 30, 28), (int(olho[0] + lado * 2), int(olho[1] + 1)), int(r * 0.1))
    # boca e queixo
    pygame.draw.arc(
        surf, CONTORNO,
        pygame.Rect(int(sx - r * 0.55), int(sy - r * 1.6), int(r * 1.1), int(r * 0.46)),
        0.25, math.pi - 0.25, 3,
    )
    pygame.draw.line(surf, escuro, (sx - r * 0.5, sy - r * 1.42), (sx + r * 0.5, sy - r * 1.42), 2)

    # coroa de juncos e cristal
    for i, ox in enumerate((-0.42, -0.14, 0.14, 0.42)):
        altura = r * (0.55 + 0.12 * (i % 2))
        base = (sx + r * ox, sy - r * 2.05)
        topo = (base[0] + r * 0.06, base[1] - altura)
        pygame.draw.line(surf, CONTORNO, base, topo, 5)
        pygame.draw.line(surf, (204, 178, 96), base, topo, 3)
        pygame.draw.circle(surf, (246, 220, 130), (int(topo[0]), int(topo[1])), 3)
    halo_suave(surf, (sx, sy - r * 2.85), r * 0.9, (180, 255, 190), 80)
    pygame.draw.polygon(
        surf, (150, 240, 190),
        [(sx, sy - r * 3.0), (sx + r * 0.16, sy - r * 2.78), (sx, sy - r * 2.55), (sx - r * 0.16, sy - r * 2.78)],
    )
    pygame.draw.polygon(
        surf, (236, 255, 240),
        [(sx, sy - r * 3.0), (sx + r * 0.16, sy - r * 2.78), (sx, sy - r * 2.55), (sx - r * 0.16, sy - r * 2.78)],
        1,
    )

    # braços com dedos
    for lado in (-1, 1):
        mao = (sx + lado * r * 0.95, sy - r * 0.4)
        pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.65, sy - r * 1.2), mao, 8)
        pygame.draw.line(surf, claro, (sx + lado * r * 0.65, sy - r * 1.2), mao, 5)
        for dedo in (-1, 0, 1):
            pygame.draw.line(surf, CONTORNO, mao, (mao[0] + lado * 9 + dedo * 3, mao[1] + 7), 3)


def _sentinela_aether(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 52)
    claro = _clarear(cor, 46)
    t = inimigo.tempo
    flutua = math.sin(t * 2.0) * 5
    sombra(surf, sx, sy - 2, r * 1.0, r * 0.34, 90)
    cy = sy - r * 1.7 + flutua
    halo_suave(surf, (sx, cy), r * 2.0, cor, 75)

    # corpo em forma de obelisco flutuante
    corpo = [
        (sx, cy - r * 1.0), (sx + r * 0.55, cy - r * 0.25),
        (sx + r * 0.38, cy + r * 0.9), (sx - r * 0.38, cy + r * 0.9),
        (sx - r * 0.55, cy - r * 0.25),
    ]
    _poly(surf, escuro, corpo, CONTORNO, 2)
    _poly(
        surf, cor,
        [(sx, cy - r * 0.86), (sx + r * 0.42, cy - r * 0.22),
         (sx + r * 0.28, cy + r * 0.74), (sx - r * 0.28, cy + r * 0.74),
         (sx - r * 0.42, cy - r * 0.22)],
    )
    pygame.draw.line(surf, claro, (sx, cy - r * 0.7), (sx, cy + r * 0.6), 2)
    # olho central
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(cy - r * 0.05)), max(3, int(r * 0.2)))
    pygame.draw.circle(surf, (255, 255, 255), (int(sx), int(cy - r * 0.05)), max(2, int(r * 0.14)))
    pygame.draw.circle(surf, (70, 180, 230), (int(sx), int(cy - r * 0.05)), max(1, int(r * 0.08)))
    # anéis orbitando
    for i in range(2):
        raio = r * (1.05 + i * 0.22)
        pygame.draw.ellipse(
            surf, _clarear(cor, 10),
            (int(sx - raio), int(cy - raio * 0.28), int(raio * 2), int(raio * 0.56)), 1,
        )
    # estilhaços
    for i in range(4):
        a = t * 1.3 + i * math.tau / 4
        px = sx + math.cos(a) * r * 1.25
        py = cy + math.sin(a) * r * 0.62
        _poly(surf, claro, [(px, py - 5), (px + 3, py), (px, py + 5), (px - 3, py)], CONTORNO, 1)


def _espectro_aether(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 58)
    claro = _clarear(cor, 46)
    t = inimigo.tempo
    flutua = math.sin(t * 2.4) * 4
    sombra(surf, sx, sy - 2, r * 0.9, r * 0.3, 70)
    sy += flutua
    halo_suave(surf, (sx, sy - r * 1.4), r * 1.8, cor, 55)
    # manto esfarrapado
    manto = [
        (sx - r * 0.75, sy - r * 1.9), (sx + r * 0.75, sy - r * 1.9),
        (sx + r * 1.05, sy - r * 0.1), (sx + r * 0.6, sy - r * 0.45),
        (sx + r * 0.28, sy + r * 0.05), (sx, sy - r * 0.5),
        (sx - r * 0.3, sy + r * 0.05), (sx - r * 0.62, sy - r * 0.45),
        (sx - r * 1.05, sy - r * 0.1),
    ]
    _poly(surf, escuro, manto, CONTORNO, 2)
    _poly(
        surf, cor,
        [(sx - r * 0.55, sy - r * 1.75), (sx + r * 0.55, sy - r * 1.75),
         (sx + r * 0.72, sy - r * 0.55), (sx, sy - r * 0.25), (sx - r * 0.72, sy - r * 0.55)],
    )
    # capuz e rosto vazio
    cy = sy - r * 2.0
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(cy)), int(r * 0.58 + 2))
    pygame.draw.circle(surf, (32, 24, 48), (int(sx), int(cy)), int(r * 0.56))
    for ox in (-r * 0.16, r * 0.16):
        pygame.draw.circle(surf, (230, 246, 255), (int(sx + ox), int(cy)), max(1, int(r * 0.07)))
    # braços etéreos
    for lado in (-1, 1):
        mao = (sx + lado * r * 0.9, sy - r * 0.6 + math.sin(t * 3 + lado) * 3)
        pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.55, sy - r * 1.5), mao, max(3, int(r * 0.14)))
        pygame.draw.line(surf, claro, (sx + lado * r * 0.55, sy - r * 1.5), mao, max(1, int(r * 0.07)))
    # fragmentos flutuantes
    for i in range(3):
        a = t * 1.6 + i * math.tau / 3
        px = sx + math.cos(a) * r * 1.2
        py = sy - r * 1.2 + math.sin(a) * r * 0.55
        _poly(surf, claro, [(px, py - 4), (px + 3, py), (px, py + 4), (px - 3, py)], CONTORNO, 1)


def _ceifador_nevoa(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 62)
    nevoa = _clarear(cor, 22)
    t = inimigo.tempo
    flutua = math.sin(t * 1.9) * 6
    sombra(surf, sx, sy - 2, r * 0.95, r * 0.32, 80)
    cy = sy - r * 1.7 + flutua
    halo_suave(surf, (sx, cy), r * 2.2, cor, 70)

    # manto esfarrapado
    manto = [
        (sx - r * 0.8, cy - r * 0.9), (sx + r * 0.8, cy - r * 0.9),
        (sx + r * 1.15, cy + r * 0.8), (sx + r * 0.55, cy + r * 0.5),
        (sx + r * 0.25, cy + r * 1.0), (sx, cy + r * 0.55),
        (sx - r * 0.3, cy + r * 1.0), (sx - r * 0.6, cy + r * 0.5),
        (sx - r * 1.15, cy + r * 0.8),
    ]
    _poly(surf, escuro, manto, CONTORNO, 2)
    _poly(
        surf, cor,
        [(sx - r * 0.55, cy - r * 0.75), (sx + r * 0.55, cy - r * 0.75),
         (sx + r * 0.72, cy + r * 0.35), (sx, cy + r * 0.1), (sx - r * 0.72, cy + r * 0.35)],
    )
    # capuz e olhos
    topo = cy - r * 1.05
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(topo)), int(r * 0.55 + 2))
    pygame.draw.circle(surf, (26, 30, 44), (int(sx), int(topo)), int(r * 0.53))
    for ox in (-r * 0.16, r * 0.16):
        pygame.draw.circle(surf, (190, 240, 255), (int(sx + ox), int(topo)), max(1, int(r * 0.08)))
    # foice
    cabo_ini = (sx - r * 0.95, cy + r * 1.25)
    cabo_fim = (sx + r * 0.85, cy - r * 1.15)
    pygame.draw.line(surf, CONTORNO, cabo_ini, cabo_fim, max(5, int(r * 0.18)))
    pygame.draw.line(surf, (120, 104, 86), cabo_ini, cabo_fim, max(3, int(r * 0.09)))
    lamina = [
        cabo_fim,
        (cabo_fim[0] + r * 0.75, cabo_fim[1] - r * 0.15),
        (cabo_fim[0] + r * 1.15, cabo_fim[1] + r * 0.35),
        (cabo_fim[0] + r * 0.7, cabo_fim[1] + r * 0.3),
    ]
    _poly(surf, (230, 245, 255), lamina, CONTORNO, 2)
    pygame.draw.line(surf, (255, 255, 255), lamina[1], lamina[2], 2)
    # névoa ao redor
    for i in range(5):
        a = t * 0.8 + i * math.tau / 5
        px = sx + math.cos(a) * r * 1.35
        py = cy + r * 0.55 + math.sin(a) * r * 0.3
        pygame.draw.circle(surf, nevoa, (int(px), int(py)), max(2, int(r * 0.12)))


def _guardiao_eclipse(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 60)
    claro = _clarear(cor, 50)
    prata = (220, 224, 240)
    ouro = (240, 214, 140)
    t = inimigo.tempo
    flutua = math.sin(t * 1.4) * 3
    sombra(surf, sx, sy - 2, r * 1.2, r * 0.42, 115)
    cy = sy - r * 1.9 + flutua
    halo_suave(surf, (sx, cy), r * 2.5, cor, 90)

    # halo de eclipse atrás da cabeça
    pygame.draw.circle(surf, (16, 12, 26), (int(sx), int(cy - r * 0.75)), int(r * 1.15))
    pygame.draw.circle(surf, ouro, (int(sx), int(cy - r * 0.75)), int(r * 1.15), 3)
    pygame.draw.circle(surf, (90, 60, 130), (int(sx), int(cy - r * 0.75)), int(r * 1.0), 1)

    # capa
    capa = [
        (sx - r * 0.7, cy - r * 1.0), (sx + r * 0.7, cy - r * 1.0),
        (sx + r * 1.35, cy + r * 1.1), (sx + r * 0.55, cy + r * 0.75),
        (sx, cy + r * 1.15), (sx - r * 0.55, cy + r * 0.75),
        (sx - r * 1.35, cy + r * 1.1),
    ]
    _poly(surf, escuro, capa, CONTORNO, 2)

    # torso/armadura
    torso = [
        (sx - r * 0.58, cy - r * 0.85), (sx + r * 0.58, cy - r * 0.85),
        (sx + r * 0.72, cy + r * 0.35), (sx + r * 0.3, cy + r * 0.8),
        (sx - r * 0.3, cy + r * 0.8), (sx - r * 0.72, cy + r * 0.35),
    ]
    _poly(surf, cor, torso, CONTORNO, 2)
    _poly(
        surf, claro,
        [(sx - r * 0.42, cy - r * 0.7), (sx + r * 0.42, cy - r * 0.7),
         (sx + r * 0.3, cy - r * 0.05), (sx, cy + r * 0.2), (sx - r * 0.3, cy - r * 0.05)],
        CONTORNO, 1,
    )
    pygame.draw.circle(surf, (16, 12, 26), (int(sx), int(cy - r * 0.35)), int(r * 0.16))
    pygame.draw.circle(surf, ouro, (int(sx), int(cy - r * 0.35)), int(r * 0.16), 2)

    # cabeça/elmo
    topo = cy - r * 1.25
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(topo)), int(r * 0.45 + 2))
    pygame.draw.circle(surf, escuro, (int(sx), int(topo)), int(r * 0.43))
    for lado in (-1, 1):
        _poly(
            surf, prata,
            [(sx + lado * r * 0.3, topo - r * 0.25),
             (sx + lado * r * 0.55, topo - r * 0.6),
             (sx + lado * r * 0.42, topo - r * 0.2)],
            CONTORNO, 1,
        )
    for ox in (-r * 0.14, r * 0.14):
        pygame.draw.circle(surf, (220, 250, 255), (int(sx + ox), int(topo)), max(2, int(r * 0.06)))

    # escudo à esquerda
    escudo = (sx - r * 0.95, cy + r * 0.1)
    pygame.draw.circle(surf, CONTORNO, escudo, int(r * 0.7 + 2))
    pygame.draw.circle(surf, claro, escudo, int(r * 0.7))
    pygame.draw.circle(surf, (16, 12, 26), escudo, int(r * 0.42))
    pygame.draw.circle(surf, ouro, escudo, int(r * 0.42), 3)
    pygame.draw.circle(
        surf, (255, 246, 210),
        (int(escudo[0] - r * 0.12), int(escudo[1] - r * 0.12)), max(2, int(r * 0.07)),
    )

    # lança à direita
    ponta = (sx + r * 1.05, cy - r * 1.45)
    base = (sx + r * 0.5, cy + r * 1.15)
    pygame.draw.line(surf, CONTORNO, base, ponta, max(5, int(r * 0.13)))
    pygame.draw.line(surf, prata, base, ponta, max(3, int(r * 0.07)))
    _poly(
        surf, prata,
        [(ponta[0], ponta[1] - r * 0.28),
         (ponta[0] + r * 0.16, ponta[1] + r * 0.12),
         (ponta[0] - r * 0.16, ponta[1] + r * 0.12)],
        CONTORNO, 1,
    )

    # estilhaços orbitando
    for i in range(6):
        a = t * 1.1 + i * math.tau / 6
        px = sx + math.cos(a) * r * 1.45
        py = cy + math.sin(a) * r * 0.9
        _poly(surf, claro, [(px, py - 6), (px + 4, py), (px, py + 6), (px - 4, py)], CONTORNO, 1)


def _avatar_aether(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 48)
    claro = _clarear(cor, 42)
    dourado = (238, 214, 140)
    t = inimigo.tempo
    flutua = math.sin(t * 1.8) * 5
    sombra(surf, sx, sy - 2, r * 1.2, r * 0.4, 105)
    sy += flutua
    halo_suave(surf, (sx, sy - r * 2.2), r * 2.6, cor, 80)

    # asas de luz em camadas
    for lado in (-1, 1):
        for i, (alcance, altura) in enumerate(((1.7, 1.1), (1.35, 1.5), (1.0, 1.9))):
            pts = [
                (sx + lado * r * 0.35, sy - r * 2.2),
                (sx + lado * r * alcance, sy - r * (2.1 + altura * 0.35)),
                (sx + lado * r * (alcance * 0.75), sy - r * 0.8),
            ]
            _poly(surf, _clarear(cor, 20 + i * 12), pts, CONTORNO, 1)

    # manto longo
    manto = [
        (sx - r * 0.8, sy - r * 2.4), (sx + r * 0.8, sy - r * 2.4),
        (sx + r * 1.25, sy - r * 0.1), (sx + r * 0.55, sy - r * 0.35),
        (sx, sy + r * 0.05), (sx - r * 0.55, sy - r * 0.35),
        (sx - r * 1.25, sy - r * 0.1),
    ]
    _poly(surf, escuro, manto, CONTORNO, 2)
    _poly(
        surf, cor,
        [(sx - r * 0.6, sy - r * 2.3), (sx + r * 0.6, sy - r * 2.3),
         (sx + r * 0.9, sy - r * 0.5), (sx, sy - r * 0.2), (sx - r * 0.9, sy - r * 0.5)],
    )
    # peitoral e núcleo
    _poly(
        surf, claro,
        [(sx - r * 0.42, sy - r * 2.1), (sx + r * 0.42, sy - r * 2.1),
         (sx + r * 0.3, sy - r * 1.2), (sx - r * 0.3, sy - r * 1.2)],
        CONTORNO, 1,
    )
    pulso = 0.6 + 0.4 * math.sin(t * 3.4)
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(sy - r * 1.62)), int(r * 0.28 + 2))
    pygame.draw.circle(surf, (255, 252, 220), (int(sx), int(sy - r * 1.62)), int(r * 0.24))
    pygame.draw.circle(surf, dourado, (int(sx), int(sy - r * 1.62)), int(r * 0.12 + pulso * 2))

    # cabeça com coroa radiante
    cy = sy - r * 2.75
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(cy)), int(r * 0.48 + 2))
    pygame.draw.circle(surf, (246, 246, 255), (int(sx), int(cy)), int(r * 0.46))
    for ox in (-r * 0.16, r * 0.16):
        pygame.draw.circle(surf, dourado, (int(sx + ox), int(cy)), max(1, int(r * 0.07)))
    for i in range(7):
        ang = -math.pi / 2 + (i - 3) * 0.35
        bx = sx + math.cos(ang) * r * 0.42
        by = cy + math.sin(ang) * r * 0.42
        tx = sx + math.cos(ang) * r * (0.85 + (i % 2) * 0.18)
        ty = cy + math.sin(ang) * r * (0.85 + (i % 2) * 0.18)
        pygame.draw.line(surf, dourado, (bx, by), (tx, ty), 2)
        pygame.draw.circle(surf, (255, 250, 220), (int(tx), int(ty)), 2)

    # braços erguidos durante o ataque
    raise_t = 0.0
    if inimigo.preparando:
        raise_t = 1.0 - max(0.0, inimigo.preparo) / 0.75
    for lado in (-1, 1):
        ombro = (sx + lado * r * 0.62, sy - r * 2.2)
        mao = (sx + lado * r * (0.95 + raise_t * 0.2), sy - r * (0.9 + raise_t * 0.9))
        pygame.draw.line(surf, CONTORNO, ombro, mao, max(4, int(r * 0.18)))
        pygame.draw.line(surf, claro, ombro, mao, max(2, int(r * 0.1)))
        pygame.draw.circle(surf, dourado, (int(mao[0]), int(mao[1])), max(2, int(r * 0.09)))

    # estilhaços orbitando
    for i in range(6):
        a = t * 1.2 + i * math.tau / 6
        px = sx + math.cos(a) * r * 1.5
        py = sy - r * 1.6 + math.sin(a) * r * 0.9
        _poly(surf, claro, [(px, py - 7), (px + 4, py), (px, py + 7), (px - 4, py)], CONTORNO, 1)


def _escorpiao(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 52)
    claro = _clarear(cor, 48)
    brasa = (255, 130, 80)
    andando = inimigo.estado == "chase"
    swing = math.sin(inimigo.walk_phase) * 5.0 if andando else 0.0
    t = inimigo.tempo
    sombra(surf, sx, sy - 2, r * 1.3, r * 0.42, 100)

    # patas segmentadas
    for lado in (-1, 1):
        for i in range(4):
            fase = swing * (1 if i % 2 == 0 else -1) * lado
            origem = (sx + lado * r * 0.4, sy - r * 0.8 + i * r * 0.13)
            joelho = (sx + lado * r * (0.95 + i * 0.08), sy - r * 0.58 + fase * 0.4)
            pe = (sx + lado * r * (1.3 + i * 0.16), sy - 2 + fase)
            pygame.draw.line(surf, CONTORNO, origem, joelho, 6)
            pygame.draw.line(surf, escuro, origem, joelho, 3)
            pygame.draw.line(surf, CONTORNO, joelho, pe, 5)
            pygame.draw.line(surf, escuro, joelho, pe, 2)
            pygame.draw.circle(surf, claro, (int(joelho[0]), int(joelho[1])), 2)

    # corpo em placas
    corpo = pygame.Rect(int(sx - r * 0.78), int(sy - r * 1.15), int(r * 1.56), int(r * 0.95))
    pygame.draw.ellipse(surf, CONTORNO, corpo.inflate(6, 6))
    pygame.draw.ellipse(surf, escuro, corpo)
    pygame.draw.ellipse(surf, cor, corpo.inflate(-5, -5))
    # placas do dorso
    for i in range(3):
        ry = corpo.y + 4 + i * int(corpo.h * 0.22)
        pygame.draw.arc(
            surf, _clarear(cor, 16),
            pygame.Rect(corpo.x + 6 + i * 3, ry, corpo.w - 12 - i * 6, int(corpo.h * 0.4)),
            0.3, math.pi - 0.3, 2,
        )
    # veios de brasa
    for ox, oy in ((-0.3, -0.3), (0.18, -0.55), (0.34, -0.1)):
        pygame.draw.circle(surf, brasa, (int(sx + r * ox), int(sy + r * oy)), max(1, int(r * 0.06)))
        pygame.draw.circle(surf, (255, 220, 170), (int(sx + r * ox), int(sy + r * oy)), 1)
    # brilho no dorso
    pygame.draw.ellipse(surf, claro, (corpo.x + 6, corpo.y + 5, int(corpo.w * 0.38), int(corpo.h * 0.3)))

    # cauda articulada
    pontos = [
        (sx, sy - r * 1.0),
        (sx - r * 0.18, sy - r * 1.4),
        (sx - r * 0.48, sy - r * 1.75),
        (sx - r * 0.82, sy - r * 1.9),
        (sx - r * 1.02, sy - r * 1.66),
        (sx - r * 1.0, sy - r * 1.4),
    ]
    for i in range(len(pontos) - 1):
        pygame.draw.line(surf, CONTORNO, pontos[i], pontos[i + 1], 8)
        pygame.draw.line(surf, escuro, pontos[i], pontos[i + 1], 5)
        pygame.draw.circle(surf, claro, (int(pontos[i][0]), int(pontos[i][1])), 2)
    ferrao = pontos[-1]
    _poly(
        surf, claro,
        [(ferrao[0] - 4, ferrao[1] + 5), (ferrao[0] + 4, ferrao[1] + 5), (ferrao[0], ferrao[1] - 10)],
        CONTORNO, 1,
    )
    pygame.draw.circle(surf, brasa, (int(ferrao[0]), int(ferrao[1] - 1)), 2)

    # pinças grandes
    for lado in (-1, 1):
        base = (sx + lado * r * 0.58, sy - r * 0.9)
        ponta = (sx + lado * r * 1.12, sy - r * 1.0)
        pygame.draw.line(surf, CONTORNO, base, ponta, 7)
        pygame.draw.line(surf, cor, base, ponta, 4)
        pygame.draw.circle(surf, CONTORNO, (int(ponta[0]), int(ponta[1])), 7)
        pygame.draw.circle(surf, cor, (int(ponta[0]), int(ponta[1])), 5)
        # dedos serrilhados
        for dy, comp in ((-6, 11), (4, 11)):
            pygame.draw.line(
                surf, CONTORNO,
                (ponta[0], ponta[1] + dy * 0.4),
                (ponta[0] + lado * comp, ponta[1] + dy), 4,
            )
            pygame.draw.line(
                surf, claro,
                (ponta[0], ponta[1] + dy * 0.4),
                (ponta[0] + lado * comp, ponta[1] + dy), 2,
            )
        pygame.draw.circle(surf, brasa, (int(ponta[0] + lado * 3), int(ponta[1] - 1)), 1)

    # olhos e mandíbula
    for ox in (-0.22, 0.22):
        olho = (int(sx + r * ox), int(sy - r * 1.18))
        halo_suave(surf, olho, r * 0.22, brasa, alpha=80)
        pygame.draw.circle(surf, CONTORNO, olho, 4)
        pygame.draw.circle(surf, (255, 210, 100), olho, 2)
    for ox in (-1, 1):
        pygame.draw.line(
            surf, CONTORNO,
            (sx + ox * r * 0.12, sy - r * 1.02), (sx + ox * r * 0.34, sy - r * 0.9), 2,
        )

    # partículas de brasa
    for i in range(3):
        fase = (t * 0.5 + i / 3.0) % 1.0
        px = sx + math.sin(t * 2 + i * 2.1) * r * 0.9
        py = sy - r * 1.2 - fase * r * 1.2
        pygame.draw.circle(surf, (255, 160, 90), (int(px), int(py)), max(1, int(2 * (1 - fase))))



def _devorador(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool) -> None:
    r = inimigo.raio
    cor = _c(inimigo.cor, flash)
    escuro = _escurecer(cor, 62)
    claro = _clarear(cor, 58)
    cristal = _c((246, 176, 238), flash)
    cristal_claro = _c((255, 226, 252), flash)
    t = inimigo.tempo
    flutua = math.sin(t * 2.0) * 3.5
    sombra(surf, sx, sy - 2, r * 1.25, r * 0.4, 105)
    sy += flutua
    andando = inimigo.estado == "chase"
    swing = math.sin(inimigo.walk_phase) * 5.0 if andando else 0.0

    # patas longas (quatro), alternando o passo
    for lado in (-1, 1):
        for i in range(2):
            fase = swing * (1 if i == 0 else -1) * lado
            quadril = (sx + lado * r * 0.42, sy - r * 0.95)
            joelho = (sx + lado * r * (0.92 + i * 0.26), sy - r * 0.5 + fase * 0.5)
            pe = (sx + lado * r * (1.18 + i * 0.34), sy - 3 + fase)
            pygame.draw.line(surf, CONTORNO, quadril, joelho, 7)
            pygame.draw.line(surf, cor, quadril, joelho, 4)
            pygame.draw.line(surf, CONTORNO, joelho, pe, 6)
            pygame.draw.line(surf, escuro, joelho, pe, 3)

    # corpo abaulado
    corpo = pygame.Rect(int(sx - r * 0.88), int(sy - r * 1.78), int(r * 1.76), int(r * 1.42))
    pygame.draw.ellipse(surf, CONTORNO, corpo.inflate(5, 5))
    pygame.draw.ellipse(surf, escuro, corpo)
    pygame.draw.ellipse(surf, cor, corpo.inflate(-6, -6))
    pygame.draw.ellipse(surf, claro, (corpo.x + 10, corpo.y + 8, int(corpo.width * 0.55), int(corpo.height * 0.4)))

    # espinhos de cristal nas costas
    for ox, altura in ((-0.55, 0.72), (0.0, 0.95), (0.55, 0.68)):
        base_x = sx + r * ox
        topo_y = sy - r * (1.55 + altura)
        _poly(
            surf, cristal,
            [(base_x - r * 0.17, sy - r * 1.42), (base_x, topo_y), (base_x + r * 0.17, sy - r * 1.42)],
            CONTORNO, 2,
        )
        pygame.draw.line(
            surf, cristal_claro,
            (base_x, topo_y + 4), (base_x + r * 0.05, sy - r * 1.5), 1,
        )

    # mandíbula aberta com dentes
    boca = pygame.Rect(int(sx - r * 0.5), int(sy - r * 1.16), int(r * 1.0), int(r * 0.5))
    pygame.draw.ellipse(surf, CONTORNO, boca.inflate(4, 4))
    pygame.draw.ellipse(surf, (44, 16, 42), boca)
    for i in range(4):
        dx = boca.x + 6 + i * (boca.width - 12) / 3
        _poly(
            surf, cristal_claro,
            [(dx - 4, boca.y + 2), (dx + 4, boca.y + 2), (dx, boca.y + 12)],
        )
        _poly(
            surf, cristal_claro,
            [(dx - 4, boca.bottom - 2), (dx + 4, boca.bottom - 2), (dx, boca.bottom - 11)],
        )

    # núcleo pulsante
    pulso = 0.5 + 0.5 * math.sin(t * 4.2)
    halo_suave(surf, (sx, sy - r * 1.9), r * (0.8 + pulso * 0.25), (255, 150, 235), 60)
    pygame.draw.circle(surf, CONTORNO, (int(sx), int(sy - r * 1.9)), int(r * 0.25 + 2))
    pygame.draw.circle(surf, cristal, (int(sx), int(sy - r * 1.9)), int(r * 0.23))
    pygame.draw.circle(surf, cristal_claro, (int(sx - 2), int(sy - r * 1.9 - 2)), int(r * 0.09))

    # olhos
    for ox in (-0.42, 0.42):
        olho = (int(sx + r * ox), int(sy - r * 1.44))
        pygame.draw.circle(surf, CONTORNO, olho, 6)
        pygame.draw.circle(surf, (255, 226, 130), olho, 4)
        pygame.draw.circle(surf, (90, 24, 30), (olho[0] + 1, olho[1]), 2)

    # braços com garras
    for lado in (-1, 1):
        mao = (sx + lado * (r * 0.98 + swing * lado * 0.5), sy - r * 0.78 + abs(swing) * 0.3)
        pygame.draw.line(surf, CONTORNO, (sx + lado * r * 0.6, sy - r * 1.28), mao, 8)
        pygame.draw.line(surf, cor, (sx + lado * r * 0.6, sy - r * 1.28), mao, 5)
        for garra in (-1, 0, 1):
            ponta = (mao[0] + lado * 10 + garra * 4, mao[1] + 8 + garra * 4)
            pygame.draw.line(surf, CONTORNO, mao, ponta, 4)
            pygame.draw.line(surf, cristal, mao, ponta, 2)


# --------------------------------------------------------------------------
# entrada
# --------------------------------------------------------------------------


def desenhar_inimigo(inimigo: Any, surf: pygame.Surface, camera: Camera) -> None:
    if not inimigo.vivo:
        return
    sx, sy = camera.aplicar((inimigo.x, inimigo.y))
    if not camera.visivel(inimigo.x, inimigo.y, 180):
        return
    desenhar_telegraph(inimigo, surf, sx, sy)
    flash = inimigo.hit_flash > 0

    # aura de elite
    if getattr(inimigo, "elite", False):
        cor_elite = getattr(inimigo, "cor_elite", (250, 210, 110))
        pulso = 0.5 + 0.5 * math.sin(inimigo.tempo * 4.0)
        pygame.draw.circle(
            surf, cor_elite,
            (int(sx), int(sy - inimigo.raio * 0.4)),
            int(inimigo.raio * 1.55 + pulso * 4), 2,
        )
        for i in range(3):
            ang = inimigo.tempo * 1.6 + i * math.tau / 3
            px = sx + math.cos(ang) * inimigo.raio * 1.55
            py = sy - inimigo.raio * 0.4 + math.sin(ang) * inimigo.raio * 0.9
            pygame.draw.circle(surf, cor_elite, (int(px), int(py)), 2)

    # aura de boss
    if inimigo.boss:
        pulso = 0.5 + 0.5 * math.sin(inimigo.tempo * 3)
        pygame.draw.circle(surf, (250, 170, 80), (int(sx), int(sy)), int(inimigo.raio * 1.9 + pulso * 6), 2)

    if pixel_arte.ATIVO and pixel_enemy.desenhar(inimigo, surf, sx, sy, flash):
        pass
    elif inimigo.tipo in ("slime", "slime_cristal", "rei_slime"):
        _slime(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "goblin":
        _goblin(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "wisp":
        _wisp(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo in ("golem", "golem_anciao", "golem_obsidiana", "colosso_obsidiana"):
        _golem(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "senhor_fragmentos":
        _senhor_fragmentos(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "sentinela_aether":
        _sentinela_aether(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "espectro_aether":
        _espectro_aether(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "avatar_aether":
        _avatar_aether(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "morcego":
        _morcego(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "aranha":
        _aranha(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "elemental_cristal":
        _elemental_cristal(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "lobo":
        _lobo(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo in ("serpente", "serpente_aether"):
        _serpente(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "devorador":
        _devorador(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "ceifador_nevoa":
        _ceifador_nevoa(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "serpente_colossal":
        _serpente(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "sombra_eclipse":
        _espectro_aether(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "ceifador_espelhado":
        _ceifador_nevoa(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "serpente_vazio":
        _serpente(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "guardiao_eclipse":
        _guardiao_eclipse(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "sapo":
        _sapo(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "mosquito":
        _mosquito(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "lodo":
        _lodo(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "rainha_lodo":
        _rainha_lodo(inimigo, surf, sx, sy, flash)
    elif inimigo.tipo == "escorpiao":
        _escorpiao(inimigo, surf, sx, sy, flash)
    else:
        _slime(inimigo, surf, sx, sy, flash)

    # lentidão
    if inimigo.slow_timer > 0:
        pygame.draw.circle(surf, (120, 220, 250), (int(sx), int(sy - inimigo.raio)), int(inimigo.raio * 1.2), 2)
        for i in range(3):
            a = inimigo.tempo * 2 + i * 2.1
            pygame.draw.circle(
                surf, (200, 244, 255),
                (int(sx + math.cos(a) * inimigo.raio), int(sy - inimigo.raio + math.sin(a) * inimigo.raio * 0.5)),
                2,
            )

    # aviso de ataque
    if inimigo.preparando:
        t = 1.0 - max(0.0, inimigo.preparo) / (0.75 if inimigo.tipo_preparo == "especial" else 0.55)
        raio = int(inimigo.raio * (1.3 + 0.9 * t))
        cor = (250, 90, 80) if inimigo.tipo_preparo == "especial" else (250, 190, 80)
        pygame.draw.circle(surf, cor, (int(sx), int(sy - inimigo.raio * 0.4)), raio, 2)
        # Missao 05.22E: posicionamento estavel com altura real do texto
        # O texto "!" usa tamanho 22, negrito, familia "inter"; medimos a altura real via fonte()
        f_telegraph = fonte(22, True, "inter")
        telegraph_h = f_telegraph.size("!")[1]
        gap = 5  # pixels entre o indicador e o elemento abaixo
        if inimigo.boss:
            # Acima do nome: nome top = sy - raio*3.5 - 32
            name_top = sy - inimigo.raio * 3.5 - 32
            telegraph_y = name_top - gap - telegraph_h
        else:
            # Nao-boss: sempre acima da posicao geometrica da barra de vida
            # (barra top = sy - raio*2.4 - 12), para estabilidade quando HP muda
            bar_top = sy - inimigo.raio * 2.4 - 12
            telegraph_y = bar_top - gap - telegraph_h
        texto(surf, "!", (sx, telegraph_y), 22, cor, True, "center")

    # barra de vida
    if inimigo.boss or inimigo.hp < inimigo.hp_max:
        largura = 140 if inimigo.boss else 48
        altura_barra = 8 if inimigo.boss else 5
        y = sy - (inimigo.raio * 3.5 if inimigo.boss else inimigo.raio * 2.4) - 12
        if inimigo.boss:
            texto(surf, inimigo.nome, (sx, y - 20), 17, (250, 214, 130), True, "center")
        barra(
            surf, (sx - largura / 2, y, largura, altura_barra),
            inimigo.hp, inimigo.hp_max,
            (230, 80, 86) if not inimigo.boss else (246, 140, 70),
            (18, 18, 24), (0, 0, 0),
        )

    # ícones de status (coluna à direita do corpo, sem brigar com o nome)
    ativos = [
        tipo for tipo in ("queimadura", "veneno", "sangramento", "gelo", "atordoado")
        if tipo in getattr(inimigo, "status", {})
    ]
    if ativos:
        x_status = int(sx + inimigo.raio * 1.45 + 10)
        y0 = sy - inimigo.raio * 1.1
        for i, tipo in enumerate(ativos):
            cor_status = {
                "queimadura": (250, 140, 70),
                "veneno": (140, 220, 100),
                "sangramento": (230, 80, 100),
                "gelo": (120, 220, 250),
                "atordoado": (250, 220, 120),
            }[tipo]
            cy = int(y0 + i * 16)
            pygame.draw.circle(surf, (22, 18, 26), (x_status, cy), 8)
            pygame.draw.circle(surf, cor_status, (x_status, cy), 7)
            if tipo == "queimadura":
                pygame.draw.polygon(
                    surf, (255, 244, 210),
                    [(x_status, cy - 4), (x_status + 3, cy + 2), (x_status - 3, cy + 2)],
                )
            elif tipo == "sangramento":
                pygame.draw.circle(surf, (255, 226, 226), (x_status, cy + 1), 3)
                pygame.draw.polygon(
                    surf, (255, 226, 226),
                    [(x_status, cy - 5), (x_status + 2, cy), (x_status - 2, cy)],
                )
            elif tipo == "veneno":
                pygame.draw.circle(surf, (236, 255, 220), (x_status - 2, cy + 1), 2)
                pygame.draw.circle(surf, (236, 255, 220), (x_status + 2, cy - 2), 1)
            elif tipo == "gelo":
                pygame.draw.polygon(
                    surf, (240, 255, 255),
                    [(x_status, cy - 4), (x_status + 4, cy), (x_status, cy + 4), (x_status - 4, cy)],
                    1,
                )
            else:
                for ang in (0.0, math.pi / 3, 2 * math.pi / 3):
                    dx, dy = math.cos(ang) * 4, math.sin(ang) * 4
                    pygame.draw.line(
                        surf, (255, 250, 210),
                        (x_status - dx, cy - dy), (x_status + dx, cy + dy), 1,
                    )

    # estrelas de atordoamento
    if getattr(inimigo, "stun_timer", 0.0) > 0:
        for i in range(3):
            ang = inimigo.tempo * 6.0 + i * math.tau / 3
            px = sx + math.cos(ang) * inimigo.raio * 0.9
            py = sy - inimigo.raio * 2.2 + math.sin(ang) * inimigo.raio * 0.3
            pygame.draw.circle(surf, (250, 230, 140), (int(px), int(py)), 2)
