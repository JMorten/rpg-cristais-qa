"""Projéteis, drops, áreas de perigo e efeitos visuais."""
from __future__ import annotations

import math
import random
from typing import Any, Sequence

import pygame

from items import Cristal, Equipamento, Pocao
from settings import BRANCO
from utils import Camera, clamp, distancia, halo_suave, sombra, texto


# --------------------------------------------------------------------------
# projéteis
# --------------------------------------------------------------------------


class Projetil:
    def __init__(
        self, x: float, y: float, vx: float, vy: float, dano: float,
        dono: str, raio: float = 8.0, cor: Sequence[int] = (220, 180, 255),
        tipo_visual: str = "magia", tempo_vida: float = 2.2,
        perfurante: bool = False, critico: bool = False,
        explosao: float = 0.0, slow: float = 0.0,
        status: dict[str, float | str] | None = None,
    ) -> None:
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.dano = dano
        self.dono = dono
        self.raio = raio
        self.cor = tuple(cor[:3])
        self.tipo_visual = tipo_visual
        self.tempo_vida = tempo_vida
        self.perfurante = perfurante
        self.critico = critico
        self.explosao = explosao
        self.slow = slow
        self.status = status
        self.vivo = True
        self.acertados: set[int] = set()
        self.trail = 0.0
        self.angulo = math.atan2(vy, vx)

    def atualizar(self, dt: float, jogo: Any) -> None:
        if not self.vivo:
            return
        self.tempo_vida -= dt
        if self.tempo_vida <= 0:
            self.explodir(jogo)
            return
        self.x += self.vx * dt
        self.y += self.vy * dt

        # rastro
        self.trail -= dt
        if self.trail <= 0:
            self.trail = 0.035
            jogo.particulas.emitir(
                self.x, self.y, self.cor, 1, 24, max(1.5, self.raio * 0.35), 0.28,
                espalhar=math.tau,
            )

        if not self.perfurante and jogo.mundo.colidir_circulo(self.x, self.y, self.raio * 0.55):
            self.explodir(jogo)
            return

        if self.dono == "jogador":
            for inimigo in jogo.inimigos:
                if not inimigo.vivo or id(inimigo) in self.acertados:
                    continue
                if distancia((self.x, self.y), (inimigo.x, inimigo.y)) <= self.raio + inimigo.raio * 0.8:
                    inimigo.receber_dano(self.dano, jogo, self.critico)
                    if self.slow > 0:
                        inimigo.slow_timer = max(inimigo.slow_timer, self.slow)
                    if self.status:
                        jogo.aplicar_status(inimigo, **self.status)
                    jogo.particulas.emitir(inimigo.x, inimigo.y, self.cor, 10, 110, 4, 0.4)
                    self.acertados.add(id(inimigo))
                    if self.explosao > 0:
                        jogo.criar_explosao(self.x, self.y, self.explosao, self.dano * 0.7, "jogador", self.cor, self.critico)
                    if not self.perfurante:
                        self.vivo = False
                        return
        else:
            jogador = jogo.jogador
            if not jogador.morto and distancia((self.x, self.y), (jogador.x, jogador.y)) <= self.raio + jogador.raio * 0.8:
                jogador.receber_dano(self.dano, jogo, self.critico, origem=(self.x, self.y))
                jogo.particulas.emitir(self.x, self.y, self.cor, 10, 110, 4, 0.4)
                self.vivo = False
                return

    def explodir(self, jogo: Any) -> None:
        if not self.vivo:
            return
        if self.explosao > 0:
            jogo.criar_explosao(self.x, self.y, self.explosao, self.dano * 0.7, self.dono, self.cor, self.critico)
        else:
            jogo.particulas.emitir(self.x, self.y, self.cor, 8, 80, 3, 0.35)
        self.vivo = False

    def desenhar(self, surf: pygame.Surface, camera: Camera) -> None:
        if not self.vivo:
            return
        sx, sy = camera.aplicar((self.x, self.y))
        if not camera.visivel(self.x, self.y, 80):
            return
        if self.tipo_visual == "flecha":
            dx, dy = math.cos(self.angulo), math.sin(self.angulo)
            cauda = (sx - dx * 18, sy - dy * 18)
            pygame.draw.line(surf, self.cor, cauda, (sx, sy), 2)
            pygame.draw.polygon(
                surf, self.cor,
                [(sx + dx * 6, sy + dy * 6),
                 (sx - dy * 3 - dx * 2, sy + dx * 3 - dy * 2),
                 (sx + dy * 3 - dx * 2, sy - dx * 3 - dy * 2)],
            )
        elif self.tipo_visual == "cristal":
            pts = [(sx, sy - 10), (sx + 6, sy), (sx, sy + 10), (sx - 6, sy)]
            pygame.draw.polygon(surf, self.cor, pts)
            pygame.draw.polygon(surf, (255, 255, 255), pts, 1)
        else:
            dx, dy = math.cos(self.angulo), math.sin(self.angulo)
            for i in range(3):
                f = (i + 1) / 4
                px, py = sx - dx * 14 * f, sy - dy * 14 * f
                cor_trilha = tuple(int(c * (1.0 - f * 0.55)) for c in self.cor)
                pygame.draw.circle(
                    surf, cor_trilha, (int(px), int(py)),
                    max(1, int(self.raio * (1.0 - f * 0.55))),
                )
            halo_suave(surf, (sx, sy), self.raio * 2.4, self.cor, alpha=120)
            pygame.draw.circle(surf, self.cor, (int(sx), int(sy)), int(self.raio))
            pygame.draw.circle(surf, (250, 250, 255), (int(sx - self.raio * 0.25), int(sy - self.raio * 0.25)), max(1, int(self.raio * 0.35)))


