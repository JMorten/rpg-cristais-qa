"""Tela de configurações do jogo, em duas abas: Jogo e Áudio."""
from __future__ import annotations

import pygame

from core.preferences import (
    ESCALA_TEXTO_ROTULOS, Preferencias, limitar_volume, normalizar_escala_texto,
)
from settings import ALTURA, BORDA, DOURADO, LARGURA, PAINEL, TEXTO, TEXTO_FRACO, VERDE
from utils import (
    cantos_ornamentados, gradiente_vertical, modo_pixel, painel, raio_ui, texto,
    texto_contornado,
)
from ui_icons import icone

ABAS = ("Jogo", "Áudio", "Vídeo")

_ACOES = {
    "tela_cheia": "Tela cheia",
    "tremer_tela": "Tremor de tela",
    "numeros_dano": "Números de dano",
    "mostrar_fps": "Mostrar FPS",
    "dicas_tutorial": "Dicas de tutorial",
    "parada_impacto": "Parada de impacto",
    "escala_texto": "Tamanho do texto",
}

_DESCRICOES = {
    "tela_cheia": "Alterna entre janela e tela cheia",
    "tremer_tela": "Impactos e críticos sacodem a câmera e piscam a tela",
    "numeros_dano": "Mostra o dano causado e recebido",
    "mostrar_fps": "Exibe a taxa de quadros no HUD",
    "dicas_tutorial": "Mostra objetivos e dicas para iniciantes",
    "parada_impacto": "Desacelera o mundo por um instante nos golpes fortes",
    "escala_texto": "Ajusta o tamanho do texto da interface",
}

_ACOES_AUDIO = {
    "volume_geral": "Volume geral",
    "volume_musica": "Música",
    "volume_efeitos": "Efeitos",
    "mudo": "Mudo",
}

_DESCRICOES_AUDIO = {
    "volume_geral": "Volume de tudo, música e efeitos juntos",
    "volume_musica": "Trilha de ambiente de cada bioma",
    "volume_efeitos": "Golpes, magias, itens e interface",
    "mudo": "Silencia tudo (atalho: M)",
}

_VOLUMES = ("volume_geral", "volume_musica", "volume_efeitos")

_ACOES_VIDEO = {
    "bloom": "Bloom",
    "luz_avancada": "Iluminação avançada",
    "arte_pixel": "Arte pixel (experimental)",
}

_DESCRICOES_VIDEO = {
    "bloom": "Brilho suave em cristais, magia e críticos",
    "luz_avancada": "Luzes coloridas por fonte; desligado usa o visual antigo",
    "arte_pixel": "Herói, NPCs, casas, inimigos e interface em pixel art",
}


