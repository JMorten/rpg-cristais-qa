"""Estado do jogo, loop de atualização e ligação entre sistemas."""
from __future__ import annotations

import logging
import math
import os
import random
from typing import Any

import pygame

from core.audio import Sons
from core.input import Entrada
from core.paths import em_web, legacy_save_path, save_path
from core.preferences import (
    Preferencias, carregar_preferencias, proxima_escala_texto, proximo_volume,
    salvar_preferencias,
)
from core.save import SAVE_VERSION, read_save, write_save
from core.tutorial import Tutorial
from entities import AreaPerigo, Drop, Efeito, Inimigo, Jogador, Projetil
from iluminacao import Iluminacao, Luz
from items import (
    Cristal, Equipamento, Pocao, TIPOS_POCAO, gerar_amuleto_eclipse,
    gerar_cristal, gerar_equipamento, gerar_pocao, gerar_reliquia_eclipse,
    rolar_loot,
)
from npc import NPC, desenhar_indicador
import pixel_arte
from quests import Missoes
from settings import (
    ALTURA, AMARELO, AZUL, BRANCO, CHANCE_ELITE, COOLDOWN_POCAO, CRISTAIS_FORJA,
    CUSTO_FORJA, DOURADO, ECO_MORTE, LARGURA, LUZ_AVANCADA, ROXO, VERDE, VERMELHO,
)
from skills import Habilidade, parametro, som_da_habilidade
from touch import TouchControls
from ui import UI
from ui_panel import ABAS_SERVICOS
from ui_settings import TelaConfiguracoes
from utils import (
    Camera, SistemaParticulas, TextoFlutuante, clamp, definir_escala_texto,
    distancia, etiqueta, lerp, superficie_luz,
)
from world import Mundo, Zona

DISTANCIA_MIRA = 200.0
ALCANCE_ASSISTENCIA = 380.0
CONE_ASSISTENCIA_LIVRE = 0.5      # ~60° quando o analógico direito está solto
CONE_ASSISTENCIA_MIRANDO = 0.94   # ~20° quando o jogador está mirando
VELOCIDADE_CURSOR = 900.0

# Abates de inimigos comuns na zona até o boss raro aparecer, por garantia.
# A chance por abate pode antecipar; este teto existe para o boss não depender de sorte.
PIEDADE_BOSS = {
    "Floresta de Lumen": 15,
    "Ruínas de Aether": 18,
    "Caverna de Cristal": 22,
    "Pântano de Veyra": 20,
    "Desfiladeiro de Obsidiana": 22,
    "Coração de Aether": 20,
    "Fenda do Eclipse": 12,
}
STATUS_CORES = {
    "queimadura": (250, 140, 70),
    "veneno": (140, 220, 100),
    "sangramento": (230, 80, 100),
    "gelo": (120, 220, 250),
    "atordoado": (250, 220, 120),
}
AFIXOS_ELITE = {
    "Veloz": (120, 220, 250),
    "Blindado": (180, 190, 210),
    "Explosivo": (250, 140, 80),
    "Vampírico": (230, 90, 120),
    "Invocador": (190, 150, 240),
}
PRECOS_MERCADO = {
    "pocao_vida": 40,
    "pocao_mana": 50,
    "pocao_stamina": 45,
    "cristal": 120,
    "equipamento": 300,
    "equipamento_epico": 900,
}
CUSTO_REFORCO_BASE = 80
CUSTO_ENCANTAMENTO = 150
CUSTO_RESPEC_BASE = 200
CUSTO_RESPEC_POR_NIVEL = 20
BOSSES_PARA_CAVERNA = 2
ERRANTES = (
    {"tipo": "devorador", "nivel_min": 4, "peso": 3, "vida": 110.0},
    {"tipo": "ceifador_nevoa", "nivel_min": 8, "peso": 2, "vida": 95.0},
    {"tipo": "serpente_colossal", "nivel_min": 14, "peso": 2, "vida": 120.0},
)
EVENTOS = ("veio", "bau", "emboscada", "santuario")
FATOR_PARADA = 0.10      # desaceleração do mundo durante a parada de impacto
PARADA_MAXIMA = 0.35     # teto da parada de impacto, em segundos

# Cor de ambiente por bioma (multiplica a cena antes de somar as luzes).
AMBIENTE_ZONA = {
    "Clareira de Lumen": (255, 252, 242),
    "Floresta de Lumen": (240, 246, 236),
    "Ruínas de Aether": (158, 166, 196),
    "Caverna de Cristal": (118, 110, 148),
    "Pântano de Veyra": (172, 186, 150),
    "Vila de Veyra": (252, 226, 190),
    "Desfiladeiro de Obsidiana": (150, 110, 120),
    "Coração de Aether": (220, 230, 255),
    "Fenda do Eclipse": (120, 90, 150),
}

# Raio e intensidade da luz do jogador por bioma.
LUZ_JOGADOR = {
    "Clareira de Lumen": (200, 60),
    "Floresta de Lumen": (220, 70),
    "Ruínas de Aether": (240, 115),
    "Caverna de Cristal": (260, 150),
    "Pântano de Veyra": (230, 100),
    "Vila de Veyra": (230, 100),
    "Desfiladeiro de Obsidiana": (260, 140),
    "Coração de Aether": (270, 150),
    "Fenda do Eclipse": (300, 120),
}


