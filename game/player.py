"""Lógica do jogador: atributos, progressão, inventário e combate."""
from __future__ import annotations

import math
import random
from typing import Any, Sequence

import pygame

from core.input import teclado_correndo, teclado_movimento
from items import (
    Cristal, Equipamento, Pocao, Item, SLOTS, STAT_NOMES, gerar_pocao, preco_venda,
)
from settings import (
    AMARELO, ATRASO_REGEN_MP, ATRASO_REGEN_STAMINA, CLASSES, CRITICO_MULT,
    COOLDOWN_ESQUIVA, CUSTO_CORRIDA, CUSTO_ESQUIVA, DANO_VARIACAO,
    DURACAO_ESQUIVA, INVULNERABILIDADE_ESQUIVA, REGEN_HP, REGEN_MP,
    REGEN_STAMINA, VELOCIDADE_ESQUIVA, VEL_CORRIDA, xp_para_nivel,
)
from skills import Habilidade, criar_habilidades
from utils import clamp, distancia, normalizar


ATRIBUTOS = {
    "forca": ("Força", "+2,0 Ataque"),
    "vitalidade": ("Vitalidade", "+14 Vida e +0,25 Defesa"),
    "inteligencia": ("Inteligência", "+10 Mana"),
    "destreza": ("Destreza", "+1,2% Crítico e +3 Velocidade"),
    "foco": ("Foco", "+0,35 Regen. de mana"),
}

CAPACIDADE_INVENTARIO = 48


