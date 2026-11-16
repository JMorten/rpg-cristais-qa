"""Ícones vetoriais desenhados em código."""
from __future__ import annotations

import math
from typing import Sequence

import pygame

import pixel_arte
import pixel_icons
import pixel_portrait
from settings import CLASSES, DOURADO


def _c(cor: Sequence[int]) -> tuple[int, int, int]:
    return tuple(int(c) for c in cor[:3])


def icone(surf: pygame.Surface, tipo: str, rect: pygame.Rect | Sequence[int], cor: Sequence[int] | None = None, pulso: float = 1.0) -> None:
    if pixel_arte.ATIVO:
        pixel_icons.desenhar(surf, tipo, rect, cor, pulso=pulso)
        return
    r = pygame.Rect(rect)
    x, y, w, h = r
    cx, cy = x + w / 2, y + h / 2
    s = min(w, h)
    cor = _c(cor or DOURADO)
    contorno = (24, 22, 30)

    if tipo == "espada":
        pygame.draw.line(surf, contorno, (cx - s * 0.28, cy + s * 0.32), (cx + s * 0.30, cy - s * 0.34), max(3, int(s * 0.12)))
        pygame.draw.line(surf, cor, (cx - s * 0.28, cy + s * 0.32), (cx + s * 0.30, cy - s * 0.34), max(2, int(s * 0.07)))
        pygame.draw.line(surf, (228, 190, 108), (cx - s * 0.30, cy + s * 0.06), (cx - s * 0.04, cy + s * 0.32), max(2, int(s * 0.08)))
        pygame.draw.circle(surf, (240, 220, 150), (int(cx + s * 0.30), int(cy - s * 0.34)), max(2, int(s * 0.05)))
    elif tipo == "arco":
        rect_arco = pygame.Rect(int(cx - s * 0.34), int(cy - s * 0.42), int(s * 0.56), int(s * 0.84))
        pygame.draw.arc(surf, contorno, rect_arco.inflate(4, 4), -1.3, 1.3, max(3, int(s * 0.10)))
        pygame.draw.arc(surf, cor, rect_arco, -1.3, 1.3, max(2, int(s * 0.06)))
        pygame.draw.line(surf, (230, 220, 190), (cx + s * 0.10, cy - s * 0.38), (cx - s * 0.12, cy), 2)
        pygame.draw.line(surf, (230, 220, 190), (cx - s * 0.12, cy), (cx + s * 0.10, cy + s * 0.38), 2)
        pygame.draw.line(surf, (240, 240, 220), (cx - s * 0.12, cy), (cx + s * 0.34, cy), 2)
        pygame.draw.polygon(surf, cor, [(cx + s * 0.34, cy), (cx + s * 0.22, cy - s * 0.06), (cx + s * 0.22, cy + s * 0.06)])
    elif tipo == "cajado":
        pygame.draw.line(surf, contorno, (cx - s * 0.14, cy + s * 0.40), (cx + s * 0.16, cy - s * 0.24), max(4, int(s * 0.11)))
        pygame.draw.line(surf, (146, 104, 62), (cx - s * 0.14, cy + s * 0.40), (cx + s * 0.16, cy - s * 0.24), max(2, int(s * 0.06)))
        pygame.draw.circle(surf, contorno, (int(cx + s * 0.20), int(cy - s * 0.32)), max(4, int(s * 0.17)))
        pygame.draw.circle(surf, cor, (int(cx + s * 0.20), int(cy - s * 0.32)), max(3, int(s * 0.13)))
        pygame.draw.circle(surf, (255, 255, 255), (int(cx + s * 0.16), int(cy - s * 0.36)), max(1, int(s * 0.04)))
    elif tipo == "armadura":
        pts = [
            (cx - s * 0.32, cy - s * 0.28), (cx - s * 0.12, cy - s * 0.40),
            (cx + s * 0.12, cy - s * 0.40), (cx + s * 0.32, cy - s * 0.28),
            (cx + s * 0.26, cy + s * 0.30), (cx, cy + s * 0.42), (cx - s * 0.26, cy + s * 0.30),
        ]
        pygame.draw.polygon(surf, contorno, pts)
        pts2 = [(x + (cx - x) * 0.12, y + (cy - y) * 0.12) for x, y in pts]
        pygame.draw.polygon(surf, cor, pts2)
        pygame.draw.line(surf, (240, 230, 200), (cx, cy - s * 0.28), (cx, cy + s * 0.26), max(1, int(s * 0.05)))
    elif tipo == "anel":
        pygame.draw.circle(surf, contorno, (int(cx), int(cy + s * 0.06)), int(s * 0.26), max(4, int(s * 0.11)))
        pygame.draw.circle(surf, cor, (int(cx), int(cy + s * 0.06)), int(s * 0.26), max(2, int(s * 0.06)))
        pygame.draw.circle(surf, (240, 230, 180), (int(cx), int(cy - s * 0.26)), max(3, int(s * 0.10)))
        pygame.draw.circle(surf, (255, 255, 255), (int(cx - 1), int(cy - s * 0.28)), max(1, int(s * 0.035)))
    elif tipo == "amuleto":
        pygame.draw.arc(surf, (228, 200, 120), (int(cx - s * 0.30), int(cy - s * 0.42), int(s * 0.60), int(s * 0.70)), 3.4, 6.0, max(2, int(s * 0.05)))
        pygame.draw.circle(surf, contorno, (int(cx), int(cy + s * 0.12)), max(4, int(s * 0.16)))
        pygame.draw.circle(surf, cor, (int(cx), int(cy + s * 0.12)), max(3, int(s * 0.12)))
        pygame.draw.polygon(surf, (240, 220, 150), [(cx, cy - s * 0.02), (cx + s * 0.07, cy + s * 0.12), (cx, cy + s * 0.26), (cx - s * 0.07, cy + s * 0.12)])
    elif tipo == "cristal":
        pts = [(cx, cy - s * 0.40), (cx + s * 0.24, cy - s * 0.10), (cx + s * 0.12, cy + s * 0.36), (cx - s * 0.12, cy + s * 0.36), (cx - s * 0.24, cy - s * 0.10)]
        pygame.draw.polygon(surf, contorno, pts)
        pts2 = [(cx + (x - cx) * 0.82, cy + (y - cy) * 0.82) for x, y in pts]
        pygame.draw.polygon(surf, cor, pts2)
        pygame.draw.polygon(surf, (255, 255, 255), [pts2[0], pts2[1], (cx, cy + s * 0.10)], 1)
    elif tipo.startswith("pocao"):
        cor_liquido = {"pocao_vida": (232, 82, 96), "pocao_mana": (82, 148, 244), "pocao_stamina": (244, 206, 92)}.get(tipo, cor)
        corpo = pygame.Rect(int(cx - s * 0.18), int(cy - s * 0.18), int(s * 0.36), int(s * 0.50))
        pygame.draw.rect(surf, contorno, corpo.inflate(4, 4), border_radius=int(s * 0.10))
        pygame.draw.rect(surf, cor_liquido, corpo, border_radius=int(s * 0.09))
        pescoco = pygame.Rect(int(cx - s * 0.08), int(cy - s * 0.34), int(s * 0.16), int(s * 0.18))
        pygame.draw.rect(surf, (206, 224, 232), pescoco, border_radius=2)
        pygame.draw.rect(surf, (120, 100, 70), (int(cx - s * 0.09), int(cy - s * 0.38), int(s * 0.18), int(s * 0.07)), border_radius=2)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx - s * 0.06), int(cy - s * 0.04)), max(1, int(s * 0.04)))
    elif tipo == "giro":
        pygame.draw.arc(surf, contorno, (int(cx - s * 0.30), int(cy - s * 0.30), int(s * 0.60), int(s * 0.60)), 0.2, 5.2, max(4, int(s * 0.10)))
        pygame.draw.arc(surf, cor, (int(cx - s * 0.30), int(cy - s * 0.30), int(s * 0.60), int(s * 0.60)), 0.2, 5.2, max(2, int(s * 0.06)))
        pygame.draw.polygon(surf, cor, [(cx + s * 0.26, cy - s * 0.30), (cx + s * 0.38, cy - s * 0.12), (cx + s * 0.16, cy - s * 0.12)])
    elif tipo == "dash":
        for i in range(3):
            ox = -s * 0.28 + i * s * 0.22
            pygame.draw.polygon(surf, contorno, [(cx + ox - s * 0.10, cy - s * 0.24), (cx + ox + s * 0.12, cy), (cx + ox - s * 0.10, cy + s * 0.24)])
            pygame.draw.polygon(surf, cor, [(cx + ox - s * 0.08, cy - s * 0.18), (cx + ox + s * 0.08, cy), (cx + ox - s * 0.08, cy + s * 0.18)])
    elif tipo == "brado":
        pygame.draw.circle(surf, contorno, (int(cx - s * 0.10), int(cy + s * 0.06)), int(s * 0.16))
        pygame.draw.circle(surf, cor, (int(cx - s * 0.10), int(cy + s * 0.06)), int(s * 0.12))
        for i in range(3):
            raio = int(s * (0.18 + i * 0.12))
            pygame.draw.arc(surf, cor, (int(cx - s * 0.10 - raio), int(cy + s * 0.06 - raio), raio * 2, raio * 2), -0.9, 0.9, 2)
    elif tipo == "duplo":
        for i, ox in enumerate((-s * 0.12, s * 0.12)):
            pygame.draw.line(surf, contorno, (cx + ox - s * 0.16, cy + s * 0.22), (cx + ox + s * 0.16, cy - s * 0.22), max(3, int(s * 0.08)))
            pygame.draw.line(surf, cor, (cx + ox - s * 0.16, cy + s * 0.22), (cx + ox + s * 0.16, cy - s * 0.22), max(2, int(s * 0.04)))
            pygame.draw.polygon(surf, cor, [(cx + ox + s * 0.22, cy - s * 0.30), (cx + ox + s * 0.10, cy - s * 0.10), (cx + ox + s * 0.26, cy - s * 0.08)])
    elif tipo == "chuva":
        for i in range(3):
            ox = (i - 1) * s * 0.22
            pygame.draw.line(surf, cor, (cx + ox, cy - s * 0.34), (cx + ox, cy + s * 0.14), max(2, int(s * 0.05)))
            pygame.draw.polygon(surf, cor, [(cx + ox, cy + s * 0.28), (cx + ox - s * 0.08, cy + s * 0.10), (cx + ox + s * 0.08, cy + s * 0.10)])
        pygame.draw.arc(surf, (220, 230, 240), (int(cx - s * 0.36), int(cy - s * 0.44), int(s * 0.72), int(s * 0.30)), 3.3, 6.1, 2)
    elif tipo == "certeiro":
        pygame.draw.circle(surf, contorno, (int(cx), int(cy)), int(s * 0.30), max(3, int(s * 0.08)))
        pygame.draw.circle(surf, cor, (int(cx), int(cy)), int(s * 0.30), max(1, int(s * 0.04)))
        pygame.draw.line(surf, cor, (cx - s * 0.40, cy), (cx + s * 0.40, cy), 2)
        pygame.draw.line(surf, cor, (cx, cy - s * 0.40), (cx, cy + s * 0.40), 2)
        pygame.draw.circle(surf, (255, 255, 255), (int(cx), int(cy)), max(2, int(s * 0.06)))
    elif tipo == "fogo":
        pts = [(cx, cy - s * 0.40), (cx + s * 0.24, cy - s * 0.06), (cx + s * 0.16, cy + s * 0.28), (cx, cy + s * 0.38), (cx - s * 0.16, cy + s * 0.28), (cx - s * 0.24, cy - s * 0.06)]
        pygame.draw.polygon(surf, contorno, pts)
        pts2 = [(cx + (x - cx) * 0.82, cy + (y - cy) * 0.82) for x, y in pts]
        pygame.draw.polygon(surf, cor, pts2)
        pygame.draw.polygon(surf, (255, 226, 130), [(cx, cy - s * 0.16), (cx + s * 0.10, cy + s * 0.10), (cx, cy + s * 0.24), (cx - s * 0.10, cy + s * 0.10)])
    elif tipo == "gelo":
        for i in range(3):
            a = i * math.pi / 3
            dx, dy = math.cos(a) * s * 0.36, math.sin(a) * s * 0.36
            pygame.draw.line(surf, contorno, (cx - dx, cy - dy), (cx + dx, cy + dy), max(3, int(s * 0.07)))
            pygame.draw.line(surf, cor, (cx - dx, cy - dy), (cx + dx, cy + dy), max(1, int(s * 0.03)))
        pygame.draw.circle(surf, (230, 250, 255), (int(cx), int(cy)), max(2, int(s * 0.07)))
    elif tipo == "raio":
        pts = [(cx + s * 0.06, cy - s * 0.42), (cx - s * 0.22, cy + s * 0.02), (cx - s * 0.02, cy + s * 0.02), (cx - s * 0.12, cy + s * 0.42), (cx + s * 0.24, cy - s * 0.08), (cx + s * 0.04, cy - s * 0.08)]
        pygame.draw.polygon(surf, contorno, pts)
        pygame.draw.polygon(surf, cor, [(cx + (x - cx) * 0.85, cy + (y - cy) * 0.85) for x, y in pts])
    else:
        pygame.draw.circle(surf, contorno, (int(cx), int(cy)), int(s * 0.30))
        pygame.draw.circle(surf, cor, (int(cx), int(cy)), int(s * 0.24))