# --------------------------------------------------------------------------
# drops
# --------------------------------------------------------------------------


_FEIXES: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}


def _feixe_loot(cor, altura: int) -> pygame.Surface:
    """Feixe vertical suave acima do item, com cache por cor e altura."""
    chave = (tuple(int(c) for c in cor[:3]), int(altura))
    feixe = _FEIXES.get(chave)
    if feixe is None:
        feixe = pygame.Surface((10, altura), pygame.SRCALPHA)
        for y in range(altura):
            alpha = int(80 * (1.0 - y / max(1, altura - 1)))
            pygame.draw.line(feixe, (*chave[0], alpha), (0, y), (9, y))
        if len(_FEIXES) > 64:
            _FEIXES.clear()
        _FEIXES[chave] = feixe
    return feixe


class Drop:
    def __init__(self, x: float, y: float, tipo: str, item: Any = None, quantidade: int = 1) -> None:
        self.x, self.y = x, y
        self.tipo = tipo
        self.item = item
        self.quantidade = quantidade
        self.tempo = 0.0
        if tipo == "eco":
            self.vida = 1e9
        elif tipo in ("bau", "santuario"):
            self.vida = 150.0
        else:
            self.vida = 90.0
        self.fase = random.uniform(0, 6.28)
        self.vivo = True
        self.raio = 16

    @property
    def cor(self) -> tuple[int, int, int]:
        if self.tipo == "eco":
            return (255, 222, 128)
        if self.tipo == "ouro":
            return (246, 204, 92)
        if self.tipo == "bau":
            return (246, 204, 92)
        if self.tipo == "santuario":
            return (150, 230, 255)
        if isinstance(self.item, Equipamento):
            return self.item.cor
        if isinstance(self.item, Cristal):
            return self.item.cor
        if isinstance(self.item, Pocao):
            return self.item.cor
        return BRANCO

    def atualizar(self, dt: float, jogo: Any) -> None:
        if not self.vivo:
            return
        self.tempo += dt
        self.vida -= dt
        if self.vida <= 0:
            self.vivo = False
            return
        jogador = jogo.jogador
        if not jogador.morto and distancia((self.x, self.y), (jogador.x, jogador.y)) < 48:
            if jogo.coletar(self):
                self.vivo = False

    def desenhar(self, surf: pygame.Surface, camera: Camera) -> None:
        if not self.vivo:
            return
        sx, sy = camera.aplicar((self.x, self.y))
        if not camera.visivel(self.x, self.y, 60):
            return
        bob = math.sin(self.tempo * 3.2 + self.fase) * 4
        y = sy + bob
        sombra(surf, sx, sy + 2, 12, 4, 70)
        cor = self.cor
        pulso = 0.5 + 0.5 * math.sin(self.tempo * 4 + self.fase)
        halo_suave(surf, (sx, y), 18 + 4 * pulso, cor, alpha=100)
        if self.tipo != "ouro":
            altura = 46 + int(6 * pulso)
            surf.blit(_feixe_loot(cor, altura), (int(sx - 5), int(y - altura - 10)))

        if self.tipo == "eco":
            for i in range(3):
                raio_anel = 10 + i * 7 + int(3 * pulso)
                pygame.draw.circle(surf, (255, 226, 140), (int(sx), int(y)), raio_anel, 2)
            pygame.draw.circle(surf, (255, 248, 210), (int(sx), int(y)), 7)
            pygame.draw.circle(surf, (255, 255, 240), (int(sx - 2), int(y - 2)), 3)
            texto(surf, f"{self.quantidade}", (sx, y - 34), 12, (255, 236, 170), True, "center")
        elif self.tipo == "ouro":
            for i in range(3):
                ox = (i - 1) * 6
                pygame.draw.circle(surf, (130, 90, 20), (int(sx + ox), int(y - 3 + (i % 2) * 3)), 6)
                pygame.draw.circle(surf, (246, 204, 92), (int(sx + ox), int(y - 4 + (i % 2) * 3)), 5)
                pygame.draw.circle(surf, (255, 240, 160), (int(sx + ox - 1), int(y - 6 + (i % 2) * 3)), 2)
        elif self.tipo == "bau":
            corpo = pygame.Rect(int(sx - 15), int(y - 8), 30, 18)
            tampa = pygame.Rect(int(sx - 16), int(y - 14), 32, 9)
            pygame.draw.rect(surf, (92, 60, 34), corpo, border_radius=4)
            pygame.draw.rect(surf, (148, 102, 56), tampa, border_radius=4)
            pygame.draw.rect(surf, (54, 36, 22), corpo, width=2, border_radius=4)
            pygame.draw.rect(surf, (54, 36, 22), tampa, width=2, border_radius=4)
            pygame.draw.rect(surf, (250, 214, 130), (int(sx - 2), int(y - 10), 4, 16), border_radius=1)
            pygame.draw.rect(surf, (250, 214, 130), (int(sx - 4), int(y + 2), 8, 6), border_radius=2)
            pygame.draw.circle(surf, (70, 46, 26), (int(sx), int(y + 5)), 2)
            pygame.draw.circle(surf, (255, 244, 190), (int(sx + 12), int(y - 18)), 2)
        elif self.tipo == "santuario":
            pygame.draw.ellipse(surf, (30, 52, 70), (int(sx - 18), int(y + 4), 36, 10))
            pygame.draw.ellipse(surf, (90, 170, 200), (int(sx - 18), int(y + 4), 36, 10), 1)
            pygame.draw.circle(surf, (60, 110, 140), (int(sx), int(y - 8)), 13, 2)
            pygame.draw.circle(surf, (150, 230, 255), (int(sx), int(y - 8)), 9, 1)
            pygame.draw.polygon(
                surf, (220, 250, 255),
                [(sx, y - 26), (sx + 6, y - 12), (sx, y + 2), (sx - 6, y - 12)],
            )
            pygame.draw.line(surf, (255, 255, 255), (sx, y - 22), (sx - 2, y - 10), 1)
            for i in range(3):
                ang = self.tempo * 1.5 + i * math.tau / 3
                px = sx + math.cos(ang) * 17
                py = y - 8 + math.sin(ang) * 7
                pygame.draw.circle(surf, (190, 245, 255), (int(px), int(py)), 2)
        elif isinstance(self.item, Cristal):
            pts = [(sx, y - 12), (sx + 7, y - 2), (sx, y + 9), (sx - 7, y - 2)]
            pygame.draw.polygon(surf, (30, 24, 40), pts)
            pygame.draw.polygon(surf, cor, [(sx, y - 10), (sx + 5, y - 2), (sx, y + 7), (sx - 5, y - 2)])
            pygame.draw.line(surf, (255, 255, 255), (sx, y - 9), (sx - 2, y - 1), 1)
        elif isinstance(self.item, Pocao):
            rect = pygame.Rect(int(sx - 6), int(y - 10), 12, 16)
            pygame.draw.rect(surf, (30, 24, 40), rect.inflate(3, 3), border_radius=4)
            pygame.draw.rect(surf, cor, rect, border_radius=3)
            pygame.draw.rect(surf, (200, 220, 230), (int(sx - 3), int(y - 14), 6, 5), border_radius=2)
            pygame.draw.circle(surf, (255, 255, 255), (int(sx - 2), int(y - 5)), 2)
        elif isinstance(self.item, Equipamento):
            _icone_equipamento(surf, sx, y, self.item.icone, cor)
        else:
            pygame.draw.circle(surf, cor, (int(sx), int(y)), 7)


