"""Inimigos: atributos, IA, ataques e bosses raros."""
from __future__ import annotations

import math
import random
from typing import Any

import pygame

from utils import distancia, normalizar


NOMES_INIMIGOS = {
    "slime": "Slime",
    "goblin": "Goblin",
    "wisp": "Fada",
    "golem": "Golem",
    "slime_cristal": "Slime de Cristal",
    "morcego": "Morcego Sombrio",
    "aranha": "Aranha das Ruínas",
    "elemental_cristal": "Elemental de Cristal",
    "lobo": "Lobo Sombrio",
    "serpente": "Serpente de Cristal",
    "sapo": "Sapo do Lodo",
    "mosquito": "Mosquito Gigante",
    "lodo": "Lodo Vivo",
    "escorpiao": "Escorpião de Obsidiana",
    "golem_obsidiana": "Golem de Obsidiana",
    "sentinela_aether": "Sentinela de Aether",
    "espectro_aether": "Espectro de Aether",
    "serpente_aether": "Serpente de Aether",
    "sombra_eclipse": "Sombra do Eclipse",
    "ceifador_espelhado": "Ceifador Espelhado",
    "serpente_vazio": "Serpente do Vazio",
    "guardiao_eclipse": "Guardião do Eclipse",
    "avatar_aether": "Avatar de Aether",
    "devorador": "Devorador de Cristais",
    "ceifador_nevoa": "Ceifador de Névoa",
    "serpente_colossal": "Serpente Colossal",
    "rei_slime": "Rei Slime",
    "golem_anciao": "Golem Ancião",
    "rainha_lodo": "Rainha do Lodo",
    "colosso_obsidiana": "Colosso de Obsidiana",
    "senhor_fragmentos": "Senhor dos Fragmentos",
}

