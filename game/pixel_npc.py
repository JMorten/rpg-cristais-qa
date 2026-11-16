"""NPCs em pixel art para o jogo principal (experimental)."""
from __future__ import annotations

import math
from typing import Any

import pygame

import pixel_arte
from pixel_arte import LARGURA
from utils import Camera

PASTA = pixel_arte.PERSONAGENS

ARQUIVOS = {
    "Mestre Aldrin": ("npc", "townfolk-old-m-001.png"),
    "Mercadora Sela": ("npc", "townfolk-adult-f-004.png"),
    "Ferreiro Durin": ("npc", "townfolk-adult-m-006.png"),
    "Encantadora Yara": ("heroes", "mage-f-01.png"),
}
PADRAO = ("npc", "townfolk-adult-m-002.png")


def desenhar(npc: Any, surf: pygame.Surface, camera: Camera, tempo: float) -> None:
    sx, sy = camera.aplicar((npc.x, npc.y))
    if not camera.visivel(npc.x, npc.y, 120):
        return
    pasta, arquivo = ARQUIVOS.get(npc.nome, PADRAO)
    linhas = pixel_arte.charset(PASTA / pasta / arquivo)

    sombra = pygame.Surface((LARGURA, 10), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra, (10, 10, 14, 90), sombra.get_rect())
    surf.blit(sombra, (int(sx) - LARGURA // 2, int(sy) - 5))

    respira = math.sin(tempo * 1.6) * 1.2
    pixel_arte.desenhar_charset(
        surf, sx, sy - respira, linhas, pixel_arte.FRENTE, 1
    )
