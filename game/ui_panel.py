"""Painel de personagem: equipamentos, inventário, cristais e habilidades."""
from __future__ import annotations

import math
from typing import Any

import pygame

from items import Cristal, Equipamento, Pocao, SLOTS, STAT_NOMES, preco_venda
from player import ATRIBUTOS
from settings import (
    ALTURA, AMARELO, BORDA, BRANCO, CRISTAIS_FORJA, CUSTO_FORJA, DOURADO,
    LARGURA, PAINEL, PAINEL_CLARO, TEXTO, TEXTO_FRACO, VERDE, VERMELHO,
)
from ui_icons import cor_raridade, icone, moeda
from utils import barra, cantos_ornamentados, fonte, modo_pixel, painel, raio_ui, texto

ABAS_BASE = ("Equipamentos", "Inventário", "Cristais", "Habilidades")
ABAS_SERVICOS = ("Mercado", "Forja", "Encantamentos")
ABAS = ABAS_BASE + ABAS_SERVICOS

ORDEM_STATS = ("ataque", "defesa", "hp_max", "mp_max", "critico", "velocidade", "regen_hp", "regen_mp")
PESO_PODER = {"ataque": 3.0, "defesa": 2.0, "hp_max": 0.35, "mp_max": 0.15, "critico": 2.0}


def fmt_valor(stat: str, valor: float) -> str:
    """Formata um valor de atributo com a unidade certa."""
    if stat == "critico":
        return f"{valor:.1f}%"
    if stat in ("regen_hp", "regen_mp"):
        return f"{valor:.1f}/s"
    return f"{valor:.0f}"


def poder_do_item(item: Any) -> float:
    """Estimativa de poder de um equipamento, na mesma escala do painel."""
    if not isinstance(item, Equipamento):
        return 0.0
    stats = item.stats_totais()
    return sum(stats.get(stat, 0.0) * peso for stat, peso in PESO_PODER.items())



def _truncar(txt: str, largura: int, tamanho: int = 14, negrito: bool = True) -> str:
    """Corta um texto com reticências para caber na largura em pixels."""
    f = fonte(tamanho, negrito)
    if f.size(txt)[0] <= largura:
        return txt
    sufixo = "…"
    while txt and f.size(txt + sufixo)[0] > largura:
        txt = txt[:-1]
    return txt.rstrip() + sufixo

ICONE_SLOT = {
    "Arma": "espada",
    "Armadura": "armadura",
    "Anel": "anel",
    "Amuleto": "amuleto",
}


