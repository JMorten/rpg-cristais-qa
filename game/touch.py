"""Controles de toque para celular/tablet (joystick virtual e botões)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pygame

from settings import ALTURA, LARGURA
from ui_icons import icone
from utils import texto

# Regiões tocáveis do painel de poções (as mesmas do HUD).
REGIOES_POCOES: tuple[tuple[str, pygame.Rect], ...] = (
    ("pocao_vida", pygame.Rect(1120, 220, 146, 82)),
    ("pocao_mana", pygame.Rect(1120, 302, 146, 82)),
    ("pocao_stamina", pygame.Rect(1120, 384, 146, 86)),
)

REGIOES_HOTBAR: tuple[tuple[str, pygame.Rect], ...] = ()


@dataclass(frozen=True)
class BotaoToque:
    id: str
    centro: tuple[int, int]
    raio: int
    rotulo: str
    cor: tuple[int, int, int]


BOTOES: tuple[BotaoToque, ...] = (
    BotaoToque("ataque", (1150, 592), 70, "", (224, 96, 96)),
    BotaoToque("skill0", (986, 648), 42, "Q", (228, 190, 108)),
    BotaoToque("skill1", (968, 556), 42, "E", (228, 190, 108)),
    BotaoToque("skill2", (986, 464), 42, "R", (228, 190, 108)),
    BotaoToque("skill3", (1024, 374), 42, "F", (228, 190, 108)),
    BotaoToque("esquiva", (1060, 680), 32, "ESQ", (140, 210, 240)),
    BotaoToque("interagir", (868, 648), 40, "T", (238, 220, 140)),
    BotaoToque("inventario", (1158, 44), 30, "I", (190, 196, 220)),
    BotaoToque("pausa", (1236, 44), 30, "II", (220, 220, 230)),
)

_JOY_CENTRO = (150, ALTURA - 100)
_JOY_RAIO = 86


class TouchControls:
    """Traduz dedos/mouse em movimento, mira e ações lógicas."""

    def __init__(self) -> None:
        self.ativo = False
        self._joy_id: int | None = None
        self._joy_vetor = (0.0, 0.0)
        self._held: dict[int, str] = {}
        self._edges: list[str] = []
        self._finger_visto = False
        self.js_ativo = False
        self._overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        self._pulso = 0.0

    # ------------------------------------------------------------------ estado
    @property
    def movimento(self) -> tuple[float, float]:
        return self._joy_vetor

    @property
    def correndo(self) -> bool:
        return math.hypot(*self._joy_vetor) > 0.88

    def pressionado(self, nome: str) -> bool:
        return nome in self._held.values()

    def consumir_eventos(self) -> list[str]:
        eventos = self._edges
        self._edges = []
        return eventos

    def atualizar(self, dt: float) -> None:
        self._pulso = (self._pulso + dt) % math.tau

    def processar_fila_js(self, jogo: Any) -> None:
        """Lê os toques que o JavaScript do navegador colocou na fila."""
        if not self.ativo:
            return
        try:
            from js import window

            eventos = window.consumirToques()
            self.js_ativo = True
        except Exception:
            return
        for ev in eventos:
            tipo = str(ev.tipo)
            ponteiro = int(ev.id)
            pos = (int(ev.x), int(ev.y))
            if jogo.estado == "jogando":
                if tipo == "down":
                    self._inicio(ponteiro, pos, jogo)
                elif tipo == "move":
                    self._mover(ponteiro, pos)
                elif tipo == "up":
                    self._fim(ponteiro)
            elif tipo == "down":
                # Menus, painel, forja, cristais, atributos e habilidades.
                jogo._clique(pos, 1)

    # ------------------------------------------------------------------ eventos
    @staticmethod
    def pos_evento(event: pygame.event.Event) -> tuple[int, int] | None:
        """Converte dedo (0..1) ou mouse (pixels) para coordenadas da tela."""
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            return int(event.x * LARGURA), int(event.y * ALTURA)
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            return int(event.pos[0]), int(event.pos[1])
        return None

    def processar_evento(self, event: pygame.event.Event, jogo: Any) -> bool:
        """Retorna True quando o toque foi consumido pelos controles."""
        if not self.ativo or jogo.estado != "jogando":
            return False

        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            self._finger_visto = True
            pos = self.pos_evento(event)
            if pos is None:
                return False
            if event.type == pygame.FINGERDOWN:
                return self._inicio(int(event.finger_id), pos, jogo)
            if event.type == pygame.FINGERMOTION:
                return self._mover(int(event.finger_id), pos)
            return self._fim(int(event.finger_id))

        if self._finger_visto:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                return False
            return self._inicio(0, self.pos_evento(event) or (0, 0), jogo)
        if event.type == pygame.MOUSEMOTION:
            return self._mover(0, self.pos_evento(event) or (0, 0))
        if event.type == pygame.MOUSEBUTTONUP:
            return self._fim(0)
        return False

    def _inicio(self, ponteiro: int, pos: tuple[int, int], jogo: Any) -> bool:
        if self._dentro_joystick(pos):
            self._joy_id = ponteiro
            self._atualizar_joystick(pos)
            return True
        for botao in BOTOES:
            if not self._botao_visivel(botao, jogo):
                continue
            if math.dist(pos, botao.centro) <= botao.raio * 1.15:
                self._held[ponteiro] = botao.id
                self._edges.append(botao.id)
                return True
        for acao, rect in REGIOES_POCOES:
            if rect.collidepoint(pos):
                self._edges.append(acao)
                return True
        return False

    def _mover(self, ponteiro: int, pos: tuple[int, int]) -> bool:
        if ponteiro == self._joy_id:
            self._atualizar_joystick(pos)
            return True
        return ponteiro in self._held

    def _fim(self, ponteiro: int) -> bool:
        if ponteiro == self._joy_id:
            self._joy_id = None
            self._joy_vetor = (0.0, 0.0)
            return True
        return self._held.pop(ponteiro, None) is not None

    def _dentro_joystick(self, pos: tuple[int, int]) -> bool:
        return math.dist(pos, _JOY_CENTRO) <= _JOY_RAIO * 1.35

    def _atualizar_joystick(self, pos: tuple[int, int]) -> None:
        dx = pos[0] - _JOY_CENTRO[0]
        dy = pos[1] - _JOY_CENTRO[1]
        distancia = math.hypot(dx, dy)
        if distancia <= 1e-3:
            self._joy_vetor = (0.0, 0.0)
            return
        magnitude = min(0.92, distancia / _JOY_RAIO)
        self._joy_vetor = (
            max(-1.0, min(1.0, dx / distancia * magnitude)),
            max(-1.0, min(1.0, dy / distancia * magnitude)),
        )

    @staticmethod
    def _botao_visivel(botao: BotaoToque, jogo: Any) -> bool:
        if botao.id == "interagir":
            return bool(jogo.npc_perto or jogo.fogueira_perto is not None)
        return True

    # ------------------------------------------------------------------ mira
    def mira(self, jogo: Any) -> tuple[float, float]:
        j = jogo.jogador
        if j is None:
            return (0.0, 0.0)
        melhor = None
        menor = 430.0
        for inimigo in jogo.inimigos:
            if not inimigo.vivo:
                continue
            d = math.dist((j.x, j.y), (inimigo.x, inimigo.y))
            if d < menor:
                menor = d
                melhor = inimigo
        if melhor is not None:
            return (melhor.x, melhor.y)
        return (j.x + j.facing[0] * 260, j.y + j.facing[1] * 260)

    # ------------------------------------------------------------------ desenho
    def desenhar(self, surf: pygame.Surface, jogo: Any, simples: bool = False) -> None:
        if not self.ativo or jogo.estado != "jogando":
            return
        if simples:
            self._desenhar_simples(surf, jogo)
            return
        self._overlay.fill((0, 0, 0, 0))

        # destaque das poções tocáveis
        for acao, rect in REGIOES_POCOES:
            cor = (240, 210, 120, 26) if self.pressionado(acao) else (240, 210, 120, 10)
            pygame.draw.rect(self._overlay, cor, rect, border_radius=10)

        # joystick
        cx, cy = _JOY_CENTRO
        pygame.draw.circle(self._overlay, (10, 14, 22, 150), (cx, cy), _JOY_RAIO)
        pygame.draw.circle(self._overlay, (220, 210, 170, 130), (cx, cy), _JOY_RAIO, 2)
        pygame.draw.circle(self._overlay, (220, 210, 170, 55), (cx, cy), _JOY_RAIO // 2, 1)
        kx = int(cx + self._joy_vetor[0] * _JOY_RAIO * 0.62)
        ky = int(cy + self._joy_vetor[1] * _JOY_RAIO * 0.62)
        cor_knob = (240, 214, 150, 210) if self._joy_id is not None else (210, 200, 170, 120)
        pygame.draw.circle(self._overlay, (10, 14, 22, 170), (kx, ky), 34)
        pygame.draw.circle(self._overlay, cor_knob, (kx, ky), 30)
        if self.correndo:
            pygame.draw.circle(self._overlay, (250, 220, 140, 190), (cx, cy), _JOY_RAIO + 4, 2)

        # botões
        for botao in BOTOES:
            if not self._botao_visivel(botao, jogo):
                continue
            ativo = self.pressionado(botao.id)
            raio = botao.raio + (2 if ativo else 0)
            pygame.draw.circle(self._overlay, (10, 14, 22, 155), botao.centro, raio + 4)
            pygame.draw.circle(
                self._overlay, (*botao.cor, 165 if ativo else 112), botao.centro, raio,
            )
            pygame.draw.circle(
                self._overlay, (*botao.cor, 245 if ativo else 210), botao.centro, raio, 2,
            )
            if botao.id == "ataque":
                self._desenhar_espada(botao.centro, raio)
            elif botao.id == "inventario":
                self._desenhar_mochila(botao.centro)
            elif botao.id == "pausa":
                pygame.draw.line(
                    self._overlay, (245, 240, 220),
                    (botao.centro[0] - 6, botao.centro[1] - 9),
                    (botao.centro[0] - 6, botao.centro[1] + 9), 3,
                )
                pygame.draw.line(
                    self._overlay, (245, 240, 220),
                    (botao.centro[0] + 6, botao.centro[1] - 9),
                    (botao.centro[0] + 6, botao.centro[1] + 9), 3,
                )
            elif botao.id.startswith("skill"):
                self._desenhar_icone_habilidade(jogo, botao, self._overlay)
            else:
                tamanho = 18 if len(botao.rotulo) <= 1 else 11
                texto(
                    self._overlay, botao.rotulo, botao.centro,
                    tamanho, (250, 246, 230), True, "center",
                )

        surf.blit(self._overlay, (0, 0))

    def _desenhar_simples(self, surf: pygame.Surface, jogo: Any) -> None:
        cx, cy = _JOY_CENTRO
        pygame.draw.circle(surf, (16, 22, 32), (cx, cy), _JOY_RAIO)
        pygame.draw.circle(surf, (212, 198, 160), (cx, cy), _JOY_RAIO, 2)
        kx = int(cx + self._joy_vetor[0] * _JOY_RAIO * 0.62)
        ky = int(cy + self._joy_vetor[1] * _JOY_RAIO * 0.62)
        pygame.draw.circle(surf, (12, 16, 24), (kx, ky), 34)
        pygame.draw.circle(
            surf, (240, 214, 150) if self._joy_id is not None else (196, 186, 156),
            (kx, ky), 30,
        )
        if self.correndo:
            pygame.draw.circle(surf, (250, 220, 140), (cx, cy), _JOY_RAIO + 4, 2)

        for botao in BOTOES:
            if not self._botao_visivel(botao, jogo):
                continue
            ativo = self.pressionado(botao.id)
            raio = botao.raio + (2 if ativo else 0)
            pygame.draw.circle(surf, (14, 19, 28), botao.centro, raio + 3)
            pygame.draw.circle(
                surf, botao.cor if ativo else tuple(int(c * 0.72) for c in botao.cor),
                botao.centro, raio,
            )
            pygame.draw.circle(surf, botao.cor, botao.centro, raio, 2)
            if botao.id == "ataque":
                x, y = botao.centro
                pygame.draw.line(surf, (250, 246, 230), (x - 14, y + 14), (x + 16, y - 16), 6)
                pygame.draw.line(surf, (228, 190, 108), (x - 18, y + 2), (x - 2, y + 18), 4)
            elif botao.id == "inventario":
                x, y = botao.centro
                pygame.draw.rect(surf, (230, 214, 170), (x - 9, y - 6, 18, 15), border_radius=3)
                pygame.draw.arc(
                    surf, (230, 214, 170),
                    pygame.Rect(x - 7, y - 13, 14, 12), math.pi, math.tau, 2,
                )
            elif botao.id == "pausa":
                x, y = botao.centro
                pygame.draw.line(surf, (245, 240, 220), (x - 6, y - 9), (x - 6, y + 9), 3)
                pygame.draw.line(surf, (245, 240, 220), (x + 6, y - 9), (x + 6, y + 9), 3)
            elif botao.id.startswith("skill"):
                self._desenhar_icone_habilidade(jogo, botao, surf)
            else:
                tamanho = 18 if len(botao.rotulo) <= 1 else 11
                texto(surf, botao.rotulo, botao.centro, tamanho, (250, 246, 230), True, "center")
            if botao.id.startswith("skill") and getattr(jogo, "jogador", None) is not None:
                indice = int(botao.id[-1])
                habilidades = jogo.jogador.habilidades
                if indice < len(habilidades):
                    restante = jogo.jogador.cooldowns.get(habilidades[indice].id, 0.0)
                    if restante > 0:
                        pygame.draw.circle(surf, (10, 14, 22), botao.centro, raio - 3)
                        texto(
                            surf, f"{restante:.0f}", botao.centro, 16,
                            (240, 220, 160), True, "center",
                        )

    @staticmethod
    def _desenhar_icone_habilidade(jogo: Any, botao: BotaoToque, surf: pygame.Surface) -> None:
        """Desenha o ícone real da habilidade no botão de toque."""
        jogador = getattr(jogo, "jogador", None)
        indice = int(botao.id[-1])
        habilidades = getattr(jogador, "habilidades", [])
        if indice >= len(habilidades):
            texto(surf, botao.rotulo, botao.centro, 18, (250, 246, 230), True, "center")
            return
        habilidade = habilidades[indice]
        lado = int(botao.raio * 1.15)
        icone(
            surf, habilidade.icone,
            (botao.centro[0] - lado // 2, botao.centro[1] - lado // 2, lado, lado),
            (250, 246, 230),
        )

    def _desenhar_espada(self, centro: tuple[int, int], raio: int) -> None:
        x, y = centro
        pygame.draw.line(self._overlay, (250, 246, 230), (x - 14, y + 14), (x + 16, y - 16), 6)
        pygame.draw.line(self._overlay, (230, 232, 240), (x - 12, y + 12), (x + 14, y - 14), 3)
        pygame.draw.line(self._overlay, (228, 190, 108), (x - 18, y + 2), (x - 2, y + 18), 4)
        pygame.draw.circle(self._overlay, (228, 190, 108), (x - 16, y + 16), 4)

    def _desenhar_mochila(self, centro: tuple[int, int]) -> None:
        x, y = centro
        pygame.draw.rect(self._overlay, (230, 214, 170), (x - 9, y - 6, 18, 15), border_radius=3)
        pygame.draw.arc(
            self._overlay, (230, 214, 170),
            pygame.Rect(x - 7, y - 13, 14, 12), math.pi, math.tau, 2,
        )
        pygame.draw.line(self._overlay, (90, 74, 56), (x - 8, y + 1), (x + 8, y + 1), 2)
