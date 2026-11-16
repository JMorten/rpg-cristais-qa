"""Entrada unificada: teclado, mouse e controle (SDL GameController).

O SDL GameController normaliza o layout de Xbox, PlayStation, Switch Pro e
genéricos compatíveis, então os nomes lógicos abaixo valem para todos.
"""
from __future__ import annotations

import logging
import math
from typing import Any

import pygame

from core.paths import em_web

LOGGER = logging.getLogger(__name__)

ZONA_MORTA = 0.24
ZONA_MORTA_MIRA = 0.30
LIMIAR_GATILHO = 0.45
_EIXO_MAX = 32767.0

BOTOES: dict[int, str] = {
    pygame.CONTROLLER_BUTTON_A: "a",
    pygame.CONTROLLER_BUTTON_B: "b",
    pygame.CONTROLLER_BUTTON_X: "x",
    pygame.CONTROLLER_BUTTON_Y: "y",
    pygame.CONTROLLER_BUTTON_LEFTSHOULDER: "lb",
    pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: "rb",
    pygame.CONTROLLER_BUTTON_BACK: "back",
    pygame.CONTROLLER_BUTTON_START: "start",
    pygame.CONTROLLER_BUTTON_LEFTSTICK: "l3",
    pygame.CONTROLLER_BUTTON_RIGHTSTICK: "r3",
    pygame.CONTROLLER_BUTTON_DPAD_UP: "cima",
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: "baixo",
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: "esquerda",
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: "direita",
}

GATILHOS: dict[int, str] = {
    pygame.CONTROLLER_AXIS_TRIGGERLEFT: "lt",
    pygame.CONTROLLER_AXIS_TRIGGERRIGHT: "rt",
}


def _limitar(valor: float) -> float:
    return max(-1.0, min(1.0, valor))


def aplicar_zona_morta(x: float, y: float, zona: float = ZONA_MORTA) -> tuple[float, float]:
    """Zona morta radial com reescala, para não perder precisão perto do centro."""
    magnitude = math.hypot(x, y)
    if magnitude < zona or magnitude == 0.0:
        return 0.0, 0.0
    util = (min(magnitude, 1.0) - zona) / (1.0 - zona)
    return x / magnitude * util, y / magnitude * util


def teclado_movimento() -> tuple[float, float]:
    teclas = pygame.key.get_pressed()
    dx = int(bool(teclas[pygame.K_d] or teclas[pygame.K_RIGHT])) - int(bool(teclas[pygame.K_a] or teclas[pygame.K_LEFT]))
    dy = int(bool(teclas[pygame.K_s] or teclas[pygame.K_DOWN])) - int(bool(teclas[pygame.K_w] or teclas[pygame.K_UP]))
    return float(dx), float(dy)


def teclado_correndo() -> bool:
    teclas = pygame.key.get_pressed()
    return bool(teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT])


