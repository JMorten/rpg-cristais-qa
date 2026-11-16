"""HUD, minimapa, menus e telas de estado."""
from __future__ import annotations

import math
import random
from typing import Any, Sequence

import pygame

from settings import (
    ALTURA, BORDA, BRANCO, CLASSES, DOURADO, LARGURA, PAINEL, TEXTO, TEXTO_FRACO,
    VERDE, VERSAO,
)
from items import Pocao
from skills import resumo_classe
from ui_icons import icone, moeda, retrato_classe
from ui_panel import Painel
from utils import (
    barra, cantos_ornamentados, fonte, gradiente_vertical, modo_pixel, painel, raio_ui,
    texto, texto_contornado,
)


BOTOES_HABILIDADE = ("X", "Y", "B", "RB")


def _usando_controle(jogo: Any) -> bool:
    entrada = getattr(jogo, "entrada", None)
    return bool(getattr(entrada, "usando_controle", False))


def _tinta_dano(surf: pygame.Surface, rect: pygame.Rect | Sequence[int], j: Any) -> None:
    """Pisca o retrato de vermelho quando o herói leva dano (só no modo pixel)."""
    if not modo_pixel():
        return
    flash = getattr(j, "hit_flash", 0.0)
    if flash <= 0.0:
        return
    r = pygame.Rect(rect)
    camada = pygame.Surface(r.size, pygame.SRCALPHA)
    camada.fill((220, 60, 60, int(130 * min(1.0, flash / 0.14))))
    surf.blit(camada, r.topleft)


def _modo_toque(jogo: Any) -> bool:
    return bool(getattr(jogo, "modo_toque", False))


_MASCARA_HALO: pygame.Surface | None = None
_HALOS_COLORIDOS: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}


def _mascara_halo() -> pygame.Surface:
    """Máscara radial suave, criada uma única vez."""
    global _MASCARA_HALO
    if _MASCARA_HALO is None:
        n = 96
        _MASCARA_HALO = pygame.Surface((n, n), pygame.SRCALPHA)
        for y in range(n):
            for x in range(n):
                dx = (x + 0.5) / (n / 2) - 1.0
                dy = (y + 0.5) / (n / 2) - 1.0
                d = math.hypot(dx, dy)
                if d <= 1.0:
                    alpha = int(64 * (1.0 - d) ** 2)
                    _MASCARA_HALO.set_at((x, y), (255, 255, 255, alpha))
    return _MASCARA_HALO