BASES_INIMIGOS = {
    "slime": {
        "hp": 30, "atk": 6, "df": 1, "vel": 72, "xp": 13, "raio": 17,
        "cor": (86, 196, 124), "ranged": False, "boss": False,
    },
    "goblin": {
        "hp": 44, "atk": 9, "df": 3, "vel": 108, "xp": 19, "raio": 18,
        "cor": (112, 176, 96), "ranged": False, "boss": False,
    },
    "wisp": {
        "hp": 36, "atk": 11, "df": 2, "vel": 88, "xp": 22, "raio": 16,
        "cor": (120, 210, 240), "ranged": True, "boss": False,
    },
    "golem": {
        "hp": 92, "atk": 14, "df": 8, "vel": 58, "xp": 34, "raio": 24,
        "cor": (122, 128, 146), "ranged": False, "boss": False,
    },
    "slime_cristal": {
        "hp": 70, "atk": 16, "df": 6, "vel": 80, "xp": 31, "raio": 20,
        "cor": (150, 96, 206), "ranged": False, "boss": False,
    },
    "morcego": {
        "hp": 26, "atk": 8, "df": 1, "vel": 138, "xp": 17, "raio": 14,
        "cor": (128, 96, 178), "ranged": False, "boss": False,
    },
    "aranha": {
        "hp": 38, "atk": 10, "df": 2, "vel": 118, "xp": 21, "raio": 16,
        "cor": (96, 72, 128), "ranged": True, "boss": False,
    },
    "elemental_cristal": {
        "hp": 118, "atk": 18, "df": 11, "vel": 50, "xp": 44, "raio": 26,
        "cor": (110, 210, 240), "ranged": False, "boss": False,
    },
    "lobo": {
        "hp": 48, "atk": 11, "df": 2, "vel": 150, "xp": 24, "raio": 18,
        "cor": (92, 98, 132), "ranged": False, "boss": False,
    },
    "serpente": {
        "hp": 62, "atk": 14, "df": 4, "vel": 92, "xp": 30, "raio": 20,
        "cor": (110, 220, 190), "ranged": True, "boss": False,
    },
    "sapo": {
        "hp": 132, "atk": 22, "df": 7, "vel": 96, "xp": 58, "raio": 21,
        "cor": (108, 176, 88), "ranged": False, "boss": False,
    },
    "mosquito": {
        "hp": 78, "atk": 19, "df": 3, "vel": 168, "xp": 50, "raio": 14,
        "cor": (164, 138, 92), "ranged": True, "boss": False,
    },
    "lodo": {
        "hp": 192, "atk": 24, "df": 13, "vel": 48, "xp": 68, "raio": 25,
        "cor": (104, 138, 84), "ranged": False, "boss": False,
    },
    "escorpiao": {
        "hp": 150, "atk": 26, "df": 8, "vel": 122, "xp": 76, "raio": 20,
        "cor": (156, 68, 92), "ranged": False, "boss": False,
    },
    "golem_obsidiana": {
        "hp": 268, "atk": 28, "df": 16, "vel": 46, "xp": 92, "raio": 28,
        "cor": (112, 58, 72), "ranged": False, "boss": False,
    },
    "sentinela_aether": {
        "hp": 240, "atk": 58, "df": 16, "vel": 58, "xp": 150, "raio": 26,
        "cor": (176, 232, 255), "ranged": True, "boss": False, "poise": 900,
    },
    "espectro_aether": {
        "hp": 200, "atk": 62, "df": 12, "vel": 142, "xp": 145, "raio": 22,
        "cor": (186, 164, 250), "ranged": False, "boss": False, "poise": 700,
    },
    "serpente_aether": {
        "hp": 280, "atk": 60, "df": 15, "vel": 96, "xp": 160, "raio": 24,
        "cor": (132, 240, 222), "ranged": True, "boss": False, "poise": 1000,
    },
    "devorador": {
        "hp": 640, "atk": 24, "df": 12, "vel": 78, "xp": 520, "raio": 38,
        "cor": (196, 82, 168), "ranged": False, "boss": True,
        "conta_progresso": False, "errante": True,
    },
    "ceifador_nevoa": {
        "hp": 520, "atk": 26, "df": 10, "vel": 118, "xp": 560, "raio": 34,
        "cor": (150, 200, 230), "ranged": True, "boss": True,
        "conta_progresso": False, "errante": True,
    },
    "serpente_colossal": {
        "hp": 780, "atk": 30, "df": 16, "vel": 92, "xp": 640, "raio": 40,
        "cor": (120, 230, 180), "ranged": True, "boss": True,
        "conta_progresso": False, "errante": True,
    },
    "rei_slime": {
        "hp": 380, "atk": 16, "df": 6, "vel": 66, "xp": 300, "raio": 32,
        "cor": (86, 206, 130), "ranged": False, "boss": True,
    },
    "golem_anciao": {
        "hp": 860, "atk": 24, "df": 14, "vel": 54, "xp": 760, "raio": 38,
        "cor": (132, 138, 158), "ranged": False, "boss": True,
    },
    "senhor_fragmentos": {
        "hp": 1550, "atk": 32, "df": 20, "vel": 62, "xp": 1600, "raio": 42,
        "cor": (156, 96, 218), "ranged": True, "boss": True,
    },
    "rainha_lodo": {
        "hp": 1500, "atk": 32, "df": 18, "vel": 68, "xp": 1500, "raio": 42,
        "cor": (120, 190, 130), "ranged": False, "boss": True,
    },
    "colosso_obsidiana": {
        "hp": 2200, "atk": 38, "df": 24, "vel": 58, "xp": 2200, "raio": 46,
        "cor": (140, 60, 74), "ranged": False, "boss": True,
    },
    "avatar_aether": {
        "hp": 1700, "atk": 92, "df": 30, "vel": 64, "xp": 4000, "raio": 50,
        "cor": (196, 232, 255), "ranged": True, "boss": True,
    },
    "sombra_eclipse": {
        "hp": 300, "atk": 128, "df": 22, "vel": 132, "xp": 190, "raio": 24,
        "cor": (120, 80, 180), "ranged": False, "boss": False, "poise": 800,
    },
    "ceifador_espelhado": {
        "hp": 260, "atk": 136, "df": 18, "vel": 108, "xp": 185, "raio": 22,
        "cor": (190, 200, 230), "ranged": True, "boss": False, "poise": 700,
    },
    "serpente_vazio": {
        "hp": 340, "atk": 132, "df": 20, "vel": 96, "xp": 200, "raio": 24,
        "cor": (90, 180, 170), "ranged": True, "boss": False, "poise": 900,
    },
    "guardiao_eclipse": {
        "hp": 3200, "atk": 160, "df": 60, "vel": 70, "xp": 6000, "raio": 48,
        "cor": (160, 120, 220), "ranged": True, "boss": True,
        "conta_progresso": False,
    },
}