class Jogador:
    def __init__(self, classe: str, nome: str = "Herói") -> None:
        self.classe = classe if classe in CLASSES else "Cavaleiro"
        self.nome = nome
        self.x = 0.0
        self.y = 0.0
        self.raio = 16.0
        self.facing = (0.0, 1.0)
        self.tempo = 0.0
        self.walk_phase = 0.0
        self.andando = False
        self.correndo = False

        self.nivel = 1
        self.xp = 0
        self.xp_proximo = xp_para_nivel(1)
        self.atributos = {chave: 0 for chave in ATRIBUTOS}
        self.pontos_status = 0
        self.pontos_habilidade = 0

        self.hp_max = 0
        self.mp_max = 0
        self.stamina_max = 0
        self.hp = 0.0
        self.mp = 0.0
        self.stamina = 0.0
        self.fome = 100.0
        self.fome_max = 100.0
        self.fome_aviso_25 = False
        self.fome_aviso_0 = False

        self.ouro = 0
        self.inventario: list[Item] = []
        self.equipamentos: dict[str, Equipamento | None] = {slot: None for slot in SLOTS}
        self.habilidades: list[Habilidade] = criar_habilidades(self.classe)
        self.cooldowns: dict[str, float] = {h.id: 0.0 for h in self.habilidades}
        self.buffs: dict[str, dict[str, Any]] = {}

        self.tempo_ataque = 0.0
        self.ataque_anim = 0.0
        self.angulo_ataque = 0.0
        self.hit_flash = 0.0
        self.invulneravel = 0.0
        self.level_flash = 0.0
        self.kb_x = 0.0
        self.kb_y = 0.0
        self.morto = False
        self.tempo_morte = 0.0

        self.kills = 0
        self.bosses = 0
        self.zona = "Clareira de Lumen"

        self.regen_mp_delay = 0.0
        self.regen_stamina_delay = 0.0
        self.esquiva_timer = 0.0
        self.esquiva_cooldown = 0.0
        self.esquiva_dx = 0.0
        self.esquiva_dy = 0.0
        self.esquiva_usada = False
        self._esquiva_particula = 0.0

        self.recalcular()
        self.hp = float(self.hp_max)
        self.mp = float(self.mp_max)
        self.stamina = float(self.stamina_max)
        self.adicionar_item(gerar_pocao("vida", 2))
        self.adicionar_item(gerar_pocao("mana", 1))
        self.adicionar_item(gerar_pocao("stamina", 1))

    # ------------------------------------------------------------------ stats
    def stats_totais(self) -> dict[str, float]:
        base = CLASSES[self.classe]
        n = self.nivel - 1
        s: dict[str, float] = {
            "ataque": base["ataque"] + n * 1.4 + self.atributos["forca"] * 2.0,
            "defesa": base["defesa"] + n * 0.65 + self.atributos["vitalidade"] * 0.25,
            "hp_max": base["hp"] + n * 9 + self.atributos["vitalidade"] * 14,
            "mp_max": base["mp"] + n * 5 + self.atributos["inteligencia"] * 10,
            "stamina_max": base["stamina"] + n * 2,
            "critico": base["critico"] + self.atributos["destreza"] * 1.2,
            "velocidade": base["velocidade"] + self.atributos["destreza"] * 3,
            "regen_hp": REGEN_HP + n * 0.02,
            "regen_mp": REGEN_MP + self.atributos["foco"] * 0.35,
        }
        for equipamento in self.equipamentos.values():
            if equipamento is not None:
                for stat, valor in equipamento.stats_totais().items():
                    s[stat] = s.get(stat, 0.0) + valor
        for buff in self.buffs.values():
            for stat, valor in buff["stats"].items():
                if stat in ("ataque", "defesa"):
                    s[stat] = s.get(stat, 0.0) * (1.0 + valor)
                else:
                    s[stat] = s.get(stat, 0.0) + valor
        return s

    def recalcular(self) -> None:
        antigos = (self.hp_max, self.mp_max, self.stamina_max)
        s = self.stats_totais()
        self.hp_max = max(1, int(s["hp_max"]))
        self.mp_max = max(1, int(s["mp_max"]))
        self.stamina_max = max(1, int(s["stamina_max"]))
        self.hp += max(0, self.hp_max - antigos[0])
        self.mp += max(0, self.mp_max - antigos[1])
        self.stamina += max(0, self.stamina_max - antigos[2])
        self.hp = clamp(self.hp, 0, self.hp_max)
        self.mp = clamp(self.mp, 0, self.mp_max)
        self.stamina = clamp(self.stamina, 0, self.stamina_max)

    # ------------------------------------------------------------------ progressão
    def ganhar_xp(self, quantidade: int) -> list[str]:
        if quantidade <= 0:
            return []
        self.xp += int(quantidade)
        mensagens: list[str] = []
        while self.xp >= self.xp_proximo:
            self.xp -= self.xp_proximo
            self.nivel += 1
            self.pontos_status += 3
            self.pontos_habilidade += 1
            self.xp_proximo = xp_para_nivel(self.nivel)
            self.recalcular()
            self.hp = float(self.hp_max)
            self.mp = float(self.mp_max)
            self.stamina = float(self.stamina_max)
            self.level_flash = 1.6
            mensagens.append(f"Nível {self.nivel} alcançado! +3 pontos de status, +1 de habilidade.")
        return mensagens

    def subir_atributo(self, chave: str) -> bool:
        if self.pontos_status <= 0 or chave not in self.atributos:
            return False
        self.atributos[chave] += 1
        self.pontos_status -= 1
        self.recalcular()
        return True

    def resetar_atributos(self) -> int:
        """Devolve todos os pontos distribuídos para o jogador redistribuir."""
        total = sum(self.atributos.values())
        if total <= 0:
            return 0
        for chave in self.atributos:
            self.atributos[chave] = 0
        self.pontos_status += total
        self.recalcular()
        return total

    def melhorar_habilidade(self, id_habilidade: str) -> bool:
        if self.pontos_habilidade <= 0:
            return False
        for h in self.habilidades:
            if h.id == id_habilidade and h.melhorar():
                self.pontos_habilidade -= 1
                return True
        return False

    # ------------------------------------------------------------------ inventário
    def adicionar_item(self, item: Item) -> bool:
        if isinstance(item, Pocao):
            for existente in self.inventario:
                if isinstance(existente, Pocao) and existente.tipo == item.tipo:
                    existente.quantidade += item.quantidade
                    return True
        if len(self.inventario) >= CAPACIDADE_INVENTARIO:
            return False
        self.inventario.append(item)
        return True

    def remover_item(self, item: Item) -> bool:
        if item in self.inventario:
            self.inventario.remove(item)
            return True
        return False

    def vender_item(self, item: Item) -> bool:
        """Remove uma unidade do item (poções vendem uma por vez)."""
        if item not in self.inventario:
            return False
        if isinstance(item, Pocao):
            item.quantidade -= 1
            if item.quantidade <= 0:
                self.inventario.remove(item)
        else:
            self.inventario.remove(item)
        return True

    def vender_comuns(self) -> tuple[int, int]:
        """Vende todo equipamento Comum; devolve (quantidade, ouro)."""
        total = 0
        quantidade = 0
        for item in list(self.inventario):
            if isinstance(item, Equipamento) and item.raridade == "Comum":
                total += preco_venda(item)
                self.vender_item(item)
                quantidade += 1
        return quantidade, total

    def consumir_cristal(self) -> Cristal | None:
        cristais = [item for item in self.inventario if isinstance(item, Cristal)]
        if not cristais:
            return None
        item = min(cristais, key=lambda c: c.tier)
        self.inventario.remove(item)
        return item

    def pode_fundir_cristais(self) -> bool:
        """True se houver 3 cristais iguais de tier < 5."""
        contagem: dict[tuple[str, int], int] = {}
        for item in self.inventario:
            if isinstance(item, Cristal) and item.tier < 5:
                chave = (item.tipo, item.tier)
                contagem[chave] = contagem.get(chave, 0) + 1
        return any(quantidade >= 3 for quantidade in contagem.values())

    def fundir_cristais(self) -> list[Cristal]:
        """Funde 3 cristais iguais em 1 do tier seguinte, em cadeia."""
        criados: list[Cristal] = []
        while True:
            contagem: dict[tuple[str, int], int] = {}
            for item in self.inventario:
                if isinstance(item, Cristal) and item.tier < 5:
                    chave = (item.tipo, item.tier)
                    contagem[chave] = contagem.get(chave, 0) + 1
            chave = next(
                ((tipo, tier) for (tipo, tier), quantidade in contagem.items() if quantidade >= 3),
                None,
            )
            if chave is None:
                break
            tipo, tier = chave
            removidos = 0
            for item in list(self.inventario):
                if (
                    isinstance(item, Cristal)
                    and item.tipo == tipo
                    and item.tier == tier
                    and removidos < 3
                ):
                    self.inventario.remove(item)
                    removidos += 1
            novo = Cristal(tipo, tier + 1)
            self.inventario.append(novo)
            criados.append(novo)
        return criados

    def melhorar_equipamento(self, slot: str) -> bool:
        """Reforça o item equipado: +1 nível e +8% nos stats, até 5 reforços."""
        eq = self.equipamentos.get(slot)
        if eq is None or eq.melhorias >= 5:
            return False
        for stat in list(eq.stats):
            eq.stats[stat] = round(eq.stats[stat] * 1.08, 2)
        eq.nivel += 1
        eq.melhorias += 1
        self.recalcular()
        return True

    def encantar_equipamento(self, slot: str) -> str | None:
        """Adiciona um bônus aleatório ao item equipado, até 3 encantamentos."""
        eq = self.equipamentos.get(slot)
        if eq is None or eq.encantamentos >= 3:
            return None
        opcoes = {
            "ataque": (1.0, 3.0),
            "defesa": (1.0, 3.0),
            "critico": (1.0, 3.0),
            "velocidade": (2.0, 6.0),
            "regen_hp": (0.2, 0.8),
            "regen_mp": (0.2, 0.8),
        }
        stat = random.choice(tuple(opcoes))
        valor = round(random.uniform(*opcoes[stat]), 2)
        eq.stats[stat] = round(eq.stats.get(stat, 0.0) + valor, 2)
        eq.encantamentos += 1
        self.recalcular()
        return f"+{valor} {STAT_NOMES.get(stat, stat)}"

    def equipar(self, item: Item) -> bool:
        if not isinstance(item, Equipamento):
            return False
        if item.classe and item.classe != self.classe:
            return False
        atual = self.equipamentos.get(item.slot)
        self.equipamentos[item.slot] = item
        self.remover_item(item)
        if atual is not None:
            self.inventario.append(atual)
        self.recalcular()
        return True

    def desequipar(self, slot: str) -> bool:
        equipamento = self.equipamentos.get(slot)
        if equipamento is None:
            return False
        if len(self.inventario) >= CAPACIDADE_INVENTARIO:
            return False
        self.equipamentos[slot] = None
        self.inventario.append(equipamento)
        self.recalcular()
        return True

    def usar_pocao(self, pocao: Pocao) -> bool:
        if not isinstance(pocao, Pocao) or pocao not in self.inventario:
            return False
        if pocao.tipo == "vida":
            if self.hp >= self.hp_max - 0.5:
                return False
            self.hp = min(self.hp_max, self.hp + self.hp_max * 0.35)
        elif pocao.tipo == "mana":
            if self.mp >= self.mp_max - 0.5:
                return False
            self.mp = min(self.mp_max, self.mp + self.mp_max * 0.40)
        else:
            if self.stamina >= self.stamina_max - 0.5:
                return False
            self.stamina = min(self.stamina_max, self.stamina + 60)
        pocao.quantidade -= 1
        if pocao.quantidade <= 0:
            self.inventario.remove(pocao)
        return True

    def encaixar_cristal(self, cristal: Cristal, slot: str) -> bool:
        equipamento = self.equipamentos.get(slot)
        if equipamento is None or cristal not in self.inventario:
            return False
        if equipamento.encaixar(cristal):
            self.inventario.remove(cristal)
            self.recalcular()
            return True
        return False

    def remover_cristal(self, slot: str, indice: int) -> bool:
        equipamento = self.equipamentos.get(slot)
        if equipamento is None:
            return False
        cristal = equipamento.remover_cristal(indice)
        if cristal is None:
            return False
        if not self.adicionar_item(cristal):
            equipamento.encaixar(cristal)
            return False
        self.recalcular()
        return True

    # ------------------------------------------------------------------ combate
    def rolar_dano(self, multiplicador: float = 1.0) -> tuple[float, bool]:
        s = self.stats_totais()
        dano = s["ataque"] * multiplicador * random.uniform(1.0 - DANO_VARIACAO, 1.0 + DANO_VARIACAO)
        critico = random.random() * 100.0 < s["critico"]
        if critico:
            dano *= CRITICO_MULT
        return max(1.0, dano), critico

    def atacar(self, jogo: Any, alvo: Sequence[float]) -> bool:
        if self.morto or self.tempo_ataque > 0:
            return False
        angulo = math.atan2(alvo[1] - self.y, alvo[0] - self.x)
        self.angulo_ataque = angulo
        self.ataque_anim = 0.24
        self.facing = (math.cos(angulo), math.sin(angulo))
        classe = self.classe
        sons = getattr(jogo, "sons", None)
        if sons is not None:
            if classe == "Arqueira":
                sons.tocar("flecha", 0.6)
            elif classe == "Maga":
                sons.tocar("magia", 0.5)
            else:
                sons.tocar("golpe", 0.45)
        if classe == "Cavaleiro":
            self.tempo_ataque = 0.55
            acertou = False
            for inimigo in jogo.inimigos:
                if not inimigo.vivo:
                    continue
                d = distancia((self.x, self.y), (inimigo.x, inimigo.y))
                if d > 96 + inimigo.raio:
                    continue
                ang_alvo = math.atan2(inimigo.y - self.y, inimigo.x - self.x)
                diff = (ang_alvo - angulo + math.pi) % math.tau - math.pi
                if abs(diff) <= 1.15:
                    dano, critico = self.rolar_dano(1.15)
                    inimigo.receber_dano(dano, jogo, critico)
                    acertou = True
            jogo.efeito_ataque(self, angulo, "espada")
            return acertou
        if classe == "Arqueira":
            self.tempo_ataque = 0.42
            dano, critico = self.rolar_dano(0.98)
            jogo.criar_projetil_jogador(
                self.x, self.y, angulo, 780.0, dano, 7, (196, 244, 160),
                "flecha", critico=critico,
            )
            jogo.efeito_ataque(self, angulo, "arco")
            return True
        self.tempo_ataque = 0.58
        dano, critico = self.rolar_dano(1.05)
        jogo.criar_projetil_jogador(
            self.x, self.y, angulo, 590.0, dano, 10, (196, 132, 250),
            "arcano", critico=critico,
        )
        jogo.efeito_ataque(self, angulo, "cajado")
        return True

    def esquivar(self, jogo: Any, direcao: Sequence[float] | None = None) -> bool:
        """Rolamento curto com invencibilidade e custo de stamina."""
        if self.morto or self.esquiva_cooldown > 0 or self.esquiva_timer > 0:
            return False
        if self.stamina < CUSTO_ESQUIVA:
            jogo.ui.notificar("Stamina insuficiente para esquivar.", AMARELO)
            return False
        dx, dy = direcao if direcao is not None else self.facing
        nx, ny = normalizar(float(dx), float(dy))
        if nx == 0.0 and ny == 0.0:
            nx, ny = self.facing
        self.esquiva_dx, self.esquiva_dy = nx, ny
        self.esquiva_timer = DURACAO_ESQUIVA
        self.esquiva_cooldown = COOLDOWN_ESQUIVA
        self.esquiva_usada = True
        self.stamina = max(0.0, self.stamina - CUSTO_ESQUIVA)
        self.regen_stamina_delay = ATRASO_REGEN_STAMINA
        self.invulneravel = max(self.invulneravel, INVULNERABILIDADE_ESQUIVA)
        self.facing = (nx, ny)
        jogo.sons.tocar("esquiva", 0.55)
        jogo.particulas.emitir(self.x, self.y - 18, (190, 230, 255), 10, 70, 3, 0.35)
        perto = any(
            i.vivo and i.preparando
            and distancia((self.x, self.y), (i.x, i.y)) < 150
            for i in jogo.inimigos
        )
        if perto:
            jogo.parar_tempo(0.14)
            jogo.piscar((170, 230, 255), 0.18)
            self.stamina = min(self.stamina_max, self.stamina + CUSTO_ESQUIVA * 0.5)
            jogo.ui.notificar("Esquiva perfeita!", (150, 230, 255))
            jogo.particulas.emitir(self.x, self.y - 20, (210, 245, 255), 18, 120, 4, 0.5)
        return True

    def usar_habilidade(self, indice: int, jogo: Any, alvo: Sequence[float]) -> bool:
        if self.morto or indice < 0 or indice >= len(self.habilidades):
            return False
        h = self.habilidades[indice]
        if self.cooldowns.get(h.id, 0.0) > 0:
            return False
        custo = h.custo_atual
        if h.custo_tipo == "mp" and self.mp < custo:
            return False
        if h.custo_tipo == "stamina" and self.stamina < custo:
            return False
        if h.custo_tipo == "mp":
            self.mp -= custo
            self.regen_mp_delay = ATRASO_REGEN_MP
        else:
            self.stamina -= custo
            self.regen_stamina_delay = ATRASO_REGEN_STAMINA
        self.cooldowns[h.id] = h.cooldown_atual
        self.angulo_ataque = math.atan2(alvo[1] - self.y, alvo[0] - self.x)
        self.facing = (math.cos(self.angulo_ataque), math.sin(self.angulo_ataque))
        jogo.executar_habilidade(self, h, alvo)
        return True

    def empurrar(self, origem: Sequence[float], forca: float = 320.0) -> None:
        """Arremessa o jogador para longe da origem do dano (knockback)."""
        dx, dy = self.x - origem[0], self.y - origem[1]
        d = math.hypot(dx, dy)
        if d < 1e-3:
            return
        self.kb_x = clamp(self.kb_x + dx / d * forca, -420.0, 420.0)
        self.kb_y = clamp(self.kb_y + dy / d * forca, -420.0, 420.0)

    def receber_dano(
        self, dano: float, jogo: Any, critico: bool = False, origem: Sequence[float] | None = None,
    ) -> float:
        if self.morto or self.invulneravel > 0:
            return 0.0
        defesa = self.stats_totais()["defesa"]
        dano_final = max(1.0, dano * (100.0 / (100.0 + defesa * 2.2)))
        self.hp -= dano_final
        self.hit_flash = 0.14
        self.invulneravel = 0.22
        if origem is not None:
            self.empurrar(origem)
        jogo.registrar_dano_jogador(self, dano_final, critico)
        if self.hp <= 0:
            self.hp = 0
            self.morto = True
            self.tempo_morte = 0.0
            jogo.jogador_morreu()
        return dano_final

    def curar(self, quantidade: float) -> None:
        self.hp = min(self.hp_max, self.hp + quantidade)

    def restaurar_mp(self, quantidade: float) -> None:
        self.mp = min(self.mp_max, self.mp + quantidade)

    def aplicar_buff(self, nome: str, stats: dict[str, float], duracao: float) -> None:
        self.buffs[nome] = {"tempo": duracao, "stats": dict(stats)}

    # ------------------------------------------------------------------ update
    def atualizar(self, dt: float, jogo: Any) -> None:
        self.tempo += dt
        for chave in list(self.cooldowns):
            self.cooldowns[chave] = max(0.0, self.cooldowns[chave] - dt)
        for nome in list(self.buffs):
            self.buffs[nome]["tempo"] -= dt
            if self.buffs[nome]["tempo"] <= 0:
                del self.buffs[nome]
        self.tempo_ataque = max(0.0, self.tempo_ataque - dt)
        self.ataque_anim = max(0.0, self.ataque_anim - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.invulneravel = max(0.0, self.invulneravel - dt)
        self.level_flash = max(0.0, self.level_flash - dt)

        if self.morto:
            self.tempo_morte += dt
            return

        self.esquiva_cooldown = max(0.0, self.esquiva_cooldown - dt)
        if self.esquiva_timer > 0:
            self.esquiva_timer = max(0.0, self.esquiva_timer - dt)
            self.mover(
                self.esquiva_dx * VELOCIDADE_ESQUIVA * dt,
                self.esquiva_dy * VELOCIDADE_ESQUIVA * dt,
                jogo.mundo,
            )
            self.andando = True
            self.correndo = False
            self.walk_phase += VELOCIDADE_ESQUIVA * dt * 0.05
            self._esquiva_particula -= dt
            if self._esquiva_particula <= 0:
                self._esquiva_particula = 0.035
                jogo.particulas.emitir(self.x, self.y - 18, (170, 220, 255), 2, 30, 3, 0.28)
            return

        s = self.stats_totais()
        self.regen_mp_delay = max(0.0, self.regen_mp_delay - dt)
        self.regen_stamina_delay = max(0.0, self.regen_stamina_delay - dt)
        self.fome = max(0.0, self.fome - dt * 0.12)
        faminto = self.fome <= 0.0
        if not faminto:
            self.hp = min(self.hp_max, self.hp + s["regen_hp"] * dt)
        if self.regen_mp_delay <= 0:
            taxa_mp = s["regen_mp"] * (0.5 if faminto else 1.0)
            self.mp = min(self.mp_max, self.mp + taxa_mp * dt)

        if abs(self.kb_x) > 1.0 or abs(self.kb_y) > 1.0:
            self.mover(self.kb_x * dt, self.kb_y * dt, jogo.mundo)
            self.kb_x *= 0.80
            self.kb_y *= 0.80
        else:
            self.kb_x = self.kb_y = 0.0

        entrada = getattr(jogo, "entrada", None)
        if entrada is not None:
            dx, dy = entrada.eixo_movimento()
            quer_correr = entrada.correndo()
        else:
            dx, dy = teclado_movimento()
            quer_correr = teclado_correndo()
        magnitude = min(1.0, math.hypot(dx, dy))
        correndo = bool(quer_correr and self.stamina > 1 and magnitude > 0)
        if correndo:
            self.stamina = max(0.0, self.stamina - CUSTO_CORRIDA * dt)
        elif self.regen_stamina_delay <= 0:
            taxa_stamina = REGEN_STAMINA * (0.5 if faminto else 1.0)
            self.stamina = min(self.stamina_max, self.stamina + taxa_stamina * dt)
        self.correndo = correndo

        if magnitude > 0:
            nx, ny = normalizar(float(dx), float(dy))
            self.facing = (nx, ny)
            # Analógico parcialmente inclinado anda mais devagar; teclado é sempre 1.0.
            fator = 0.35 + 0.65 * magnitude
            velocidade = s["velocidade"] * (VEL_CORRIDA if correndo else 1.0) * fator
            self.andando = True
            self.walk_phase += velocidade * dt * 0.055
            self.mover(nx * velocidade * dt, ny * velocidade * dt, jogo.mundo)
        else:
            self.andando = False
            self.walk_phase += dt * 2.0

        self.x = clamp(self.x, 24, jogo.mundo.largura - 24)
        self.y = clamp(self.y, 24, jogo.mundo.altura - 24)

    def mover(self, dx: float, dy: float, mundo: Any) -> None:
        hitbox = pygame.Rect(int(self.x - 13), int(self.y - 10), 26, 20)
        hitbox.x += int(dx)
        if not mundo.colidir_rect(hitbox):
            self.x += dx
        else:
            hitbox.x -= int(dx)
        hitbox.y += int(dy)
        if not mundo.colidir_rect(hitbox):
            self.y += dy

    # ------------------------------------------------------------------ save
    def to_dict(self) -> dict[str, Any]:
        def serializar(item: Item) -> dict[str, Any]:
            return item.to_dict()
        return {
            "classe": self.classe,
            "nome": self.nome,
            "nivel": self.nivel,
            "xp": self.xp,
            "atributos": self.atributos,
            "pontos_status": self.pontos_status,
            "pontos_habilidade": self.pontos_habilidade,
            "ouro": self.ouro,
            "inventario": [serializar(i) for i in self.inventario],
            "equipamentos": {
                slot: (eq.to_dict() if eq else None)
                for slot, eq in self.equipamentos.items()
            },
            "habilidades": [h.to_dict() for h in self.habilidades],
            "x": self.x,
            "y": self.y,
            "kills": self.kills,
            "bosses": self.bosses,
            "fome": self.fome,
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "Jogador":
        jogador = cls(str(dados.get("classe", "Cavaleiro")), str(dados.get("nome", "Herói")))
        jogador.nivel = int(dados.get("nivel", 1))
        jogador.xp = int(dados.get("xp", 0))
        jogador.xp_proximo = xp_para_nivel(jogador.nivel)
        jogador.atributos.update({k: int(v) for k, v in dados.get("atributos", {}).items() if k in jogador.atributos})
        jogador.pontos_status = int(dados.get("pontos_status", 0))
        jogador.pontos_habilidade = int(dados.get("pontos_habilidade", 0))
        jogador.ouro = int(dados.get("ouro", 0))
        jogador.kills = int(dados.get("kills", 0))
        jogador.bosses = int(dados.get("bosses", 0))
        jogador.x = float(dados.get("x", 0.0))
        jogador.y = float(dados.get("y", 0.0))
        jogador.fome = max(0.0, min(jogador.fome_max, float(dados.get("fome", jogador.fome_max))))

        jogador.inventario.clear()
        for dados_item in dados.get("inventario", []):
            if not isinstance(dados_item, dict):
                continue
            if "slot" in dados_item:
                jogador.inventario.append(Equipamento.from_dict(dados_item))
            elif "quantidade" in dados_item:
                jogador.inventario.append(Pocao.from_dict(dados_item))
            elif "tier" in dados_item:
                jogador.inventario.append(Cristal.from_dict(dados_item))

        for slot, dados_eq in dados.get("equipamentos", {}).items():
            if slot in jogador.equipamentos and isinstance(dados_eq, dict):
                jogador.equipamentos[slot] = Equipamento.from_dict(dados_eq)

        por_id = {h.id: h for h in jogador.habilidades}
        for dados_h in dados.get("habilidades", []):
            if isinstance(dados_h, dict) and dados_h.get("id") in por_id:
                por_id[dados_h["id"]].from_dict(dados_h)

        jogador.recalcular()
        jogador.hp = float(jogador.hp_max)
        jogador.mp = float(jogador.mp_max)
        jogador.stamina = float(jogador.stamina_max)
        return jogador

    # ------------------------------------------------------------------ draw
    def desenhar(self, surf: pygame.Surface, camera: Any) -> None:
        from player_art import desenhar_jogador
        desenhar_jogador(self, surf, camera)
