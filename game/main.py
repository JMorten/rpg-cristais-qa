"""Cristais de Aether — ponto de entrada."""
from __future__ import annotations

import asyncio
import logging
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from core.logging_setup import install_exception_hook, setup_logging
from core.paths import em_web
from game import Jogo
from settings import ALTURA, FPS, LARGURA, TITULO, VERSAO


def modo_toque_ativo() -> bool:
    """Toque só em dispositivo móvel (ou com --toque); PC usa modo desktop."""
    if "--toque" in sys.argv:
        return True
    return em_web() and os.environ.get("CRISTAIS_TOQUE", "1") == "1"


async def main() -> int:
    if "--version" in sys.argv:
        print(f"{TITULO} {VERSAO}")
        return 0

    log_path = setup_logging()
    install_exception_hook(log_path)
    logger = logging.getLogger("cristais")
    logger.info("Iniciando %s %s", TITULO, VERSAO)

    try:
        pygame.init()
        pygame.display.set_caption(TITULO)
        tela = pygame.display.set_mode((LARGURA, ALTURA))
        relogio = pygame.time.Clock()
        jogo = Jogo()
        jogo.aplicar_preferencias()
        if modo_toque_ativo():
            jogo.aplicar_modo_toque(True)
        elif em_web():
            jogo.aplicar_modo_desempenho(True)
        if em_web():
            try:
                import js
                js.window.jogo = jogo
            except Exception:
                pass
        if "--luz-simples" in sys.argv:
            jogo.luz_avancada = False

        modo_screenshot = "--screenshot" in sys.argv
        frames = 0

        while jogo.rodando:
            alvo_fps = 30 if getattr(jogo, "modo_desempenho", False) else FPS
            dt = relogio.tick(alvo_fps) / 1000.0
            for event in pygame.event.get():
                jogo.processar_evento(event)
            jogo.fps = relogio.get_fps()
            jogo.atualizar(dt)
            tela = pygame.display.get_surface() or tela
            jogo.desenhar(tela)
            pygame.display.flip()
            frames += 1

            if modo_screenshot:
                if frames == 3:
                    pygame.image.save(tela, "screenshot_menu.png")
                elif frames == 5:
                    jogo.novo_jogo("Cavaleiro")
                elif frames == 35:
                    pygame.image.save(tela, "screenshot_jogo.png")
                elif frames == 37:
                    jogo.ui.painel.aba = "Equipamentos"
                    jogo.estado = "painel"
                elif frames == 42:
                    pygame.image.save(tela, "screenshot_painel.png")
                elif frames == 44:
                    jogo.estado = "jogando"
                    jogo.ui.painel.aba = "Habilidades"
                elif frames == 46:
                    jogo.estado = "painel"
                elif frames == 50:
                    pygame.image.save(tela, "screenshot_habilidades.png")
                elif frames > 54:
                    jogo.rodando = False

            # Cede o controle ao navegador (pygbag) e mantém o desktop responsivo.
            await asyncio.sleep(0)
    finally:
        pygame.quit()
        logger.info("Encerrando")

    return 0


def cli() -> int:
    """Ponto de entrada síncrono para o comando `cristais`."""
    return asyncio.run(main())


if __name__ == "__main__":
    if em_web():
        asyncio.run(main())
    else:
        raise SystemExit(cli())