def retrato_classe(
    surf: pygame.Surface, classe: str, rect: pygame.Rect | Sequence[int],
    estado: str = "normal", tempo: float = 0.0,
) -> None:
    if pixel_arte.ATIVO:
        pixel_portrait.desenhar(surf, classe, rect, estado=estado, tempo=tempo)
        return
    r = pygame.Rect(rect)
    dados = CLASSES.get(classe, CLASSES["Cavaleiro"])
    cor = dados["cor"]
    cor2 = dados["cor2"]
    pygame.draw.rect(surf, (18, 20, 28), r, border_radius=12)
    pygame.draw.rect(surf, cor, r, width=2, border_radius=12)
    cx, cy = r.centerx, r.centery
    raio = min(r.w, r.h) // 2 - 8
    pygame.draw.circle(surf, (30, 34, 46), (cx, cy), raio)
    pygame.draw.circle(surf, cor, (cx, cy), raio, 2)
    # fundo
    pygame.draw.circle(surf, tuple(int(c * 0.35) for c in cor), (cx, cy), raio - 2)
    # cabeça
    pygame.draw.circle(surf, (242, 202, 170), (cx, cy + 2), int(raio * 0.48))
    # cabelo/chapéu
    if classe == "Cavaleiro":
        pygame.draw.arc(surf, (196, 204, 222), (cx - raio // 2, cy - raio // 2, raio, raio), 0.1, math.pi - 0.1, 5)
        pygame.draw.circle(surf, (236, 204, 116), (cx, cy - int(raio * 0.45)), 3)
        pygame.draw.circle(surf, (60, 44, 34), (cx - 6, cy + 2), 2)
        pygame.draw.circle(surf, (60, 44, 34), (cx + 6, cy + 2), 2)
    elif classe == "Arqueira":
        pygame.draw.circle(surf, (62, 142, 92), (cx, cy - 2), int(raio * 0.58))
        pygame.draw.circle(surf, (242, 202, 170), (cx, cy + 4), int(raio * 0.42))
        pygame.draw.circle(surf, (50, 40, 36), (cx - 5, cy + 4), 2)
        pygame.draw.circle(surf, (50, 40, 36), (cx + 5, cy + 4), 2)
        pygame.draw.polygon(surf, (72, 162, 104), [(cx - raio * 0.55, cy + raio * 0.30), (cx - raio * 0.45, cy - raio * 0.40), (cx, cy - raio * 0.62), (cx + raio * 0.45, cy - raio * 0.40), (cx + raio * 0.55, cy + raio * 0.30), (cx, cy + raio * 0.10)])
    else:
        pygame.draw.circle(surf, (226, 226, 238), (cx, cy - 2), int(raio * 0.55))
        pygame.draw.circle(surf, (242, 202, 170), (cx, cy + 4), int(raio * 0.40))
        pygame.draw.polygon(surf, (128, 88, 196), [(cx - raio * 0.55, cy - raio * 0.30), (cx + raio * 0.55, cy - raio * 0.30), (cx + raio * 0.15, cy - raio * 0.85), (cx - raio * 0.10, cy - raio * 0.95)])
        pygame.draw.circle(surf, (248, 218, 120), (cx + 4, cy - int(raio * 0.82)), 3)
        pygame.draw.circle(surf, (60, 40, 70), (cx - 5, cy + 4), 2)
        pygame.draw.circle(surf, (60, 40, 70), (cx + 5, cy + 4), 2)
    # moldura
    pygame.draw.circle(surf, cor2, (cx, cy), raio, 1)


def moeda(surf: pygame.Surface, x: float, y: float, raio: int = 7) -> None:
    pygame.draw.circle(surf, (130, 90, 20), (int(x), int(y)), raio)
    pygame.draw.circle(surf, (246, 204, 92), (int(x), int(y)), raio - 1)
    pygame.draw.circle(surf, (255, 240, 160), (int(x - raio * 0.25), int(y - raio * 0.25)), max(1, raio // 3))


def cor_raridade(raridade: str) -> tuple[int, int, int]:
    from settings import RARIDADES
    return RARIDADES.get(raridade, RARIDADES["Comum"])["cor"]