class TelaConfiguracoes:
    """Desenha e processa cliques da tela de configurações."""

    def __init__(self) -> None:
        self.botoes: list[tuple[pygame.Rect, str]] = []
        self.abas: list[tuple[pygame.Rect, str]] = []
        self.aba = "Jogo"
        self._fundo = gradiente_vertical((LARGURA, ALTURA), (10, 14, 24), (24, 20, 38))

    def desenhar(
        self,
        surf: pygame.Surface,
        prefs: Preferencias,
        fps: float = 0.0,
        usando_controle: bool = False,
    ) -> None:
        self.botoes.clear()
        self.abas.clear()
        surf.blit(self._fundo, (0, 0))

        painel(surf, (300, 56, 680, 608), 238, PAINEL, BORDA, 18, 2)
        cantos_ornamentados(surf, (300, 56, 680, 608))
        texto_contornado(surf, "Configurações", (LARGURA // 2, 74), 34, (246, 210, 130))
        texto(
            surf,
            "As mudanças são aplicadas e salvas na hora.",
            (LARGURA // 2, 122),
            13,
            TEXTO_FRACO,
            False,
            "center",
        )

        x = 340
        for nome in ABAS:
            r = pygame.Rect(x, 148, 130, 32)
            ativo = self.aba == nome
            pygame.draw.rect(surf, (44, 40, 28) if ativo else (20, 24, 34), r, border_radius=raio_ui(8))
            pygame.draw.rect(surf, DOURADO if ativo else (56, 64, 82), r, width=2 if ativo else 1, border_radius=raio_ui(8))
            texto(surf, nome, r.center, 14, DOURADO if ativo else TEXTO_FRACO, ativo, "center_all")
            self.abas.append((r, nome))
            x += 140

        if self.aba == "Jogo":
            self._desenhar_linhas(surf, prefs, _ACOES, _DESCRICOES, "engrenagem")
        elif self.aba == "Áudio":
            self._desenhar_linhas(surf, prefs, _ACOES_AUDIO, _DESCRICOES_AUDIO, "alto_falante")
        else:
            self._desenhar_linhas(surf, prefs, _ACOES_VIDEO, _DESCRICOES_VIDEO, "monitor")

        resetar = pygame.Rect(340, 574, 270, 40)
        voltar = pygame.Rect(670, 574, 270, 40)
        self._desenhar_botao(surf, resetar, "Restaurar padrões", "reset")
        self._desenhar_botao(surf, voltar, "Voltar", "voltar")

        dica = "A seleciona · B volta · analógico move o cursor" if usando_controle else "Clique para alternar · ESC volta"
        texto(surf, dica, (LARGURA // 2, 632), 11, (110, 118, 136), False, "center")
        if fps > 0:
            texto(surf, f"FPS {fps:.0f}", (940, 632), 11, (110, 118, 136), False, "right")

    # ------------------------------------------------------------------ linhas
    def _desenhar_linhas(
        self,
        surf: pygame.Surface,
        prefs: Preferencias,
        acoes: dict[str, str],
        descricoes: dict[str, str],
        icone_categoria: str | None = None,
    ) -> None:
        y = 192
        for chave, rotulo in acoes.items():
            linha = pygame.Rect(340, y, 600, 46)
            pygame.draw.rect(surf, (18, 22, 32), linha, border_radius=raio_ui(10))
            pygame.draw.rect(surf, (44, 50, 66), linha, width=1, border_radius=raio_ui(10))

            texto_x = linha.x + 18
            if icone_categoria is not None:
                icone(surf, icone_categoria, pygame.Rect(linha.x + 6, linha.y + 7, 32, 32), (150, 168, 200))
                texto_x = linha.x + 46
            texto(surf, rotulo, (texto_x, linha.y + 4), 15, TEXTO, True)
            texto(surf, descricoes[chave], (texto_x, linha.y + 25), 11, TEXTO_FRACO)

            alvo = pygame.Rect(linha.right - 154, linha.y + 7, 136, 32)
            if chave == "escala_texto":
                escala = normalizar_escala_texto(getattr(prefs, chave, 1.0))
                self._desenhar_seletor(surf, alvo, ESCALA_TEXTO_ROTULOS.get(escala, "Normal"))
            elif chave in _VOLUMES:
                self._desenhar_volume(surf, alvo, limitar_volume(getattr(prefs, chave), 0.8))
            else:
                self._desenhar_toggle(surf, alvo, bool(getattr(prefs, chave)))

            # A linha inteira é clicável, não apenas o controle.
            self.botoes.append((linha, chave))
            y += 52

    # ------------------------------------------------------------------ controles
    def _desenhar_toggle(self, surf: pygame.Surface, r: pygame.Rect, ativo: bool) -> None:
        fundo = (28, 58, 46) if ativo else (34, 38, 48)
        borda = VERDE if ativo else (70, 78, 96)
        pygame.draw.rect(surf, fundo, r, border_radius=raio_ui(r.height // 2))
        pygame.draw.rect(surf, borda, r, width=2, border_radius=raio_ui(r.height // 2))

        texto(
            surf,
            "Ligado" if ativo else "Desligado",
            (r.x + 14 if ativo else r.x + 38, r.y + 9),
            11,
            VERDE if ativo else TEXTO_FRACO,
            True,
        )
        centro = r.right - 17 if ativo else r.x + 17
        if modo_pixel():
            pygame.draw.rect(
                surf, (240, 240, 245) if ativo else (150, 156, 174),
                (centro - 10, r.centery - 10, 20, 20),
            )
        else:
            pygame.draw.circle(surf, (240, 240, 245) if ativo else (150, 156, 174), (centro, r.centery), 11)

    def _desenhar_seletor(self, surf: pygame.Surface, r: pygame.Rect, rotulo: str) -> None:
        """Seletor de múltiplos estados (clique na linha para avançar)."""
        pygame.draw.rect(surf, (30, 36, 50), r, border_radius=raio_ui(r.height // 2))
        pygame.draw.rect(surf, (110, 130, 170), r, width=2, border_radius=raio_ui(r.height // 2))
        texto(surf, rotulo, r.center, 12, (200, 220, 250), True, "center_all")
        for lado, x in ((-1, r.x + 14), (1, r.right - 14)):
            pygame.draw.polygon(surf, (150, 168, 200), [
                (x - lado * 4, r.centery - 5), (x + lado * 4, r.centery), (x - lado * 4, r.centery + 5),
            ])

    def _desenhar_volume(self, surf: pygame.Surface, r: pygame.Rect, valor: float) -> None:
        pygame.draw.rect(surf, (26, 30, 40), r, border_radius=raio_ui(r.height // 2))
        interno = r.inflate(-6, -6)
        interno.width = max(2, int(interno.width * valor))
        pygame.draw.rect(surf, (86, 168, 210), interno, border_radius=raio_ui(interno.height // 2))
        pygame.draw.rect(surf, (70, 78, 96), r, width=1, border_radius=raio_ui(r.height // 2))
        texto(surf, f"{int(round(valor * 100))}%", r.center, 11, (240, 244, 250), True, "center_all")

    def _desenhar_botao(self, surf: pygame.Surface, r: pygame.Rect, rotulo: str, acao: str) -> None:
        hover = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, (42, 36, 30) if hover else (22, 26, 36), r, border_radius=raio_ui(10))
        pygame.draw.rect(surf, DOURADO if hover else (96, 88, 70), r, width=2 if hover else 1, border_radius=raio_ui(10))
        texto(surf, rotulo, r.center, 15, DOURADO, True, "center_all")
        self.botoes.append((r, acao))

    def processar_clique(self, pos: tuple[int, int]) -> str | None:
        for r, nome in self.abas:
            if r.collidepoint(pos):
                self.aba = nome
                return "aba"
        for r, acao in self.botoes:
            if r.collidepoint(pos):
                return acao
        return None