class Painel:
    def __init__(self) -> None:
        self.aba = "Equipamentos"
        self.abas_rects: list[tuple[pygame.Rect, str]] = []
        self.abas_visiveis: list[str] = list(ABAS_BASE)
        self.slots_eq: list[tuple[pygame.Rect, str]] = []
        self.slots_inv: list[tuple[pygame.Rect, int]] = []
        self.botoes_attr: list[tuple[pygame.Rect, str]] = []
        self.botoes_hab: list[tuple[pygame.Rect, str]] = []
        self.cristais_rects: list[tuple[pygame.Rect, int]] = []
        self.sockets_rects: list[tuple[pygame.Rect, str, int]] = []
        self.botoes_venda: list[tuple[pygame.Rect, int]] = []
        self.botoes_venda_comuns: list[pygame.Rect] = []
        self.botoes_mercado: list[tuple[pygame.Rect, str]] = []
        self.botoes_forja: list[tuple[pygame.Rect, tuple[str, str]]] = []
        self.botoes_encanto: list[tuple[pygame.Rect, str]] = []
        self.botoes_respec: list[pygame.Rect] = []
        self.botoes_fusao: list[pygame.Rect] = []
        self.selecionado_cristal: int | None = None
        self.item_selecionado: int | None = None
        self.tooltip: list[tuple[str, tuple[int, int, int]]] = []
        self.tooltip_pos = (0, 0)
        self.item_foco: Any = None
        self.rect_painel = pygame.Rect(80, 40, 1120, 640)

    # ------------------------------------------------------------------ desenho
    def abas_disponiveis(self, jogo: Any) -> list[str]:
        """Abas base + serviços já descobertos, e só dentro da Vila de Veyra."""
        abas = list(ABAS_BASE)
        na_vila = getattr(jogo, "na_vila_veyra", lambda: False)()
        if na_vila:
            desbloqueados = getattr(jogo, "servicos_desbloqueados", set())
            for servico in ABAS_SERVICOS:
                if servico in desbloqueados:
                    abas.append(servico)
        return abas

    def desenhar(self, surf: pygame.Surface, jogo: Any) -> None:
        abas = self.abas_disponiveis(jogo)
        self.abas_visiveis = abas
        if self.aba not in abas:
            self.aba = "Equipamentos"
        self.abas_rects.clear()
        self.slots_eq.clear()
        self.slots_inv.clear()
        self.botoes_attr.clear()
        self.botoes_hab.clear()
        self.cristais_rects.clear()
        self.sockets_rects.clear()
        self.botoes_venda.clear()
        self.botoes_venda_comuns.clear()
        self.botoes_mercado.clear()
        self.botoes_forja.clear()
        self.botoes_encanto.clear()
        self.botoes_respec.clear()
        self.botoes_fusao.clear()
        self.tooltip.clear()
        self.item_foco = None

        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((4, 6, 10, 200))
        surf.blit(overlay, (0, 0))
        painel(surf, self.rect_painel, 248, PAINEL, BORDA, 18, 2)
        cantos_ornamentados(surf, self.rect_painel)

        texto(surf, "Personagem", (110, 58), 30, DOURADO, True, "left")
        texto(surf, "I / ESC para fechar", (1160, 70), 14, TEXTO_FRACO, False, "right")

        x = 110
        largura_aba = 170 if len(abas) <= 5 else 140
        passo_aba = 178 if len(abas) <= 5 else 146
        for nome in abas:
            r = pygame.Rect(x, 96, largura_aba, 38)
            ativo = self.aba == nome
            pygame.draw.rect(surf, PAINEL_CLARO if ativo else (20, 24, 34), r, border_radius=raio_ui(10))
            pygame.draw.rect(surf, DOURADO if ativo else (56, 64, 82), r, width=2 if ativo else 1, border_radius=raio_ui(10))
            texto(surf, nome, (r.centerx, r.centery - 9), 14 if len(abas) > 5 else 15, DOURADO if ativo else TEXTO_FRACO, ativo, "center")
            if nome == "Equipamentos" and jogo.jogador.pontos_status > 0:
                pygame.draw.circle(surf, DOURADO, (r.right - 10, r.y + 10), 4)
            elif nome == "Habilidades" and jogo.jogador.pontos_habilidade > 0:
                pygame.draw.circle(surf, DOURADO, (r.right - 10, r.y + 10), 4)
            self.abas_rects.append((r, nome))
            x += passo_aba

        if self.aba == "Equipamentos":
            self._desenhar_equipamentos(surf, jogo)
        elif self.aba == "Inventário":
            self._desenhar_inventario(surf, jogo)
        elif self.aba == "Cristais":
            self._desenhar_cristais(surf, jogo)
        elif self.aba == "Mercado":
            self._desenhar_mercado(surf, jogo)
        elif self.aba == "Forja":
            self._desenhar_forja(surf, jogo)
        elif self.aba == "Encantamentos":
            self._desenhar_encantamentos(surf, jogo)
        else:
            self._desenhar_habilidades(surf, jogo)

        if self.tooltip:
            self._desenhar_tooltip(surf)

    # ------------------------------------------------------------------ equipamentos
    def _desenhar_equipamentos(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        texto(surf, "Equipamentos", (120, 154), 18, TEXTO, True)
        for i, slot in enumerate(SLOTS):
            r = pygame.Rect(120, 180 + i * 88, 76, 76)
            eq = j.equipamentos.get(slot)
            self._desenhar_slot(surf, r, eq, ICONE_SLOT[slot])
            texto(surf, slot, (208, 200 + i * 88), 16, TEXTO, True)
            if eq:
                texto(surf, _truncar(eq.nome, 112, 13), (208, 220 + i * 88), 13, cor_raridade(eq.raridade))
                texto(surf, f"Nível {eq.nivel} · {eq.raridade}", (208, 238 + i * 88), 12, TEXTO_FRACO)
            else:
                texto(surf, "Vazio", (208, 220 + i * 88), 13, TEXTO_FRACO)
            self.slots_eq.append((r, slot))

        # atributos de combate
        painel(surf, (330, 176, 330, 402), 180, PAINEL_CLARO, (54, 62, 80), 12, 1)
        texto(surf, "Atributos de combate", (350, 190), 18, DOURADO, True)
        s = j.stats_totais()
        linhas = [
            ("Vida", f"{int(j.hp)} / {j.hp_max}", (232, 92, 96)),
            ("Mana", f"{int(j.mp)} / {j.mp_max}", (92, 156, 244)),
            ("Stamina", f"{int(j.stamina)} / {j.stamina_max}", (232, 200, 92)),
            ("Ataque", f"{s['ataque']:.1f}", (240, 220, 180)),
            ("Defesa", f"{s['defesa']:.1f}", (170, 210, 240)),
            ("Crítico", f"{s['critico']:.1f}%", (244, 206, 120)),
            ("Velocidade", f"{s['velocidade']:.0f}", (180, 240, 190)),
            ("Regen. vida", f"{s['regen_hp']:.1f}/s", (232, 140, 150)),
            ("Regen. mana", f"{s['regen_mp']:.1f}/s", (140, 180, 250)),
        ]
        for i, (nome, valor, cor) in enumerate(linhas):
            y = 226 + i * 34
            texto(surf, nome, (350, y), 15, TEXTO_FRACO)
            texto(surf, valor, (640, y), 15, cor, True, "right")
            if i < len(linhas) - 1:
                pygame.draw.line(surf, (44, 50, 64), (350, y + 26), (640, y + 26), 1)

        # atributos distribuíveis
        painel(surf, (680, 176, 280, 402), 180, PAINEL_CLARO, (54, 62, 80), 12, 1)
        texto(surf, "Atributos", (700, 190), 18, DOURADO, True)
        texto(surf, f"Pontos: {j.pontos_status}", (940, 194), 14, VERDE if j.pontos_status else TEXTO_FRACO, True, "right")
        for i, (chave, (nome, desc)) in enumerate(ATRIBUTOS.items()):
            y = 232 + i * 62
            texto(surf, nome, (700, y), 16, TEXTO, True)
            texto(surf, desc, (700, y + 20), 12, TEXTO_FRACO)
            texto(surf, str(j.atributos[chave]), (858, y + 4), 20, DOURADO, True, "right")
            r = pygame.Rect(880, y, 56, 34)
            ativo = j.pontos_status > 0
            pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), r, border_radius=raio_ui(8))
            pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), r, width=1, border_radius=raio_ui(8))
            texto(surf, "+", (r.centerx, r.centery - 12), 20, VERDE if ativo else (80, 86, 100), True, "center")
            if ativo:
                self.botoes_attr.append((r, chave))

        total_atributos = sum(j.atributos.values())
        custo_respec = jogo.custo_respec()
        br = pygame.Rect(700, 522, 240, 36)
        ativo = total_atributos > 0 and j.ouro >= custo_respec
        pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), br, border_radius=raio_ui(8))
        pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), br, width=1, border_radius=raio_ui(8))
        texto(
            surf, f"Redistribuir ({custo_respec}g)",
            (br.centerx, br.centery - 9), 13,
            VERDE if ativo else (90, 96, 110), True, "center",
        )
        if total_atributos > 0:
            self.botoes_respec.append(br)

        # resumo
        painel(surf, (980, 176, 200, 402), 180, PAINEL_CLARO, (54, 62, 80), 12, 1)
        texto(surf, "Poder", (1000, 190), 18, DOURADO, True)
        poder = int(s["ataque"] * 3 + s["defesa"] * 2 + j.hp_max * 0.35 + j.mp_max * 0.15 + s["critico"] * 2)
        texto(surf, str(poder), (1080, 222), 34, (250, 226, 150), True, "center")
        texto(surf, "Total", (1080, 260), 12, TEXTO_FRACO, False, "center")
        pygame.draw.line(surf, (54, 62, 80), (1000, 286), (1160, 286), 1)
        texto(surf, f"Ouro: {j.ouro}", (1000, 302), 14, (246, 204, 92), True)
        texto(surf, f"Nível: {j.nivel}", (1000, 326), 14, TEXTO_FRACO)
        texto(surf, f"XP: {j.xp}/{j.xp_proximo}", (1000, 348), 12, TEXTO_FRACO)
        barra(surf, (1000, 368, 160, 8), j.xp, j.xp_proximo, DOURADO, (24, 28, 38))
        faltam = max(0, j.xp_proximo - j.xp)
        texto(surf, f"Faltam {faltam} XP", (1000, 382), 12, DOURADO if faltam else VERDE)
        texto(surf, "Próximo nível:", (1000, 404), 12, TEXTO_FRACO)
        texto(surf, "+3 status, +1 habilidade", (1000, 420), 11, TEXTO_FRACO)
        texto(surf, f"Abates: {j.kills}  Bosses: {j.bosses}", (1000, 446), 12, TEXTO_FRACO)
        texto(surf, "Clique no equipamento", (1000, 476), 12, TEXTO_FRACO)
        texto(surf, "para desequipar.", (1000, 492), 12, TEXTO_FRACO)
        texto(surf, "Use o inventário", (1000, 516), 12, TEXTO_FRACO)
        texto(surf, "para equipar.", (1000, 532), 12, TEXTO_FRACO)

        # tooltip por hover
        mouse = pygame.mouse.get_pos()
        for r, slot in self.slots_eq:
            if r.collidepoint(mouse) and j.equipamentos.get(slot):
                self._tooltip_equipamento(j.equipamentos[slot], mouse)

    def _cristal_selecionado(self, j: Any) -> Cristal | None:
        """Cristal selecionado, ou None se a seleção estiver vazia ou inválida."""
        indice = self.selecionado_cristal
        if indice is None or indice >= len(j.inventario):
            return None
        item = j.inventario[indice]
        return item if isinstance(item, Cristal) else None

    # ------------------------------------------------------------------ inventário
    def _desenhar_inventario(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        texto(surf, "Inventário", (120, 154), 18, TEXTO, True)
        texto(surf, f"{len(j.inventario)} / 48", (580, 158), 14, TEXTO_FRACO, False, "right")
        for i in range(48):
            col, lin = i % 8, i // 8
            r = pygame.Rect(120 + col * 58, 180 + lin * 58, 52, 52)
            item = j.inventario[i] if i < len(j.inventario) else None
            self._desenhar_slot(surf, r, item, None, pequeno=True, tempo=jogo.ui.tempo, indice=i)
            if isinstance(item, Pocao):
                texto(surf, str(item.quantidade), (r.right - 6, r.bottom - 18), 12, BRANCO, True, "right")
            elif isinstance(item, Equipamento):
                self._desenhar_seta_comparacao(surf, r, item, j)
            self.slots_inv.append((r, i))

        # detalhe
        mouse = pygame.mouse.get_pos()
        foco = None
        foco_idx: int | None = None
        for r, idx in self.slots_inv:
            if r.collidepoint(mouse) and idx < len(j.inventario):
                foco = j.inventario[idx]
                foco_idx = idx
                self.item_selecionado = idx
                break
        if foco is None and self.item_selecionado is not None:
            if self.item_selecionado < len(j.inventario):
                foco_idx = self.item_selecionado
                foco = j.inventario[foco_idx]
            else:
                self.item_selecionado = None
        painel(surf, (610, 176, 570, 402), 180, PAINEL_CLARO, (54, 62, 80), 12, 1)
        if foco is None:
            texto(surf, "Passe o mouse sobre um item", (630, 200), 18, TEXTO_FRACO, True)
            texto(surf, "Clique para equipar, usar ou selecionar.", (630, 232), 14, TEXTO_FRACO)
            self._desenhar_instrucoes(surf, 630, 280)
        else:
            linhas = self._linhas_item(foco)
            y = 198
            for conteudo, cor in linhas:
                for parte in self._quebrar(conteudo, 530):
                    texto(surf, parte, (630, y), 15 if y == 198 else 14, cor, y == 198)
                    y += 22
            if isinstance(foco, Equipamento):
                equipado = j.equipamentos.get(foco.slot)
                comparacao = self._linhas_comparacao(foco, equipado)
                y += 6
                titulo = "Slot vazio" if equipado is None else f"Comparação com {equipado.nome}"
                texto(surf, titulo, (630, y), 13, DOURADO, True)
                y += 20
                for conteudo, cor in comparacao:
                    texto(surf, conteudo, (630, y), 14, cor)
                    y += 20
                dica = "Clique para equipar (melhora seu poder)" if poder_do_item(foco) > poder_do_item(equipado) else "Clique para equipar"
                texto(surf, dica, (630, 540), 14, VERDE, True)
            elif isinstance(foco, Pocao):
                texto(surf, "Clique para usar", (630, 540), 14, VERDE, True)
            elif isinstance(foco, Cristal):
                texto(surf, "Clique para selecionar e encaixar", (630, 540), 14, DOURADO, True)

            if foco_idx is not None:
                preco = preco_venda(foco)
                br = pygame.Rect(930, 528, 230, 36)
                pygame.draw.rect(surf, (44, 82, 56), br, border_radius=raio_ui(8))
                pygame.draw.rect(surf, VERDE, br, width=1, border_radius=raio_ui(8))
                texto(surf, f"Vender por {preco} ouro", (br.centerx, br.centery - 9), 14, VERDE, True, "center")
                self.botoes_venda.append((br, foco_idx))

        comuns = sum(
            1 for item in j.inventario
            if isinstance(item, Equipamento) and item.raridade == "Comum"
        )
        brc = pygame.Rect(120, 600, 300, 34)
        ativo = comuns > 0
        pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), brc, border_radius=raio_ui(8))
        pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), brc, width=1, border_radius=raio_ui(8))
        texto(
            surf, f"Vender equipamentos comuns ({comuns})",
            (brc.centerx, brc.centery - 9), 13, VERDE if ativo else (90, 96, 110), True, "center",
        )
        if ativo:
            self.botoes_venda_comuns.append(brc)


        texto(surf, f"Ouro: {j.ouro}", (120, 560), 18, (246, 204, 92), True)
        moeda(surf, 110, 570, 7)

    # ------------------------------------------------------------------ forja
    def _desenhar_forja(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        cristais = sum(1 for item in j.inventario if isinstance(item, Cristal))
        texto(surf, "Forja de Durin", (120, 154), 18, TEXTO, True)
        texto(surf, f"Ouro: {j.ouro} · Cristais: {cristais}", (1160, 158), 14, (246, 204, 92), True, "right")
        if not jogo.na_vila_veyra():
            texto(surf, "Visite a Vila de Veyra para usar a forja.", (120, 200), 16, AMARELO, True)
            return
        texto(surf, "Reforçar equipamento (máx. 5 reforços)", (120, 182), 13, TEXTO_FRACO)
        for i, slot in enumerate(SLOTS):
            r = pygame.Rect(120, 206 + i * 82, 1000, 72)
            painel(surf, r, 190, PAINEL_CLARO, (54, 62, 80), 10, 1)
            eq = j.equipamentos.get(slot)
            if eq is None:
                texto(surf, f"{slot}: vazio", (r.x + 16, r.y + 24), 15, TEXTO_FRACO)
                continue
            texto(surf, f"{slot} · {eq.nome}", (r.x + 16, r.y + 10), 15, eq.cor, True)
            texto(surf, f"Nível {eq.nivel} · Reforços {eq.melhorias}/5", (r.x + 16, r.y + 34), 12, TEXTO_FRACO)
            custo = jogo.custo_reforco(eq)
            br = pygame.Rect(r.right - 190, r.y + 18, 170, 36)
            ativo = eq.melhorias < 5 and j.ouro >= custo and cristais >= 1
            pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), br, border_radius=raio_ui(8))
            pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), br, width=1, border_radius=raio_ui(8))
            rotulo = f"Reforçar ({custo}g)" if eq.melhorias < 5 else "Máximo"
            texto(surf, rotulo, (br.centerx, br.centery - 9), 13, VERDE if ativo else (90, 96, 110), True, "center")
            if ativo:
                self.botoes_forja.append((br, ("reforcar", slot)))

        y = 206 + len(SLOTS) * 82 + 8
        texto(surf, "Forjar equipamento novo", (120, y), 15, TEXTO, True)
        for i, raridade in enumerate(("Raro", "Épico", "Lendário")):
            custo = CUSTO_FORJA[raridade]
            custo_cristais = CRISTAIS_FORJA[raridade]
            br = pygame.Rect(120 + i * 330, y + 26, 310, 38)
            ativo = j.ouro >= custo and cristais >= custo_cristais
            pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), br, border_radius=raio_ui(8))
            pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), br, width=1, border_radius=raio_ui(8))
            texto(
                surf, f"Forjar {raridade} ({custo}g + {custo_cristais} cristais)",
                (br.centerx, br.centery - 9), 13, VERDE if ativo else (90, 96, 110), True, "center",
            )
            if ativo:
                self.botoes_forja.append((br, ("forjar", raridade)))

    # ------------------------------------------------------------------ encantamentos
    def _desenhar_encantamentos(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        cristais = sum(1 for item in j.inventario if isinstance(item, Cristal))
        texto(surf, "Encantamentos de Yara", (120, 154), 18, TEXTO, True)
        texto(surf, f"Ouro: {j.ouro} · Cristais: {cristais}", (1160, 158), 14, (246, 204, 92), True, "right")
        texto(surf, "150 ouro + 1 cristal por encantamento (máx. 3 por item).", (120, 182), 13, TEXTO_FRACO)
        if not jogo.na_vila_veyra():
            texto(surf, "Visite a Vila de Veyra para encantar.", (120, 210), 16, AMARELO, True)
            return
        for i, slot in enumerate(SLOTS):
            r = pygame.Rect(120, 214 + i * 92, 1000, 80)
            painel(surf, r, 190, PAINEL_CLARO, (54, 62, 80), 10, 1)
            eq = j.equipamentos.get(slot)
            if eq is None:
                texto(surf, f"{slot}: vazio", (r.x + 16, r.y + 26), 15, TEXTO_FRACO)
                continue
            texto(surf, f"{slot} · {eq.nome}", (r.x + 16, r.y + 10), 15, eq.cor, True)
            texto(
                surf, f"Encantamentos: {eq.encantamentos}/3 · Nível {eq.nivel}",
                (r.x + 16, r.y + 36), 12, TEXTO_FRACO,
            )
            br = pygame.Rect(r.right - 190, r.y + 22, 170, 36)
            ativo = eq.encantamentos < 3 and j.ouro >= 150 and cristais >= 1
            pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), br, border_radius=raio_ui(8))
            pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), br, width=1, border_radius=raio_ui(8))
            rotulo = "Encantar (150g)" if eq.encantamentos < 3 else "Máximo"
            texto(surf, rotulo, (br.centerx, br.centery - 9), 13, VERDE if ativo else (90, 96, 110), True, "center")
            if ativo:
                self.botoes_encanto.append((br, slot))

    def _desenhar_instrucoes(self, surf: pygame.Surface, x: int, y: int) -> None:
        linhas = [
            "• Equipamentos: clique para equipar.",
            "• Poções: clique para consumir.",
            "• Cristais: selecione e encaixe na aba Cristais.",
            "• Itens melhores vêm de inimigos mais fortes.",
        ]
        for i, linha in enumerate(linhas):
            texto(surf, linha, (x, y + i * 26), 14, TEXTO_FRACO)

    # ------------------------------------------------------------------ mercado
    def _desenhar_mercado(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        texto(surf, "Mercado de Veyra", (120, 154), 18, TEXTO, True)
        texto(surf, f"Ouro: {j.ouro}", (1160, 158), 16, (246, 204, 92), True, "right")
        texto(surf, "Compre recursos aqui e venda itens na aba Inventário.", (120, 180), 13, TEXTO_FRACO)

        itens = (
            ("pocao_vida", "Poção de Vida", "Restaura 35% da vida máxima", 40, (232, 82, 96), "pocao_vida"),
            ("pocao_mana", "Poção de Mana", "Restaura 40% da mana máxima", 50, (82, 148, 244), "pocao_mana"),
            ("pocao_stamina", "Elixir de Fôlego", "Restaura 60 de stamina", 45, (244, 206, 92), "pocao_stamina"),
            ("cristal", "Cristal aleatório", "Tier sorteado conforme seu nível", 120, (120, 200, 240), "cristal"),
            ("equipamento", "Equipamento raro", "Peça rara para a sua classe", 300, (190, 116, 242), "armadura"),
            ("equipamento_epico", "Equipamento épico", "Peça épica para a sua classe", 900, (250, 192, 88), "armadura"),
        )
        for i, (chave, nome, desc, preco, cor, icone_tipo) in enumerate(itens):
            col, lin = i % 2, i // 2
            r = pygame.Rect(120 + col * 530, 212 + lin * 112, 500, 96)
            painel(surf, r, 190, PAINEL_CLARO, (54, 62, 80), 12, 1)
            icone(surf, icone_tipo, pygame.Rect(r.x + 14, r.y + 16, 64, 64), cor)
            texto(surf, nome, (r.x + 92, r.y + 14), 17, TEXTO, True)
            texto(surf, desc, (r.x + 92, r.y + 38), 12, TEXTO_FRACO)
            texto(surf, f"{preco} ouro", (r.x + 92, r.y + 60), 14, (246, 204, 92), True)
            br = pygame.Rect(r.right - 132, r.y + 30, 112, 36)
            ativo = j.ouro >= preco
            pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), br, border_radius=raio_ui(8))
            pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), br, width=1, border_radius=raio_ui(8))
            texto(surf, "Comprar", (br.centerx, br.centery - 9), 14, VERDE if ativo else (90, 96, 110), True, "center")
            if ativo:
                self.botoes_mercado.append((br, chave))

        texto(
            surf,
            "Dica: venda equipamentos comuns no Inventário para liberar espaço.",
            (120, 590), 14, (200, 210, 230),
        )

    # ------------------------------------------------------------------ cristais
    def _desenhar_cristais(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        cristais = [(i, item) for i, item in enumerate(j.inventario) if isinstance(item, Cristal)]
        equipados = [e for e in j.equipamentos.values() if e is not None]
        livres = sum(e.sockets_livres for e in equipados)
        selecionado = self._cristal_selecionado(j)

        texto(surf, "Cristais", (120, 154), 18, TEXTO, True)
        texto(
            surf,
            f"{len(cristais)} cristal(is) · {livres} encaixe(s) livre(s)",
            (1160, 158), 14, DOURADO if livres else VERMELHO, True, "right",
        )
        if not cristais:
            texto(surf, "Nenhum cristal no inventário.", (120, 182), 15, TEXTO_FRACO)
            texto(surf, "Cristais caem de inimigos, e bosses dão tiers altos.", (120, 204), 13, TEXTO_FRACO)
        elif selecionado is None:
            texto(surf, "1. Clique em um cristal para selecioná-lo.", (120, 180), 13, (250, 226, 150))
            texto(surf, "2. Clique em um encaixe vazio (marcado com +) para encaixar.", (120, 200), 13, TEXTO_FRACO)
        else:
            texto(surf, f"Selecionado: {selecionado.nome} — clique em um encaixe marcado com +.", (120, 180), 13, selecionado.cor, True)
        if not livres and equipados:
            texto(surf, "Nenhum encaixe livre: equipe itens Raros, Épicos ou Lendários.", (120, 622), 13, AMARELO)
        elif not equipados:
            texto(surf, "Você não tem equipamentos equipados.", (120, 622), 13, AMARELO)
        if len(cristais) > 12:
            texto(surf, f"Mostrando 12 de {len(cristais)}; encaixe para liberar espaço.", (120, 646), 12, TEXTO_FRACO)

        for n, (idx, cristal) in enumerate(cristais[:12]):
            col, lin = n % 2, n // 2
            r = pygame.Rect(120 + col * 240, 224 + lin * 58, 228, 50)
            marcado = self.selecionado_cristal == idx
            pygame.draw.rect(surf, (30, 36, 48) if not marcado else (48, 44, 30), r, border_radius=raio_ui(8))
            pygame.draw.rect(surf, cristal.cor if marcado else (54, 62, 80), r, width=2 if marcado else 1, border_radius=raio_ui(8))
            tempo = getattr(getattr(jogo, "ui", None), "tempo", 0.0)
            tempo = getattr(getattr(jogo, "ui", None), "tempo", 0.0)
            icone(surf, "cristal", pygame.Rect(r.x + 6, r.y + 6, 38, 38), cristal.cor, pulso=1.0 + 0.06 * math.sin(tempo * 3.0 + n))
            texto(surf, cristal.nome, (r.x + 52, r.y + 7), 14, cristal.cor, True)
            texto(surf, cristal.descricao, (r.x + 52, r.y + 27), 12, TEXTO_FRACO)
            if marcado:
                pygame.draw.circle(surf, DOURADO, (r.right - 14, r.y + 14), 5)
            self.cristais_rects.append((r, idx))

        # equipamentos e encaixes
        painel(surf, (620, 176, 560, 402), 180, PAINEL_CLARO, (54, 62, 80), 12, 1)
        texto(surf, "Encaixes", (640, 190), 18, DOURADO, True)
        pulso = 0.5 + 0.5 * math.sin(getattr(getattr(jogo, "ui", None), "tempo", 0.0) * 5.0)
        y = 224
        for slot in SLOTS:
            eq = j.equipamentos.get(slot)
            if eq is None:
                texto(surf, f"{slot}: vazio", (640, y), 14, TEXTO_FRACO)
                y += 54
                continue
            nome = _truncar(f"{slot}: {eq.nome}", 292, 14, True)
            texto(surf, nome, (640, y), 14, cor_raridade(eq.raridade), True)
            if not eq.sockets:
                texto(surf, "Sem encaixes", (640, y + 22), 12, TEXTO_FRACO)
            for i, cristal in enumerate(eq.sockets):
                cr = pygame.Rect(950 + i * 54, y - 4, 42, 42)
                pygame.draw.circle(surf, (26, 30, 40), cr.center, 20)
                pygame.draw.circle(surf, cristal.cor if cristal else (62, 70, 88), cr.center, 20, 2)
                if cristal:
                    tempo = getattr(getattr(jogo, "ui", None), "tempo", 0.0)
                    icone(surf, "cristal", cr.inflate(-14, -14), cristal.cor, pulso=1.0 + 0.06 * math.sin(tempo * 3.0 + i))
                else:
                    cor = (86, 94, 112)
                    if selecionado is not None:
                        cor = tuple(int(120 + 135 * pulso) for _ in range(3))
                        pygame.draw.circle(surf, (250, 226, 150), cr.center, 23, 2)
                    texto(surf, "+", cr.center, 18, cor, True, "center")
                self.sockets_rects.append((cr, slot, i))
            y += 62

        if cristais:
            pode_fundir = j.pode_fundir_cristais()
            br = pygame.Rect(920, 182, 240, 32)
            pygame.draw.rect(surf, (44, 82, 56) if pode_fundir else (36, 40, 50), br, border_radius=raio_ui(8))
            pygame.draw.rect(surf, VERDE if pode_fundir else (60, 66, 80), br, width=1, border_radius=raio_ui(8))
            texto(
                surf, "Fundir cristais (3 → 1)",
                (br.centerx, br.centery - 9), 13,
                VERDE if pode_fundir else (90, 96, 110), True, "center",
            )
            if pode_fundir:
                self.botoes_fusao.append(br)

        # tooltip (só nos encaixes: o detalhe do cristal já aparece no card)
        mouse = pygame.mouse.get_pos()
        for cr, slot, i in self.sockets_rects:
            if cr.collidepoint(mouse):
                eq = j.equipamentos.get(slot)
                if eq and i < len(eq.sockets) and eq.sockets[i]:
                    self._tooltip_item(eq.sockets[i], mouse)

    # ------------------------------------------------------------------ habilidades
    def _desenhar_habilidades(self, surf: pygame.Surface, jogo: Any) -> None:
        j = jogo.jogador
        texto(surf, "Habilidades", (120, 154), 18, TEXTO, True)
        texto(surf, f"Pontos de habilidade: {j.pontos_habilidade}", (1160, 158), 15, VERDE if j.pontos_habilidade else TEXTO_FRACO, True, "right")
        texto(
            surf, "Tiers 6–10: maestria (mais dano, menos recarga e alcance).",
            (120, 172), 12, TEXTO_FRACO,
        )
        for i, h in enumerate(j.habilidades):
            r = pygame.Rect(120, 190 + i * 104, 1020, 100)
            pygame.draw.rect(surf, PAINEL_CLARO, r, border_radius=raio_ui(12))
            pygame.draw.rect(surf, (54, 62, 80), r, width=1, border_radius=raio_ui(12))
            icone(surf, h.icone, pygame.Rect(r.x + 16, r.y + 14, 64, 64), h.cor)
            pygame.draw.rect(surf, (24, 28, 38), pygame.Rect(r.x + 16, r.y + 14, 64, 64), width=2, border_radius=raio_ui(12))
            texto(surf, f"{h.tecla} · {h.nome}", (r.x + 96, r.y + 8), 18, TEXTO, True)
            texto(surf, f"Tier {h.tier} / {h.max_tier}", (r.x + 96, r.y + 32), 13, DOURADO, True)
            texto(surf, h.descricao, (r.x + 96, r.y + 52), 12, TEXTO_FRACO)
            ataque = j.stats_totais()["ataque"]
            if h.dano_mult > 0:
                detalhe = (
                    f"Dano {h.dano(ataque):.0f} → {h.dano(ataque) * 1.22:.0f}"
                    if h.tier < h.max_tier
                    else f"Dano {h.dano(ataque):.0f}"
                )
            else:
                detalhe = "Efeito de aprimoramento"
            if h.tier < h.max_tier:
                custo_prox = int(round(h.custo * (1.0 + 0.06 * h.tier), 1))
                cd_prox = h.cooldown * (1.0 - 0.035 * h.tier)
                recurso = (
                    f"{int(h.custo_atual)} → {custo_prox} {h.custo_tipo.upper()}"
                    f" · recarga {h.cooldown_atual:.1f}s → {cd_prox:.1f}s"
                )
            else:
                recurso = f"{int(h.custo_atual)} {h.custo_tipo.upper()} · recarga {h.cooldown_atual:.1f}s"
            texto(surf, f"{detalhe} · {recurso}", (r.x + 96, r.y + 70), 12, (170, 200, 230))
            evolucao = h.evolucao_atual or h.proxima_evolucao()
            if evolucao:
                cor_evolucao = (140, 230, 160) if h.evolucao_atual else (140, 154, 172)
                texto(surf, evolucao, (r.x + 96, r.y + 86), 9, cor_evolucao)

            # botão +
            br = pygame.Rect(r.right - 130, r.y + 24, 100, 40)
            ativo = j.pontos_habilidade > 0 and h.tier < h.max_tier
            pygame.draw.rect(surf, (44, 82, 56) if ativo else (36, 40, 50), br, border_radius=raio_ui(10))
            pygame.draw.rect(surf, VERDE if ativo else (60, 66, 80), br, width=1, border_radius=raio_ui(10))
            texto(surf, "Melhorar" if h.tier < h.max_tier else "Máximo", (br.centerx, br.centery - 9), 14, VERDE if ativo else (90, 96, 110), True, "center")
            if ativo:
                self.botoes_hab.append((br, h.id))
            # tooltip
            mouse = pygame.mouse.get_pos()
            if r.collidepoint(mouse):
                self._tooltip_habilidade(h, j, mouse)

    # ------------------------------------------------------------------ slots
    def _desenhar_slot(
        self, surf: pygame.Surface, r: pygame.Rect, item: Any,
        vazio_icone: str | None, pequeno: bool = False,
        tempo: float = 0.0, indice: int = 0,
    ) -> None:
        pygame.draw.rect(surf, (18, 22, 30), r, border_radius=raio_ui(9))
        if item is not None:
            cor = getattr(item, "cor", (160, 166, 180))
            pygame.draw.rect(surf, cor, r, width=2, border_radius=raio_ui(9))
            if isinstance(item, Equipamento) and item.raridade in ("Épico", "Lendário"):
                pygame.draw.rect(surf, cor, r.inflate(6, 6), width=1, border_radius=raio_ui(12))
            if isinstance(item, Equipamento):
                icone_tipo = item.icone
            elif isinstance(item, Cristal):
                icone_tipo = "cristal"
            else:
                icone_tipo = getattr(item, "icone", "cristal")
            rect_icone = r.inflate(-12, -12)
            # poções balançam levemente quando a arte pixel está ligada
            if isinstance(item, Pocao) and modo_pixel():
                bob = int(round(math.sin(tempo * 2.0 + indice * 0.7) * 2))
                rect_icone = rect_icone.move(0, bob)
            icone(surf, icone_tipo, rect_icone, cor)

            # itens raros pulsam com a cor da raridade
            if isinstance(item, Equipamento) and item.raridade in ("Épico", "Lendário") and modo_pixel():
                pulso = 0.5 + 0.5 * math.sin(tempo * 2.4 + indice)
                a = int(70 + 90 * pulso)
                halo = pygame.Surface((r.width + 6, r.height + 6), pygame.SRCALPHA)
                pygame.draw.rect(halo, (*cor, a), halo.get_rect(), 1)
                surf.blit(halo, (r.x - 3, r.y - 3))
            if isinstance(item, Equipamento) and item.raridade in ("Épico", "Lendário"):
                sx2, sy2 = r.right - 10, r.y + 10
                pygame.draw.line(surf, (255, 255, 255), (sx2 - 3, sy2), (sx2 + 3, sy2), 1)
                pygame.draw.line(surf, (255, 255, 255), (sx2, sy2 - 3), (sx2, sy2 + 3), 1)
        else:
            pygame.draw.rect(surf, (46, 52, 66), r, width=1, border_radius=raio_ui(9))
            if vazio_icone:
                icone(surf, vazio_icone, r.inflate(-20, -20), (58, 64, 80))

    def _desenhar_seta_comparacao(
        self, surf: pygame.Surface, r: pygame.Rect, item: Equipamento, j: Any,
    ) -> None:
        """Seta verde/vermelha indicando se o item é melhor que o equipado no slot."""
        equipado = j.equipamentos.get(item.slot)
        if equipado is None:
            texto(surf, "▲", (r.right - 13, r.y + 2), 13, VERDE, True, "center")
            return
        delta = poder_do_item(item) - poder_do_item(equipado)
        if delta > 0.5:
            texto(surf, "▲", (r.right - 13, r.y + 2), 13, VERDE, True, "center")
        elif delta < -0.5:
            texto(surf, "▼", (r.right - 13, r.y + 2), 13, VERMELHO, True, "center")

    @staticmethod
    def _linhas_comparacao(
        item: Equipamento, equipado: Equipamento | None,
    ) -> list[tuple[str, tuple[int, int, int]]]:
        """Diferença de atributos entre o item e o que já está equipado no slot."""
        novos = item.stats_totais()
        if equipado is None:
            positivos = [s for s in ORDEM_STATS if novos.get(s, 0.0) > 0]
            return [
                (f"+{fmt_valor(s, novos[s])} {STAT_NOMES.get(s, s)}", VERDE)
                for s in positivos
            ] or [("Sem atributos.", TEXTO_FRACO)]
        antigos = equipado.stats_totais()
        linhas: list[tuple[str, tuple[int, int, int]]] = []
        for stat in ORDEM_STATS:
            delta = novos.get(stat, 0.0) - antigos.get(stat, 0.0)
            if abs(delta) < 0.05:
                continue
            sinal = "+" if delta > 0 else ""
            linhas.append((f"{sinal}{fmt_valor(stat, delta)} {STAT_NOMES.get(stat, stat)}", VERDE if delta > 0 else VERMELHO))
        if not linhas:
            linhas.append(("Mesmos atributos do equipado.", AMARELO))
        return linhas


    # ------------------------------------------------------------------ tooltips
    def _tooltip_item(self, item: Any, pos: tuple[int, int]) -> None:
        self.tooltip = self._linhas_item(item)
        self.tooltip_pos = pos

    def _tooltip_equipamento(self, eq: Equipamento, pos: tuple[int, int]) -> None:
        self.tooltip = eq.linhas()
        self.tooltip_pos = pos

    def _tooltip_habilidade(self, h: Any, j: Any, pos: tuple[int, int]) -> None:
        self.tooltip = [
            (f"{h.nome} — Tier {h.tier}", h.cor),
            (h.descricao, (200, 206, 220)),
            (f"Dano: {h.dano(j.stats_totais()['ataque']):.0f}", (240, 220, 180)),
            (f"Custo: {int(h.custo_atual)} {h.custo_tipo.upper()}", (160, 200, 240)),
            (f"Recarga: {h.cooldown_atual:.1f}s", (160, 200, 240)),
        ]
        if h.tier < h.max_tier:
            self.tooltip.append(("Próximo tier: +22% de dano", (120, 220, 150)))
        else:
            self.tooltip.append(("Tier máximo", (250, 200, 100)))
        if h.evolucao_atual:
            self.tooltip.append((h.evolucao_atual, (150, 235, 170)))
        elif h.proxima_evolucao():
            self.tooltip.append((f"Próxima evolução: {h.proxima_evolucao()}", (150, 180, 165)))
        self.tooltip_pos = pos

    def _linhas_item(self, item: Any) -> list[tuple[str, tuple[int, int, int]]]:
        if isinstance(item, Equipamento):
            return item.linhas()
        if isinstance(item, Cristal):
            return [
                (item.nome, item.cor),
                (f"Cristal · Tier {item.tier}", (160, 166, 180)),
                (item.descricao, (206, 214, 228)),
                ("Encaixe em um equipamento com espaço.", (130, 138, 156)),
            ]
        if isinstance(item, Pocao):
            return [
                (item.nome, item.cor),
                (f"Quantidade: {item.quantidade}", (160, 166, 180)),
                (item.descricao, (206, 214, 228)),
                ("Clique para consumir.", (130, 138, 156)),
            ]
        return [("Item", BRANCO)]

    def _desenhar_tooltip(self, surf: pygame.Surface) -> None:
        from utils import fonte
        largura = max(220, max(fonte(14).size(t)[0] for t, _ in self.tooltip) + 30)
        altura = len(self.tooltip) * 22 + 20
        x, y = self.tooltip_pos
        x = min(x + 18, LARGURA - largura - 10)
        y = min(y + 18, ALTURA - altura - 10)
        painel(surf, (x, y, largura, altura), 245, (16, 20, 28), (90, 98, 116), 10, 1)
        for i, (conteudo, cor) in enumerate(self.tooltip):
            texto(surf, conteudo, (x + 14, y + 10 + i * 22), 14 if i else 15, cor, i == 0)

    # ------------------------------------------------------------------ eventos
    def processar_clique(self, pos: tuple[int, int], jogo: Any, botao: int = 1) -> bool:
        for r, nome in self.abas_rects:
            if r.collidepoint(pos):
                self.aba = nome
                jogo.sons.tocar("clique", 0.3)
                return True
        j = jogo.jogador
        if self.aba == "Equipamentos":
            for r, slot in self.slots_eq:
                if r.collidepoint(pos):
                    if j.equipamentos.get(slot) is not None:
                        if j.desequipar(slot):
                            jogo.ui.notificar(f"{slot} desequipado.", TEXTO)
                            jogo.sons.tocar("equipar", 0.5)
                    return True
            for r, chave in self.botoes_attr:
                if r.collidepoint(pos):
                    if j.subir_atributo(chave):
                        jogo.ui.notificar(f"{ATRIBUTOS[chave][0]} aumentado!", VERDE)
                        jogo.sons.tocar("level_up", 0.4)
                    return True
            for r in self.botoes_respec:
                if r.collidepoint(pos):
                    jogo.resetar_atributos()
                    return True
        elif self.aba == "Inventário":
            for r, idx in self.botoes_venda:
                if r.collidepoint(pos) and idx < len(j.inventario):
                    item = j.inventario[idx]
                    preco = preco_venda(item)
                    if j.vender_item(item):
                        j.ouro += preco
                        jogo.ui.notificar(f"{item.nome} vendido por {preco} ouro.", (246, 204, 92))
                        jogo.sons.tocar("venda", 0.6)
                        if item not in j.inventario:
                            self.item_selecionado = None
                    return True
            for r in self.botoes_venda_comuns:
                if r.collidepoint(pos):
                    quantidade, total = j.vender_comuns()
                    if quantidade:
                        j.ouro += total
                        jogo.sons.tocar("venda", 0.7)
                        jogo.ui.notificar(
                            f"{quantidade} equipamento(s) comum(ns) vendido(s) por {total} ouro.",
                            (246, 204, 92),
                        )
                        self.item_selecionado = None
                    else:
                        jogo.ui.notificar("Nenhum equipamento comum para vender.", AMARELO)
                    return True
            for r, idx in self.slots_inv:
                if r.collidepoint(pos) and idx < len(j.inventario):
                    item = j.inventario[idx]
                    if isinstance(item, Equipamento):
                        if j.equipar(item):
                            jogo.ui.notificar(f"{item.nome} equipado.", item.cor)
                            jogo.sons.tocar("equipar", 0.6)
                            self.item_selecionado = None
                        else:
                            jogo.ui.notificar("Classe incompatível com esta arma.", VERMELHO)
                    elif isinstance(item, Pocao):
                        if j.usar_pocao(item):
                            jogo.ui.notificar(f"{item.nome} usado.", item.cor)
                            jogo.sons.tocar("pocao", 0.7)
                            if item not in j.inventario:
                                self.item_selecionado = None
                        else:
                            jogo.ui.notificar("Recurso já está cheio.", AMARELO)
                    elif isinstance(item, Cristal):
                        self.selecionado_cristal = idx
                        self.item_selecionado = None
                        self.aba = "Cristais"
                        jogo.ui.notificar(f"{item.nome} selecionado.", item.cor)
                    return True
        elif self.aba == "Cristais":
            for r in self.botoes_fusao:
                if r.collidepoint(pos):
                    jogo.fundir_cristais()
                    self.selecionado_cristal = None
                    return True
            for r, idx in self.cristais_rects:
                if r.collidepoint(pos):
                    self.selecionado_cristal = idx
                    return True
            for cr, slot, i in self.sockets_rects:
                if cr.collidepoint(pos):
                    eq = j.equipamentos.get(slot)
                    if eq is None:
                        return True
                    if self.selecionado_cristal is not None and self.selecionado_cristal < len(j.inventario):
                        item = j.inventario[self.selecionado_cristal]
                        if isinstance(item, Cristal):
                            if eq.sockets[i] is not None:
                                jogo.ui.notificar("Este encaixe já está ocupado.", VERMELHO)
                            elif j.encaixar_cristal(item, slot):
                                jogo.ui.notificar(f"{item.nome} encaixado em {eq.nome}.", item.cor)
                                jogo.sons.tocar("cristal", 0.7)
                                self.selecionado_cristal = None
                    elif eq.sockets[i] is not None:
                        if j.remover_cristal(slot, i):
                            jogo.ui.notificar("Cristal removido.", TEXTO)
                            jogo.sons.tocar("cristal", 0.5)
                    return True
        elif self.aba == "Habilidades":
            for r, id_h in self.botoes_hab:
                if r.collidepoint(pos):
                    if j.melhorar_habilidade(id_h):
                        jogo.ui.notificar("Habilidade melhorada!", VERDE)
                        jogo.sons.tocar("level_up", 0.5)
                    return True
        elif self.aba == "Mercado":
            for r, chave in self.botoes_mercado:
                if r.collidepoint(pos):
                    jogo.comprar_item(chave)
                    return True
        elif self.aba == "Forja":
            for r, (acao, valor) in self.botoes_forja:
                if r.collidepoint(pos):
                    if acao == "reforcar":
                        jogo.reforcar_equipamento(valor)
                    else:
                        jogo.forjar_equipamento(valor)
                    return True
        elif self.aba == "Encantamentos":
            for r, slot in self.botoes_encanto:
                if r.collidepoint(pos):
                    jogo.encantar_equipamento(slot)
                    return True
        return False

    def _quebrar(self, texto_str: str, largura: int) -> list[str]:
        from utils import fonte
        palavras = str(texto_str).split(" ")
        linhas: list[str] = []
        atual = ""
        for p in palavras:
            teste = (atual + " " + p).strip()
            if fonte(14).size(teste)[0] <= largura:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas or [""]
