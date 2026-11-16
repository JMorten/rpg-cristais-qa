"""NPC da vila: arte procedural e posição no mundo."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

import pixel_arte
import pixel_npc
from utils import Camera, halo_suave, sombra, texto


def _poly(
    surf: pygame.Surface, cor: tuple[int, int, int], pts, borda=None, largura: int = 2,
) -> None:
    p = [(int(x), int(y)) for x, y in pts]
    pygame.draw.polygon(surf, cor, p)
    if borda is not None:
        pygame.draw.polygon(surf, borda, p, max(1, largura))


@dataclass
class NPC:
    nome: str
    x: float
    y: float
    raio: float = 15.0
    cor: tuple[int, int, int] = (86, 156, 132)
    estilo: str = "cronista"

    def desenhar(self, surf: pygame.Surface, camera: Camera, tempo: float) -> None:
        if pixel_arte.ATIVO:
            pixel_npc.desenhar(self, surf, camera, tempo)
            return
        sx, sy = camera.aplicar((self.x, self.y))
        if not camera.visivel(self.x, self.y, 120):
            return
        _desenhar_aldrin(surf, sx, sy, tempo, self.cor, self.estilo)


def _desenhar_aldrin(
    surf: pygame.Surface, sx: float, sy: float, tempo: float,
    cor: tuple[int, int, int], estilo: str = "cronista",
) -> None:
    contorno = (24, 26, 30)
    respira = math.sin(tempo * 1.6) * 1.6
    sy += respira * 0.4
    sombra(surf, sx, sy - 2, 24, 8, 105)

    # cajado (cronista/encantadora) ou martelo (ferreiro)
    if estilo in ("cronista", "encantadora"):
        cajado_x = sx + 21
        pygame.draw.line(surf, contorno, (cajado_x, sy - 2), (cajado_x + 2, sy - 72), 6)
        pygame.draw.line(surf, (126, 92, 56), (cajado_x, sy - 2), (cajado_x + 2, sy - 72), 3)
        pygame.draw.line(surf, (176, 138, 86), (cajado_x, sy - 6), (cajado_x + 1, sy - 66), 1)
        cor_orbe = (196, 150, 250) if estilo == "encantadora" else (150, 240, 210)
        halo_suave(surf, (cajado_x + 2, sy - 78), 30, cor_orbe, 80)
        pygame.draw.circle(surf, contorno, (int(cajado_x + 2), int(sy - 78)), 8)
        pygame.draw.circle(surf, cor_orbe, (int(cajado_x + 2), int(sy - 78)), 6)
        pygame.draw.circle(surf, (235, 255, 245), (int(cajado_x), int(sy - 80)), 2)
        # argola de metal no cajado
        pygame.draw.circle(surf, (206, 172, 98), (int(cajado_x + 1), int(sy - 64)), 3, 1)
    elif estilo == "ferreiro":
        pygame.draw.line(surf, contorno, (sx + 22, sy - 2), (sx + 24, sy - 40), 6)
        pygame.draw.line(surf, (126, 92, 56), (sx + 22, sy - 2), (sx + 24, sy - 40), 3)
        pygame.draw.rect(surf, contorno, (int(sx + 12), int(sy - 54), 24, 14), border_radius=3)
        pygame.draw.rect(surf, (120, 124, 134), (int(sx + 13), int(sy - 53), 22, 12), border_radius=2)
        pygame.draw.line(surf, (176, 180, 190), (int(sx + 15), int(sy - 50)), (int(sx + 33), int(sy - 50)), 2)

    if estilo == "mercadora":
        _npc_mercadora(surf, sx, sy, tempo, cor, contorno)
    elif estilo == "ferreiro":
        _npc_ferreiro(surf, sx, sy, tempo, cor, contorno)
    elif estilo == "encantadora":
        _npc_encantadora(surf, sx, sy, tempo, cor, contorno)
    else:
        _npc_cronista(surf, sx, sy, tempo, cor, contorno)

    # runa flutuante (cronista/encantadora)
    if estilo in ("cronista", "encantadora"):
        brilho = 0.6 + 0.4 * math.sin(tempo * 3.0)
        ry = sy - 96 + math.sin(tempo * 2) * 2
        halo_suave(surf, (sx, ry), 16, (250, 220, 130), 70)
        pygame.draw.circle(surf, (250, 220, 130), (int(sx), int(ry)), int(3 + 2 * brilho))
        pygame.draw.circle(surf, (255, 250, 210), (int(sx), int(ry)), 1)


def _npc_rosto(
    surf: pygame.Surface, sx: float, sy: float, contorno: tuple[int, int, int],
    pele: tuple[int, int, int] = (226, 194, 162), olhar_brilho: bool = False,
) -> None:
    cy = sy - 54
    pygame.draw.circle(surf, contorno, (int(sx), int(cy)), 11)
    pygame.draw.circle(surf, pele, (int(sx), int(cy)), 9)
    cor_olho = (250, 232, 170) if olhar_brilho else (40, 36, 40)
    pygame.draw.circle(surf, cor_olho, (int(sx - 3), int(cy - 1)), 1)
    pygame.draw.circle(surf, cor_olho, (int(sx + 3), int(cy - 1)), 1)
    if olhar_brilho:
        pygame.draw.circle(surf, (255, 250, 210), (int(sx - 3), int(cy - 1)), 1)
        pygame.draw.circle(surf, (255, 250, 210), (int(sx + 3), int(cy - 1)), 1)
    pygame.draw.line(surf, (176, 126, 110), (sx - 2, cy + 5), (sx + 2, cy + 5), 1)


def _npc_cronista(
    surf: pygame.Surface, sx: float, sy: float, tempo: float,
    cor: tuple[int, int, int], contorno: tuple[int, int, int],
) -> None:
    # manto externo
    manto = [
        (sx - 15, sy), (sx - 12, sy - 38), (sx - 6, sy - 48),
        (sx + 6, sy - 48), (sx + 12, sy - 38), (sx + 15, sy),
    ]
    pygame.draw.polygon(surf, contorno, [(x, y + 2) for x, y in manto])
    pygame.draw.polygon(surf, cor, manto)
    pygame.draw.polygon(surf, tuple(max(0, c - 34) for c in cor), manto, 2)
    # manto interno e dobras
    pygame.draw.polygon(
        surf, tuple(min(255, c + 26) for c in cor),
        [(sx - 8, sy - 44), (sx + 8, sy - 44), (sx + 10, sy - 3), (sx - 10, sy - 3)],
    )
    pygame.draw.line(surf, (228, 190, 108), (sx - 14, sy - 4), (sx + 14, sy - 4), 2)
    for ox in (-6, 6):
        pygame.draw.line(surf, tuple(max(0, c - 26) for c in cor), (sx + ox, sy - 8), (sx + ox * 1.2, sy - 40), 1)
    # gola
    _poly(
        surf, (52, 92, 82),
        [(sx - 12, sy - 48), (sx - 4, sy - 56), (sx + 4, sy - 56), (sx + 12, sy - 48), (sx + 6, sy - 40), (sx - 6, sy - 40)],
        contorno, 1,
    )
    # cabeça e barba longa
    _npc_rosto(surf, sx, sy, contorno)
    pygame.draw.polygon(
        surf, (232, 232, 224),
        [(sx - 8, sy - 51), (sx + 8, sy - 51), (sx + 6, sy - 34), (sx, sy - 26), (sx - 6, sy - 34)],
    )
    pygame.draw.line(surf, (198, 198, 190), (sx - 2, sy - 44), (sx - 2, sy - 30), 1)
    pygame.draw.line(surf, (198, 198, 190), (sx + 3, sy - 42), (sx + 3, sy - 32), 1)
    # capuz
    pygame.draw.arc(surf, contorno, pygame.Rect(int(sx - 14), int(sy - 72), 28, 28), math.pi, math.tau, 4)
    pygame.draw.arc(surf, (58, 110, 96), pygame.Rect(int(sx - 12), int(sy - 70), 24, 26), math.pi, math.tau, 3)
    pygame.draw.circle(surf, (228, 190, 108), (int(sx), int(sy - 63)), 2)


def _npc_mercadora(
    surf: pygame.Surface, sx: float, sy: float, tempo: float,
    cor: tuple[int, int, int], contorno: tuple[int, int, int],
) -> None:
    marrom = (138, 92, 58)
    creme = (232, 214, 176)
    vinho = (156, 74, 72)
    # saia em camadas
    saia = [
        (sx - 10, sy - 34), (sx + 10, sy - 34),
        (sx + 17, sy - 2), (sx + 11, sy + 1), (sx + 5, sy - 2),
        (sx, sy + 1), (sx - 5, sy - 2), (sx - 11, sy + 1), (sx - 17, sy - 2),
    ]
    _poly(surf, vinho, saia, contorno, 2)
    pygame.draw.line(surf, (198, 116, 104), (sx - 15, sy - 5), (sx + 15, sy - 5), 2)
    for ox in (-9, 0, 9):
        pygame.draw.line(surf, (120, 54, 58), (sx + ox, sy - 30), (sx + ox * 1.5, sy - 3), 1)
    # avental de couro
    _poly(
        surf, marrom,
        [(sx - 7, sy - 34), (sx + 7, sy - 34), (sx + 9, sy - 6), (sx - 9, sy - 6)],
        contorno, 1,
    )
    pygame.draw.line(surf, (196, 156, 104), (sx - 6, sy - 30), (sx + 6, sy - 30), 1)
    # blusa e corpete
    _poly(
        surf, creme,
        [(sx - 9, sy - 50), (sx + 9, sy - 50), (sx + 8, sy - 34), (sx - 8, sy - 34)],
        contorno, 1,
    )
    _poly(
        surf, marrom,
        [(sx - 8, sy - 45), (sx + 8, sy - 45), (sx + 7, sy - 34), (sx - 7, sy - 34)],
        contorno, 1,
    )
    for i in range(3):
        pygame.draw.line(surf, (206, 170, 112), (sx - 6, sy - 43 + i * 3), (sx + 6, sy - 43 + i * 3), 1)
    # xale sobre os ombros
    _poly(
        surf, (178, 108, 82),
        [(sx - 13, sy - 50), (sx - 2, sy - 55), (sx + 2, sy - 55), (sx + 13, sy - 50),
         (sx + 10, sy - 42), (sx + 3, sy - 46), (sx - 3, sy - 46), (sx - 10, sy - 42)],
        contorno, 1,
    )
    # cabeça, cabelo e coque
    _npc_rosto(surf, sx, sy, contorno)
    pygame.draw.circle(surf, contorno, (int(sx), int(sy - 55)), 11, 0)
    pygame.draw.circle(surf, (112, 74, 48), (int(sx), int(sy - 55)), 10)
    pygame.draw.circle(surf, (226, 194, 162), (int(sx), int(sy - 53)), 9)
    pygame.draw.arc(
        surf, (112, 74, 48),
        pygame.Rect(int(sx - 10), int(sy - 64), 20, 16), math.pi, math.tau, 4,
    )
    pygame.draw.circle(surf, (112, 74, 48), (int(sx + 9), int(sy - 64)), 4)
    pygame.draw.circle(surf, (166, 120, 76), (int(sx + 9), int(sy - 64)), 2)
    # olhos e brincos
    pygame.draw.circle(surf, (40, 36, 40), (int(sx - 3), int(sy - 56)), 1)
    pygame.draw.circle(surf, (40, 36, 40), (int(sx + 3), int(sy - 56)), 1)
    pygame.draw.line(surf, (176, 126, 110), (sx - 2, sy - 50), (sx + 2, sy - 50), 1)
    pygame.draw.circle(surf, (240, 200, 110), (int(sx - 8), int(sy - 51)), 1)
    pygame.draw.circle(surf, (240, 200, 110), (int(sx + 8), int(sy - 51)), 1)
    # chapéu de aba larga com fita
    pygame.draw.ellipse(surf, contorno, (int(sx - 17), int(sy - 66), 34, 9))
    pygame.draw.ellipse(surf, (150, 104, 62), (int(sx - 16), int(sy - 65), 32, 7))
    pygame.draw.rect(surf, contorno, (int(sx - 8), int(sy - 76), 16, 11), border_radius=3)
    pygame.draw.rect(surf, (150, 104, 62), (int(sx - 7), int(sy - 75), 14, 9), border_radius=3)
    pygame.draw.line(surf, vinho, (sx - 7, sy - 69), (sx + 7, sy - 69), 2)
    # bolsa e moedas
    pygame.draw.circle(surf, contorno, (int(sx - 14), int(sy - 16)), 7)
    pygame.draw.circle(surf, (196, 150, 90), (int(sx - 14), int(sy - 16)), 5)
    pygame.draw.circle(surf, (250, 220, 120), (int(sx - 14), int(sy - 17)), 2)
    for i in range(3):
        pygame.draw.circle(surf, (250, 214, 120), (int(sx + 12 + i * 2), int(sy - 28 - i * 2)), 1)


def _npc_ferreiro(
    surf: pygame.Surface, sx: float, sy: float, tempo: float,
    cor: tuple[int, int, int], contorno: tuple[int, int, int],
) -> None:
    pele = (206, 166, 132)
    couro = (122, 82, 52)
    avental = (92, 62, 44)
    # pernas
    for ox in (-7, 7):
        pygame.draw.line(surf, contorno, (sx + ox, sy - 28), (sx + ox, sy - 2), 12)
        pygame.draw.line(surf, (76, 60, 46), (sx + ox, sy - 26), (sx + ox, sy - 3), 8)
        pygame.draw.ellipse(surf, contorno, (int(sx + ox - 7), int(sy - 6), 14, 7))
    # torso largo
    pygame.draw.ellipse(surf, contorno, (int(sx - 16), int(sy - 52), 32, 30))
    pygame.draw.ellipse(surf, cor, (int(sx - 14), int(sy - 51), 28, 27))
    # peito e braços nus
    pygame.draw.ellipse(surf, pele, (int(sx - 8), int(sy - 49), 16, 12))
    for lado in (-1, 1):
        ombro = (sx + lado * 13, sy - 47)
        mao = (sx + lado * 16, sy - 28)
        pygame.draw.line(surf, contorno, ombro, mao, 9)
        pygame.draw.line(surf, pele, ombro, mao, 6)
    # avental de couro
    _poly(
        surf, avental,
        [(sx - 11, sy - 47), (sx + 11, sy - 47), (sx + 13, sy - 10), (sx + 6, sy - 6),
         (sx, sy - 10), (sx - 6, sy - 6), (sx - 13, sy - 10)],
        contorno, 2,
    )
    pygame.draw.line(surf, (150, 106, 70), (sx - 9, sy - 40), (sx + 9, sy - 40), 1)
    for ox in (-6, 0, 6):
        pygame.draw.line(surf, (66, 44, 32), (sx + ox, sy - 34), (sx + ox, sy - 14), 1)
    # alças cruzadas
    pygame.draw.line(surf, couro, (sx - 10, sy - 46), (sx + 7, sy - 30), 3)
    pygame.draw.line(surf, couro, (sx + 10, sy - 46), (sx - 7, sy - 30), 3)
    # cabeça calva e barba ruiva
    _npc_rosto(surf, sx, sy, contorno, pele)
    pygame.draw.circle(surf, (110, 66, 42), (int(sx), int(sy - 57)), 10)
    pygame.draw.circle(surf, pele, (int(sx), int(sy - 54)), 9)
    pygame.draw.polygon(
        surf, (150, 78, 44),
        [(sx - 9, sy - 52), (sx + 9, sy - 52), (sx + 6, sy - 38), (sx, sy - 32), (sx - 6, sy - 38)],
    )
    pygame.draw.line(surf, (176, 104, 66), (sx - 2, sy - 46), (sx - 2, sy - 34), 1)
    pygame.draw.circle(surf, (40, 36, 40), (int(sx - 3), int(sy - 56)), 1)
    pygame.draw.circle(surf, (40, 36, 40), (int(sx + 3), int(sy - 56)), 1)
    # bandana e marca de queimadura
    pygame.draw.line(surf, contorno, (sx - 11, sy - 62), (sx + 11, sy - 62), 5)
    pygame.draw.line(surf, (156, 62, 54), (sx - 10, sy - 62), (sx + 10, sy - 62), 3)
    pygame.draw.line(surf, (176, 112, 92), (sx + 5, sy - 50), (sx + 8, sy - 47), 1)
    # martelo apoiado no ombro? (já desenhado atrás)


def _npc_encantadora(
    surf: pygame.Surface, sx: float, sy: float, tempo: float,
    cor: tuple[int, int, int], contorno: tuple[int, int, int],
) -> None:
    roxo = cor
    roxo_escuro = tuple(max(0, c - 38) for c in roxo)
    prata = (222, 222, 238)
    # robe longo com cauda
    robe = [
        (sx - 12, sy - 50), (sx + 12, sy - 50),
        (sx + 20, sy - 2), (sx + 12, sy + 2), (sx + 5, sy - 2),
        (sx, sy + 2), (sx - 5, sy - 2), (sx - 12, sy + 2), (sx - 20, sy - 2),
    ]
    _poly(surf, roxo_escuro, robe, contorno, 2)
    _poly(
        surf, roxo,
        [(sx - 10, sy - 48), (sx + 10, sy - 48), (sx + 16, sy - 4), (sx + 8, sy), (sx, sy - 4), (sx - 8, sy), (sx - 16, sy - 4)],
    )
    # estrelas e barra dourada
    for ox, oy in ((-7, -12), (4, -20), (10, -10), (-3, -32), (7, -36)):
        pygame.draw.circle(surf, (236, 214, 140), (int(sx + ox), int(sy + oy)), 1)
    pygame.draw.line(surf, (228, 190, 108), (sx - 15, sy - 5), (sx + 15, sy - 5), 2)
    # mangas largas
    for lado in (-1, 1):
        _poly(
            surf, roxo_escuro,
            [(sx + lado * 10, sy - 48), (sx + lado * 19, sy - 44),
             (sx + lado * 17, sy - 30), (sx + lado * 10, sy - 33)],
            contorno, 1,
        )
        pygame.draw.line(surf, (228, 190, 108), (sx + lado * 15, sy - 44), (sx + lado * 13, sy - 33), 1)
    # gola alta
    _poly(
        surf, roxo_escuro,
        [(sx - 11, sy - 50), (sx - 5, sy - 58), (sx + 5, sy - 58), (sx + 11, sy - 50), (sx + 6, sy - 44), (sx - 6, sy - 44)],
        contorno, 1,
    )
    # cabeça, cabelo prateado e olhos brilhantes
    _npc_rosto(surf, sx, sy, contorno, (232, 206, 182), olhar_brilho=True)
    pygame.draw.circle(surf, contorno, (int(sx), int(sy - 55)), 11)
    pygame.draw.circle(surf, prata, (int(sx), int(sy - 55)), 10)
    pygame.draw.circle(surf, (232, 206, 182), (int(sx), int(sy - 53)), 9)
    pygame.draw.arc(
        surf, prata, pygame.Rect(int(sx - 11), int(sy - 65), 22, 18), math.pi, math.tau, 4,
    )
    pygame.draw.circle(surf, (232, 206, 182), (int(sx), int(sy - 53)), 8)
    pygame.draw.circle(surf, (250, 232, 170), (int(sx - 3), int(sy - 56)), 1)
    pygame.draw.circle(surf, (250, 232, 170), (int(sx + 3), int(sy - 56)), 1)
    # capuz pontudo
    _poly(
        surf, contorno,
        [(sx - 15, sy - 60), (sx, sy - 86), (sx + 15, sy - 60)],
    )
    _poly(
        surf, roxo,
        [(sx - 12, sy - 60), (sx, sy - 82), (sx + 12, sy - 60)],
    )
    pygame.draw.circle(surf, (250, 220, 130), (int(sx), int(sy - 82)), 2)
    # runas orbitando
    for i in range(3):
        ang = tempo * 1.2 + i * math.tau / 3
        px = sx + math.cos(ang) * 22
        py = sy - 40 + math.sin(ang) * 10
        pygame.draw.circle(surf, (214, 186, 250), (int(px), int(py)), 1)



def desenhar_indicador(
    surf: pygame.Surface, camera: Camera, npc: NPC, tempo: float,
    tem_missao: bool, pronta: bool, simbolo: str | None = None,
    cor: tuple[int, int, int] | None = None,
) -> None:
    """Sinal acima do NPC: '!'/'?' para missão ou um símbolo de serviço."""
    if simbolo is None and not (tem_missao or pronta):
        return
    sx, sy = camera.aplicar((npc.x, npc.y))
    pulso = 0.5 + 0.5 * math.sin(tempo * 4.0)
    if simbolo is not None:
        cor = cor or (250, 220, 120)
        texto_simbolo = simbolo
    else:
        cor = (250, 220, 120) if pronta else (150, 235, 180)
        texto_simbolo = "?" if pronta else "!"
    y = sy - 112 + math.sin(tempo * 2.4) * 3
    halo_suave(surf, (sx, y), 18 + pulso * 4, cor, 80)
    texto(surf, texto_simbolo, (sx, y - 10), 20, cor, True, "center")