class Inimigo:
    def __init__(self, tipo: str, nivel: int, x: float, y: float) -> None:
        base = BASES_INIMIGOS.get(tipo, BASES_INIMIGOS["slime"])
        self.tipo = tipo
        self.nome = NOMES_INIMIGOS.get(tipo, tipo.title())
        self.nivel = max(1, int(nivel))
        self.x, self.y = x, y
        self.spawn_x, self.spawn_y = x, y
        self.boss = bool(base["boss"])
        self.errante = bool(base.get("errante", False))
        # bosses errantes não contam para o selo da Caverna
        self.conta_progresso = bool(base.get("conta_progresso", True))
        self.ranged = bool(base["ranged"])
        self.cor = base["cor"]
        self.raio = float(base["raio"]) * (1.0 if not self.boss else 1.0)

        escala_hp = 1.0 + 0.24 * (self.nivel - 1)
        escala_atk = 1.0 + 0.17 * (self.nivel - 1)
        escala_df = 1.0 + 0.11 * (self.nivel - 1)
        self.hp_max = float(base["hp"]) * escala_hp
        self.hp = self.hp_max
        self.ataque = float(base["atk"]) * escala_atk
        self.defesa = float(base["df"]) * escala_df
        self.velocidade = float(base["vel"])
        if self.boss:
            # bosses já dão muita XP; escala suave para não trivializar a curva
            escala_xp = min(2.0, 1.0 + 0.08 * (self.nivel - 1))
        else:
            escala_xp = 1.0 + 0.28 * (self.nivel - 1)
        self.xp_recompensa = int(base["xp"] * escala_xp)

        self.aggro = 460.0 if self.boss else 270.0
        self.ataque_raio = 250.0 if self.ranged else (94.0 if self.boss else 54.0)
        self.ataque_cooldown = 1.9 if self.ranged else (1.35 if self.boss else 1.25)
        self.ataque_timer = random.uniform(0.2, 0.8)
        self.especial_timer = random.uniform(3.0, 5.0)

        self.estado = "idle"
        self.estado_timer = random.uniform(0.5, 2.0)
        self.wander = (0.0, 0.0)
        self.facing = (0.0, 1.0)
        self.walk_phase = random.uniform(0, 6.28)
        self.tempo = random.uniform(0, 10)
        self.hit_flash = 0.0
        self.slow_timer = 0.0
        self.kb_x = 0.0
        self.kb_y = 0.0
        self.preparando = False
        self.preparo = 0.0
        self.tipo_preparo = "normal"
        self.vivo = True
        self.fase = 1
        self.anunciado = False

        # status, atordoamento e poise (resistência a stagger)
        self.status: dict[str, dict[str, float]] = {}
        self.status_tick = 0.0
        self.stun_timer = 0.0
        self.poise_max = 260.0 if self.boss else float(base.get("poise", 45.0 + self.raio * 2.0))
        self.poise = 0.0
        self._status_particula = 0.0
        # elite (afixo) e ataque com direção travada no telegrafo
        self.elite = False
        self.afixo = ""
        self.cor_elite = (250, 210, 110)
        self.filhote = False
        self.ataque_angulo = 0.0

    # ------------------------------------------------------------------ dano
    def receber_dano(self, dano: float, jogo: Any, critico: bool = False) -> float:
        if not self.vivo:
            return 0.0
        dano_final = max(1.0, dano * (100.0 / (100.0 + self.defesa * 2.0)))
        self.hp -= dano_final
        self.hit_flash = 0.13
        ang = math.atan2(self.y - jogo.jogador.y, self.x - jogo.jogador.x)
        forca = 40.0 if self.boss else 130.0
        self.kb_x += math.cos(ang) * forca
        self.kb_y += math.sin(ang) * forca
        jogo.registrar_dano_inimigo(self, dano_final, critico)
        if not self.boss and self.stun_timer <= 0:
            self.poise += dano_final
            if self.poise >= self.poise_max:
                self.poise = 0.0
                self.aplicar_status("atordoado", 0.0, 0.55)
                jogo.particulas.emitir(self.x, self.y - self.raio * 1.6, (250, 230, 140), 14, 90, 3, 0.4)
        if self.hp <= 0:
            self.hp = 0
            self.morrer(jogo)
        return dano_final

    def aplicar_status(self, tipo: str, dano_por_segundo: float, tempo: float) -> None:
        """Aplica/renova um status; bosses e elites resistem parcialmente."""
        if not self.vivo or tempo <= 0:
            return
        if self.boss:
            tempo *= 0.5
            dano_por_segundo *= 0.5
        elif self.elite and tipo == "atordoado":
            tempo *= 0.6
        atual = self.status.get(tipo)
        if atual is None:
            self.status[tipo] = {"tempo": tempo, "dano": max(0.0, dano_por_segundo)}
        else:
            atual["tempo"] = max(atual["tempo"], tempo)
            atual["dano"] = max(atual["dano"], dano_por_segundo)
        if tipo == "gelo":
            self.slow_timer = max(self.slow_timer, tempo)
        if tipo == "atordoado":
            self.stun_timer = max(self.stun_timer, tempo)
        if dano_por_segundo > 0 and self.status_tick <= 0:
            self.status_tick = 0.5

    def _atualizar_status(self, dt: float, jogo: Any) -> None:
        for tipo in list(self.status):
            self.status[tipo]["tempo"] -= dt
            if self.status[tipo]["tempo"] <= 0:
                del self.status[tipo]
        if self.status:
            self._status_particula -= dt
            if self._status_particula <= 0:
                self._status_particula = 0.18
                for tipo in self.status:
                    cor = {
                        "queimadura": (250, 140, 70),
                        "veneno": (140, 220, 100),
                        "sangramento": (230, 80, 100),
                        "gelo": (120, 220, 250),
                        "atordoado": (250, 220, 120),
                    }.get(tipo)
                    if cor is not None:
                        jogo.particulas.emitir(self.x, self.y - self.raio, cor, 1, 24, 2, 0.3)
        self.status_tick -= dt
        if self.status_tick > 0:
            return
        self.status_tick = 0.5
        ativos = [
            (tipo, dados["dano"])
            for tipo, dados in self.status.items()
            if tipo in ("queimadura", "veneno", "sangramento") and dados["dano"] > 0
        ]
        if not ativos:
            return
        tipo, _ = max(ativos, key=lambda par: par[1])
        total = sum(dano * 0.5 for _, dano in ativos)
        self.hp -= total
        jogo.registrar_dano_status(self, total, tipo)
        if self.hp <= 0:
            self.hp = 0
            self.morrer(jogo)

    def morrer(self, jogo: Any) -> None:
        if not self.vivo:
            return
        self.vivo = False
        jogo.inimigo_morreu(self)

    # ------------------------------------------------------------------ update
    def atualizar(self, dt: float, jogo: Any) -> None:
        if not self.vivo:
            return
        self.tempo += dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.ataque_timer = max(0.0, self.ataque_timer - dt)
        self.slow_timer = max(0.0, self.slow_timer - dt)
        self.stun_timer = max(0.0, self.stun_timer - dt)
        self.poise = max(0.0, self.poise - 12.0 * dt)
        self._atualizar_status(dt, jogo)
        if not self.vivo:
            return
        if self.stun_timer > 0:
            self.preparando = False
            self.estado = "idle"
            return

        if abs(self.kb_x) > 1 or abs(self.kb_y) > 1:
            self.mover(self.kb_x * dt, self.kb_y * dt, jogo.mundo)
            self.kb_x *= 0.82
            self.kb_y *= 0.82

        jogador = jogo.jogador
        if jogador.morto:
            self.preparando = False
            self.estado = "idle"
            return
        zona_jogador = jogo.mundo.zona_em(jogador.x, jogador.y)
        if zona_jogador is not None and zona_jogador.seguro:
            self.preparando = False
            self.estado = "idle"
            return

        d = distancia((self.x, self.y), (jogador.x, jogador.y))
        aggro = self.aggro * (1.15 if getattr(jogo, "eh_noite", lambda: False)() else 1.0)

        if self.boss and self.fase == 1 and self.hp < self.hp_max * 0.5:
            self.fase = 2
            self.velocidade *= 1.18
            self.ataque_cooldown *= 0.8
            jogo.sons.tocar("fase_boss", 1.0)
            jogo.anunciar(f"{self.nome} enfureceu!", (250, 160, 90))

        if self.preparando:
            self.preparo -= dt
            if self.preparo <= 0:
                self.preparando = False
                if self.tipo_preparo == "especial":
                    jogo.executar_especial_boss(self)
                else:
                    self.executar_ataque(jogo)
                self.ataque_timer = self.ataque_cooldown
                if self.elite and random.random() < 0.30:
                    # elites encadeiam um segundo golpe mais rápido
                    self.ataque_timer *= 0.45
            return

        if self.boss:
            self.especial_timer -= dt
            if self.especial_timer <= 0 and d < aggro:
                self.preparando = True
                self.preparo = 0.75
                self.tipo_preparo = "especial"
                jogo.avisar_ataque(self)
                return

        if d > aggro * 1.8 and not self.boss:
            self.estado = "idle"
        elif d <= aggro:
            self.estado = "chase"
        elif self.estado != "idle":
            self.estado = "idle"

        if self.estado == "idle":
            self.estado_timer -= dt
            if self.estado_timer <= 0:
                self.estado_timer = random.uniform(1.2, 3.2)
                ang = random.uniform(0, math.tau)
                self.wander = (math.cos(ang), math.sin(ang))
            # volta para perto do spawn se estiver longe
            d_spawn = distancia((self.x, self.y), (self.spawn_x, self.spawn_y))
            if d_spawn > 160 and not self.boss:
                nx, ny = normalizar(self.spawn_x - self.x, self.spawn_y - self.y)
                self.mover(nx * self.velocidade * 0.45 * dt, ny * self.velocidade * 0.45 * dt, jogo.mundo)
                self.facing = (nx, ny)
            elif self.wander != (0.0, 0.0):
                self.mover(self.wander[0] * self.velocidade * 0.3 * dt, self.wander[1] * self.velocidade * 0.3 * dt, jogo.mundo)
                self.facing = self.wander
                self.walk_phase += self.velocidade * dt * 0.02
            return

        # perseguição
        if self.ranged and not self.boss:
            if d < 145:
                nx, ny = normalizar(self.x - jogador.x, self.y - jogador.y)
                self.mover(nx * self.velocidade * dt, ny * self.velocidade * dt, jogo.mundo)
                self.facing = (nx, ny)
            elif d > 215:
                nx, ny = normalizar(jogador.x - self.x, jogador.y - self.y)
                self.mover(nx * self.velocidade * dt, ny * self.velocidade * dt, jogo.mundo)
                self.facing = (nx, ny)
            else:
                self.facing = normalizar(jogador.x - self.x, jogador.y - self.y)
                # Missao 05.20: gatilho de ataque para ranged nao-boss na faixa de combate (145-215)
                if self.ataque_timer <= 0:
                    self.preparando = True
                    self.preparo = 0.55
                    self.tipo_preparo = "normal"
                    self.ataque_angulo = math.atan2(jogador.y - self.y, jogador.x - self.x)
                    jogo.avisar_ataque(self)
        elif d > self.ataque_raio * 0.92:
            nx, ny = normalizar(jogador.x - self.x, jogador.y - self.y)
            vel = self.velocidade * (0.55 if self.slow_timer > 0 else 1.0)
            self.mover(nx * vel * dt, ny * vel * dt, jogo.mundo)
            self.facing = (nx, ny)
            self.walk_phase += vel * dt * 0.05
        else:
            self.facing = normalizar(jogador.x - self.x, jogador.y - self.y)
            if self.ataque_timer <= 0:
                self.preparando = True
                self.preparo = 0.55 if self.ranged else 0.34
                self.tipo_preparo = "normal"
                self.ataque_angulo = math.atan2(jogador.y - self.y, jogador.x - self.x)
                jogo.avisar_ataque(self)

    def mover(self, dx: float, dy: float, mundo: Any) -> None:
        largura = self.raio * 1.25
        altura = self.raio * 0.85
        hitbox = pygame.Rect(int(self.x - largura / 2), int(self.y - altura / 2), int(largura), int(altura))
        hitbox.x += int(dx)
        if not mundo.colidir_rect(hitbox):
            self.x += dx
        else:
            hitbox.x -= int(dx)
        hitbox.y += int(dy)
        if not mundo.colidir_rect(hitbox):
            self.y += dy

    # ------------------------------------------------------------------ ataques
    def executar_ataque(self, jogo: Any) -> None:
        jogador = jogo.jogador
        if jogador.morto:
            return
        d = distancia((self.x, self.y), (jogador.x, jogador.y))
        ang = self.ataque_angulo
        if self.ranged:
            if self.tipo == "senhor_fragmentos":
                cor_proj = (240, 180, 110)
            elif self.tipo == "aranha":
                cor_proj = (150, 230, 120)
            elif self.tipo == "serpente":
                cor_proj = (120, 240, 200)
            elif self.tipo == "mosquito":
                cor_proj = (232, 214, 120)
            elif self.tipo == "escorpiao":
                cor_proj = (230, 100, 130)
            else:
                cor_proj = (130, 210, 240)
            jogo.criar_projetil_inimigo(
                self.x, self.y, ang, 300.0, self.ataque, 9,
                cor_proj,
                "cristal" if self.boss else "magia",
            )
            d = distancia((self.x, self.y), (jogador.x, jogador.y))
            volume = max(0.0, 1.0 - d / 620.0) * (1.0 if self.boss else 0.6)
            if volume > 0.05:
                jogo.sons.tocar("inimigo_projetil", volume, intervalo=0.10)
            jogo.particulas.emitir(self.x, self.y, self.cor, 8, 90, 4, 0.4, direcao=ang, espalhar=0.8)
            if self.afixo == "Vampírico":
                self.hp = min(self.hp_max, self.hp + self.ataque * 0.12)
                jogo.particulas.emitir(self.x, self.y - self.raio, (230, 90, 120), 4, 50, 2, 0.3)
        else:
            ang_alvo = math.atan2(jogador.y - self.y, jogador.x - self.x)
            diff = (ang_alvo - ang + math.pi) % math.tau - math.pi
            if d <= self.ataque_raio + 24 and abs(diff) <= 1.2:
                jogador.receber_dano(self.ataque, jogo, origem=(self.x, self.y))
                if self.afixo == "Vampírico":
                    self.hp = min(self.hp_max, self.hp + self.ataque * 0.25)
                    jogo.particulas.emitir(self.x, self.y - self.raio, (230, 90, 120), 6, 70, 3, 0.35)
            jogo.efeito_ataque_inimigo(self, ang)

    def desenhar(self, surf: pygame.Surface, camera: Any) -> None:
        from enemy_art import desenhar_inimigo
        desenhar_inimigo(self, surf, camera)
