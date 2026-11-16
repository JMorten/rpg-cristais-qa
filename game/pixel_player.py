"""Herói em pixel art para o jogo principal (experimental)."""
from __future__ import annotations

import math
from typing import Any

import pygame

import pixel_arte
from pixel_arte import LARGURA
from utils import Camera, halo_suave

PASTA = pixel_arte.PERSONAGENS / "heroes"

ARQUIVOS = {
    "Cavaleiro": "fighter-m-02.png",
    "Arqueira": "ranger-f-01.png",
    "Maga": "mage-f-01.png",
}


def desenhar(j: Any, surf: pygame.Surface, camera: Camera) -> None:
    sx, sy = camera.aplicar((j.x, j.y))
    if not camera.visivel(j.x, j.y, 160):
        return

    linhas = pixel_arte.charset(PASTA / ARQUIVOS.get(j.classe, ARQUIVOS["Cavaleiro"]))
    quadro = int(j.tempo * 8) % 3 if j.andando else 1

    sombra = pygame.Surface((LARGURA, 10), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra, (10, 10, 14, 90), sombra.get_rect())
    surf.blit(sombra, (int(sx) - LARGURA // 2, int(sy) - 5))

    if j.ataque_anim > 0:
        t = 1.0 - j.ataque_anim / 0.24
        avanco = math.sin(max(0.0, min(1.0, t)) * math.pi) * 10
        sx += j.facing[0] * avanco
        sy += j.facing[1] * avanco * 0.6

    for equipamento in (j.equipamentos.get("Armadura"), j.equipamentos.get("Arma")):
        if equipamento is not None and equipamento.raridade in ("Épico", "Lendário"):
            halo_suave(surf, (sx, sy - 34), 34, equipamento.cor, 28)

    pixel_arte.desenhar_charset(
        surf, sx, sy, linhas, pixel_arte.direcao(j.facing), quadro, j.hit_flash > 0
    )