def _icone_equipamento(surf: pygame.Surface, sx: float, sy: float, icone: str, cor: Sequence[int]) -> None:
    contorno = (26, 24, 32)
    if icone in ("espada",):
        pygame.draw.line(surf, contorno, (sx - 7, sy + 7), (sx + 7, sy - 9), 6)
        pygame.draw.line(surf, cor, (sx - 7, sy + 7), (sx + 7, sy - 9), 3)
        pygame.draw.line(surf, (228, 190, 108), (sx - 9, sy + 1), (sx - 1, sy + 9), 3)
    elif icone == "arco":
        pygame.draw.arc(surf, contorno, (int(sx - 9), int(sy - 12), 18, 24), -1.3, 1.3, 4)
        pygame.draw.arc(surf, cor, (int(sx - 9), int(sy - 12), 18, 24), -1.3, 1.3, 2)
        pygame.draw.line(surf, (220, 220, 200), (sx + 4, sy - 10), (sx - 2, sy), 1)
        pygame.draw.line(surf, (220, 220, 200), (sx - 2, sy), (sx + 4, sy + 10), 1)
    elif icone == "cajado":
        pygame.draw.line(surf, contorno, (sx - 4, sy + 10), (sx + 4, sy - 8), 5)
        pygame.draw.line(surf, (146, 104, 62), (sx - 4, sy + 10), (sx + 4, sy - 8), 3)
        pygame.draw.circle(surf, contorno, (int(sx + 5), int(sy - 10)), 6)
        pygame.draw.circle(surf, cor, (int(sx + 5), int(sy - 10)), 4)
    elif icone == "armadura":
        pts = [(sx - 9, sy - 8), (sx - 3, sy - 11), (sx + 3, sy - 11), (sx + 9, sy - 8), (sx + 7, sy + 9), (sx, sy + 12), (sx - 7, sy + 9)]
        pygame.draw.polygon(surf, contorno, pts)
        pygame.draw.polygon(surf, cor, [(sx - 6, sy - 6), (sx - 2, sy - 8), (sx + 2, sy - 8), (sx + 6, sy - 6), (sx + 4, sy + 6), (sx, sy + 8), (sx - 4, sy + 6)])
    elif icone == "anel":
        pygame.draw.circle(surf, contorno, (int(sx), int(sy + 2)), 8, 4)
        pygame.draw.circle(surf, cor, (int(sx), int(sy + 2)), 8, 2)
        pygame.draw.circle(surf, (240, 230, 180), (int(sx), int(sy - 7)), 3)
    else:
        pygame.draw.circle(surf, contorno, (int(sx), int(sy - 3)), 7)
        pygame.draw.circle(surf, cor, (int(sx), int(sy - 3)), 5)
        pygame.draw.polygon(surf, (228, 190, 108), [(sx, sy + 1), (sx + 4, sy + 9), (sx, sy + 7), (sx - 4, sy + 9)])