class Entrada:
    """Agrega teclado/mouse e um controle, e sabe qual foi usado por último."""

    def __init__(self, iniciar_controles: bool = True) -> None:
        self.controle: Any | None = None
        self.dispositivo = "teclado"
        self._modulo: Any | None = None
        self._gatilhos = {"lt": False, "rt": False}
        self._cursor_sintetico: tuple[int, int] | None = None
        self.modo_toque = False
        self.toque_vetor: tuple[float, float] = (0.0, 0.0)
        self.toque_correndo = False
        self.toque_ataque = False
        if iniciar_controles:
            self._iniciar()

    # ------------------------------------------------------------------ conexão
    def _iniciar(self) -> None:
        if em_web():
            return
        try:
            from pygame._sdl2 import controller

            controller.init()
            self._modulo = controller
            self._procurar_controle()
        except Exception:  # pragma: no cover - depende do driver/SO
            LOGGER.warning("Suporte a controle indisponível.", exc_info=True)
            self._modulo = None

    def _procurar_controle(self) -> bool:
        if self._modulo is None:
            return False
        for indice in range(self._modulo.get_count()):
            if self._modulo.is_controller(indice):
                try:
                    self.conectar(self._modulo.Controller(indice))
                    return True
                except Exception:  # pragma: no cover
                    LOGGER.warning("Falha ao abrir o controle %s.", indice, exc_info=True)
        return False

    def conectar(self, controle: Any) -> None:
        self.controle = controle
        self._gatilhos = {"lt": False, "rt": False}
        LOGGER.info("Controle conectado: %s", self.nome_controle)

    def desconectar(self) -> None:
        LOGGER.info("Controle desconectado: %s", self.nome_controle)
        self.controle = None
        self.dispositivo = "teclado"
        self._gatilhos = {"lt": False, "rt": False}

    @staticmethod
    def _esta_conectado(controle: Any) -> bool:
        try:
            return bool(controle.attached())
        except Exception:
            return False

    @property
    def nome_controle(self) -> str:
        if self.controle is None:
            return ""
        return str(getattr(self.controle, "name", "") or "Controle")

    @property
    def usando_controle(self) -> bool:
        return self.controle is not None and self.dispositivo == "controle"

    def marcar_cursor_sintetico(self, pos: tuple[float, float]) -> None:
        """Registra um movimento de mouse gerado pelo próprio jogo (cursor virtual)."""
        self._cursor_sintetico = (int(pos[0]), int(pos[1]))

    # ------------------------------------------------------------------ eventos
    def processar_evento(self, event: pygame.event.Event) -> list[str]:
        """Retorna botões lógicos pressionados neste evento (edge-trigger).

        Eventos especiais: "_conectado" e "_desconectado".
        """
        tipo = event.type

        if tipo in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL):
            self.dispositivo = "teclado"
            return []

        if tipo == pygame.MOUSEMOTION:
            sintetico = self._cursor_sintetico
            if sintetico is not None and abs(event.pos[0] - sintetico[0]) <= 2 and abs(event.pos[1] - sintetico[1]) <= 2:
                return []
            rel = getattr(event, "rel", (0, 0))
            if abs(rel[0]) + abs(rel[1]) >= 3:
                self.dispositivo = "teclado"
            return []

        if tipo == pygame.CONTROLLERDEVICEADDED:
            if self.controle is None and self._modulo is not None:
                try:
                    self.conectar(self._modulo.Controller(event.device_index))
                    return ["_conectado"]
                except Exception:  # pragma: no cover
                    LOGGER.warning("Falha ao conectar controle.", exc_info=True)
            return []

        if tipo == pygame.CONTROLLERDEVICEREMOVED:
            if self.controle is not None and not self._esta_conectado(self.controle):
                self.desconectar()
                self._procurar_controle()
                return ["_desconectado"]
            return []

        if tipo == pygame.CONTROLLERBUTTONDOWN:
            nome = BOTOES.get(event.button)
            if nome is None:
                return []
            self.dispositivo = "controle"
            return [nome]

        if tipo == pygame.CONTROLLERAXISMOTION:
            valor = event.value / _EIXO_MAX
            gatilho = GATILHOS.get(event.axis)
            if gatilho is not None:
                apertado = valor > LIMIAR_GATILHO
                antes = self._gatilhos[gatilho]
                self._gatilhos[gatilho] = apertado
                if apertado and not antes:
                    self.dispositivo = "controle"
                    return [gatilho]
                return []
            if abs(valor) > 0.5:
                self.dispositivo = "controle"
            return []

        return []

    # ------------------------------------------------------------------ leitura contínua
    def _eixo(self, eixo: int) -> float:
        if self.controle is None:
            return 0.0
        try:
            return _limitar(self.controle.get_axis(eixo) / _EIXO_MAX)
        except Exception:
            return 0.0

    def _botao(self, botao: int) -> bool:
        if self.controle is None:
            return False
        try:
            return bool(self.controle.get_button(botao))
        except Exception:
            return False

    def eixo_controle(self) -> tuple[float, float]:
        """Analógico esquerdo, já com zona morta. O D-pad fica para poções/falar."""
        x, y = aplicar_zona_morta(
            self._eixo(pygame.CONTROLLER_AXIS_LEFTX),
            self._eixo(pygame.CONTROLLER_AXIS_LEFTY),
        )
        return _limitar(x), _limitar(y)

    def eixo_movimento(self) -> tuple[float, float]:
        kx, ky = teclado_movimento()
        cx, cy = self.eixo_controle()
        tx, ty = self.toque_vetor
        return _limitar(kx + cx + tx), _limitar(ky + cy + ty)

    def correndo(self) -> bool:
        return (
            teclado_correndo()
            or self.toque_correndo
            or self._botao(pygame.CONTROLLER_BUTTON_LEFTSTICK)
            or self._eixo(pygame.CONTROLLER_AXIS_TRIGGERLEFT) > LIMIAR_GATILHO
        )

    def segurando_ataque(self) -> bool:
        if self.toque_ataque:
            return True
        if self.controle is None:
            return False
        return (
            self._botao(pygame.CONTROLLER_BUTTON_A)
            or self._eixo(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) > LIMIAR_GATILHO
        )

    def direcao_mira(self) -> tuple[float, float] | None:
        """Direção normalizada do analógico direito, ou None se estiver solto."""
        x, y = aplicar_zona_morta(
            self._eixo(pygame.CONTROLLER_AXIS_RIGHTX),
            self._eixo(pygame.CONTROLLER_AXIS_RIGHTY),
            ZONA_MORTA_MIRA,
        )
        magnitude = math.hypot(x, y)
        if magnitude == 0.0:
            return None
        return x / magnitude, y / magnitude

    def vibrar(self, fraco: float, forte: float, duracao_ms: int) -> None:
        if self.controle is None:
            return
        try:
            self.controle.rumble(fraco, forte, duracao_ms)
        except Exception:
            pass