def _halo_colorido(cor: Sequence[int], tamanho: int) -> pygame.Surface:
    pixel = modo_pixel()
    chave = (tuple(int(c) for c in cor[:3]), tamanho, pixel)
    halo = _HALOS_COLORIDOS.get(chave)
    if halo is None:
        if pixel:
            # Brilho em degraus, para combinar com a arte pixel.
            halo = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
            centro = (tamanho // 2, tamanho // 2)
            for f, peso in ((1.0, 18), (0.68, 34), (0.40, 58)):
                pygame.draw.circle(halo, (*chave[0], peso), centro, max(2, int(tamanho * 0.5 * f)))
        else:
            base = _mascara_halo().copy()
            base.fill((*chave[0], 255), special_flags=pygame.BLEND_RGBA_MULT)
            halo = pygame.transform.smoothscale(base, (tamanho, tamanho))
        _HALOS_COLORIDOS[chave] = halo
    return halo


def _quebrar_texto(txt: str, largura: int, tamanho: int = 12) -> list[str]:
    palavras = str(txt).split()
    linhas: list[str] = []
    atual = ""
    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        if fonte(tamanho).size(teste)[0] <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas or [""]


class UI:
    def __init__(self) -> None:
        self.painel = Painel()
        self.tempo = 0.0
        self._pronto_antes: dict[str, bool] = {}
        self._pronto_em: dict[str, float] = {}
        self.notificacoes: list[dict[str, Any]] = []
        self.botoes_menu: list[tuple[pygame.Rect, str]] = []
        self.botoes_pausa: list[tuple[pygame.Rect, str]] = []
        self.botoes_morte: list[tuple[pygame.Rect, str]] = []
        self.botoes_vitoria: list[tuple[pygame.Rect, str]] = []
        self.cartoes_classe: list[tuple[pygame.Rect, str]] = []
        self.botao_voltar: pygame.Rect | None = None
        self.fundo_menu = self._criar_fundo()
        self.estrelas = [
            (random.randrange(LARGURA), random.randrange(ALTURA), random.uniform(0.4, 1.6))
            for _ in range(120)
        ]
        self.aba_painel = "Equipamentos"

    # ------------------------------------------------------------------ base
    def _criar_fundo(self) -> pygame.Surface:
        s = gradiente_vertical((LARGURA, ALTURA), (12, 16, 30), (34, 22, 48))
        # névoa com bordas suaves
        n = 64
        blob = pygame.Surface((n, n), pygame.SRCALPHA)
        for y in range(n):
            for x in range(n):
                dx = (x + 0.5) / (n / 2) - 1.0
                dy = (y + 0.5) / (n / 2) - 1.0
                d = math.hypot(dx, dy)
                if d <= 1.0:
                    blob.set_at((x, y), (80, 60, 130, int(17 * (1.0 - d) ** 2)))
        for _ in range(30):
            x = random.randrange(LARGURA)
            y = random.randrange(ALTURA)
            r = random.randint(80, 260)
            nevoa = pygame.transform.smoothscale(blob, (r * 2, r * 2))
            s.blit(nevoa, (x - r, y - r))
        return s

    def notificar(self, mensagem: str, cor: Sequence[int] = TEXTO) -> None:
        self.notificacoes.append({"texto": mensagem, "cor": tuple(cor[:3]), "tempo": 3.4})
        if len(self.notificacoes) > 6:
            self.notificacoes.pop(0)

    def atualizar(self, dt: float) -> None:
        self.tempo += dt
        for n in self.notificacoes:
            n["tempo"] -= dt
        self.notificacoes = [n for n in self.notificacoes if n["tempo"] > 0]

    # ------------------------------------------------------------------ HUD
    def desenhar_hud(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        toque = _modo_toque(jogo)
        if toque:
            self._desenhar_cartao_toque(surf, j)
        else:
            self._desenhar_cartao(surf, j)
            self._desenhar_relogio(surf, jogo)
        self._desenhar_ouro(surf, j, toque)
        controle = _usando_controle(jogo)
        jogando = getattr(jogo, "estado", "jogando") == "jogando"
        if not toque:
            self._desenhar_hotbar(surf, j, controle, toque)
        if jogando:
            self._desenhar_pocoes(surf, j, controle, toque)
            if not toque:
                self._desenhar_minimapa(surf, jogo)
        self._desenhar_notificacoes(surf)
        self._desenhar_avisos(surf, jogo)
        self._desenhar_dicas(surf, controle, toque)
        if jogando:
            if not toque:
                self._desenhar_card_tutorial(surf, jogo, controle, toque)
            self._desenhar_missao(surf, jogo)
            self._desenhar_dialogo(surf, jogo)
        if getattr(jogo, "prefs", None) is not None and jogo.prefs.mostrar_fps:
            texto(surf, f"FPS {getattr(jogo, 'fps', 0.0):.0f}", (20, 670), 11, TEXTO_FRACO)

    def _desenhar_cartao(self, surf: pygame.Surface, j: Any) -> None:
        """Cartão compacto do jogador no desktop."""
        cartao = pygame.Rect(16, 14, 306, 110)
        fundo = pygame.Surface(cartao.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (10, 14, 22, 168), fundo.get_rect(), border_radius=raio_ui(16))
        pygame.draw.rect(fundo, (196, 164, 98, 110), fundo.get_rect(), width=1, border_radius=raio_ui(16))
        surf.blit(fundo, cartao.topleft)
        cantos_ornamentados(surf, cartao, tamanho=12)

        estado = "morto" if j.morto else "ferido" if j.hp < j.hp_max * 0.3 else "normal"
        retrato_classe(surf, j.classe, (cartao.x + 10, cartao.y + 10, 56, 56), estado=estado, tempo=self.tempo)
        _tinta_dano(surf, (cartao.x + 10, cartao.y + 10, 56, 56), j)
        texto(surf, j.nome, (cartao.x + 78, cartao.y + 6), 17, TEXTO, True)
        texto(surf, f"Nível {j.nivel} · {j.classe}", (cartao.x + 78, cartao.y + 28), 10, DOURADO, True)

        barra(surf, (cartao.x + 78, cartao.y + 46, 212, 11), j.hp, j.hp_max, (226, 82, 90), (28, 18, 24), (0, 0, 0), f"{int(j.hp)}/{j.hp_max}", 9)
        barra(surf, (cartao.x + 78, cartao.y + 61, 212, 9), j.mp, j.mp_max, (82, 148, 244), (16, 22, 38), (0, 0, 0), f"{int(j.mp)}/{j.mp_max}", 8)
        barra(surf, (cartao.x + 78, cartao.y + 74, 212, 8), j.stamina, j.stamina_max, (238, 200, 92), (36, 30, 18), (0, 0, 0), None, 8)
        cor_fome = (220, 150, 90) if j.fome > 25 else (230, 80, 80)
        texto(surf, "Fome", (cartao.x + 10, cartao.y + 82), 8, TEXTO_FRACO)
        barra(surf, (cartao.x + 78, cartao.y + 86, 212, 6), j.fome, j.fome_max, cor_fome, (34, 26, 20), (0, 0, 0))
        barra(surf, (cartao.x + 78, cartao.y + 100, 212, 4), j.xp, j.xp_proximo, DOURADO, (24, 28, 38), (0, 0, 0))

    def _desenhar_cartao_toque(self, surf: pygame.Surface, j: Any) -> None:
        """Cartão do jogador no celular: barras e textos maiores."""
        cartao = pygame.Rect(12, 10, 340, 124)
        fundo = pygame.Surface(cartao.size, pygame.SRCALPHA)
        pygame.draw.rect(fundo, (10, 14, 22, 182), fundo.get_rect(), border_radius=raio_ui(16))
        pygame.draw.rect(fundo, (196, 164, 98, 120), fundo.get_rect(), width=1, border_radius=raio_ui(16))
        surf.blit(fundo, cartao.topleft)
        cantos_ornamentados(surf, cartao, tamanho=12)

        estado = "morto" if j.morto else "ferido" if j.hp < j.hp_max * 0.3 else "normal"
        retrato_classe(surf, j.classe, (cartao.x + 12, cartao.y + 12, 62, 62), estado=estado, tempo=self.tempo)
        _tinta_dano(surf, (cartao.x + 12, cartao.y + 12, 62, 62), j)
        texto(surf, j.nome, (cartao.x + 88, cartao.y + 8), 20, TEXTO, True)
        texto(surf, f"Nível {j.nivel} · {j.classe}", (cartao.x + 88, cartao.y + 33), 12, DOURADO, True)

        barra(surf, (cartao.x + 88, cartao.y + 54, 240, 16), j.hp, j.hp_max, (226, 82, 90), (28, 18, 24), (0, 0, 0), f"{int(j.hp)}/{int(j.hp_max)}", 11)
        barra(surf, (cartao.x + 88, cartao.y + 74, 240, 11), j.mp, j.mp_max, (82, 148, 244), (16, 22, 38), (0, 0, 0), f"{int(j.mp)}/{int(j.mp_max)}", 9)
        barra(surf, (cartao.x + 88, cartao.y + 89, 240, 9), j.stamina, j.stamina_max, (238, 200, 92), (36, 30, 18), (0, 0, 0), None, 8)
        cor_fome = (220, 150, 90) if j.fome > 25 else (230, 80, 80)
        texto(surf, "Fome", (cartao.x + 12, cartao.y + 90), 10, TEXTO_FRACO)
        barra(surf, (cartao.x + 88, cartao.y + 103, 240, 6), j.fome, j.fome_max, cor_fome, (34, 26, 20), (0, 0, 0))
        barra(surf, (cartao.x + 88, cartao.y + 114, 240, 5), j.xp, j.xp_proximo, DOURADO, (24, 28, 38), (0, 0, 0))

    @staticmethod
    def _desenhar_ouro(surf: pygame.Surface, j: Any, toque: bool) -> None:
        if toque:
            moeda(surf, 1046, 28, 8)
            texto(surf, str(j.ouro), (1060, 18), 17, (246, 204, 92), True)
            return
        moeda(surf, 1070, 34, 8)
        texto(surf, str(j.ouro), (1084, 24), 15, (246, 204, 92), True)

    @staticmethod
    def _tutorial_ativo(jogo: Any) -> Any:
        tutorial = getattr(jogo, "tutorial", None)
        prefs = getattr(jogo, "prefs", None)
        if tutorial is None or tutorial.etapa is None:
            return None
        if prefs is not None and not prefs.dicas_tutorial:
            return None
        return tutorial

    def _desenhar_card_tutorial(self, surf: pygame.Surface, jogo: Any, controle: bool, toque: bool = False) -> None:
        tutorial = self._tutorial_ativo(jogo)
        if tutorial is None:
            return
        etapa = tutorial.etapa
        detalhe = _quebrar_texto(etapa.detalhe, 282, 11)[:2]
        progresso = tutorial.progresso()
        altura = 62 + 15 * len(detalhe) + (9 if progresso is not None else 0)
        r = pygame.Rect(16, 132, 306, altura)
        painel(surf, r, 170, PAINEL, BORDA, 12, 1)
        texto(surf, f"OBJETIVO {tutorial.indice + 1}/{tutorial.total}", (r.x + 14, r.y + 8), 10, DOURADO, True)
        if tutorial.aguardando_confirmacao:
            texto(surf, "Pressione de novo para pular tudo", (r.right - 12, r.y + 8), 10, (240, 190, 110), True, "right")
        else:
            rotulo = "Toque no menu para pausar" if toque else (
                "R3 etapa · → tutorial" if controle else "F2 etapa · F3 tutorial"
            )
            texto(surf, rotulo, (r.right - 12, r.y + 8), 10, TEXTO_FRACO, False, "right")
        texto(surf, etapa.titulo, (r.x + 14, r.y + 22), 15, TEXTO, True)
        texto(surf, tutorial.dica(controle, toque=toque), (r.x + 14, r.y + 43), 12, (250, 226, 150), True)
        y = r.y + 62
        for linha in detalhe:
            texto(surf, linha, (r.x + 14, y), 11, TEXTO_FRACO)
            y += 15
        if progresso is not None:
            barra(surf, (r.x + 14, y + 3, r.w - 28, 4), progresso, 1.0, DOURADO, (24, 28, 38))

    def _desenhar_dica_painel_tutorial(self, surf: pygame.Surface, jogo: Any) -> None:
        tutorial = self._tutorial_ativo(jogo)
        if tutorial is None or not tutorial.etapa.teclado_painel:
            return
        dica = tutorial.dica(_usando_controle(jogo), painel_aberto=True, toque=_modo_toque(jogo))
        texto(surf, f"Objetivo: {tutorial.etapa.titulo} — {dica}", (LARGURA // 2, 692), 13, (250, 226, 150), True, "center")

    def _desenhar_relogio(self, surf: pygame.Surface, jogo: Any) -> None:
        hora = float(getattr(jogo, "hora", 8.0))
        noite = bool(getattr(jogo, "eh_noite", lambda: False)())
        x, y = 956, 22
        cor = (170, 190, 240) if noite else (250, 220, 140)
        pygame.draw.circle(surf, cor, (x, y + 8), 7)
        if noite:
            pygame.draw.circle(surf, (18, 22, 36), (x + 3, y + 6), 6)
        else:
            pygame.draw.circle(surf, (255, 248, 200), (x - 2, y + 5), 2)
        texto(surf, f"{int(hora):02d}:{int((hora % 1) * 60):02d}", (x + 14, y), 14, TEXTO, True)
        texto(surf, "Noite" if noite else "Dia", (x + 14, y + 16), 9, TEXTO_FRACO)

    def _desenhar_hotbar(self, surf: pygame.Surface, j: Any, controle: bool = False, toque: bool = False) -> None:
        slots = 5
        largura_slot = 64
        # Na arte pixel os nomes das habilidades ficam mais largos (fonte de 8 px)
        espaco = 20 if modo_pixel() else 8
        total = slots * largura_slot + (slots - 1) * espaco
        x0 = (LARGURA - total) // 2
        y = 620

        # ataque básico
        arma = CLASSES[j.classe]["arma"]
        icone_tipo = "espada" if arma == "Espada" else "arco" if arma == "Arco" else "cajado"
        r = pygame.Rect(x0, y, largura_slot, largura_slot)
        tecla_ataque = "ATQ" if toque else ("RT" if controle else "LMB")
        self._desenhar_slot_habilidade(surf, r, icone_tipo, tecla_ataque, (220, 220, 230), 0.0, None, True)
        texto(surf, "Ataque", (r.centerx, r.bottom + 6), 8, TEXTO_FRACO, False, "center", largura_max=largura_slot + espaco - 4)

        for i, h in enumerate(j.habilidades):
            r = pygame.Rect(x0 + (i + 1) * (largura_slot + espaco), y, largura_slot, largura_slot)
            restante = j.cooldowns.get(h.id, 0.0)
            fracao = restante / max(0.01, h.cooldown_atual)
            pronto = restante <= 0
            custo = f"{int(h.custo_atual)}"
            cor_custo = (120, 200, 250) if h.custo_tipo == "mp" else (240, 210, 120)
            tecla = BOTOES_HABILIDADE[i] if controle and i < len(BOTOES_HABILIDADE) else h.tecla
            brilho = self._brilho_pronto(h.id, pronto)
            self._desenhar_slot_habilidade(
                surf, r, h.icone, tecla, h.cor, fracao,
                restante if not pronto else None, pronto, custo, cor_custo, brilho,
            )
            texto(surf, h.nome, (r.centerx, r.bottom + 6), 8, TEXTO_FRACO, False, "center", largura_max=largura_slot + espaco - 4)

    def _brilho_pronto(self, chave: str, pronto: bool) -> float:
        """Clarão de 0,45 s quando a habilidade sai do cooldown (só no modo pixel)."""
        anterior = self._pronto_antes.get(chave, True)
        if pronto and not anterior:
            self._pronto_em[chave] = self.tempo
        self._pronto_antes[chave] = pronto
        marca = self._pronto_em.get(chave)
        if marca is None or not modo_pixel():
            return 0.0
        brilho = max(0.0, 1.0 - (self.tempo - marca) / 0.45)
        if brilho <= 0.0:
            self._pronto_em.pop(chave, None)
        return brilho

    def _desenhar_pocoes(self, surf: pygame.Surface, j: Any, controle: bool = False, toque: bool = False) -> None:
        dados = (
            ("vida", "pocao_vida", (232, 82, 96), "HP" if toque else ("LB" if controle else "1"), "Vida"),
            ("mana", "pocao_mana", (82, 148, 244), "MP" if toque else ("◀" if controle else "2"), "Mana"),
            ("stamina", "pocao_stamina", (244, 206, 92), "ST" if toque else ("▼" if controle else "3"), "Fôlego"),
        )
        if toque:
            painel(surf, (1120, 220, 146, 250), 205, PAINEL, BORDA, 16, 2)
        else:
            painel(surf, (1078, 230, 184, 218), 190, PAINEL, BORDA, 14, 1)
        for i, (tipo, icone_tipo, cor, tecla, nome) in enumerate(dados):
            qtd = sum(
                p.quantidade for p in j.inventario
                if isinstance(p, Pocao) and p.tipo == tipo
            )
            if toque:
                r = pygame.Rect(1156, 228 + i * 78, 74, 74)
                raio, margem_icone = 12, 26
                largura_badge, altura_badge = 30, 20
                fonte_badge, fonte_qtd, base_qtd = 11, 14, 22
            else:
                r = pygame.Rect(1176, 238 + i * 70, 62, 62)
                raio, margem_icone = 10, 18
                largura_badge, altura_badge = 26, 16
                fonte_badge, fonte_qtd, base_qtd = 9, 10, 17
            pygame.draw.rect(surf, (16, 20, 28), r, border_radius=raio_ui(raio))
            pygame.draw.rect(surf, cor if qtd else (58, 64, 80), r, width=2 if qtd else 1, border_radius=raio_ui(raio))
            icone(surf, icone_tipo, r.inflate(-margem_icone, -margem_icone), cor if qtd else (86, 90, 104))
            pygame.draw.rect(
                surf, (10, 12, 18),
                (r.x + 4, r.y + 4, largura_badge, altura_badge), border_radius=raio_ui(4),
            )
            texto(surf, tecla, (r.x + 4 + largura_badge / 2, r.y + 4), fonte_badge, DOURADO, True, "center")
            texto(
                surf, f"x{qtd}", (r.right - 6, r.bottom - base_qtd), fonte_qtd,
                BRANCO if qtd else TEXTO_FRACO, True, "right",
            )
            if not toque:
                texto(
                    surf, nome, (r.x - 8, r.y + 24), 12,
                    cor if qtd else TEXTO_FRACO, True, "right",
                )

    def _desenhar_slot_habilidade(
        self, surf: pygame.Surface, r: pygame.Rect, icone_tipo: str, tecla: str,
        cor: Sequence[int], fracao: float, restante: float | None, pronto: bool,
        custo: str | None = None, cor_custo: Sequence[int] = (200, 200, 200),
        brilho: float = 0.0,
    ) -> None:
        pygame.draw.rect(surf, (16, 20, 28), r, border_radius=raio_ui(10))
        pygame.draw.rect(surf, DOURADO if pronto else (58, 64, 80), r, width=2 if pronto else 1, border_radius=raio_ui(10))
        cor_icone = cor if pronto else (90, 94, 108)
        if brilho > 0.0:
            cor_icone = tuple(min(255, int(c + 80 * brilho)) for c in cor_icone)
        icone(surf, icone_tipo, r.inflate(-14, -14), cor_icone, pulso=1.0 + 0.12 * brilho)
        if brilho > 0.0:
            # clarão dourado em volta do slot quando a habilidade fica pronta
            halo = pygame.Surface((r.width + 8, r.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(halo, (250, 226, 150, int(170 * brilho)), halo.get_rect(), 2)
            surf.blit(halo, (r.x - 4, r.y - 4))
        # tecla
        pygame.draw.rect(surf, (10, 12, 18), (r.x + 4, r.y + 4, 20, 17), border_radius=raio_ui(4))
        texto(surf, tecla, (r.x + 14, r.y + 5), 10, DOURADO, True, "center")
        # custo
        if custo is not None:
            texto(surf, custo, (r.right - 5, r.bottom - 16), 10, cor_custo, True, "right")
        # cooldown
        if fracao > 0:
            altura = int(r.height * min(1.0, fracao))
            overlay = pygame.Surface((r.width - 4, altura), pygame.SRCALPHA)
            overlay.fill((4, 6, 10, 190))
            surf.blit(overlay, (r.x + 2, r.y + 2))
            if restante is not None:
                texto(surf, f"{restante:.1f}", r.center, 18, BRANCO, True, "center_all")

    def _desenhar_minimapa(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        m = jogo.mundo
        painel(surf, (1078, 18, 184, 202), 190, PAINEL, BORDA, 14, 1)
        area = pygame.Rect(1090, 30, 160, 120)
        pygame.draw.rect(surf, (10, 14, 22), area, border_radius=raio_ui(6))
        escala = min(area.w / m.largura, area.h / m.altura)
        desloc_x = area.x + (area.w - m.largura * escala) / 2
        desloc_y = area.y + (area.h - m.altura * escala) / 2

        def ponto(x: float, y: float) -> tuple[int, int]:
            return (int(desloc_x + x * escala), int(desloc_y + y * escala))

        for z in reversed(m.zonas):
            r = pygame.Rect(
                desloc_x + z.rect.x * escala, desloc_y + z.rect.y * escala,
                z.rect.w * escala, z.rect.h * escala,
            )
            pygame.draw.rect(surf, z.cor, r)
        vr = pygame.Rect(
            desloc_x + m.vila.rect.x * escala, desloc_y + m.vila.rect.y * escala,
            m.vila.rect.w * escala, m.vila.rect.h * escala,
        )
        pygame.draw.rect(surf, (120, 210, 140), vr)
        vv = pygame.Rect(
            desloc_x + m.vila_veyra.rect.x * escala, desloc_y + m.vila_veyra.rect.y * escala,
            m.vila_veyra.rect.w * escala, m.vila_veyra.rect.h * escala,
        )
        pygame.draw.rect(surf, (196, 158, 108), vv)
        pygame.draw.rect(surf, (40, 48, 62), area, width=1, border_radius=raio_ui(6))

        for inimigo in jogo.inimigos:
            if not inimigo.vivo:
                continue
            px, py = ponto(inimigo.x, inimigo.y)
            if inimigo.boss:
                pygame.draw.circle(surf, (250, 160, 80), (px, py), 4)
                pygame.draw.circle(surf, (255, 220, 150), (px, py), 2)
            else:
                pygame.draw.circle(surf, (232, 92, 96), (px, py), 2)
        for drop in getattr(jogo, "drops", []):
            if not drop.vivo or drop.tipo not in ("bau", "santuario"):
                continue
            px, py = ponto(drop.x, drop.y)
            cor = (250, 214, 130) if drop.tipo == "bau" else (150, 230, 255)
            pygame.draw.circle(surf, cor, (px, py), 3)
            pygame.draw.circle(surf, (255, 255, 255), (px, py), 1)
        px, py = ponto(j.x, j.y)
        pygame.draw.circle(surf, (10, 12, 18), (px, py), 5)
        pygame.draw.circle(surf, (120, 240, 240), (px, py), 3)

        texto(surf, j.zona, (1170, 158), 13, DOURADO, True, "center")
        texto(surf, f"Abates: {j.kills}", (1090, 180), 11, TEXTO_FRACO)
        texto(surf, f"Bosses: {j.bosses}", (1160, 180), 11, TEXTO_FRACO)
        status = jogo.status_boss(jogo.mundo.zona_em(j.x, j.y))
        if status:
            cor_status = (250, 150, 120) if status == "Boss ativo" else (200, 190, 150)
            texto(surf, status, (1170, 200), 11, cor_status, True, "center")

    def _desenhar_notificacoes(self, surf: pygame.Surface) -> None:
        for i, n in enumerate(self.notificacoes):
            alpha = int(255 * min(1.0, n["tempo"] / 0.6))
            largura = max(220, fonte(15).size(n["texto"])[0] + 36)
            x = (LARGURA - largura) // 2
            y = 24 + i * 36
            temp = pygame.Surface((largura, 28), pygame.SRCALPHA)
            pygame.draw.rect(temp, (10, 14, 20, min(220, alpha)), temp.get_rect(), border_radius=raio_ui(8))
            pygame.draw.rect(temp, (*n["cor"], min(180, alpha)), temp.get_rect(), width=1, border_radius=raio_ui(8))
            surf.blit(temp, (x, y))
            cor = tuple(int(c * (0.6 + 0.4 * alpha / 255)) for c in n["cor"])
            texto(surf, n["texto"], (LARGURA // 2, y + 5), 15, cor, True, "center")

    def _desenhar_avisos(self, surf: pygame.Surface, jogo: Any) -> None:
        if jogo.boss_alerta > 0 and jogo.boss_nome:
            pulso = 0.65 + 0.35 * math.sin(self.tempo * 6)
            cor = (250, int(80 + 60 * pulso), int(70 + 30 * pulso))
            texto_contornado(surf, f"⚠  {jogo.boss_nome} despertou!  ⚠", (LARGURA // 2, 92), 26, cor)
            texto(surf, "Um boss raro apareceu. Derrote-o para um loot lendário.", (LARGURA // 2, 128), 14, (240, 200, 180), False, "center")
        if jogo.zona_banner[1] > 0:
            nome = jogo.zona_banner[0]
            alpha = int(255 * min(1.0, jogo.zona_banner[1] / 0.8))
            cor = tuple(int(c * (0.5 + 0.5 * alpha / 255)) for c in DOURADO)
            y_banner = 214 if (jogo.boss_ativo is not None or jogo.boss_alerta > 0) else 160
            texto_contornado(surf, nome, (LARGURA // 2, y_banner), 22, cor)

    def _desenhar_dicas(self, surf: pygame.Surface, controle: bool = False, toque: bool = False) -> None:
        if toque:
            return
        if controle:
            esquerda = "Analógico mover · L3 correr · A/RT atacar · X/Y/B/RB habilidades"
            direita = "LT esquivar · ▲ falar · ◀/▼ poções · LB vida · Back/Start"
        else:
            esquerda = "WASD mover · Shift correr · Mouse atacar · Q/E/R/F habilidades"
            direita = "V esquivar · T falar · 1/2/3 poções · F1 config · I/ESC menus"
        texto(surf, esquerda, (20, 690), 11, TEXTO_FRACO)
        texto(surf, direita, (1260, 690), 11, TEXTO_FRACO, False, "right")

    def _desenhar_missao(self, surf: pygame.Surface, jogo: Any) -> None:
        quests = getattr(jogo, "quests", None)
        if quests is None:
            return
        toque = bool(getattr(jogo, "modo_toque", False))
        if toque:
            r = pygame.Rect(12, 142, 340, 66)
            fonte_rotulo, fonte_nome, fonte_progresso = 10, 15, 12
        else:
            r = pygame.Rect(16, 552, 306, 66)
            fonte_rotulo, fonte_nome, fonte_progresso = 10, 14, 11
        painel(surf, r, 185, PAINEL, BORDA, 12, 1)
        texto(surf, "MISSÃO", (r.x + 14, r.y + 6), fonte_rotulo, DOURADO, True)
        missao = quests.atual
        if missao is None:
            texto(surf, "Todas as missões concluídas", (r.x + 14, r.y + 24), 13, VERDE, True)
            return
        texto(surf, str(missao["nome"]), (r.x + 14, r.y + 20), fonte_nome, TEXTO, True)
        texto(surf, quests.texto_progresso(), (r.x + 14, r.y + 40), fonte_progresso, TEXTO_FRACO)
        if quests.completa:
            barra(surf, (r.x + 14, r.y + 56, r.w - 28, 4), 1.0, 1.0, DOURADO, (24, 28, 38))
        else:
            total = max(1, int(missao["quantidade"]))
            barra(surf, (r.x + 14, r.y + 56, r.w - 28, 4), quests.progresso, total, VERDE, (24, 28, 38))

    def _desenhar_dialogo(self, surf: pygame.Surface, jogo: Any) -> None:
        linhas = getattr(jogo, "dialogo", None)
        if not linhas:
            return
        r = pygame.Rect(300, 482, 680, 118)
        painel(surf, r, 238, PAINEL, BORDA, 16, 2)
        cantos_ornamentados(surf, r, tamanho=14)
        texto(surf, "Mestre Aldrin", (r.x + 22, r.y + 10), 15, DOURADO, True)
        texto(surf, "Cronista de Lumen", (r.right - 22, r.y + 11), 10, TEXTO_FRACO, False, "right")
        y = r.y + 38
        for linha in linhas[:3]:
            for parte in _quebrar_texto(str(linha), r.w - 44, 14)[:2]:
                texto(surf, parte, (r.x + 22, y), 14, TEXTO)
                y += 19
        tecla = "▲" if getattr(jogo, "entrada", None) is not None and jogo.entrada.usando_controle else "T"
        texto(surf, f"{tecla} para conversar de novo", (r.right - 22, r.bottom - 20), 10, TEXTO_FRACO, False, "right")

    # ------------------------------------------------------------------ menu
    def desenhar_menu(self, surf: pygame.Surface, jogo: Any, tem_save: bool) -> None:
        self.botoes_menu.clear()
        surf.blit(self.fundo_menu, (0, 0))
        self._desenhar_estrelas(surf)
        self._desenhar_cristais_decorativos(surf)
        texto_contornado(surf, "Cristais de Aether", (LARGURA // 2, 118), 62, (246, 210, 130))
        texto(surf, "Um RPG de ação, progressão e cristais", (LARGURA // 2, 206), 19, (190, 198, 220), False, "center")
        pygame.draw.line(surf, (120, 100, 70), (LARGURA // 2 - 220, 238), (LARGURA // 2 + 220, 238), 1)

        y = 292
        self._botao_menu(surf, (LARGURA // 2 - 150, y, 300, 54), "Novo Jogo", "novo")
        self._botao_menu(surf, (LARGURA // 2 - 150, y + 68, 300, 54), "Continuar", "continuar", ativo=tem_save)
        self._botao_menu(surf, (LARGURA // 2 - 150, y + 136, 300, 54), "Configurações", "configuracoes")
        self._botao_menu(surf, (LARGURA // 2 - 150, y + 204, 300, 54), "Sair", "sair")

        texto(surf, f"Versão {VERSAO} · vertical slice", (LARGURA - 20, ALTURA - 28), 12, (110, 118, 136), False, "right")
        texto(surf, "Dica: cristais encaixados em equipamentos mudam sua build.", (LARGURA // 2, ALTURA - 48), 13, (140, 148, 168), False, "center")
        texto(surf, "Achou um bug? Anote o que aconteceu e a versão no canto.", (LARGURA // 2, ALTURA - 70), 12, (120, 128, 148), False, "center")

    def _botao_menu(
        self,
        surf: pygame.Surface,
        r: pygame.Rect | Sequence[int],
        rotulo: str,
        acao: str,
        ativo: bool = True,
        destino: list[tuple[pygame.Rect, str]] | None = None,
        registrar: bool = True,
    ) -> None:
        r = pygame.Rect(r)
        hover = r.collidepoint(pygame.mouse.get_pos()) and ativo
        cor_fundo = (42, 36, 30) if hover else (22, 26, 36)
        cor_borda = DOURADO if hover else (96, 88, 70)
        if not ativo:
            cor_fundo = (18, 20, 28)
            cor_borda = (50, 54, 64)
        pygame.draw.rect(surf, cor_fundo, r, border_radius=raio_ui(12))
        pygame.draw.rect(surf, cor_borda, r, width=2 if hover else 1, border_radius=raio_ui(12))
        if hover:
            brilho = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(brilho, (250, 210, 120, 18), brilho.get_rect(), border_radius=raio_ui(12))
            surf.blit(brilho, r.topleft)
        texto(surf, rotulo, r.center, 20, DOURADO if ativo else (80, 86, 100), True, "center_all")
        if ativo and registrar:
            (destino if destino is not None else self.botoes_menu).append((r, acao))

    def _desenhar_estrelas(self, surf: pygame.Surface) -> None:
        for x, y, brilho in self.estrelas:
            a = 0.35 + 0.35 * math.sin(self.tempo * 1.5 + x * 0.02)
            cor = tuple(int(180 * a) for _ in range(3))
            pygame.draw.circle(surf, cor, (x, y), max(1, int(brilho)))

    def _desenhar_cristais_decorativos(self, surf: pygame.Surface) -> None:
        for i, (x, y, cor, escala) in enumerate((
            (150, 180, (120, 200, 240), 1.0),
            (1100, 240, (190, 120, 240), 0.8),
            (220, 560, (100, 220, 200), 0.7),
            (1040, 560, (240, 180, 90), 0.9),
            (640, 640, (180, 120, 240), 0.5),
        )):
            flut = math.sin(self.tempo * 1.2 + i) * 8
            self._cristal_decorativo(surf, x, y + flut, cor, escala)

    def _cristal_decorativo(self, surf: pygame.Surface, x: float, y: float, cor: Sequence[int], e: float) -> None:
        tamanho = max(8, int(140 * e))
        halo = _halo_colorido(cor, tamanho)
        surf.blit(halo, (int(x - tamanho / 2), int(y - tamanho / 2)))
        pts = [(x, y - 46 * e), (x + 18 * e, y - 8 * e), (x, y + 38 * e), (x - 18 * e, y - 8 * e)]
        pygame.draw.polygon(surf, tuple(max(0, c - 50) for c in cor), pts)
        pygame.draw.polygon(surf, cor, [(x, y - 42 * e), (x + 14 * e, y - 8 * e), (x, y + 32 * e), (x - 14 * e, y - 8 * e)])
        pygame.draw.line(surf, (255, 255, 255), (x, y - 38 * e), (x - 6 * e, y - 4 * e), max(1, int(2 * e)))

    # ------------------------------------------------------------------ seleção
    def desenhar_selecao(self, surf: pygame.Surface, jogo: Any) -> None:
        self.cartoes_classe.clear()
        self.botao_voltar = None
        surf.blit(self.fundo_menu, (0, 0))
        self._desenhar_estrelas(surf)
        texto_contornado(surf, "Escolha seu Guardião", (LARGURA // 2, 44), 40, (246, 210, 130))
        texto(surf, "Cada classe tem uma build, recursos e habilidades próprios.", (LARGURA // 2, 100), 16, (180, 188, 210), False, "center")

        for i, (classe, dados) in enumerate(CLASSES.items()):
            x = 120 + i * 360
            r = pygame.Rect(x, 138, 320, 492)
            hover = r.collidepoint(pygame.mouse.get_pos())
            if hover:
                r.y -= 4
            pygame.draw.rect(surf, (18, 22, 32) if not hover else (28, 32, 44), r, border_radius=raio_ui(16))
            pygame.draw.rect(surf, dados["cor"] if hover else (64, 70, 86), r, width=3 if hover else 1, border_radius=raio_ui(16))
            # faixa
            faixa = pygame.Rect(r.x, r.y, r.w, 8)
            pygame.draw.rect(
                surf, dados["cor"], faixa,
                border_top_left_radius=raio_ui(16), border_top_right_radius=raio_ui(16),
            )
            retrato_classe(surf, classe, (r.centerx - 48, r.y + 26, 96, 96), estado="normal", tempo=self.tempo)
            texto(surf, classe, (r.centerx, r.y + 134), 26, TEXTO, True, "center")
            for n, linha in enumerate(_quebrar_texto(dados["descricao"], r.w - 44, 12)[:2]):
                texto(surf, linha, (r.centerx, r.y + 164 + n * 16), 12, TEXTO_FRACO, False, "center")
            # stats
            stats = [
                ("Vida", dados["hp"]), ("Mana", dados["mp"]), ("Stamina", dados["stamina"]),
                ("Ataque", dados["ataque"]), ("Defesa", dados["defesa"]),
                ("Crítico", f"{dados['critico']}%"), ("Velocidade", dados["velocidade"]),
            ]
            for n, (nome, valor) in enumerate(stats):
                col = n % 2
                lin = n // 2
                sx = r.x + 26 + col * 146
                sy = r.y + 210 + lin * 28
                texto(surf, nome, (sx, sy), 12, TEXTO_FRACO)
                texto(surf, str(valor), (sx + 128, sy), 12, (230, 220, 190), True, "right")
            pygame.draw.line(surf, (50, 56, 72), (r.x + 24, r.y + 330), (r.right - 24, r.y + 330), 1)
            texto(surf, "Habilidades", (r.x + 26, r.y + 344), 14, DOURADO, True)
            for n, linha in enumerate(resumo_classe(classe)):
                texto(surf, linha, (r.x + 26, r.y + 370 + n * 23), 13, (200, 208, 224))
            texto(surf, "Clique para escolher", (r.centerx, r.bottom - 18), 12, dados["cor"], True, "center")
            self.cartoes_classe.append((pygame.Rect(x, 138, 320, 492), classe))

        self.botao_voltar = pygame.Rect(40, ALTURA - 60, 120, 40)
        self._botao_menu(surf, self.botao_voltar, "Voltar", "voltar", registrar=False)

    # ------------------------------------------------------------------ pausa
    def desenhar_pausa(self, surf: pygame.Surface, jogo: Any) -> None:
        self.botoes_pausa.clear()
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((4, 6, 10, 190))
        surf.blit(overlay, (0, 0))
        painel(surf, (410, 118, 460, 496), 245, PAINEL, BORDA, 18, 2)
        cantos_ornamentados(surf, (410, 118, 460, 496))
        texto_contornado(surf, "Pausado", (LARGURA // 2, 158), 34, (246, 210, 130))
        y = 220
        self._botao_menu(surf, (490, y, 300, 48), "Continuar", "continuar", destino=self.botoes_pausa)
        self._botao_menu(surf, (490, y + 58, 300, 48), "Salvar", "salvar", destino=self.botoes_pausa)
        self._botao_menu(surf, (490, y + 116, 300, 48), "Configurações", "configuracoes", destino=self.botoes_pausa)
        self._botao_menu(surf, (490, y + 174, 300, 48), "Menu Principal", "menu", destino=self.botoes_pausa)
        texto(surf, "Controles", (LARGURA // 2, 466), 15, DOURADO, True, "center")
        if _usando_controle(jogo):
            linhas = (
                "Analógico mover · L3/LT correr",
                "A/RT atacar · X/Y/B habilidades · LB poção",
                "Back inventário · Start pausa",
            )
        else:
            linhas = (
                "WASD mover · Shift correr",
                "Mouse atacar · Q/E/R habilidades",
                "F1 configurações · ESC pausa",
            )
        for i, linha in enumerate(linhas):
            texto(surf, linha, (LARGURA // 2, 492 + i * 22), 13, TEXTO_FRACO, False, "center")

        # resumo da sessão: o playtester pode fotografar para reportar feedback
        j = jogo.jogador
        minutos = int(getattr(jogo, "tempo", 0.0) // 60)
        abates = f"{j.kills} abate" + ("" if j.kills == 1 else "s")
        bosses = f"{j.bosses} boss" + ("" if j.bosses == 1 else "es")
        resumo = f"Sessão: {minutos} min · {abates} · {bosses} · v{VERSAO}"
        texto(surf, resumo, (LARGURA // 2, 552), 12, (150, 158, 178), False, "center")
        texto(surf, "Bug? Anote o que aconteceu e a versão.", (LARGURA // 2, 576), 11, (128, 136, 156), False, "center")

    # ------------------------------------------------------------------ morte
    def desenhar_morte(self, surf: pygame.Surface, jogo: Any) -> None:
        self.botoes_morte.clear()
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((20, 4, 8, 190))
        surf.blit(overlay, (0, 0))
        painel(surf, (400, 190, 480, 340), 245, (30, 16, 22), (160, 70, 70), 18, 2)
        cantos_ornamentados(surf, (400, 190, 480, 340), (200, 90, 90))
        texto_contornado(surf, "Você caiu", (LARGURA // 2, 220), 42, (240, 100, 100))
        texto(surf, "A Clareira de Lumen ainda precisa de você.", (LARGURA // 2, 280), 15, (220, 180, 180), False, "center")
        j = jogo.jogador
        texto(surf, f"Nível {j.nivel} · {j.kills} abates · {j.bosses} bosses", (LARGURA // 2, 312), 13, TEXTO_FRACO, False, "center")
        self._botao_menu(surf, (LARGURA // 2 - 150, 360, 300, 50), "Renascer na Clareira", "renascer", destino=self.botoes_morte)
        self._botao_menu(surf, (LARGURA // 2 - 150, 424, 300, 42), "Menu Principal", "menu", destino=self.botoes_morte)
        texto(surf, "Você mantém nível, itens e ouro.", (LARGURA // 2, 490), 12, (170, 150, 150), False, "center")

    # ------------------------------------------------------------------ vitória
    def desenhar_vitoria(self, surf: pygame.Surface, jogo: Any) -> None:
        self.botoes_vitoria.clear()
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((18, 12, 4, 200))
        surf.blit(overlay, (0, 0))
        # raios suaves ao fundo
        raios = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        for i in range(14):
            a = i * math.tau / 14 + self.tempo * 0.1
            x2 = LARGURA // 2 + math.cos(a) * 800
            y2 = ALTURA // 2 + math.sin(a) * 800
            pygame.draw.line(raios, (250, 210, 120, 16), (LARGURA // 2, ALTURA // 2), (x2, y2), 2)
        surf.blit(raios, (0, 0))
        painel(surf, (360, 130, 560, 460), 245, (28, 24, 16), DOURADO, 18, 2)
        cantos_ornamentados(surf, (360, 130, 560, 460))
        final = bool(getattr(jogo, "final_derrotado", False))
        if final:
            texto_contornado(surf, "O Avatar de Aether", (LARGURA // 2, 160), 32, (250, 220, 140))
            texto_contornado(surf, "foi derrotado", (LARGURA // 2, 198), 24, (250, 220, 140))
            texto(surf, "A fonte dos cristais está livre. O ciclo terminou.", (LARGURA // 2, 248), 14, (230, 210, 170), False, "center")
        else:
            texto_contornado(surf, "O Coração de Aether", (LARGURA // 2, 160), 34, (250, 220, 140))
            texto_contornado(surf, "foi restaurado", (LARGURA // 2, 200), 26, (250, 220, 140))
            texto(surf, "A luz voltou a pulsar sob as ruínas.", (LARGURA // 2, 250), 15, (230, 210, 170), False, "center")
        j = jogo.jogador
        linhas = [
            f"Nível final: {j.nivel}",
            f"Abates: {j.kills}",
            f"Bosses derrotados: {j.bosses}",
            f"Ouro: {j.ouro}",
        ]
        for i, linha in enumerate(linhas):
            texto(surf, linha, (LARGURA // 2, 292 + i * 28), 15, (230, 220, 200), False, "center")
        if final:
            texto(
                surf, "Recompensa: Núcleo de Aether V + 5.000 ouro",
                (LARGURA // 2, 404), 13, DOURADO, True, "center",
            )
        self._botao_menu(surf, (LARGURA // 2 - 160, 430, 320, 50), "Continuar explorando", "continuar", destino=self.botoes_vitoria)
        self._botao_menu(surf, (LARGURA // 2 - 160, 494, 320, 42), "Menu Principal", "menu", destino=self.botoes_vitoria)

    # ------------------------------------------------------------------ painel
    def desenhar_painel(self, surf: pygame.Surface, jogo: Any) -> None:
        self.painel.desenhar(surf, jogo)
        self._desenhar_dica_painel_tutorial(surf, jogo)

    # ------------------------------------------------------------------ cliques
    def clique_menu(self, pos: tuple[int, int]) -> str | None:
        for r, acao in self.botoes_menu:
            if r.collidepoint(pos):
                return acao
        return None

    def clique_selecao(self, pos: tuple[int, int]) -> str | None:
        for r, classe in self.cartoes_classe:
            if r.collidepoint(pos):
                return classe
        if self.botao_voltar and self.botao_voltar.collidepoint(pos):
            return "voltar"
        return None

    def clique_pausa(self, pos: tuple[int, int]) -> str | None:
        for r, acao in self.botoes_pausa:
            if r.collidepoint(pos):
                return acao
        return None

    def clique_morte(self, pos: tuple[int, int]) -> str | None:
        for r, acao in self.botoes_morte:
            if r.collidepoint(pos):
                return acao
        return None

    def clique_vitoria(self, pos: tuple[int, int]) -> str | None:
        for r, acao in self.botoes_vitoria:
            if r.collidepoint(pos):
                return acao
        return None