# --------------------------------------------------------------------------
# áreas de perigo
# --------------------------------------------------------------------------


class AreaPerigo:
    def __init__(
        self, x: float, y: float, raio: float, dano: float, dono: str,
        tempo: float = 0.9, cor: Sequence[int] = (250, 90, 80),
        critico: bool = False, slow: float = 0.0,
        status: dict[str, float | str] | None = None,
    ) -> None:
        self.x, self.y = x, y
        self.raio = raio
        self.dano = dano
        self.dono = dono
        self.tempo = tempo
        self.tempo_max = tempo
        self.cor = tuple(cor[:3])
        self.critico = critico
        self.slow = slow
        self.status = status
        self.vivo = True

    def atualizar(self, dt: float, jogo: Any) -> None:
        if not self.vivo:
            return
        self.tempo -= dt
        if self.tempo > 0:
            return
        self.vivo = False
        if self.dono == "inimigo":
            jogador = jogo.jogador
            if not jogador.morto and distancia((self.x, self.y), (jogador.x, jogador.y)) <= self.raio + jogador.raio * 0.5:
                jogador.receber_dano(self.dano, jogo, self.critico, origem=(self.x, self.y))
        else:
            for inimigo in jogo.inimigos:
                if inimigo.vivo and distancia((self.x, self.y), (inimigo.x, inimigo.y)) <= self.raio + inimigo.raio * 0.5:
                    inimigo.receber_dano(self.dano, jogo, self.critico)
                    if self.slow > 0:
                        inimigo.slow_timer = max(inimigo.slow_timer, self.slow)
                    if self.status:
                        jogo.aplicar_status(inimigo, **self.status)
        jogo.particulas.emitir(self.x, self.y, self.cor, 26, 180, 5, 0.55)
        jogo.tremer(9, 0.25)
        jogo.efeitos.append(Efeito("explosao", self.x, self.y, self.raio, 0.4, self.cor))
        jogo.efeitos.append(Efeito("onda", self.x, self.y, self.raio * 1.15, 0.45, self.cor))

    def desenhar(self, surf: pygame.Surface, camera: Camera) -> None:
        if not self.vivo:
            return
        sx, sy = camera.aplicar((self.x, self.y))
        if not camera.visivel(self.x, self.y, self.raio + 40):
            return
        t = 1.0 - clamp(self.tempo / max(0.01, self.tempo_max), 0, 1)
        temp = pygame.Surface((int(self.raio * 2 + 8), int(self.raio * 2 + 8)), pygame.SRCALPHA)
        centro = (int(self.raio + 4), int(self.raio + 4))
        pygame.draw.circle(temp, (*self.cor, int(30 + 40 * t)), centro, int(self.raio))
        pygame.draw.circle(temp, (*self.cor, int(120 + 80 * t)), centro, int(self.raio), 3)
        pygame.draw.circle(temp, (255, 255, 255, int(80 + 80 * t)), centro, int(self.raio * (0.2 + 0.8 * t)), 1)
        for i in range(6):
            a = t * math.tau * 0.5 + i * math.tau / 6
            px = centro[0] + math.cos(a) * self.raio * 0.92
            py = centro[1] + math.sin(a) * self.raio * 0.92
            pygame.draw.circle(temp, (*self.cor, int(160 * (1 - t))), (int(px), int(py)), 3)
        surf.blit(temp, (int(sx - self.raio - 4), int(sy - self.raio - 4)))