class Jogo:
    def __init__(self) -> None:
        self.estado = "menu"
        self.rodando = True
        self.tempo = 0.0

        self.mundo = Mundo()
        self.camera = Camera(LARGURA, ALTURA)
        self.ui = UI()
        self.particulas = SistemaParticulas(1200)
        self.toque = TouchControls()
        self.modo_toque = False
        self.modo_desempenho = False
        self._escuridao_surf = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        self.vignette = self._criar_vignette()
        self.iluminacao = Iluminacao()
        self.luz_avancada = LUZ_AVANCADA

        self.jogador: Jogador | None = None
        self.inimigos: list[Inimigo] = []
        self.projeteis: list[Projetil] = []
        self.drops: list[Drop] = []
        self.areas: list[AreaPerigo] = []
        self.efeitos: list[Efeito] = []
        self.textos: list[TextoFlutuante] = []

        self.spawn_timer = 0.0
        self.evento_timer = random.uniform(90, 150)
        self._ultimo_evento = ""
        self.errante_timer = random.uniform(200, 320)
        self.errante_vida = 0.0
        self.boss_ativo: Inimigo | None = None
        self.boss_alerta = 0.0
        self.boss_nome = ""
        self.zona_banner: list[Any] = ["", 0.0]
        self.zona_atual = ""
        self.kills_sem_boss: dict[str, int] = {z.nome: 0 for z in self.mundo.zonas}
        self.quests = Missoes()
        self.servicos_desbloqueados: set[str] = set()
        self.dialogo: list[str] = []
        self.dialogo_timer = 0.0
        self.npc_perto = False
        self.npc_atual: NPC | None = None
        self.npc_dist = 1e9
        self.fogueira_perto: tuple[float, float] | None = None
        self.fogueira_dist = 1e9
        self.eco: Drop | None = None
        self.pocao_cooldown = 0.0
        self.final_derrotado = False
        self.hora = 8.0
        self.duracao_dia = 480.0
        self.chuva = 0.0
        self.chuva_ativa = False
        self.clima_timer = random.uniform(45, 90)
        self._gotas = [
            (
                random.uniform(0, LARGURA), random.uniform(0, ALTURA),
                random.uniform(520, 900), random.randint(8, 18),
            )
            for _ in range(140)
        ]
        self._chuva_surf = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        self._chuva_overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        self.vitoria_timer = 0.0
        self.mouse_world = (0.0, 0.0)
        self.save_path = save_path()
        self.save_path_antigo = legacy_save_path()

        self.prefs = carregar_preferencias()
        self.sons = Sons(
            ativo=os.environ.get("CRISTAIS_SEM_AUDIO") != "1" and not em_web(),
            volume_geral=self.prefs.volume_geral,
            volume_musica=self.prefs.volume_musica,
            volume_efeitos=self.prefs.volume_efeitos,
        )
        self.sons.mudo = self.prefs.mudo
        self._aplicar_iluminacao()
        self.ui_config = TelaConfiguracoes()
        self.config_origem = "menu"
        self.fps = 0.0
        self.tutorial = Tutorial()

        self.entrada = Entrada()
        self._cursor: list[float] | None = None
        self._mouse_visivel = True

        self.hit_stop = 0.0
        self.flash = 0.0
        self.flash_cor = (255, 255, 255)
        self._flash_surf: pygame.Surface | None = None
        self._passo_timer = 0.0
        self._ducking = 1.0

    # ------------------------------------------------------------------ preferências
    def aplicar_preferencias(self, salvar: bool = False) -> bool:
        if salvar:
            salvar_preferencias(self.prefs)
        definir_escala_texto(self.prefs.escala_texto)
        self._aplicar_audio()
        self._aplicar_iluminacao()
        pixel_arte.definir(self.prefs.arte_pixel)
        ok = self._aplicar_tela_cheia(self.prefs.tela_cheia)
        if not ok and self.prefs.tela_cheia:
            self.prefs.tela_cheia = False
            salvar_preferencias(self.prefs)
        return ok

    def aplicar_modo_toque(self, ativo: bool = True) -> None:
        """Ativa o modo mobile: controles na tela e orçamento de render menor."""
        self.modo_toque = ativo
        self.toque.ativo = ativo
        self.entrada.modo_toque = ativo
        self.aplicar_modo_desempenho(ativo)

    def aplicar_modo_desempenho(self, ativo: bool = True) -> None:
        """Orçamento de render reduzido (usado no mobile e no navegador)."""
        self.modo_desempenho = ativo
        if ativo:
            self.particulas.maximo = 250
            self.iluminacao.bloom = False
            self.luz_avancada = False
            self.mundo.qualidade = 0.5
        else:
            self.particulas.maximo = 1200
            self.iluminacao.bloom = self.prefs.bloom
            self.luz_avancada = LUZ_AVANCADA
            self.mundo.qualidade = 1.0

    def _aplicar_tela_cheia(self, ativa: bool) -> bool:
        try:
            flags = pygame.FULLSCREEN if ativa else 0
            pygame.display.set_mode((LARGURA, ALTURA), flags)
            return True
        except pygame.error:
            logging.getLogger("cristais").exception("Falha ao aplicar tela cheia")
            return False

    def alternar_preferencia(self, chave: str) -> None:
        if not hasattr(self.prefs, chave):
            return
        if chave == "tela_cheia":
            novo = not self.prefs.tela_cheia
            if not self._aplicar_tela_cheia(novo):
                self.ui.notificar("Não foi possível alternar a tela cheia.", VERMELHO)
                return
            self.prefs.tela_cheia = novo
        elif chave == "escala_texto":
            self.prefs.escala_texto = proxima_escala_texto(self.prefs.escala_texto)
            definir_escala_texto(self.prefs.escala_texto)
        elif chave.startswith("volume_"):
            setattr(self.prefs, chave, proximo_volume(getattr(self.prefs, chave)))
            self._aplicar_audio()
        elif chave == "mudo":
            self.prefs.mudo = not self.prefs.mudo
            self._aplicar_audio()
        else:
            setattr(self.prefs, chave, not bool(getattr(self.prefs, chave)))
        if chave in ("bloom", "luz_avancada"):
            self._aplicar_iluminacao()
        if chave == "arte_pixel":
            pixel_arte.definir(self.prefs.arte_pixel)
        if not salvar_preferencias(self.prefs):
            self.ui.notificar("Falha ao salvar as configurações.", VERMELHO)

    def resetar_preferencias(self) -> None:
        self.prefs = Preferencias()
        self._aplicar_tela_cheia(False)
        definir_escala_texto(self.prefs.escala_texto)
        self._aplicar_iluminacao()
        if not salvar_preferencias(self.prefs):
            self.ui.notificar("Falha ao salvar as configurações.", VERMELHO)
        else:
            self.ui.notificar("Configurações restauradas.", DOURADO)

    def abrir_configuracoes(self, origem: str) -> None:
        self.config_origem = origem if origem in ("menu", "pausa") else "menu"
        self.estado = "configuracoes"

    def fechar_configuracoes(self) -> None:
        self.estado = self.config_origem

    def tremer(self, forca: float = 8.0, tempo: float = 0.25) -> None:
        if self.prefs.tremer_tela:
            self.camera.tremer(forca, tempo)

    def _aplicar_audio(self) -> None:
        """Leva os volumes e o mudo das preferências para o mixer."""
        self.sons.mudo = self.prefs.mudo
        self.sons.definir_volumes(
            self.prefs.volume_geral, self.prefs.volume_musica, self.prefs.volume_efeitos,
        )

    def _aplicar_iluminacao(self) -> None:
        """Leva bloom e iluminação das preferências para o renderer."""
        self.luz_avancada = LUZ_AVANCADA and self.prefs.luz_avancada
        self.iluminacao.bloom = self.prefs.bloom

    def _atualizar_musica(self) -> None:
        if not self.sons.disponivel:
            return
        if self.estado in ("menu", "selecao", "configuracoes"):
            self.sons.tocar_musica("clareira")
            return
        if self.estado == "morte":
            self.sons.tocar_musica(None)
            return
        if self.estado == "vitoria":
            self.sons.tocar_musica("clareira")
            return
        mapa = {
            "Clareira de Lumen": "clareira",
            "Floresta de Lumen": "floresta",
            "Ruínas de Aether": "ruinas",
            "Caverna de Cristal": "caverna",
            "Pântano de Veyra": "pantano",
            "Vila de Veyra": "clareira",
            "Desfiladeiro de Obsidiana": "desfiladeiro",
            "Coração de Aether": "coracao",
            "Fenda do Eclipse": "eclipse",
        }
        self.sons.tocar_musica(mapa.get(self.zona_atual, "floresta"))

    def parar_tempo(self, duracao: float) -> None:
        """Parada de impacto: desacelera o mundo por um instante no golpe."""
        if not self.prefs.parada_impacto:
            return
        self.hit_stop = min(PARADA_MAXIMA, max(self.hit_stop, duracao))

    def piscar(self, cor: tuple[int, int, int], forca: float = 0.45) -> None:
        """Clarão de tela; acompanha a opção de tremor para não incomodar."""
        if not self.prefs.tremer_tela:
            return
        self.flash_cor = tuple(cor[:3])
        self.flash = max(self.flash, min(1.0, forca))

    # ------------------------------------------------------------------ setup
    def _criar_vignette(self) -> pygame.Surface:
        pequena = pygame.Surface((160, 90), pygame.SRCALPHA)
        for y in range(90):
            for x in range(160):
                dx = abs(x - 80) / 80.0
                dy = abs(y - 45) / 45.0
                d = max(dx, dy)
                a = int(115 * max(0.0, d - 0.55) / 0.45)
                pequena.set_at((x, y), (0, 0, 0, a))
        return pygame.transform.smoothscale(pequena, (LARGURA, ALTURA))

    def novo_jogo(self, classe: str) -> None:
        self.jogador = Jogador(classe)
        self.jogador.x, self.jogador.y = self.mundo.spawn_jogador
        self.jogador.zona = "Clareira de Lumen"
        self.inimigos.clear()
        self.projeteis.clear()
        self.drops.clear()
        self.areas.clear()
        self.efeitos.clear()
        self.textos.clear()
        self.particulas = SistemaParticulas(250 if self.modo_desempenho else 1200)
        self.boss_ativo = None
        self.boss_alerta = 0.0
        self.boss_nome = ""
        self.vitoria_timer = 0.0
        self.hit_stop = 0.0
        self.flash = 0.0
        self.kills_sem_boss = {z.nome: 0 for z in self.mundo.zonas}
        self.quests = Missoes()
        self.servicos_desbloqueados = set()
        self.dialogo = []
        self.dialogo_timer = 0.0
        self.npc_perto = False
        self.npc_atual = None
        self.npc_dist = 1e9
        self.fogueira_perto = None
        self.fogueira_dist = 1e9
        self.eco = None
        self.pocao_cooldown = 0.0
        self.final_derrotado = False
        self.hora = 8.0
        self.chuva = 0.0
        self.chuva_ativa = False
        self.clima_timer = random.uniform(45, 90)
        self.errante_timer = random.uniform(150, 240)
        self.errante_vida = 0.0
        self.evento_timer = random.uniform(90, 150)
        self._ultimo_evento = ""
        self.zona_atual = "Clareira de Lumen"
        self.zona_banner = ["Clareira de Lumen", 3.5]
        self.tutorial = Tutorial()
        self._spawn_inicial()
        self._snap_camera()
        self.estado = "jogando"
        self.ui.notificar("As Cristais de Aether se fragmentaram. Restaure o Coração.", DOURADO)
        self.ui.notificar("Mate criaturas, colete cristais e derrote os bosses raros.", (180, 190, 210))
        self.ui.notificar("V (ou LT) esquiva com invencibilidade curta.", (150, 230, 255))

    def _snap_camera(self) -> None:
        if self.jogador is None:
            return
        self.camera.x = clamp(self.jogador.x - LARGURA / 2, 0, max(0, self.mundo.largura - LARGURA))
        self.camera.y = clamp(self.jogador.y - ALTURA / 2, 0, max(0, self.mundo.altura - ALTURA))
        self.camera.ox = self.camera.oy = 0.0

    def _spawn_inicial(self) -> None:
        self.inimigos.clear()
        if self.jogador is None:
            return
        for zona in self.mundo.zonas:
            for _ in range(zona.max_inimigos):
                pos = self.mundo.ponto_spawn(zona, (self.jogador.x, self.jogador.y), 360)
                if pos is None:
                    continue
                tipo = random.choice(zona.inimigos)
                self.inimigos.append(self._criar_inimigo(
                    tipo, self._nivel_inimigo(zona), pos[0], pos[1], self._chance_elite(),
                ))

    # ------------------------------------------------------------------ save
    def tem_save(self) -> bool:
        return self.save_path.exists() or self.save_path_antigo.exists()

    def salvar(self) -> bool:
        if self.jogador is None:
            return False
        try:
            dados = {
                "versao": SAVE_VERSION,
                "jogador": self.jogador.to_dict(),
                "kills_sem_boss": self.kills_sem_boss,
                "quests": self.quests.to_dict(),
                "servicos": sorted(self.servicos_desbloqueados),
                "hora": self.hora,
                "eco": (
                    {"x": self.eco.x, "y": self.eco.y, "quantidade": self.eco.quantidade}
                    if self.eco is not None and self.eco.vivo else None
                ),
                "tutorial_concluido": self.tutorial.concluido,
                "final_derrotado": self.final_derrotado,
            }
            write_save(self.save_path, dados)
            self.ui.notificar("Jogo salvo.", VERDE)
            return True
        except Exception as exc:  # pragma: no cover - proteção de I/O
            self.ui.notificar(f"Falha ao salvar: {exc}", VERMELHO)
            return False

    def carregar(self) -> bool:
        if not self.tem_save():
            self.ui.notificar("Nenhum save encontrado.", VERMELHO)
            return False
        try:
            origem = self.save_path if self.save_path.exists() else self.save_path_antigo
            dados = read_save(origem)
            self.jogador = Jogador.from_dict(dados.get("jogador", {}))
            self.kills_sem_boss = {z.nome: int(dados.get("kills_sem_boss", {}).get(z.nome, 0)) for z in self.mundo.zonas}
            self.quests = Missoes.from_dict(dados.get("quests"))
            self.final_derrotado = bool(dados.get("final_derrotado", False))
            self.servicos_desbloqueados = {
                str(servico) for servico in dados.get("servicos", [])
                if str(servico) in ABAS_SERVICOS
            }
            self.dialogo = []
            self.dialogo_timer = 0.0
            self.npc_perto = False
            self.npc_atual = None
            self.npc_dist = 1e9
            self.fogueira_perto = None
            self.fogueira_dist = 1e9
            self.eco = None
            self.pocao_cooldown = 0.0
            self.hora = float(dados.get("hora", 8.0)) % 24.0
            self.chuva = 0.0
            self.chuva_ativa = False
            self.clima_timer = random.uniform(45, 90)
            self.errante_timer = random.uniform(150, 240)
            self.errante_vida = 0.0
            self.evento_timer = random.uniform(90, 150)
            self._ultimo_evento = ""
            self.inimigos.clear()
            self.projeteis.clear()
            self.drops.clear()
            self.areas.clear()
            self.efeitos.clear()
            self.textos.clear()
            dados_eco = dados.get("eco")
            if isinstance(dados_eco, dict):
                try:
                    eco = Drop(
                        float(dados_eco["x"]), float(dados_eco["y"]), "eco", None,
                        int(dados_eco["quantidade"]),
                    )
                    self.drops.append(eco)
                    self.eco = eco
                except (KeyError, TypeError, ValueError):
                    self.eco = None
            self.boss_ativo = None
            self.boss_alerta = 0.0
            self.boss_nome = ""
            self.vitoria_timer = 0.0
            self.hit_stop = 0.0
            self.flash = 0.0
            # Saves anteriores ao tutorial não têm o campo: o jogador já passou do começo.
            self.tutorial = Tutorial(concluido=bool(dados.get("tutorial_concluido", True)))
            self._spawn_inicial()
            self._snap_camera()
            self.estado = "jogando"
            self.zona_atual = self.jogador.zona
            self.zona_banner = [self.jogador.zona, 3.0]
            if origem != self.save_path:
                try:
                    write_save(self.save_path, dados)
                except OSError:
                    pass
            self.ui.notificar("Jogo carregado.", VERDE)
            return True
        except Exception as exc:  # pragma: no cover
            self.ui.notificar(f"Falha ao carregar: {exc}", VERMELHO)
            return False

    # ------------------------------------------------------------------ update
    def atualizar(self, dt: float) -> None:
        dt = min(dt, 0.05)
        self.tempo += dt
        if self.modo_toque:
            self.toque.processar_fila_js(self)
        self.ui.atualizar(dt)
        self.boss_alerta = max(0.0, self.boss_alerta - dt)
        if self.zona_banner[1] > 0:
            self.zona_banner[1] = max(0.0, self.zona_banner[1] - dt)
        if self.vitoria_timer > 0:
            self.vitoria_timer -= dt
            if self.vitoria_timer <= 0:
                self.estado = "vitoria"
                self.sons.tocar("vitoria")
        self._atualizar_cursor_virtual(dt)
        self._atualizar_visibilidade_mouse()
        self._atualizar_musica()
        self.dialogo_timer = max(0.0, self.dialogo_timer - dt)
        if self.dialogo_timer <= 0:
            self.dialogo = []
        self.pocao_cooldown = max(0.0, self.pocao_cooldown - dt)
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 2.4)
        if self.hit_stop > 0:
            self.hit_stop = max(0.0, self.hit_stop - dt)
            dt *= FATOR_PARADA
        if self.estado == "jogando":
            self._atualizar_jogo(dt)

    # ------------------------------------------------------------------ controle
    def _atualizar_cursor_virtual(self, dt: float) -> None:
        """Nos menus, o analógico esquerdo move o cursor e A clica."""
        if self.modo_toque or not self.entrada.usando_controle or self.estado == "jogando":
            self._cursor = None
            return
        vx, vy = self.entrada.eixo_controle()
        if vx == 0 and vy == 0:
            return
        if self._cursor is None:
            self._cursor = [float(v) for v in pygame.mouse.get_pos()]
        self._cursor[0] = clamp(self._cursor[0] + vx * VELOCIDADE_CURSOR * dt, 0, LARGURA - 1)
        self._cursor[1] = clamp(self._cursor[1] + vy * VELOCIDADE_CURSOR * dt, 0, ALTURA - 1)
        pos = (int(self._cursor[0]), int(self._cursor[1]))
        self.entrada.marcar_cursor_sintetico(pos)
        try:
            pygame.mouse.set_pos(pos)
        except pygame.error:
            pass

    def _posicao_cursor(self) -> tuple[int, int]:
        if self._cursor is not None:
            return int(self._cursor[0]), int(self._cursor[1])
        return pygame.mouse.get_pos()

    def _atualizar_visibilidade_mouse(self) -> None:
        visivel = not ((self.entrada.usando_controle or self.modo_toque) and self.estado == "jogando")
        if visivel == self._mouse_visivel:
            return
        self._mouse_visivel = visivel
        try:
            pygame.mouse.set_visible(visivel)
        except pygame.error:
            pass

    def _alvo_assistido(self, direcao: tuple[float, float], cone: float) -> Inimigo | None:
        if self.jogador is None:
            return None
        melhor: Inimigo | None = None
        menor = ALCANCE_ASSISTENCIA
        for inimigo in self.inimigos:
            if not inimigo.vivo:
                continue
            dx, dy = inimigo.x - self.jogador.x, inimigo.y - self.jogador.y
            d = math.hypot(dx, dy)
            if d == 0 or d > menor:
                continue
            if (dx * direcao[0] + dy * direcao[1]) / d < cone:
                continue
            melhor, menor = inimigo, d
        return melhor

    def _mira_controle(self) -> tuple[float, float]:
        j = self.jogador
        assert j is not None
        direcao = self.entrada.direcao_mira()
        cone = CONE_ASSISTENCIA_MIRANDO
        if direcao is None:
            direcao = j.facing
            cone = CONE_ASSISTENCIA_LIVRE
        alvo = self._alvo_assistido(direcao, cone)
        if alvo is not None:
            return (alvo.x, alvo.y)
        return (j.x + direcao[0] * DISTANCIA_MIRA, j.y + direcao[1] * DISTANCIA_MIRA)

    def _botao_controle(self, botao: str) -> None:
        if botao == "_conectado":
            self.ui.notificar(f"Controle conectado: {self.entrada.nome_controle}", VERDE)
            return
        if botao == "_desconectado":
            self.ui.notificar("Controle desconectado.", AMARELO)
            if self.estado == "jogando":
                self.estado = "pausa"
            return

        estado = self.estado
        if estado == "jogando":
            if botao == "start":
                self.estado = "pausa"
            elif botao == "back":
                self.ui.painel.aba = "Inventário"
                self.estado = "painel"
            elif botao == "x":
                self._usar_skill(0)
            elif botao == "y":
                self._usar_skill(1)
            elif botao == "b":
                self._usar_skill(2)
            elif botao == "lb":
                self._usar_pocao_rapida()
            elif botao == "lt":
                self._esquivar()
            elif botao == "esquerda":
                self._usar_pocao("mana")
            elif botao == "baixo":
                self._usar_pocao("stamina")
            elif botao == "r3":
                if self.prefs.dicas_tutorial and not self.tutorial.concluido:
                    self.pular_etapa_tutorial()
            elif botao == "rb":
                self._usar_skill(3)
            elif botao == "direita":
                if self.prefs.dicas_tutorial and not self.tutorial.concluido:
                    self.pular_tutorial()
            elif botao == "cima" and (self.npc_perto or self.fogueira_perto is not None):
                self._interagir()
            return

        if botao == "a":
            self._clique(self._posicao_cursor(), 1)
            return

        if estado == "painel":
            if botao == "y":
                self._clique(self._posicao_cursor(), 3)
            elif botao in ("b", "back", "start"):
                self.estado = "jogando"
            elif botao in ("lb", "rb"):
                self._trocar_aba(-1 if botao == "lb" else 1)
        elif estado == "configuracoes":
            if botao in ("b", "start"):
                self.fechar_configuracoes()
        elif estado == "pausa":
            if botao in ("b", "start"):
                self.estado = "jogando"
        elif estado == "selecao":
            if botao == "b":
                self.estado = "menu"
        elif estado == "morte":
            if botao == "start":
                self._renascer()
        elif estado == "vitoria":
            if botao == "start":
                self.estado = "jogando"

    def _acao_toque(self, acao: str) -> None:
        if acao.startswith("skill") and acao[-1].isdigit():
            self._usar_skill(int(acao[-1]))
        elif acao == "esquiva":
            self._esquivar()
        elif acao == "pocao_vida":
            self._usar_pocao("vida")
        elif acao == "pocao_mana":
            self._usar_pocao("mana")
        elif acao == "pocao_stamina":
            self._usar_pocao("stamina")
        elif acao == "interagir":
            self._interagir()
        elif acao == "inventario":
            self.ui.painel.aba = "Inventário"
            self.estado = "painel"
        elif acao == "pausa":
            self.estado = "pausa"

    def _trocar_aba(self, passo: int) -> None:
        abas = self.ui.painel.abas_disponiveis(self)
        if not abas:
            return
        atual = self.ui.painel.aba
        indice = abas.index(atual) if atual in abas else 0
        self.ui.painel.aba = abas[(indice + passo) % len(abas)]

    def _atualizar_jogo(self, dt: float) -> None:
        if self.jogador is None:
            return
        if self.modo_toque:
            self.toque.atualizar(dt)
            self.entrada.toque_vetor = self.toque.movimento
            self.entrada.toque_correndo = self.toque.correndo
            self.entrada.toque_ataque = self.toque.pressionado("ataque")
            self.mouse_world = self.toque.mira(self)
            for acao in self.toque.consumir_eventos():
                self._acao_toque(acao)
            if self.estado != "jogando":
                return
        elif self.entrada.usando_controle:
            self.mouse_world = self._mira_controle()
        else:
            self.mouse_world = self.camera.mundo(pygame.mouse.get_pos())
        self.mundo.atualizar(dt)
        self.jogador.atualizar(dt, self)
        self.hora = (self.hora + dt * (24.0 / self.duracao_dia)) % 24.0
        self.mundo.noite = 1.0 - self._fator_ambiente()[0]
        j = self.jogador
        if j.fome <= 25 and not j.fome_aviso_25:
            j.fome_aviso_25 = True
            self.ui.notificar("Fome baixa. Volte a uma fogueira para descansar.", (240, 180, 100))
        if j.fome <= 0 and not j.fome_aviso_0:
            j.fome_aviso_0 = True
            self.ui.notificar("Você está faminto: regeneração reduzida.", VERMELHO)
        zona = self.mundo.zona_em(j.x, j.y)
        elegivel = zona is not None and zona.nome in (
            "Clareira de Lumen", "Floresta de Lumen", "Pântano de Veyra",
        )
        self.clima_timer -= dt
        if self.clima_timer <= 0:
            self.clima_timer = random.uniform(70, 140)
            self.chuva_ativa = (not self.chuva_ativa) and elegivel
        alvo_chuva = 1.0 if (elegivel and self.chuva_ativa) else 0.0
        self.chuva = lerp(self.chuva, alvo_chuva, min(1.0, dt * 0.5))
        self._atualizar_npc()
        self._atualizar_passos(dt)
        if self.jogador.morto:
            self.estado = "morte"
        elif self.entrada.segurando_ataque():
            self.jogador.atacar(self, self.mouse_world)

        for inimigo in self.inimigos:
            if inimigo.vivo:
                inimigo.atualizar(dt, self)
        self._separar_inimigos()

        for projetil in self.projeteis:
            projetil.atualizar(dt, self)
        for area in self.areas:
            area.atualizar(dt, self)
        for drop in self.drops:
            drop.atualizar(dt, self)
        for efeito in self.efeitos:
            efeito.atualizar(dt)
        for texto in self.textos:
            texto.update(dt)
        self.particulas.update(dt)

        self.inimigos = [i for i in self.inimigos if i.vivo]
        self.projeteis = [p for p in self.projeteis if p.vivo]
        self.areas = [a for a in self.areas if a.vivo]
        self.drops = [d for d in self.drops if d.vivo]
        self.efeitos = [e for e in self.efeitos if e.vivo]
        self.textos = [t for t in self.textos if t.vida > 0]

        self._atualizar_spawn(dt)
        self._atualizar_evento(dt)
        self._atualizar_errante(dt)
        self._detectar_zona()
        self._atualizar_tutorial(dt)
        olhar_x, olhar_y = self.jogador.facing
        alvo_camera = (self.jogador.x + olhar_x * 42, self.jogador.y + olhar_y * 28)
        self.camera.seguir(alvo_camera, dt, (0, 0, self.mundo.largura, self.mundo.altura))
        self._atualizar_ducking(dt)

    def _atualizar_npc(self) -> None:
        if self.jogador is None:
            self.npc_perto = False
            self.npc_atual = None
            self.npc_dist = 1e9
            self.fogueira_perto = None
            self.fogueira_dist = 1e9
            return
        self.npc_perto = False
        self.npc_atual = None
        self.npc_dist = 1e9
        melhor = 100.0
        for npc in self.mundo.npcs:
            d = distancia((self.jogador.x, self.jogador.y), (npc.x, npc.y))
            if d <= melhor:
                melhor = d
                self.npc_atual = npc
        self.npc_perto = self.npc_atual is not None
        self.npc_dist = melhor if self.npc_atual is not None else 1e9
        self.fogueira_perto = None
        self.fogueira_dist = 1e9
        for fx, fy in self.mundo.fogueiras:
            d = distancia((self.jogador.x, self.jogador.y), (fx, fy))
            if d <= 90.0 and d < self.fogueira_dist:
                self.fogueira_dist = d
                self.fogueira_perto = (fx, fy)

    def _atualizar_passos(self, dt: float) -> None:
        if self.jogador is None or self.jogador.morto:
            return
        if not self.jogador.andando:
            self._passo_timer = 0.0
            return
        self._passo_timer -= dt
        if self._passo_timer > 0:
            return
        self._passo_timer = 0.22 if self.jogador.correndo else 0.36
        self.sons.tocar("passo", 0.30 if self.jogador.correndo else 0.20)
        self.particulas.emitir(
            self.jogador.x, self.jogador.y - 2, (150, 140, 120), 2, 24, 2, 0.28,
        )

    def _atualizar_ducking(self, dt: float) -> None:
        alvo = 1.0
        if self.boss_ativo is not None and self.boss_ativo.vivo:
            alvo = 0.45
        elif (
            self.jogador is not None
            and self.jogador.hp_max > 0
            and self.jogador.hp / self.jogador.hp_max < 0.30
        ):
            alvo = 0.55
        self._ducking = lerp(self._ducking, alvo, min(1.0, dt * 2.5))
        self.sons.definir_ducking(self._ducking)

    def _atualizar_evento(self, dt: float) -> None:
        self.evento_timer -= dt
        if self.evento_timer > 0:
            return
        self.evento_timer = random.uniform(120, 180)
        if self.jogador is None or self.jogador.morto:
            return
        opcoes = [nome for nome in EVENTOS if nome != self._ultimo_evento]
        escolha = random.choice(opcoes)
        self._ultimo_evento = escolha
        {
            "veio": self._evento_veio_de_cristais,
            "bau": self._evento_bau_viajante,
            "emboscada": self._evento_emboscada,
            "santuario": self._evento_santuario,
        }[escolha]()

    def _posicao_evento(
        self, distancia_min: float, distancia_max: float, evitar_clareira: bool = True,
    ) -> tuple[float, float] | None:
        """Procura um ponto livre perto do jogador para um evento."""
        if self.jogador is None:
            return None
        for _ in range(32):
            ang = random.uniform(0, math.tau)
            dist = random.uniform(distancia_min, distancia_max)
            x = self.jogador.x + math.cos(ang) * dist
            y = self.jogador.y + math.sin(ang) * dist
            if not (40 <= x <= self.mundo.largura - 40 and 40 <= y <= self.mundo.altura - 40):
                continue
            zona = self.mundo.zona_em(x, y)
            if zona is None:
                continue
            if evitar_clareira and zona.nome == "Clareira de Lumen":
                continue
            if self.mundo._em_agua(x, y) or self.mundo.colidir_circulo(x, y, 26):
                continue
            return (x, y)
        return None

    def _evento_veio_de_cristais(self) -> None:
        """Evento raro: um veio se abre perto do jogador e espalha cristais e ouro."""
        if self.jogador is None:
            return
        alvo = self._posicao_evento(180, 320)
        if alvo is None:
            return
        x, y = alvo
        self.ui.notificar("Um veio de cristais se abriu perto de você!", (150, 230, 255))
        self.sons.tocar("cristal", 0.9)
        self.particulas.emitir(x, y, (120, 220, 255), 34, 170, 5, 0.7)
        self.efeitos.append(Efeito("onda", x, y, 96, 0.55, (120, 220, 255)))
        for _ in range(random.randint(4, 6)):
            self.drops.append(
                Drop(
                    x + random.uniform(-46, 46), y + random.uniform(-34, 34),
                    "item", gerar_cristal(self.jogador.nivel + 1, boss=True),
                )
            )
        for _ in range(random.randint(2, 4)):
            self.drops.append(
                Drop(
                    x + random.uniform(-40, 40), y + random.uniform(-30, 30),
                    "ouro", None, random.randint(20, 45),
                )
            )

    def _evento_bau_viajante(self) -> None:
        """Baú com ouro, cristal e poções."""
        alvo = self._posicao_evento(180, 300, evitar_clareira=False)
        if alvo is None:
            return
        x, y = alvo
        drop = Drop(x, y, "bau")
        drop.vida = 150.0
        self.drops.append(drop)
        self.ui.notificar("Um baú do viajante apareceu perto de você!", (246, 204, 92))
        self.sons.tocar("loot", 0.8)
        self.particulas.emitir(x, y, (250, 220, 140), 20, 120, 4, 0.6)
        self.efeitos.append(Efeito("onda", x, y, 70, 0.5, (246, 204, 92)))

    def _evento_emboscada(self) -> None:
        """Cerca o jogador com três elites da zona."""
        if self.jogador is None:
            return
        if self.boss_ativo is not None and self.boss_ativo.vivo:
            return
        zona = self.mundo.zona_em(self.jogador.x, self.jogador.y)
        if zona is None or zona.seguro or zona.nome == "Clareira de Lumen":
            return
        criados = 0
        for _ in range(3):
            alvo = self._posicao_evento(200, 320)
            if alvo is None:
                continue
            tipo = random.choice(zona.inimigos)
            self.inimigos.append(self._criar_inimigo(
                tipo, zona.sortear_nivel(), alvo[0], alvo[1], chance_elite=1.0,
            ))
            criados += 1
        if criados <= 0:
            return
        self.ui.notificar(f"Emboscada! {criados} elite(s) cercaram você.", (250, 120, 100))
        self.sons.tocar("perigo", 0.9)
        self.tremer(10, 0.35)
        self.piscar((255, 90, 80), 0.3)

    def _evento_santuario(self) -> None:
        """Santuário que cura e concede uma bênção temporária."""
        alvo = self._posicao_evento(180, 320, evitar_clareira=False)
        if alvo is None:
            return
        x, y = alvo
        drop = Drop(x, y, "santuario")
        drop.vida = 120.0
        self.drops.append(drop)
        self.ui.notificar(
            "Um santuário de Aether surgiu. Toque nele para receber a bênção.",
            (150, 230, 255),
        )
        self.sons.tocar("encanto", 0.8)
        self.particulas.emitir(x, y, (150, 230, 255), 24, 130, 4, 0.7)
        self.efeitos.append(Efeito("onda", x, y, 80, 0.5, (150, 230, 255)))

    def _atualizar_errante(self, dt: float) -> None:
        """Boss errante: aparece de tempos em tempos e vai embora se for ignorado."""
        if self.jogador is None:
            return
        ativo = self.boss_ativo
        if ativo is not None and ativo.vivo and getattr(ativo, "errante", False):
            self.errante_vida -= dt
            if self.errante_vida <= 0:
                nome = ativo.nome
                ativo.vivo = False
                self.inimigos = [i for i in self.inimigos if i is not ativo]
                self.particulas.emitir(ativo.x, ativo.y - ativo.raio, (190, 110, 200), 26, 140, 5, 0.6)
                self.boss_ativo = None
                self.boss_nome = ""
                self.boss_alerta = 0.0
                self.ui.notificar(f"{nome} se afastou...", (196, 150, 214))
            return
        self.errante_timer -= dt
        if self.errante_timer > 0:
            return
        self.errante_timer = random.uniform(240, 360)
        self._spawn_errante()

    def _spawn_errante(self) -> None:
        """Spawna um boss errante sem consumir a progressão de bosses."""
        if self.jogador is None or self.jogador.morto:
            return
        if self.boss_ativo is not None and self.boss_ativo.vivo:
            return
        if any(i.vivo and getattr(i, "errante", False) for i in self.inimigos):
            return
        zona = self.mundo.zona_em(self.jogador.x, self.jogador.y)
        if zona is None or zona.seguro or zona.nome == "Clareira de Lumen":
            return
        opcoes = [dados for dados in ERRANTES if self.jogador.nivel >= dados["nivel_min"]]
        if not opcoes:
            return
        dados = random.choices(opcoes, weights=[d["peso"] for d in opcoes], k=1)[0]
        pos = self.mundo.ponto_spawn(zona, (self.jogador.x, self.jogador.y), 430)
        if pos is None:
            return
        nivel = max(int(dados["nivel_min"]), self.jogador.nivel + 2)
        boss = Inimigo(str(dados["tipo"]), nivel, pos[0], pos[1])
        self.inimigos.append(boss)
        self.boss_ativo = boss
        self.boss_nome = boss.nome
        self.boss_alerta = 7.0
        self.errante_vida = float(dados["vida"])
        self.sons.tocar("boss", 1.0)
        self.ui.notificar(f"{boss.nome} ronda a região!", boss.cor)
        self.ui.notificar("Boss errante: loot lendário, sem contar para o selo.", (220, 190, 240))
        self.tremer(14, 0.5)
        self.particulas.emitir(boss.x, boss.y - 30, boss.cor, 46, 210, 6, 0.85)

    def _atualizar_tutorial(self, dt: float) -> None:
        if self.jogador is None or not self.prefs.dicas_tutorial:
            return
        for mensagem in self.tutorial.atualizar(dt, self.jogador):
            self.ui.notificar(mensagem, DOURADO)

    def _avisar_missao_concluida(self) -> None:
        missao = self.quests.atual
        if missao is not None:
            self.ui.notificar(f"Missão concluída: {missao['nome']}! Fale com Mestre Aldrin.", DOURADO)
            self.sons.tocar("missao", 0.7)

    def _interagir(self) -> None:
        if self.jogador is None or self.estado != "jogando":
            return
        if self.fogueira_perto is not None and self.fogueira_dist < self.npc_dist:
            self._descansar()
        elif self.npc_perto:
            self._falar_npc()

    def _descansar(self) -> None:
        if self.jogador is None:
            return
        j = self.jogador
        j.hp = float(j.hp_max)
        j.mp = float(j.mp_max)
        j.stamina = float(j.stamina_max)
        j.fome = j.fome_max
        j.fome_aviso_25 = False
        j.fome_aviso_0 = False
        j.regen_mp_delay = 0.0
        j.regen_stamina_delay = 0.0
        self.hora = 7.0
        self.chuva_ativa = False
        self.clima_timer = random.uniform(70, 140)
        self.sons.tocar("descanso", 0.8)
        self.ui.notificar(
            "Você descansou até o amanhecer. Vida, mana, fôlego e fome restaurados.",
            DOURADO,
        )
        self.particulas.emitir(j.x, j.y - 24, (255, 190, 100), 26, 130, 4, 0.7)

    def _falar_npc(self) -> None:
        if self.jogador is None or self.estado != "jogando" or not self.npc_perto:
            return
        npc = self.npc_atual
        if npc is None:
            return
        self.sons.tocar("clique", 0.4)
        if npc is not self.mundo.npc:
            abas = {
                "Mercadora Sela": "Mercado",
                "Ferreiro Durin": "Forja",
                "Encantadora Yara": "Encantamentos",
            }
            aba = abas.get(npc.nome)
            if aba is not None:
                novo = aba not in self.servicos_desbloqueados
                self.servicos_desbloqueados.add(aba)
                if novo:
                    self.ui.notificar(f"{aba} desbloqueado na Vila de Veyra!", DOURADO)
                self.ui.painel.aba = aba
                self.estado = "painel"
            return
        if self.quests.completa:
            missao = self.quests.entregar()
            if missao is not None:
                self._recompensar_missao(missao)
                self.dialogo = [
                    f"Excelente! '{missao['nome']}' está concluída.",
                    "Obrigado, herói. Leve isto como recompensa.",
                ]
        elif self.quests.atual is not None:
            missao = self.quests.atual
            self.dialogo = [str(missao["descricao"]), self.quests.texto_progresso()]
        else:
            self.dialogo = [
                "O Coração de Aether está estável. Descanse, herói.",
                "Se algo mudar, estarei aqui.",
            ]
        self.dialogo_timer = 7.0

    def _recompensar_missao(self, missao: dict[str, Any]) -> None:
        if self.jogador is None:
            return
        j = self.jogador
        j.ouro += int(missao["ouro"])
        for msg in j.ganhar_xp(int(missao["xp"])):
            self.ui.notificar(msg, VERDE)
        tipo = missao["item"][0]
        if tipo == "pocao":
            item: Any = Pocao(str(missao["item"][1]), int(missao["item"][2]))
        else:
            item = gerar_equipamento(j.nivel, j.classe, raridade=str(missao["item"][1]))
        if j.adicionar_item(item):
            self.ui.notificar(f"Recompensa: {item.nome}", getattr(item, "cor", DOURADO))
        else:
            tipo_drop = "equipamento" if isinstance(item, Equipamento) else "pocao"
            self.drops.append(Drop(j.x, j.y + 24, tipo_drop, item))
            self.ui.notificar("Inventário cheio: a recompensa caiu no chão.", VERMELHO)
        self.sons.tocar("missao", 0.9)
        self.particulas.emitir(j.x, j.y - 30, (250, 220, 120), 32, 160, 5, 0.8)
        self.efeitos.append(Efeito("nivel", j.x, j.y, 110, 0.85, (250, 220, 120)))
        self.ui.notificar(f"Missão concluída: {missao['nome']} (+{missao['ouro']} ouro)", DOURADO)

    def pular_etapa_tutorial(self) -> None:
        if self.jogador is None or not self.prefs.dicas_tutorial or self.tutorial.concluido:
            return
        for mensagem in self.tutorial.pular_etapa(self.jogador):
            self.ui.notificar(mensagem, DOURADO)

    def pular_tutorial(self) -> None:
        """Pula o tutorial; pede uma segunda confirmação para evitar acidentes."""
        if not self.prefs.dicas_tutorial or self.tutorial.concluido:
            return
        if self.tutorial.pedir_pular():
            self.ui.notificar("Tutorial pulado. Reative as dicas em Configurações.", AMARELO)

    def _separar_inimigos(self) -> None:
        vivos = [i for i in self.inimigos if i.vivo and not i.boss]
        for i, a in enumerate(vivos):
            for b in vivos[i + 1:]:
                dx, dy = b.x - a.x, b.y - a.y
                d = math.hypot(dx, dy)
                minimo = (a.raio + b.raio) * 0.8
                if 0 < d < minimo:
                    empurrao = (minimo - d) * 0.5
                    nx, ny = dx / d, dy / d
                    a.x -= nx * empurrao * 0.35
                    a.y -= ny * empurrao * 0.35
                    b.x += nx * empurrao * 0.35
                    b.y += ny * empurrao * 0.35

    def _criar_inimigo(
        self, tipo: str, nivel: int, x: float, y: float,
        chance_elite: float | None = None,
    ) -> Inimigo:
        inimigo = Inimigo(tipo, nivel, x, y)
        chance = CHANCE_ELITE if chance_elite is None else chance_elite
        if not inimigo.boss and nivel >= 3 and random.random() < chance:
            self._tornar_elite(inimigo)
        return inimigo

    def _nivel_inimigo(self, zona: Zona) -> int:
        """Zonas antigas mantêm o nível original; desafio vem de mapas novos."""
        return zona.sortear_nivel()

    def _chance_elite(self) -> float:
        return CHANCE_ELITE

    def _tornar_elite(self, inimigo: Inimigo) -> None:
        afixo = random.choice(tuple(AFIXOS_ELITE))
        inimigo.elite = True
        inimigo.afixo = afixo
        inimigo.cor_elite = AFIXOS_ELITE[afixo]
        inimigo.nome = f"{inimigo.nome} {afixo}"
        inimigo.hp_max *= 1.45
        inimigo.hp = inimigo.hp_max
        inimigo.ataque *= 1.15
        inimigo.xp_recompensa = int(inimigo.xp_recompensa * 1.8)
        if afixo == "Veloz":
            inimigo.velocidade *= 1.35
            inimigo.ataque_cooldown *= 0.85
        elif afixo == "Blindado":
            inimigo.defesa *= 1.5
            inimigo.velocidade *= 0.9
            inimigo.poise_max *= 1.5
        elif afixo == "Explosivo":
            inimigo.ataque *= 1.10
        elif afixo == "Vampírico":
            inimigo.ataque *= 1.05
        elif afixo == "Invocador":
            inimigo.hp_max *= 1.10
            inimigo.hp = inimigo.hp_max

    def _efeito_elite(self, inimigo: Inimigo) -> None:
        bonus = random.randint(12, 24) + inimigo.nivel * 3
        self.drops.append(Drop(inimigo.x, inimigo.y, "ouro", None, bonus))
        self.drops.append(Drop(inimigo.x + 18, inimigo.y + 10, "pocao", gerar_pocao()))
        self.ui.notificar(f"Elite {inimigo.afixo} derrotado! Loot extra.", inimigo.cor_elite)
        if inimigo.afixo == "Explosivo":
            self.areas.append(AreaPerigo(
                inimigo.x, inimigo.y, 96, inimigo.ataque * 1.3,
                "inimigo", 0.35, (250, 150, 80),
            ))
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 120, 0.5, (250, 150, 80)))
        elif inimigo.afixo == "Invocador" and not inimigo.filhote:
            base = inimigo.nome.split(" ")[0]
            for _ in range(2):
                filho = Inimigo(
                    inimigo.tipo, max(1, inimigo.nivel - 2),
                    inimigo.x + random.uniform(-28, 28),
                    inimigo.y + random.uniform(-24, 24),
                )
                filho.hp_max *= 0.30
                filho.hp = filho.hp_max
                filho.xp_recompensa = max(1, int(filho.xp_recompensa * 0.25))
                filho.filhote = True
                filho.nome = f"Filhote de {base}"
                self.inimigos.append(filho)
            self.ui.notificar("O elite se dividiu em filhotes!", (190, 150, 240))

    def _atualizar_spawn(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        self.spawn_timer = 2.4
        if self.jogador is None:
            return
        for zona in self.mundo.zonas:
            vivos = sum(
                1 for i in self.inimigos
                if i.vivo and not i.boss and zona.rect.collidepoint(i.x, i.y)
            )
            if vivos >= zona.max_inimigos:
                continue
            pos = self.mundo.ponto_spawn(zona, (self.jogador.x, self.jogador.y), 420)
            if pos is None:
                continue
            self.inimigos.append(self._criar_inimigo(
                random.choice(zona.inimigos), self._nivel_inimigo(zona),
                pos[0], pos[1], self._chance_elite(),
            ))

    def _detectar_zona(self) -> None:
        if self.jogador is None:
            return
        zona = self.mundo.zona_em(self.jogador.x, self.jogador.y)
        if zona is None:
            return
        if zona.nome != self.zona_atual:
            self.zona_atual = zona.nome
            self.jogador.zona = zona.nome
            self.zona_banner = [zona.nome, 3.2]
            if self.quests.registrar_zona(zona.nome):
                self._avisar_missao_concluida()
            if zona.nome == "Caverna de Cristal":
                self.ui.notificar("O ar fica pesado. Algo antigo observa.", ROXO)
                if self.jogador.bosses < BOSSES_PARA_CAVERNA:
                    self.ui.notificar(
                        f"O caminho está selado: derrote {BOSSES_PARA_CAVERNA} bosses raros antes "
                        f"({self.jogador.bosses}/{BOSSES_PARA_CAVERNA}).", (250, 190, 120),
                    )
            elif zona.nome == "Pântano de Veyra":
                self.ui.notificar("O Pântano de Veyra cheira a cristal podre.", (170, 230, 150))
                self.ui.notificar("A Rainha do Lodo guarda este lugar.", (200, 240, 170))
            elif zona.nome == "Vila de Veyra":
                self.ui.notificar("Vila de Veyra: mercador, ferreiro e encantadora.", (240, 210, 150))
            elif zona.nome == "Desfiladeiro de Obsidiana":
                self.ui.notificar("Obsidiana viva. O chão queima sob as botas.", (250, 140, 100))
            elif zona.nome == "Coração de Aether":
                self.ui.notificar("O Coração de Aether pulsa. A origem dos cristais.", (190, 230, 255))
            elif zona.nome == "Fenda do Eclipse":
                if self.jogador.nivel < 38:
                    self.ui.notificar(
                        "A Fenda do Eclipse exige nível 38. Volte mais forte.",
                        (250, 120, 100),
                    )
                else:
                    self.ui.notificar("O eclipse devora a luz. Algo antigo observa.", (190, 130, 240))

    # ------------------------------------------------------------------ draw
    def desenhar(self, surf: pygame.Surface) -> None:
        if self.estado == "configuracoes":
            self.ui_config.desenhar(surf, self.prefs, self.fps, self.entrada.usando_controle)
            return
        if self.estado == "menu":
            self.ui.desenhar_menu(surf, self, self.tem_save())
            return
        if self.estado == "selecao":
            self.ui.desenhar_selecao(surf, self)
            return
        if self.jogador is None:
            surf.fill((12, 16, 26))
            return

        passo_visual = 3 if self.modo_desempenho else 1
        self.mundo.desenhar_terreno(surf, self.camera)
        self.mundo.desenhar_detalhes(surf, self.camera, passo_visual)
        self.mundo.desenhar_grama(surf, self.camera, passo_visual)
        self.mundo.desenhar_agua(surf, self.camera)
        self.mundo.desenhar_fundo(surf, self.camera)
        self.mundo.desenhar_ambiente(surf, self.camera)
        self._desenhar_ordenado(surf)
        for projetil in self.projeteis:
            projetil.desenhar(surf, self.camera)
        for area in self.areas:
            area.desenhar(surf, self.camera)
        for efeito in self.efeitos:
            efeito.desenhar(surf, self.camera)
        self.particulas.draw(surf, self.camera)
        for texto in self.textos:
            texto.draw(surf, self.camera)
        self._desenhar_luz(surf)
        self._desenhar_flash(surf)
        self._desenhar_chuva(surf, passo_visual)
        self._desenhar_nomes(surf)
        self._desenhar_npc(surf)
        self._desenhar_mira(surf)
        self.ui.desenhar_hud(surf, self)
        if self.estado == "jogando":
            self.toque.desenhar(surf, self, self.modo_desempenho)

        if self.estado == "pausa":
            self.ui.desenhar_pausa(surf, self)
        elif self.estado == "painel":
            self.ui.desenhar_painel(surf, self)
        elif self.estado == "morte":
            self.ui.desenhar_morte(surf, self)
        elif self.estado == "vitoria":
            self.ui.desenhar_vitoria(surf, self)

    def _desenhar_ordenado(self, surf: pygame.Surface) -> None:
        objetos: list[tuple[float, int, Any]] = []
        margem_deco = 90 if self.modo_desempenho else 220
        for d in self.mundo.decoracoes:
            if not self.camera.visivel(d.x, d.y, margem_deco):
                continue
            objetos.append((d.y, 0, d))
        for drop in self.drops:
            objetos.append((drop.y, 1, drop))
        for inimigo in self.inimigos:
            if inimigo.vivo:
                objetos.append((inimigo.y, 2, inimigo))
        if self.jogador is not None and not self.jogador.morto:
            objetos.append((self.jogador.y, 3, self.jogador))
        for npc in self.mundo.npcs:
            objetos.append((npc.y, 4, npc))
        objetos.sort(key=lambda t: (t[0], t[1]))
        for _, tipo, obj in objetos:
            if tipo == 0:
                obj.desenhar(surf, self.camera, self.mundo.tempo)
            elif tipo == 4:
                obj.desenhar(surf, self.camera, self.mundo.tempo)
            else:
                obj.desenhar(surf, self.camera)

    def _desenhar_nomes(self, surf: pygame.Surface) -> None:
        """Nome curto acima dos inimigos próximos (a barra de vida fica no enemy_art)."""
        if self.jogador is None:
            return
        for inimigo in self.inimigos:
            if not inimigo.vivo or inimigo.boss:
                continue
            if distancia((self.jogador.x, self.jogador.y), (inimigo.x, inimigo.y)) > 320:
                continue
            sx, sy = self.camera.aplicar((inimigo.x, inimigo.y))
            etiqueta(surf, inimigo.nome, (sx, sy - inimigo.raio * 2.6 - 18), 10)

    def _desenhar_npc(self, surf: pygame.Surface) -> None:
        if self.jogador is None:
            return
        simbolos = {
            "Mercadora Sela": ("M", (240, 190, 120)),
            "Ferreiro Durin": ("F", (230, 170, 120)),
            "Encantadora Yara": ("E", (210, 160, 250)),
        }
        for npc in self.mundo.npcs:
            if not self.camera.visivel(npc.x, npc.y, 160):
                continue
            if npc is self.mundo.npc:
                desenhar_indicador(
                    surf, self.camera, npc, self.mundo.tempo,
                    self.quests.atual is not None, self.quests.completa,
                )
            else:
                simbolo, cor = simbolos.get(npc.nome, ("?", (240, 220, 160)))
                desenhar_indicador(
                    surf, self.camera, npc, self.mundo.tempo, False, False,
                    simbolo=simbolo, cor=cor,
                )
        if self.npc_atual is not None:
            npc = self.npc_atual
            sx, sy = self.camera.aplicar((npc.x, npc.y))
            tecla = "▲" if self.entrada.usando_controle else "T"
            etiqueta(surf, f"{tecla} · Falar com {npc.nome}", (sx, sy - 148), 11)
        if self.fogueira_perto is not None and self.fogueira_dist < self.npc_dist:
            fx, fy = self.camera.aplicar(self.fogueira_perto)
            tecla = "▲" if self.entrada.usando_controle else "T"
            etiqueta(surf, f"{tecla} · Descansar na fogueira", (fx, fy - 82), 11)

    def _desenhar_mira(self, surf: pygame.Surface) -> None:
        """Retícula da mira; aparece no controle ou ao atacar no celular."""
        if self.estado != "jogando" or self.jogador is None:
            return
        if self.modo_toque:
            if not self.toque.pressionado("ataque"):
                return
            sx, sy = self.camera.aplicar(self.mouse_world)
            pygame.draw.circle(surf, (250, 220, 140), (int(sx), int(sy)), 10, 1)
            pygame.draw.line(surf, (250, 220, 140), (int(sx - 14), int(sy)), (int(sx - 6), int(sy)), 1)
            pygame.draw.line(surf, (250, 220, 140), (int(sx + 6), int(sy)), (int(sx + 14), int(sy)), 1)
            pygame.draw.line(surf, (250, 220, 140), (int(sx), int(sy - 14)), (int(sx), int(sy - 6)), 1)
            pygame.draw.line(surf, (250, 220, 140), (int(sx), int(sy + 6)), (int(sx), int(sy + 14)), 1)
            return
        if not self.entrada.usando_controle:
            return
        sx, sy = self.camera.aplicar(self.mouse_world)
        x, y = int(sx), int(sy)
        raio = 11 + int(2 * math.sin(self.tempo * 6))
        pygame.draw.circle(surf, (20, 16, 10), (x, y), raio + 2, 3)
        pygame.draw.circle(surf, (250, 226, 150), (x, y), raio, 2)
        for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(surf, (250, 226, 150), (x + ax * (raio + 3), y + ay * (raio + 3)), (x + ax * (raio + 8), y + ay * (raio + 8)), 2)

    def _desenhar_flash(self, surf: pygame.Surface) -> None:
        """Clarão colorido sobre o mundo, usado em dano, crítico e morte."""
        if self.flash <= 0.01:
            return
        if self._flash_surf is None:
            self._flash_surf = pygame.Surface((LARGURA, ALTURA))
        self._flash_surf.fill(self.flash_cor)
        self._flash_surf.set_alpha(int(150 * min(1.0, self.flash)))
        surf.blit(self._flash_surf, (0, 0))

    def eh_noite(self) -> bool:
        return self.hora >= 19.0 or self.hora < 5.0

    def _fator_ambiente(self) -> tuple[float, tuple[float, float, float]]:
        h = self.hora
        if 7.0 <= h < 18.0:
            return 1.0, (1.0, 1.0, 1.0)
        if 18.0 <= h < 20.0:
            f = (h - 18.0) / 2.0
            return lerp(1.0, 0.55, f), (1.0, 0.88, 0.76)
        if 5.0 <= h < 7.0:
            f = (h - 5.0) / 2.0
            return lerp(0.55, 1.0, f), (0.78, 0.84, 1.0)
        return 0.55, (0.68, 0.76, 1.0)

    def _desenhar_chuva(self, surf: pygame.Surface, passo: int = 1) -> None:
        if self.modo_desempenho or self.chuva <= 0.03:
            return
        overlay = self._chuva_overlay
        overlay.fill((60, 78, 110, int(20 * self.chuva)))
        surf.blit(overlay, (0, 0))
        self._chuva_surf.fill((0, 0, 0, 0))
        alpha = int(90 * self.chuva)
        for i in range(0, len(self._gotas), max(1, passo)):
            x, y, vel, comprimento = self._gotas[i]
            yy = (y + self.tempo * vel) % (ALTURA + 40) - 20
            xx = (x - self.tempo * vel * 0.18) % LARGURA
            pygame.draw.line(
                self._chuva_surf, (170, 190, 220, alpha),
                (int(xx), int(yy)), (int(xx - 4), int(yy + comprimento)), 1,
            )
        surf.blit(self._chuva_surf, (0, 0))

    def _desenhar_luz(self, surf: pygame.Surface) -> None:
        if self.modo_desempenho:
            return
        surf.blit(self.vignette, (0, 0))
        if self.jogador is None:
            return
        zona = self.mundo.zona_em(self.jogador.x, self.jogador.y)
        if zona is None:
            return

        if self.luz_avancada:
            fator, tint = self._fator_ambiente()
            base = AMBIENTE_ZONA.get(zona.nome, (255, 255, 255))
            ambiente = tuple(int(base[i] * fator * tint[i]) for i in range(3))
            self.iluminacao.desenhar(surf, self._luzes_do_mundo(zona), ambiente)
            return

        # Técnica antiga, mantida para comparação (python main.py --luz-simples).
        if zona.nome == "Caverna de Cristal":
            escuridao = self._escuridao_surf
            escuridao.fill((4, 3, 10, 135))
            surf.blit(escuridao, (0, 0))
            px, py = self.camera.aplicar((self.jogador.x, self.jogador.y))
            luz = superficie_luz(240, (200, 180, 255), 100)
            surf.blit(luz, (int(px - 240), int(py - 240)))
        elif zona.nome == "Ruínas de Aether":
            escuridao = self._escuridao_surf
            escuridao.fill((6, 8, 16, 40))
            surf.blit(escuridao, (0, 0))
        fator, tint = self._fator_ambiente()
        if fator < 0.95:
            escuridao = self._escuridao_surf
            escuridao.fill((
                int(10 * tint[0]), int(12 * tint[1]), int(26 * tint[2]),
                int((1.0 - fator) * 230),
            ))
            surf.blit(escuridao, (0, 0))

    def _luzes_do_mundo(self, zona: Zona) -> list[Luz]:
        """Monta as fontes de luz visíveis, já em coordenadas de tela."""
        if self.jogador is None:
            return []

        luzes: list[Luz] = []
        px, py = self.camera.aplicar((self.jogador.x, self.jogador.y))
        raio, intensidade = LUZ_JOGADOR.get(zona.nome, (220, 90))
        if self.eh_noite():
            raio = int(raio * 0.78)
            intensidade = int(intensidade * 0.9)
        luzes.append(Luz(px, py - 26, raio, (255, 206, 156), intensidade))

        margem = 220
        tempo = self.mundo.tempo

        # Boss: cristal vivo, então também ilumina o ambiente.
        if self.boss_ativo is not None and self.boss_ativo.vivo:
            bx, by = self.camera.aplicar((self.boss_ativo.x, self.boss_ativo.y))
            if -margem <= bx <= LARGURA + margem and -margem <= by <= ALTURA + margem:
                pulso = 0.5 + 0.5 * math.sin(tempo * 3.0)
                luzes.append(
                    Luz(bx, by - 60, 240, self.boss_ativo.cor, 130 + int(30 * pulso))
                )

        for d in self.mundo.decoracoes:
            sx, sy = self.camera.aplicar((d.x, d.y))
            if sx < -margem or sy < -margem or sx > LARGURA + margem or sy > ALTURA + margem:
                continue
            if d.tipo == "cristal":
                pulso = 0.75 + 0.25 * math.sin(tempo * 2.2 + d.fase)
                luzes.append(
                    Luz(sx, sy - 30 * d.escala, int(110 * d.escala), d.cor, int(96 + 26 * pulso))
                )
            elif d.tipo == "lampiao":
                luzes.append(Luz(sx, sy - 52 * d.escala, int(180 * d.escala), (255, 196, 120), 150))
            elif d.tipo == "fonte":
                luzes.append(Luz(sx, sy - 46 * d.escala, 120, (120, 210, 240), 85))
            elif d.tipo == "obelisco":
                luzes.append(Luz(sx, sy - 58 * d.escala, 130, (120, 220, 236), 110))
            elif d.tipo == "altar":
                luzes.append(Luz(sx, sy - 32 * d.escala, 130, (100, 180, 255), 120))
            elif d.tipo == "cogumelo":
                luzes.append(Luz(sx, sy - 16 * d.escala, 70, d.cor, 70))
            elif d.tipo == "fogueira":
                pulso = 0.5 + 0.5 * math.sin(tempo * 6.0 + d.fase)
                luzes.append(Luz(sx, sy - 18 * d.escala, int(170 * d.escala), (255, 170, 90), int(150 + 30 * pulso)))

        return luzes

    # ------------------------------------------------------------------ eventos
    def processar_evento(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.rodando = False
            return
        if (
            self.modo_toque and self.toque.js_ativo
            and event.type in (
                pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION,
                pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP,
            )
        ):
            return
        for botao in self.entrada.processar_evento(event):
            self._botao_controle(botao)
        if self.modo_toque:
            if self.toque.processar_evento(event, self):
                return
            pos = self.toque.pos_evento(event)
            if pos is not None:
                if event.type in (pygame.FINGERDOWN, pygame.MOUSEBUTTONDOWN):
                    if self.estado == "jogando":
                        self.mouse_world = self.camera.mundo(pos)
                        if self.jogador is not None:
                            self.jogador.atacar(self, self.mouse_world)
                    else:
                        self._clique(pos, 1)
                    return
                if event.type in (pygame.FINGERMOTION, pygame.MOUSEMOTION):
                    if self.estado in ("jogando", "pausa", "painel"):
                        self.mouse_world = self.camera.mundo(pos)
                    return
        if event.type == pygame.KEYDOWN:
            self._tecla(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._clique(event.pos, event.button)
        elif event.type == pygame.MOUSEMOTION:
            if self.estado in ("jogando", "pausa", "painel"):
                self.mouse_world = self.camera.mundo(event.pos)

    def _tecla(self, tecla: int) -> None:
        if tecla == pygame.K_m:
            self.alternar_mudo()
            return
        if self.estado == "configuracoes":
            if tecla in (pygame.K_ESCAPE, pygame.K_F1):
                self.fechar_configuracoes()
            return
        if self.estado == "menu":
            if tecla == pygame.K_ESCAPE:
                self.rodando = False
            elif tecla == pygame.K_F1:
                self.abrir_configuracoes("menu")
            return
        if self.estado == "selecao":
            if tecla == pygame.K_ESCAPE:
                self.estado = "menu"
            return
        if self.estado == "jogando":
            if tecla == pygame.K_ESCAPE:
                self.estado = "pausa"
            elif tecla == pygame.K_F1:
                self.abrir_configuracoes("pausa")
            elif tecla in (pygame.K_i, pygame.K_TAB):
                self.ui.painel.aba = "Inventário"
                self.estado = "painel"
            elif tecla == pygame.K_c:
                self.ui.painel.aba = "Equipamentos"
                self.estado = "painel"
            elif tecla == pygame.K_k:
                self.ui.painel.aba = "Habilidades"
                self.estado = "painel"
            elif tecla == pygame.K_j:
                self.ui.painel.aba = "Cristais"
                self.estado = "painel"
            elif tecla == pygame.K_q:
                self._usar_skill(0)
            elif tecla == pygame.K_e:
                self._usar_skill(1)
            elif tecla == pygame.K_r:
                self._usar_skill(2)
            elif tecla == pygame.K_f:
                self._usar_skill(3)
            elif tecla == pygame.K_1:
                self._usar_pocao("vida")
            elif tecla == pygame.K_2:
                self._usar_pocao("mana")
            elif tecla == pygame.K_3:
                self._usar_pocao("stamina")
            elif tecla == pygame.K_SPACE:
                if self.jogador is not None:
                    self.jogador.atacar(self, self.mouse_world)
            elif tecla == pygame.K_t:
                self._interagir()
            elif tecla == pygame.K_v:
                self._esquivar()
            elif tecla == pygame.K_F2:
                self.pular_etapa_tutorial()
            elif tecla == pygame.K_F3:
                self.pular_tutorial()
            elif tecla == pygame.K_F5:
                self.salvar()
            return
        if self.estado == "pausa":
            if tecla == pygame.K_ESCAPE:
                self.estado = "jogando"
            elif tecla == pygame.K_F1:
                self.abrir_configuracoes("pausa")
            return
        if self.estado == "painel":
            if tecla in (pygame.K_ESCAPE, pygame.K_i, pygame.K_c, pygame.K_k, pygame.K_j, pygame.K_TAB):
                self.estado = "jogando"
            return
        if self.estado == "morte":
            if tecla in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self._renascer()
            elif tecla == pygame.K_ESCAPE:
                self.estado = "menu"
            return
        if self.estado == "vitoria":
            if tecla == pygame.K_ESCAPE:
                self.estado = "menu"

    def alternar_mudo(self) -> None:
        """Liga/desliga todo o som e guarda a escolha."""
        self.prefs.mudo = not self.prefs.mudo
        self._aplicar_audio()
        salvar_preferencias(self.prefs)
        self.ui.notificar("Som desligado (M)" if self.prefs.mudo else "Som ligado (M)", AMARELO)

    def _clique(self, pos: tuple[int, int], botao: int) -> None:
        if self.estado in ("menu", "selecao", "pausa", "configuracoes", "morte", "vitoria"):
            self.sons.tocar("clique", 0.5)
        if self.estado == "configuracoes":
            acao = self.ui_config.processar_clique(pos)
            if acao == "voltar":
                self.fechar_configuracoes()
            elif acao == "reset":
                self.resetar_preferencias()
            elif acao == "aba":
                return
            elif acao is not None:
                self.alternar_preferencia(acao)
            return
        if self.estado == "menu":
            acao = self.ui.clique_menu(pos)
            if acao == "novo":
                self.estado = "selecao"
            elif acao == "continuar":
                self.carregar()
            elif acao == "configuracoes":
                self.abrir_configuracoes("menu")
            elif acao == "sair":
                self.rodando = False
            return
        if self.estado == "selecao":
            escolha = self.ui.clique_selecao(pos)
            if escolha == "voltar":
                self.estado = "menu"
            elif escolha in ("Cavaleiro", "Arqueira", "Maga"):
                self.novo_jogo(escolha)
            return
        if self.estado == "jogando":
            if botao == 1 and self.jogador is not None:
                self.jogador.atacar(self, self.mouse_world)
            elif botao == 3:
                self._usar_pocao_rapida()
            return
        if self.estado == "pausa":
            acao = self.ui.clique_pausa(pos)
            if acao == "continuar":
                self.estado = "jogando"
            elif acao == "salvar":
                self.salvar()
            elif acao == "configuracoes":
                self.abrir_configuracoes("pausa")
            elif acao == "menu":
                self.estado = "menu"
            return
        if self.estado == "painel":
            tratado = self.ui.painel.processar_clique(pos, self, botao)
            if not tratado and not self.ui.painel.rect_painel.collidepoint(pos):
                self.estado = "jogando"
            return
        if self.estado == "morte":
            acao = self.ui.clique_morte(pos)
            if acao == "renascer":
                self._renascer()
            elif acao == "menu":
                self.estado = "menu"
            return
        if self.estado == "vitoria":
            acao = self.ui.clique_vitoria(pos)
            if acao == "continuar":
                self.estado = "jogando"
            elif acao == "menu":
                self.estado = "menu"

    def _usar_skill(self, indice: int) -> None:
        if self.jogador is None:
            return
        h = self.jogador.habilidades[indice]
        if self.jogador.cooldowns.get(h.id, 0) > 0:
            return
        if h.custo_tipo == "mp" and self.jogador.mp < h.custo_atual:
            self.ui.notificar("Mana insuficiente.", AZUL)
            return
        if h.custo_tipo == "stamina" and self.jogador.stamina < h.custo_atual:
            self.ui.notificar("Stamina insuficiente.", AMARELO)
            return
        self.jogador.usar_habilidade(indice, self, self.mouse_world)
        self.sons.tocar(som_da_habilidade(h), 0.6)

    def _usar_pocao_rapida(self) -> None:
        """Atalho principal (clique direito / LB): poção de vida."""
        self._usar_pocao("vida")

    def comprar_item(self, chave: str) -> None:
        if self.jogador is None:
            return
        if not self.na_vila_veyra():
            self.ui.notificar("O mercado fica na Vila de Veyra.", AMARELO)
            return
        preco = PRECOS_MERCADO.get(chave)
        if preco is None:
            return
        if self.jogador.ouro < preco:
            self.ui.notificar("Ouro insuficiente.", VERMELHO)
            return
        if chave.startswith("pocao_"):
            item: Any = Pocao(chave[6:], 1)
        elif chave == "cristal":
            item = gerar_cristal(self.jogador.nivel)
        elif chave == "equipamento_epico":
            item = gerar_equipamento(self.jogador.nivel, self.jogador.classe, raridade="Épico")
        else:
            item = gerar_equipamento(self.jogador.nivel, self.jogador.classe, raridade="Raro")
        if not self.jogador.adicionar_item(item):
            self.ui.notificar("Inventário cheio. Venda algo primeiro.", VERMELHO)
            return
        self.jogador.ouro -= preco
        self.sons.tocar("compra", 0.8)
        self.ui.notificar(f"Comprado: {item.nome} ({preco} ouro).", getattr(item, "cor", DOURADO))

    def _esquivar(self) -> None:
        if self.jogador is None:
            return
        dx, dy = self.entrada.eixo_movimento()
        if abs(dx) + abs(dy) < 0.12:
            dx, dy = self.jogador.facing
        self.jogador.esquivar(self, (dx, dy))

    def na_vila_veyra(self) -> bool:
        if self.jogador is None:
            return False
        zona = self.mundo.zona_em(self.jogador.x, self.jogador.y)
        return zona is not None and zona.nome == "Vila de Veyra"

    def custo_reforco(self, equipamento: Equipamento) -> int:
        return CUSTO_REFORCO_BASE + equipamento.nivel * 30 + equipamento.melhorias * 60

    def custo_respec(self) -> int:
        if self.jogador is None:
            return 0
        return CUSTO_RESPEC_BASE + CUSTO_RESPEC_POR_NIVEL * self.jogador.nivel

    def resetar_atributos(self) -> None:
        if self.jogador is None:
            return
        if sum(self.jogador.atributos.values()) <= 0:
            self.ui.notificar("Nenhum ponto de atributo para redistribuir.", AMARELO)
            return
        custo = self.custo_respec()
        if self.jogador.ouro < custo:
            self.ui.notificar(f"Ouro insuficiente ({custo} necessário).", VERMELHO)
            return
        pontos = self.jogador.resetar_atributos()
        self.jogador.ouro -= custo
        self.sons.tocar("level_up", 0.5)
        self.ui.notificar(f"{pontos} pontos devolvidos por {custo} ouro.", VERDE)

    def _cristais_no_inventario(self) -> int:
        if self.jogador is None:
            return 0
        return sum(1 for item in self.jogador.inventario if isinstance(item, Cristal))

    def reforcar_equipamento(self, slot: str) -> None:
        if self.jogador is None:
            return
        if not self.na_vila_veyra():
            self.ui.notificar("Reforços só na forja da Vila de Veyra.", AMARELO)
            return
        eq = self.jogador.equipamentos.get(slot)
        if eq is None:
            self.ui.notificar("Nenhum item equipado nesse slot.", AMARELO)
            return
        if eq.melhorias >= 5:
            self.ui.notificar("Este item já está no reforço máximo.", AMARELO)
            return
        custo = self.custo_reforco(eq)
        if self.jogador.ouro < custo:
            self.ui.notificar(f"Ouro insuficiente ({custo} necessário).", VERMELHO)
            return
        if self._cristais_no_inventario() < 1:
            self.ui.notificar("Você precisa de 1 cristal para reforçar.", VERMELHO)
            return
        self.jogador.consumir_cristal()
        if self.jogador.melhorar_equipamento(slot):
            self.jogador.ouro -= custo
            self.sons.tocar("forja", 0.8)
            self.ui.notificar(
                f"{eq.nome} reforçado (+{eq.melhorias}/5) por {custo} ouro e 1 cristal.",
                DOURADO,
            )

    def encantar_equipamento(self, slot: str) -> None:
        if self.jogador is None:
            return
        if not self.na_vila_veyra():
            self.ui.notificar("Encantamentos só na Vila de Veyra.", AMARELO)
            return
        eq = self.jogador.equipamentos.get(slot)
        if eq is None:
            self.ui.notificar("Nenhum item equipado nesse slot.", AMARELO)
            return
        if eq.encantamentos >= 3:
            self.ui.notificar("Este item já tem 3 encantamentos.", AMARELO)
            return
        if self.jogador.ouro < CUSTO_ENCANTAMENTO:
            self.ui.notificar(f"Ouro insuficiente ({CUSTO_ENCANTAMENTO} necessário).", VERMELHO)
            return
        if self._cristais_no_inventario() < 1:
            self.ui.notificar("Você precisa de 1 cristal para encantar.", VERMELHO)
            return
        self.jogador.consumir_cristal()
        bonus = self.jogador.encantar_equipamento(slot)
        if bonus is not None:
            self.jogador.ouro -= CUSTO_ENCANTAMENTO
            self.sons.tocar("encanto", 0.8)
            self.ui.notificar(f"{eq.nome}: {bonus} ({eq.encantamentos}/3).", DOURADO)

    def forjar_equipamento(self, raridade: str) -> None:
        if self.jogador is None:
            return
        if not self.na_vila_veyra():
            self.ui.notificar("Forja só na Vila de Veyra.", AMARELO)
            return
        custo = CUSTO_FORJA.get(raridade)
        if custo is None:
            return
        custo_cristais = CRISTAIS_FORJA.get(raridade, 2)
        if self.jogador.ouro < custo:
            self.ui.notificar(f"Ouro insuficiente ({custo} necessário).", VERMELHO)
            return
        if self._cristais_no_inventario() < custo_cristais:
            self.ui.notificar(f"Você precisa de {custo_cristais} cristais para forjar.", VERMELHO)
            return
        item = gerar_equipamento(self.jogador.nivel, self.jogador.classe, raridade=raridade)
        if not self.jogador.adicionar_item(item):
            self.ui.notificar("Inventário cheio. Venda algo primeiro.", VERMELHO)
            return
        for _ in range(custo_cristais):
            self.jogador.consumir_cristal()
        self.jogador.ouro -= custo
        self.sons.tocar("forja", 0.9)
        self.ui.notificar(
            f"Forjado: {item.nome} ({raridade}) por {custo} ouro e {custo_cristais} cristais.",
            item.cor,
        )

    def fundir_cristais(self) -> None:
        if self.jogador is None:
            return
        criados = self.jogador.fundir_cristais()
        if not criados:
            self.ui.notificar("Você precisa de 3 cristais do mesmo tipo e tier.", AMARELO)
            return
        self.sons.tocar("cristal", 0.8)
        nomes = ", ".join(c.nome for c in criados[:3])
        if len(criados) > 3:
            nomes += f" e mais {len(criados) - 3}"
        self.ui.notificar(f"Cristais fundidos: {nomes}.", DOURADO)

    def _usar_pocao(self, tipo: str) -> None:
        if self.jogador is None:
            return
        if self.pocao_cooldown > 0:
            self.ui.notificar("Aguarde um instante para usar outra poção.", AMARELO)
            return
        nomes = {"vida": "vida", "mana": "mana", "stamina": "fôlego"}
        cheios = {
            "vida": "A vida já está cheia.",
            "mana": "A mana já está cheia.",
            "stamina": "O fôlego já está cheio.",
        }
        for item in self.jogador.inventario:
            if isinstance(item, Pocao) and item.tipo == tipo:
                if self.jogador.usar_pocao(item):
                    self.sons.tocar("pocao", 0.8)
                    self.ui.notificar(f"{item.nome} usado.", item.cor)
                    self.pocao_cooldown = COOLDOWN_POCAO
                else:
                    self.ui.notificar(cheios.get(tipo, "Recurso já está cheio."), AMARELO)
                return
        self.ui.notificar(f"Nenhuma poção de {nomes.get(tipo, tipo)} disponível.", VERMELHO)

    def _renascer(self) -> None:
        if self.jogador is None:
            return
        self.jogador.x, self.jogador.y = self.mundo.spawn_jogador
        self.jogador.morto = False
        self.jogador.hp = float(self.jogador.hp_max)
        self.jogador.mp = float(self.jogador.mp_max)
        self.jogador.stamina = float(self.jogador.stamina_max)
        self.jogador.invulneravel = 2.0
        self.projeteis.clear()
        self.areas.clear()
        self.boss_ativo = None
        self.boss_alerta = 0.0
        self.boss_nome = ""
        self.errante_vida = 0.0
        self.evento_timer = random.uniform(90, 150)
        self._ultimo_evento = ""
        self._spawn_inicial()
        self._snap_camera()
        self.estado = "jogando"
        self.ui.notificar("Você renasceu na Clareira de Lumen.", VERDE)

    # ------------------------------------------------------------------ combate
    def criar_projetil_jogador(
        self, x: float, y: float, angulo: float, velocidade: float, dano: float,
        raio: float, cor: tuple[int, int, int], tipo_visual: str,
        critico: bool = False, perfurante: bool = False,
        explosao: float = 0.0, slow: float = 0.0,
        status: dict[str, float | str] | None = None,
    ) -> None:
        vx, vy = math.cos(angulo) * velocidade, math.sin(angulo) * velocidade
        self.projeteis.append(
            Projetil(
                x, y, vx, vy, dano, "jogador", raio, cor, tipo_visual,
                perfurante=perfurante, critico=critico, explosao=explosao, slow=slow,
                status=status,
            )
        )

    def criar_projetil_inimigo(
        self, x: float, y: float, angulo: float, velocidade: float, dano: float,
        raio: float, cor: tuple[int, int, int], tipo_visual: str,
    ) -> None:
        vx, vy = math.cos(angulo) * velocidade, math.sin(angulo) * velocidade
        self.projeteis.append(
            Projetil(x, y, vx, vy, dano, "inimigo", raio, cor, tipo_visual)
        )

    def criar_explosao(
        self, x: float, y: float, raio: float, dano: float, dono: str,
        cor: tuple[int, int, int], critico: bool = False, slow: float = 0.0,
    ) -> None:
        self.areas.append(AreaPerigo(x, y, raio, dano, dono, 0.12, cor, critico, slow))
        self.efeitos.append(Efeito("explosao", x, y, raio, 0.38, cor))
        self.particulas.emitir(x, y, cor, 22, 160, 5, 0.5)

    def efeito_ataque(self, jogador: Jogador, angulo: float, tipo: str) -> None:
        if tipo == "espada":
            for i in range(7):
                a = angulo - 0.8 + i * 0.23
                self.particulas.emitir(
                    jogador.x + math.cos(a) * 50, jogador.y - 30 + math.sin(a) * 50,
                    (250, 240, 200), 2, 50, 3, 0.3,
                )
        else:
            x = jogador.x + math.cos(angulo) * 26
            y = jogador.y - 34 + math.sin(angulo) * 26
            cor = (220, 250, 200) if tipo == "arco" else (210, 150, 255)
            self.particulas.emitir(x, y, cor, 6, 90, 3, 0.3, direcao=angulo, espalhar=0.7)
        self.tremer(2.0, 0.12)

    def efeito_ataque_inimigo(self, inimigo: Inimigo, angulo: float) -> None:
        self.particulas.emitir(
            inimigo.x + math.cos(angulo) * 24, inimigo.y - 26 + math.sin(angulo) * 24,
            (250, 140, 100), 8, 90, 4, 0.35, direcao=angulo, espalhar=0.8,
        )
        self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, inimigo.raio * 1.8, 0.25, (250, 140, 100)))
        self.tremer(3.0, 0.12)
        if self.jogador is not None:
            d = distancia((self.jogador.x, self.jogador.y), (inimigo.x, inimigo.y))
            volume = max(0.0, 1.0 - d / 520.0) * (1.0 if inimigo.boss else 0.7)
            if volume > 0.05:
                self.sons.tocar("inimigo_ataque", volume, intervalo=0.06)

    def avisar_ataque(self, inimigo: Inimigo) -> None:
        self.particulas.emitir(inimigo.x, inimigo.y - inimigo.raio * 1.8, (250, 190, 90), 5, 40, 3, 0.4)
        if self.jogador is not None:
            d = distancia((self.jogador.x, self.jogador.y), (inimigo.x, inimigo.y))
            volume = max(0.0, 1.0 - d / 420.0) * 0.45
            if volume > 0.03:
                self.sons.tocar("perigo", volume, intervalo=0.22)

    def executar_habilidade(self, jogador: Jogador, h: Habilidade, alvo: tuple[float, float]) -> None:
        tier_mult = 1.0 + 0.22 * (h.tier - 1)
        angulo = math.atan2(alvo[1] - jogador.y, alvo[0] - jogador.x)
        self.efeitos.append(Efeito("runa", jogador.x, jogador.y - 12, 58, 0.45, h.cor))

        raio = h.raio_atual
        if h.tier >= 5:
            raio *= parametro(h, "raio5", 1.0)
        elif h.tier >= 3:
            raio *= parametro(h, "raio3", 1.0)

        def onda_extra(fracao: float, atraso: float, x: float, y: float, r: float) -> None:
            dano_extra, crit_extra = jogador.rolar_dano(h.dano_mult * tier_mult * fracao)
            self.areas.append(AreaPerigo(
                x, y, r, dano_extra, "jogador", atraso, h.cor, crit_extra,
                status=self._status_da_habilidade(h, dano_extra),
            ))

        if h.tipo == "aoe_self":
            for inimigo in self.inimigos:
                if inimigo.vivo and distancia((jogador.x, jogador.y), (inimigo.x, inimigo.y)) <= raio + inimigo.raio:
                    dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
                    dano_final = inimigo.receber_dano(dano, self, crit)
                    self._aplicar_status_habilidade(inimigo, h, dano_final)
            self.efeitos.append(Efeito("onda", jogador.x, jogador.y, raio, 0.4, h.cor))
            self.particulas.emitir(jogador.x, jogador.y - 30, h.cor, 20, 150, 4, 0.5)
            self.tremer(6, 0.2)
            fracao = (
                parametro(h, "onda5", 0.0) if h.tier >= 5
                else parametro(h, "onda3", 0.0) if h.tier >= 3
                else 0.0
            )
            if fracao > 0:
                onda_extra(fracao, 0.35, jogador.x, jogador.y, raio)

        elif h.tipo == "dash":
            passos = int(parametro(h, "passos5", 9)) if h.tier >= 5 else 9
            dx = math.cos(angulo) * 18
            dy = math.sin(angulo) * 18
            acertados: set[int] = set()
            lento = parametro(h, "lentidao3", 0.0) if h.tier >= 3 else 0.0
            for _ in range(passos):
                jogador.mover(dx, dy, self.mundo)
                for inimigo in self.inimigos:
                    if not inimigo.vivo or id(inimigo) in acertados:
                        continue
                    if distancia((jogador.x, jogador.y), (inimigo.x, inimigo.y)) < 58 + inimigo.raio:
                        dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
                        dano_final = inimigo.receber_dano(dano, self, crit)
                        self._aplicar_status_habilidade(inimigo, h, dano_final)
                        if lento > 0:
                            inimigo.slow_timer = max(inimigo.slow_timer, lento)
                        acertados.add(id(inimigo))
                self.particulas.emitir(jogador.x, jogador.y - 20, h.cor, 2, 40, 3, 0.3)
            self.efeitos.append(Efeito("onda", jogador.x, jogador.y, 80, 0.3, h.cor))
            self.tremer(5, 0.18)

        elif h.tipo == "buff":
            duracao = h.duracao * (parametro(h, "duracao3", 1.0) if h.tier >= 3 else 1.0)
            jogador.aplicar_buff(h.id, h.extra.get("buff", {}), duracao)
            if h.tier >= 5:
                cura = jogador.hp_max * parametro(h, "cura5", 0.0)
                if cura > 0:
                    jogador.curar(cura)
                    self.ui.notificar(f"{h.nome} também restaurou {int(cura)} de vida!", h.cor)
            self.efeitos.append(Efeito("onda", jogador.x, jogador.y, 90, 0.5, h.cor))
            self.particulas.emitir(jogador.x, jogador.y - 30, h.cor, 24, 120, 4, 0.6)
            self.ui.notificar(f"{h.nome} ativo por {duracao:.0f}s!", h.cor)

        elif h.tipo == "projetil":
            explosao = float(h.extra.get("explosao", 0))
            if h.tier >= 3:
                explosao *= parametro(h, "explosao3", 1.0)
            lento = parametro(h, "lentidao5", 0.0) if h.tier >= 5 else 0.0
            quantidade = int(parametro(h, "projeteis5", 1)) if h.tier >= 5 else 1
            desvios = [0.0] if quantidade <= 1 else [
                -0.11 + 0.22 * i / (quantidade - 1) for i in range(quantidade)
            ]
            for desvio in desvios:
                dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
                self.criar_projetil_jogador(
                    jogador.x, jogador.y - 24, angulo + desvio, 620, dano, h.raio, h.cor,
                    h.extra.get("visual", "magia"),
                    critico=crit, explosao=explosao, slow=lento,
                    status=self._status_da_habilidade(h, dano),
                )
            self.tremer(3, 0.12)

        elif h.tipo == "projetil_duplo":
            quantidade = 2
            if h.tier >= 5:
                quantidade = int(parametro(h, "projeteis5", 2))
            elif h.tier >= 3:
                quantidade = int(parametro(h, "projeteis3", 2))
            for i in range(quantidade):
                desvio = 0.0 if quantidade <= 1 else -0.14 + 0.28 * i / (quantidade - 1)
                dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
                self.criar_projetil_jogador(
                    jogador.x, jogador.y - 28, angulo + desvio, 800, dano, h.raio,
                    h.cor, "flecha", critico=crit,
                    status=self._status_da_habilidade(h, dano),
                )
            self.tremer(2, 0.1)

        elif h.tipo == "aoe_cursor":
            dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
            self.areas.append(AreaPerigo(
                alvo[0], alvo[1], raio, dano, "jogador", 0.55, h.cor, crit,
                status=self._status_da_habilidade(h, dano),
            ))
            self.efeitos.append(Efeito("onda", alvo[0], alvo[1], raio, 0.6, h.cor))
            self.particulas.emitir(alvo[0], alvo[1], h.cor, 16, 130, 4, 0.5)
            self.tremer(4, 0.15)
            if h.tier >= 5:
                fracao = parametro(h, "onda5", 0.0)
                if fracao > 0:
                    onda_extra(fracao, 0.55, alvo[0], alvo[1], raio)

        elif h.tipo == "projetil_perfurante":
            quantidade = int(parametro(h, "projeteis5", 1)) if h.tier >= 5 else 1
            lento = parametro(h, "lentidao3", 0.0) if h.tier >= 3 else 0.0
            for i in range(quantidade):
                desvio = 0.0 if quantidade <= 1 else -0.12 + 0.24 * i / (quantidade - 1)
                dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
                self.criar_projetil_jogador(
                    jogador.x, jogador.y - 28, angulo + desvio, 920, dano, h.raio, h.cor,
                    "flecha", critico=crit, perfurante=True, slow=lento,
                    status=self._status_da_habilidade(h, dano),
                )
            self.tremer(4, 0.15)

        elif h.tipo == "nova":
            gelo = h.duracao
            if h.tier >= 3:
                gelo = max(gelo, parametro(h, "gelo3", gelo))
            dano, crit = jogador.rolar_dano(h.dano_mult * tier_mult)
            self.areas.append(AreaPerigo(
                jogador.x, jogador.y, raio, dano, "jogador", 0.22, h.cor, crit, slow=gelo,
                status=self._status_da_habilidade(h, dano),
            ))
            self.efeitos.append(Efeito("onda", jogador.x, jogador.y, raio, 0.55, h.cor))
            self.particulas.emitir(jogador.x, jogador.y - 20, h.cor, 26, 180, 4, 0.6)
            self.tremer(5, 0.2)
            if h.tier >= 5:
                fracao = parametro(h, "onda5", 0.0)
                if fracao > 0:
                    onda_extra(fracao, 0.4, jogador.x, jogador.y, raio)

        elif h.tipo == "chain":
            saltos = int(h.extra.get("saltos", 3))
            if h.tier >= 5:
                saltos += int(parametro(h, "saltos5", 0))
            elif h.tier >= 3:
                saltos += int(parametro(h, "saltos3", 0))
            mult_dano = h.dano_mult * tier_mult
            if h.tier >= 5:
                mult_dano *= parametro(h, "dano5", 1.0)
            candidatos = sorted(
                (i for i in self.inimigos if i.vivo and distancia((jogador.x, jogador.y), (i.x, i.y)) <= raio),
                key=lambda i: distancia((jogador.x, jogador.y), (i.x, i.y)),
            )[:saltos]
            pontos = [(jogador.x, jogador.y - 30)]
            for inimigo in candidatos:
                dano, crit = jogador.rolar_dano(mult_dano)
                dano_final = inimigo.receber_dano(dano, self, crit)
                self._aplicar_status_habilidade(inimigo, h, dano_final)
                pontos.append((inimigo.x, inimigo.y - 24))
                self.particulas.emitir(inimigo.x, inimigo.y - 20, h.cor, 10, 100, 4, 0.4)
            if len(pontos) > 1:
                self.efeitos.append(Efeito("raio", jogador.x, jogador.y, 0, 0.32, h.cor, pontos))
            self.tremer(6, 0.2)

    def executar_especial_boss(self, inimigo: Inimigo) -> None:
        if self.jogador is None:
            return
        alvo = (self.jogador.x, self.jogador.y)
        ang = math.atan2(self.jogador.y - inimigo.y, self.jogador.x - inimigo.x)
        if inimigo.tipo == "rei_slime":
            self.areas.append(AreaPerigo(alvo[0], alvo[1], 135, inimigo.ataque * 1.8, "inimigo", 0.9, (250, 130, 80)))
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 180, 0.6, (250, 160, 90)))
        elif inimigo.tipo == "golem_anciao":
            for i in range(5):
                self.criar_projetil_inimigo(
                    inimigo.x, inimigo.y - 30, ang + (i - 2) * 0.20, 330,
                    inimigo.ataque * 0.8, 10, (170, 150, 120), "pedra",
                )
            self.areas.append(AreaPerigo(alvo[0], alvo[1], 115, inimigo.ataque * 1.5, "inimigo", 0.95, (250, 160, 90)))
        elif inimigo.tipo == "rainha_lodo":
            # poças de veneno ao redor do jogador, com aviso antes de fechar
            for i in range(3):
                a = ang + (i - 1) * 0.55
                px = alvo[0] + math.cos(a) * 95
                py = alvo[1] + math.sin(a) * 70
                self.areas.append(
                    AreaPerigo(px, py, 76, inimigo.ataque * 1.15, "inimigo", 1.0, (140, 220, 110), slow=1.4)
                )
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 190, 0.6, (150, 230, 130)))
        elif inimigo.tipo == "avatar_aether":
            for i in range(16):
                self.criar_projetil_inimigo(
                    inimigo.x, inimigo.y - 36, i * math.tau / 16 + ang * 0.2, 320,
                    inimigo.ataque * 0.72, 10, (196, 238, 255), "cristal",
                )
            for i in range(2):
                px = alvo[0] + math.cos(ang + i * math.pi) * 90
                py = alvo[1] + math.sin(ang + i * math.pi) * 90
                self.areas.append(
                    AreaPerigo(px, py, 105, inimigo.ataque * 1.35, "inimigo", 1.0, (180, 226, 255))
                )
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 220, 0.7, (210, 244, 255)))
        elif inimigo.tipo == "ceifador_nevoa":
            for i in range(5):
                self.criar_projetil_inimigo(
                    inimigo.x, inimigo.y - 20, ang + (i - 2) * 0.22, 380,
                    inimigo.ataque * 0.85, 8, (180, 225, 250), "magia",
                )
            self.areas.append(
                AreaPerigo(
                    alvo[0], alvo[1], 95, inimigo.ataque * 1.15,
                    "inimigo", 0.9, (150, 210, 240), slow=1.2,
                )
            )
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 160, 0.55, (190, 230, 250)))
        elif inimigo.tipo == "serpente_colossal":
            for i in range(10):
                self.criar_projetil_inimigo(
                    inimigo.x, inimigo.y - 24, i * math.tau / 10, 300,
                    inimigo.ataque * 0.7, 9, (140, 240, 190), "magia",
                )
            self.areas.append(
                AreaPerigo(
                    alvo[0], alvo[1], 115, inimigo.ataque * 1.2,
                    "inimigo", 1.0, (120, 230, 170), slow=1.4,
                )
            )
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 200, 0.6, (150, 240, 190)))
        elif inimigo.tipo == "guardiao_eclipse":
            for i in range(18):
                a = ang + i * math.tau / 18 + inimigo.tempo * 0.4
                self.criar_projetil_inimigo(
                    inimigo.x, inimigo.y - 30, a, 340,
                    inimigo.ataque * 0.65, 9, (190, 140, 240), "cristal",
                )
            for i in range(2):
                px = alvo[0] + math.cos(ang + i * math.pi) * 110
                py = alvo[1] + math.sin(ang + i * math.pi) * 110
                self.areas.append(
                    AreaPerigo(
                        px, py, 120, inimigo.ataque * 1.25,
                        "inimigo", 1.0, (170, 110, 220),
                    )
                )
            self.efeitos.append(Efeito("onda", inimigo.x, inimigo.y, 240, 0.7, (200, 160, 255)))
            self.piscar((80, 40, 120), 0.25)
        else:
            for i in range(12):
                self.criar_projetil_inimigo(
                    inimigo.x, inimigo.y - 30, i * math.tau / 12, 290,
                    inimigo.ataque * 0.7, 9, (190, 120, 240), "cristal",
                )
            self.areas.append(AreaPerigo(alvo[0], alvo[1], 105, inimigo.ataque * 1.3, "inimigo", 0.85, (190, 110, 240)))
        inimigo.especial_timer = random.uniform(3.2, 5.0)
        self.tremer(11, 0.35)
        self.particulas.emitir(inimigo.x, inimigo.y - 30, inimigo.cor, 30, 170, 5, 0.6)

    # ------------------------------------------------------------------ dano e morte
    def registrar_dano_inimigo(self, inimigo: Inimigo, dano: float, critico: bool) -> None:
        self.sons.tocar("critico" if critico else "acerto", 0.8 if critico else 0.6)
        if self.prefs.numeros_dano:
            self.textos.append(
                TextoFlutuante(
                    inimigo.x + random.uniform(-12, 12), inimigo.y - inimigo.raio * 1.7,
                    f"{int(dano)}", (255, 230, 120) if critico else (240, 240, 245),
                    22 if critico else 15, 0.75,
                )
            )
        self.particulas.emitir(inimigo.x, inimigo.y - inimigo.raio * 0.6, (250, 220, 150), 5, 70, 3, 0.3)
        if self.jogador is not None:
            ang = math.atan2(inimigo.y - self.jogador.y, inimigo.x - self.jogador.x)
            self.particulas.emitir_direcional(
                inimigo.x, inimigo.y - inimigo.raio * 0.6,
                (255, 236, 190), ang, 8 if critico else 4, 200, 3, 0.22,
            )
        self.parar_tempo(0.10 if critico else 0.045)
        if critico:
            self.tremer(3, 0.1)
            self.piscar((255, 244, 200), 0.16)
            self.efeitos.append(
                Efeito("onda", inimigo.x, inimigo.y - inimigo.raio * 0.6, 36, 0.22, (255, 248, 220))
            )

    def registrar_dano_status(self, inimigo: Inimigo, dano: float, tipo: str) -> None:
        """Dano de status: texto pequeno e partículas, sem som nem hit-stop."""
        cor = STATUS_CORES.get(tipo, (240, 240, 240))
        if self.prefs.numeros_dano:
            self.textos.append(
                TextoFlutuante(
                    inimigo.x + random.uniform(-10, 10), inimigo.y - inimigo.raio * 1.6,
                    f"{int(dano)}", cor, 12, 0.5,
                )
            )
        self.particulas.emitir(inimigo.x, inimigo.y - inimigo.raio * 0.8, cor, 2, 30, 2, 0.25)

    def aplicar_status(
        self, inimigo: Inimigo, tipo: str, dano_por_segundo: float = 0.0, tempo: float = 0.0,
    ) -> None:
        """Aplica status e resolve combinações (gelo+fogo, veneno+sangramento)."""
        if not inimigo.vivo:
            return
        if tipo in ("queimadura", "gelo"):
            oposto = "gelo" if tipo == "queimadura" else "queimadura"
            if oposto in inimigo.status:
                del inimigo.status[oposto]
                if oposto == "gelo":
                    inimigo.slow_timer = 0.0
                bonus = inimigo.hp_max * 0.06
                inimigo.receber_dano(bonus, self, False)
                if not inimigo.vivo:
                    return
                self.textos.append(
                    TextoFlutuante(
                        inimigo.x, inimigo.y - inimigo.raio * 2.3,
                        "Choque térmico!", (150, 230, 255), 14, 0.8,
                    )
                )
                self.particulas.emitir(inimigo.x, inimigo.y - inimigo.raio, (180, 240, 255), 14, 90, 3, 0.4)
        elif tipo == "veneno" and "sangramento" in inimigo.status:
            bonus = inimigo.hp_max * 0.05
            inimigo.receber_dano(bonus, self, False)
            if not inimigo.vivo:
                return
            self.textos.append(
                TextoFlutuante(
                    inimigo.x, inimigo.y - inimigo.raio * 2.3,
                    "Hemorragia!", (180, 240, 140), 14, 0.8,
                )
            )
        inimigo.aplicar_status(tipo, dano_por_segundo, tempo)

    def _status_da_habilidade(self, h: Habilidade, dano: float) -> dict[str, float | str] | None:
        mapa = {
            "golpe_giro": ("sangramento", 0.12, 3.0),
            "investida": ("atordoado", 0.0, 0.7),
            "golpe_sismico": ("atordoado", 0.0, 1.0),
            "flecha_dupla": ("sangramento", 0.10, 2.5),
            "chuva_flechas": ("sangramento", 0.12, 3.0),
            "tiro_certeiro": ("sangramento", 0.15, 4.0),
            "flecha_explosiva": ("queimadura", 0.12, 3.0),
            "bola_fogo": ("queimadura", 0.12, 3.0),
            "nova_gelo": ("gelo", 0.0, 4.0),
            "raio_cadeia": ("atordoado", 0.0, 0.6),
            "meteoro": ("queimadura", 0.12, 4.0),
        }
        dados = mapa.get(h.id)
        if dados is None:
            return None
        tipo, fator, tempo = dados
        return {"tipo": tipo, "dano_por_segundo": dano * fator, "tempo": tempo}

    def _aplicar_status_habilidade(self, inimigo: Inimigo, h: Habilidade, dano: float) -> None:
        status = self._status_da_habilidade(h, dano)
        if status is not None:
            self.aplicar_status(inimigo, **status)

    def registrar_dano_jogador(self, jogador: Jogador, dano: float, critico: bool) -> None:
        self.sons.tocar("dano", 0.85)
        if self.prefs.numeros_dano:
            self.textos.append(
                TextoFlutuante(
                    jogador.x + random.uniform(-8, 8), jogador.y - 62,
                    f"-{int(dano)}", (250, 90, 90), 20, 0.8,
                )
            )
        self.particulas.emitir(jogador.x, jogador.y - 30, (230, 70, 80), 8, 90, 4, 0.4)
        self.tremer(6, 0.18)
        self.entrada.vibrar(0.35, 0.55, 140)
        self.parar_tempo(0.12)
        self.piscar((255, 64, 64), 0.5)

    def jogador_morreu(self) -> None:
        self.estado = "morte"
        self.sons.tocar("morte_jogador", 0.9)
        self.sons.tocar_musica(None)
        self.tremer(14, 0.5)
        self.parar_tempo(0.28)
        self.piscar((255, 40, 40), 0.6)
        if self.jogador is not None:
            self.particulas.emitir(self.jogador.x, self.jogador.y - 30, (220, 80, 90), 26, 150, 5, 0.7)
            perdido = int(self.jogador.ouro * ECO_MORTE)
            if self.eco is not None:
                self.eco.vivo = False
                self.drops = [d for d in self.drops if d is not self.eco]
                self.eco = None
            if perdido >= 5:
                self.jogador.ouro -= perdido
                eco = Drop(self.jogador.x, self.jogador.y, "eco", None, perdido)
                self.drops.append(eco)
                self.eco = eco
                self.ui.notificar(f"Você deixou {perdido} ouro em um Eco de Aether.", DOURADO)
        self.ui.notificar("Você foi derrotado...", VERMELHO)

    def inimigo_morreu(self, inimigo: Inimigo) -> None:
        if self.jogador is None:
            return
        self.jogador.kills += 1
        if self.quests.registrar_abate(inimigo.tipo):
            self._avisar_missao_concluida()
        self.sons.tocar("morte_boss" if inimigo.boss else "morte_inimigo", 1.0 if inimigo.boss else 0.55)
        self.particulas.emitir(inimigo.x, inimigo.y - inimigo.raio, inimigo.cor, 22, 160, 5, 0.6)
        self.textos.append(
            TextoFlutuante(inimigo.x, inimigo.y - inimigo.raio * 1.8, f"+{inimigo.xp_recompensa} XP", (180, 240, 180), 14, 0.9)
        )
        mensagens = self.jogador.ganhar_xp(inimigo.xp_recompensa)
        if mensagens:
            self.sons.tocar("level_up", 0.8)
        for msg in mensagens:
            self.ui.notificar(msg, VERDE)
        if mensagens:
            self.efeitos.append(Efeito("nivel", self.jogador.x, self.jogador.y, 120, 0.9, (250, 220, 120)))
            self.particulas.emitir(self.jogador.x, self.jogador.y - 30, (250, 220, 120), 30, 140, 4, 0.8)

        loot = rolar_loot(inimigo.nivel, self.jogador.classe, boss=inimigo.boss)
        for entrada in loot:
            ox, oy = random.uniform(-30, 30), random.uniform(-24, 24)
            if isinstance(entrada, tuple) and entrada[0] == "ouro":
                self.drops.append(Drop(inimigo.x + ox, inimigo.y + oy, "ouro", None, int(entrada[1])))
            elif isinstance(entrada, Equipamento):
                self.drops.append(Drop(inimigo.x + ox, inimigo.y + oy, "equipamento", entrada))
            elif isinstance(entrada, Cristal):
                self.drops.append(Drop(inimigo.x + ox, inimigo.y + oy, "cristal", entrada))
            elif isinstance(entrada, Pocao):
                self.drops.append(Drop(inimigo.x + ox, inimigo.y + oy, "pocao", entrada))

        if getattr(inimigo, "elite", False):
            self._efeito_elite(inimigo)

        if inimigo.boss:
            if getattr(inimigo, "conta_progresso", True):
                self.jogador.bosses += 1
            self.boss_ativo = None
            self.boss_alerta = 0.0
            self.errante_vida = 0.0
            self.tremer(16, 0.5)
            self.parar_tempo(0.3)
            self.piscar((255, 214, 130), 0.4)
            self.ui.notificar(f"{inimigo.nome} derrotado! Loot raro garantido.", DOURADO)
            self.particulas.emitir(inimigo.x, inimigo.y - 40, (250, 210, 120), 50, 220, 6, 0.9)
            if self.quests.registrar_boss(inimigo.nome):
                self._avisar_missao_concluida()
            if getattr(inimigo, "errante", False):
                self.ui.notificar("O selo da Caverna segue intacto.", (200, 180, 230))
            if inimigo.tipo == "senhor_fragmentos":
                self.ui.notificar(
                    "O selo foi quebrado. O caminho para o Coração de Aether está aberto.",
                    DOURADO,
                )
            if inimigo.tipo == "avatar_aether":
                self.final_derrotado = True
                self.vitoria_timer = 3.4
                self.jogador.ouro += 5000
                self.drops.append(Drop(inimigo.x, inimigo.y + 20, "cristal", Cristal("Nucleo", 5)))
                self.ui.notificar(
                    "O Avatar de Aether caiu. A fonte dos cristais está livre!",
                    DOURADO,
                )
            if inimigo.tipo == "guardiao_eclipse":
                reliquia = gerar_reliquia_eclipse(self.jogador.classe)
                amuleto = gerar_amuleto_eclipse()
                self.drops.append(Drop(inimigo.x, inimigo.y + 20, "equipamento", reliquia))
                self.drops.append(Drop(inimigo.x + 24, inimigo.y + 20, "equipamento", amuleto))
                self.drops.append(
                    Drop(inimigo.x - 24, inimigo.y + 20, "cristal", Cristal("Eclipse", 5))
                )
                self.jogador.ouro += 4000
                self.ui.notificar(
                    "O Guardião do Eclipse caiu. A relíquia do eclipse é sua.",
                    (200, 160, 255),
                )
        else:
            self._rolar_boss(inimigo)

    def _rolar_boss(self, inimigo: Inimigo) -> None:
        if self.jogador is None:
            return
        zona = self.mundo.zona_em(inimigo.x, inimigo.y)
        if zona is None or zona.seguro or zona.boss is None:
            return
        if self.boss_ativo is not None and self.boss_ativo.vivo:
            return
        if zona.nome == "Coração de Aether" and self.final_derrotado:
            return
        if zona.nome == "Caverna de Cristal" and self.jogador.bosses < BOSSES_PARA_CAVERNA:
            return
        antes = self.kills_sem_boss.get(zona.nome, 0)
        self.kills_sem_boss[zona.nome] = antes + 1
        piedade = PIEDADE_BOSS.get(zona.nome, 18)
        # avisa quando o boss está ficando perto, para o jogador saber onde insistir
        if antes < piedade * 0.6 <= antes + 1:
            self.ui.notificar(f"Algo grande se agita em {zona.nome}. Continue caçando por aqui.", (250, 190, 120))
        if random.random() < zona.chance_boss or self.kills_sem_boss[zona.nome] >= piedade:
            self._spawn_boss(zona)

    def status_boss(self, zona: Zona | None) -> str:
        """Linha curta para o HUD: quanto falta para o boss da zona aparecer."""
        if zona is None or zona.boss is None:
            return ""
        if self.boss_ativo is not None and self.boss_ativo.vivo:
            return "Boss ativo"
        if self.jogador is None:
            return ""
        if zona.nome == "Caverna de Cristal" and self.jogador.bosses < BOSSES_PARA_CAVERNA:
            return f"Boss selado ({self.jogador.bosses}/{BOSSES_PARA_CAVERNA})"
        piedade = PIEDADE_BOSS.get(zona.nome, 18)
        faltam = max(0, piedade - self.kills_sem_boss.get(zona.nome, 0))
        return f"Boss em ~{faltam} abates"

    def _spawn_boss(self, zona: Zona) -> None:
        if self.jogador is None or zona.boss is None:
            return
        mapa = {
            "Rei Slime": "rei_slime",
            "Golem Ancião": "golem_anciao",
            "Senhor dos Fragmentos": "senhor_fragmentos",
            "Rainha do Lodo": "rainha_lodo",
            "Colosso de Obsidiana": "colosso_obsidiana",
            "Avatar de Aether": "avatar_aether",
            "Guardião do Eclipse": "guardiao_eclipse",
        }
        tipo = mapa.get(zona.boss)
        if tipo is None:
            return
        pos = self.mundo.ponto_spawn(zona, (self.jogador.x, self.jogador.y), 420)
        if pos is None:
            return
        nivel_boss = zona.nivel_max + 2
        boss = Inimigo(tipo, nivel_boss, pos[0], pos[1])
        self.inimigos.append(boss)
        self.boss_ativo = boss
        self.boss_nome = boss.nome
        self.boss_alerta = 6.0
        self.kills_sem_boss[zona.nome] = 0
        self.sons.tocar("boss", 0.9)
        self.ui.notificar(f"{boss.nome} despertou em {zona.nome}!", (250, 130, 100))
        self.tremer(12, 0.4)
        self.particulas.emitir(boss.x, boss.y - 30, (250, 170, 100), 40, 200, 6, 0.8)

    # ------------------------------------------------------------------ coleta
    def coletar(self, drop: Drop) -> bool:
        if self.jogador is None:
            return False
        if drop.tipo == "ouro":
            self.jogador.ouro += drop.quantidade
            self.sons.tocar("loot", 0.35)
            self.textos.append(
                TextoFlutuante(drop.x, drop.y - 20, f"+{drop.quantidade} ouro", (246, 204, 92), 13, 0.7)
            )
            self.particulas.emitir(drop.x, drop.y - 8, (246, 204, 92), 5, 50, 3, 0.35)
            return True
        if drop.tipo == "eco":
            self.jogador.ouro += drop.quantidade
            self.sons.tocar("loot", 0.85)
            self.textos.append(
                TextoFlutuante(drop.x, drop.y - 24, f"+{drop.quantidade} ouro recuperado", DOURADO, 15, 0.9)
            )
            self.particulas.emitir(drop.x, drop.y - 8, (255, 230, 150), 18, 110, 4, 0.55)
            if self.eco is drop:
                self.eco = None
            self.ui.notificar(f"Eco de Aether recuperado: +{drop.quantidade} ouro.", DOURADO)
            return True
        if drop.tipo == "bau":
            ouro = 80 + self.jogador.nivel * 15
            self.jogador.ouro += ouro
            cristal = gerar_cristal(self.jogador.nivel + 1, boss=True)
            if not self.jogador.adicionar_item(cristal):
                self.drops.append(Drop(drop.x, drop.y + 18, "cristal", cristal))
            pocao = gerar_pocao(random.choice(list(TIPOS_POCAO)), 2)
            if not self.jogador.adicionar_item(pocao):
                self.drops.append(Drop(drop.x - 18, drop.y + 18, "pocao", pocao))
            self.sons.tocar("loot", 0.9)
            self.ui.notificar(
                f"Baú do viajante: +{ouro} ouro, cristal e poções.", DOURADO,
            )
            self.particulas.emitir(drop.x, drop.y - 10, (250, 220, 140), 26, 140, 5, 0.7)
            self.efeitos.append(Efeito("onda", drop.x, drop.y, 70, 0.4, (250, 220, 140)))
            return True
        if drop.tipo == "santuario":
            j = self.jogador
            j.curar(j.hp_max * 0.35)
            j.restaurar_mp(j.mp_max * 0.35)
            j.aplicar_buff("santuario", {"ataque": 0.20, "defesa": 0.20}, 45.0)
            self.sons.tocar("encanto", 1.0)
            self.ui.notificar(
                "Bênção do santuário: +20% ataque e defesa por 45s.", (150, 230, 255),
            )
            self.particulas.emitir(drop.x, drop.y - 10, (150, 230, 255), 30, 150, 5, 0.8)
            self.efeitos.append(Efeito("onda", drop.x, drop.y, 90, 0.5, (150, 230, 255)))
            return True
        item = drop.item
        if item is None:
            return True
        if not self.jogador.adicionar_item(item):
            self.ui.notificar("Inventário cheio!", VERMELHO)
            return False
        self.sons.tocar("loot", 0.7)
        if isinstance(item, Equipamento):
            self.ui.notificar(f"{item.nome} ({item.raridade})", item.cor)
        elif isinstance(item, Cristal):
            self.ui.notificar(f"Cristal: {item.nome}", item.cor)
            if self.quests.registrar_cristal():
                self._avisar_missao_concluida()
        elif isinstance(item, Pocao):
            self.ui.notificar(f"{item.nome} obtido", item.cor)
        self.particulas.emitir(drop.x, drop.y - 8, drop.cor, 10, 80, 3, 0.45)
        return True

    # ------------------------------------------------------------------ utilidades
    def anunciar(self, mensagem: str, cor: tuple[int, int, int] = BRANCO) -> None:
        self.ui.notificar(mensagem, cor)
