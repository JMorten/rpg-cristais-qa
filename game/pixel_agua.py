"""Água em pixel art (experimental).

O lago da Clareira e as lagoas do Pântano são elipses desenhadas por cima do
chão. Aqui elas são rasterizadas em 1/4 da resolução e ampliadas 4x, o que dá
o mesmo degrau grosso da pixel art, com margem de areia/lama e ondulações
animadas.
"""
from __future__ import annotations

import math

import pygame

ESCALA = 4

CORES = {
    "lago": {
        "margem": (168, 148, 104),
        "margem_escura": (132, 114, 78),
        "fundo": (46, 112, 148),
        "raso": (66, 146, 178),
        "onda": (108, 186, 208),
        "brilho": (176, 226, 240),
    },
    "pantano": {
        "margem": (84, 74, 50),
        "margem_escura": (62, 54, 36),
        "fundo": (40, 78, 54),
        "raso": (56, 102, 68),
        "onda": (92, 142, 92),
        "brilho": (132, 178, 118),
    },
}


def _pequena(tipo: str, largura: int, altura: int, tempo: float, fase: float) -> pygame.Surface:
    cores = CORES.get(tipo, CORES["lago"])
    surf = pygame.Surface((largura + 4, altura + 4), pygame.SRCALPHA)

    # margem fina e água em três tons
    pygame.draw.ellipse(surf, cores["margem_escura"], (0, 0, largura + 4, altura + 4))
    pygame.draw.ellipse(surf, cores["margem"], (1, 1, largura + 2, altura + 2))
    pygame.draw.ellipse(surf, cores["fundo"], (2, 2, largura, altura))
    pygame.draw.ellipse(
        surf, cores["raso"],
        (2 + largura // 6, 2 + altura // 6, max(2, largura - largura // 3), max(2, altura - altura // 3)),
    )

    # ondinhas curtas subindo devagar
    for k in range(5):
        f = (tempo * 0.22 + fase + k / 5.0) % 1.0
        y = 3 + int((altura - 4) * (1.0 - f))
        x = 3 + int((largura - 12) * ((k * 0.37 + f * 0.4) % 1.0))
        comprimento = 3 + int(3 * abs(math.sin(f * math.pi)))
        surf.fill(cores["onda"], (x, y, comprimento, 1))

    # dois brilhos parados dão a textura de água
    surf.fill(cores["brilho"], (3 + largura // 4, 3 + altura // 3, 3, 1))
    surf.fill(cores["brilho"], (3 + largura // 2, 3 + altura // 2, 2, 1))
    return surf


def desenhar(
    surf: pygame.Surface,
    camera: object,
    aguas: list[tuple[str, float, float, float, float]] | tuple,
    tempo: float,
) -> None:
    largura_tela, altura_tela = surf.get_size()
    for i, (tipo, cx, cy, rx, ry) in enumerate(aguas):
        sx, sy = camera.aplicar((cx, cy))
        if sx + rx < -20 or sy + ry < -20 or sx - rx > largura_tela + 20 or sy - ry > altura_tela + 20:
            continue
        largura = max(6, int(rx * 2 / ESCALA))
        altura = max(4, int(ry * 2 / ESCALA))
        pequena = _pequena(tipo, largura, altura, tempo, i * 0.21)
        grande = pygame.transform.scale(
            pequena, (pequena.get_width() * ESCALA, pequena.get_height() * ESCALA),
        )
        surf.blit(grande, (int(sx) - grande.get_width() // 2, int(sy) - grande.get_height() // 2))