# --------------------------------------------------------------------------
# efeitos
# --------------------------------------------------------------------------


class Efeito:
    def __init__(
        self, tipo: str, x: float, y: float, raio: float = 40.0,
        tempo: float = 0.4, cor: Sequence[int] = (250, 220, 150),
        pontos: list[tuple[float, float]] | None = None,
    ) -> None:
        self.tipo = tipo
        self.x, self.y = x, y
        self.raio = raio
        self.tempo = tempo
        self.tempo_max = tempo
        self.cor = tuple(cor[:3])
        self.pontos = pontos or []
        self.vivo = True

    def atualizar(self, dt: float) -> None:
        self.tempo -= dt
        if self.tempo <= 0:
            self.vivo = False

    def desenhar(self, surf: pygame.Surface, camera: Camera) -> None:
        if not self.vivo:
            return
        sx, sy = camera.aplicar((self.x, self.y))
        t = 1.0 - clamp(self.tempo / max(0.01, self.tempo_max), 0, 1)
        alpha = int(220 * (1.0 - t))
        if self.tipo == "onda":
            raio = int(self.raio * (0.3 + 0.7 * t))
            temp = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(temp, (*self.cor, alpha), (raio + 4, raio + 4), raio, max(2, int(5 * (1 - t))))
            surf.blit(temp, (int(sx - raio - 4), int(sy - raio - 4)))
        elif self.tipo == "runa":
            raio = int(self.raio * (0.85 + 0.15 * t))
            temp = pygame.Surface((raio * 2 + 12, raio * 2 + 12), pygame.SRCALPHA)
            centro = (raio + 6, raio + 6)
            pygame.draw.circle(temp, (*self.cor, int(alpha * 0.30)), centro, raio, 2)
            pygame.draw.circle(temp, (*self.cor, int(alpha * 0.65)), centro, int(raio * 0.72), 1)
            for i in range(8):
                a = t * math.tau + i * math.tau / 8
                px = centro[0] + math.cos(a) * raio * 0.88
                py = centro[1] + math.sin(a) * raio * 0.88
                pygame.draw.circle(temp, (*self.cor, alpha), (int(px), int(py)), 3)
            surf.blit(temp, (int(sx - raio - 6), int(sy - raio - 6)))
        elif self.tipo == "explosao":
            raio = int(self.raio * (0.25 + 0.75 * t))
            temp = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(temp, (*self.cor, int(alpha * 0.35)), (raio + 4, raio + 4), raio)
            pygame.draw.circle(temp, (*self.cor, alpha), (raio + 4, raio + 4), raio, max(2, int(4 * (1 - t))))
            surf.blit(temp, (int(sx - raio - 4), int(sy - raio - 4)))
        elif self.tipo == "raio" and len(self.pontos) >= 2:
            pts = [(int(px - camera.x + camera.ox), int(py - camera.y + camera.oy)) for px, py in self.pontos]
            for i in range(len(pts) - 1):
                pygame.draw.line(surf, (255, 255, 255), pts[i], pts[i + 1], max(1, int(5 * (1 - t))))
                pygame.draw.line(surf, self.cor, pts[i], pts[i + 1], max(1, int(2 * (1 - t))))
        elif self.tipo == "cura":
            raio = int(self.raio * (0.5 + 0.5 * t))
            pygame.draw.circle(surf, self.cor, (int(sx), int(sy - 30)), raio, max(1, int(3 * (1 - t))))
        elif self.tipo == "nivel":
            raio = int(self.raio * (0.2 + 0.8 * t))
            temp = pygame.Surface((raio * 2 + 8, raio * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(temp, (*self.cor, alpha), (raio + 4, raio + 4), raio, 4)
            surf.blit(temp, (int(sx - raio - 4), int(sy - raio - 4)))
