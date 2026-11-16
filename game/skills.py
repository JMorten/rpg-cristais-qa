"""Habilidades das classes, custos, cooldowns e tiers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from settings import CIANO, DOURADO, LARANJA, ROXO, VERDE, VERMELHO, AMARELO

# Evoluções que mudam o comportamento da habilidade no tier 3 e no tier 5.
# Os valores numéricos são lidos por game.executar_habilidade.
EVOLUCOES: dict[str, tuple[str, str]] = {
    "golpe_giro": (
        "T3: o giro deixa uma onda de choque que atinge de novo.",
        "T5: a onda fica mais forte e o raio cresce 15%.",
    ),
    "investida": (
        "T3: inimigos atingidos ficam lentos por 1,5s.",
        "T5: a investida percorre uma distância maior.",
    ),
    "brado": (
        "T3: o brado dura 50% a mais.",
        "T5: também cura 20% da vida máxima.",
    ),
    "golpe_sismico": (
        "T3: a rachadura atinge de novo após 0,35s.",
        "T5: raio +20% e segunda onda mais forte.",
    ),
    "flecha_dupla": (
        "T3: dispara 3 flechas.",
        "T5: dispara 4 flechas.",
    ),
    "chuva_flechas": (
        "T3: raio +15%.",
        "T5: uma segunda saraivada cai após 0,5s.",
    ),
    "tiro_certeiro": (
        "T3: inimigos atravessados ficam lentos.",
        "T5: dispara 3 flechas perfurantes em leque.",
    ),
    "flecha_explosiva": (
        "T3: explosão 30% maior.",
        "T5: a explosão deixa os inimigos lentos por 2s.",
    ),
    "bola_fogo": (
        "T3: explosão 30% maior.",
        "T5: lança duas bolas de fogo.",
    ),
    "nova_gelo": (
        "T3: o gelo dura 4s.",
        "T5: raio +15% e dano extra após 0,4s.",
    ),
    "raio_cadeia": (
        "T3: salta para +1 inimigo.",
        "T5: +2 saltos e 15% mais dano.",
    ),
    "meteoro": (
        "T3: raio +15%.",
        "T5: um segundo meteoro cai após 0,45s.",
    ),
}

# Parâmetros numéricos das evoluções, por id de habilidade.
MELHORIAS: dict[str, dict[str, float]] = {
    "golpe_giro": {"onda3": 0.45, "onda5": 0.75, "raio5": 1.15},
    "investida": {"lentidao3": 1.5, "passos5": 12},
    "brado": {"duracao3": 1.5, "cura5": 0.20},
    "golpe_sismico": {"onda3": 0.45, "onda5": 0.75, "raio5": 1.20},
    "flecha_dupla": {"projeteis3": 3, "projeteis5": 4},
    "chuva_flechas": {"raio3": 1.15, "onda5": 0.60},
    "tiro_certeiro": {"lentidao3": 1.2, "projeteis5": 3},
    "flecha_explosiva": {"explosao3": 1.30, "lentidao5": 2.0},
    "bola_fogo": {"explosao3": 1.30, "projeteis5": 2},
    "nova_gelo": {"gelo3": 4.0, "raio5": 1.15, "onda5": 0.45},
    "raio_cadeia": {"saltos3": 1, "saltos5": 2, "dano5": 1.15},
    "meteoro": {"raio3": 1.15, "onda5": 0.60},
}


def parametro(h: "Habilidade", chave: str, padrao: float = 0.0) -> float:
    """Lê um parâmetro de evolução; devolve o padrão se não existir."""
    return float(MELHORIAS.get(h.id, {}).get(chave, padrao))


@dataclass
class Habilidade:
    id: str
    nome: str
    classe: str
    tecla: str
    tipo: str
    descricao: str
    custo_tipo: str
    custo: float
    cooldown: float
    dano_mult: float
    raio: float = 0.0
    duracao: float = 0.0
    cor: tuple[int, int, int] = DOURADO
    icone: str = "giro"
    tier: int = 1
    max_tier: int = 10
    extra: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ escala
    @property
    def custo_atual(self) -> float:
        return round(self.custo * (1.0 + 0.06 * (self.tier - 1)), 1)

    @property
    def cooldown_atual(self) -> float:
        return round(self.cooldown * (1.0 - 0.035 * (self.tier - 1)), 2)

    @property
    def raio_atual(self) -> float:
        return self.raio * (1.0 + 0.05 * (self.tier - 1))

    def dano(self, ataque: float) -> float:
        return ataque * self.dano_mult * (1.0 + 0.22 * (self.tier - 1))

    def descricao_detalhada(self, ataque: float) -> str:
        custo = f"{int(self.custo_atual)} {self.custo_tipo.upper()}"
        dano = f"{self.dano(ataque):.0f} de dano"
        partes = [self.descricao, f"{dano} · {custo} · recarga {self.cooldown_atual:.1f}s"]
        if self.tier < self.max_tier:
            partes.append("Próximo tier: +22% de dano")
        else:
            partes.append("Tier máximo alcançado")
        if self.evolucao_atual:
            partes.append(self.evolucao_atual)
        return "\n".join(partes)

    @property
    def evolucao_3(self) -> str:
        return EVOLUCOES.get(self.id, ("", ""))[0]

    @property
    def evolucao_5(self) -> str:
        return EVOLUCOES.get(self.id, ("", ""))[1]

    @property
    def evolucao_atual(self) -> str:
        if self.tier >= 5:
            return self.evolucao_5
        if self.tier >= 3:
            return self.evolucao_3
        return ""

    def proxima_evolucao(self) -> str:
        if self.tier < 3:
            return self.evolucao_3
        if self.tier < 5:
            return self.evolucao_5
        return ""

    def melhorar(self) -> bool:
        if self.tier >= self.max_tier:
            return False
        self.tier += 1
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "tier": self.tier}

    def from_dict(self, dados: dict[str, Any]) -> None:
        self.tier = max(1, min(self.max_tier, int(dados.get("tier", 1))))


# --------------------------------------------------------------------------
# catálogo
# --------------------------------------------------------------------------

CATALOGO: dict[str, list[Habilidade]] = {
    "Cavaleiro": [
        Habilidade(
            id="golpe_giro",
            nome="Golpe Giratório",
            classe="Cavaleiro",
            tecla="Q",
            tipo="aoe_self",
            descricao="Gira a lâmina em um arco completo, atingindo tudo ao redor.",
            custo_tipo="stamina",
            custo=30,
            cooldown=6.0,
            dano_mult=1.65,
            raio=98,
            cor=DOURADO,
            icone="giro",
        ),
        Habilidade(
            id="investida",
            nome="Investida",
            classe="Cavaleiro",
            tecla="E",
            tipo="dash",
            descricao="Avança com o escudo erguido, atropelando inimigos no caminho.",
            custo_tipo="stamina",
            custo=36,
            cooldown=8.0,
            dano_mult=1.45,
            raio=56,
            duracao=0.26,
            cor=LARANJA,
            icone="dash",
        ),
        Habilidade(
            id="brado",
            nome="Brado de Guerra",
            classe="Cavaleiro",
            tecla="R",
            tipo="buff",
            descricao="Ruge, aumentando o próprio ataque e defesa por 8 segundos.",
            custo_tipo="stamina",
            custo=46,
            cooldown=20.0,
            dano_mult=0.0,
            duracao=8.0,
            cor=VERMELHO,
            icone="brado",
            extra={"buff": {"ataque": 0.28, "defesa": 0.40}},
        ),
        Habilidade(
            id="golpe_sismico",
            nome="Golpe Sísmico",
            classe="Cavaleiro",
            tecla="F",
            tipo="aoe_self",
            descricao="Crava a lâmina no chão, rachando o solo e atingindo tudo em volta.",
            custo_tipo="stamina",
            custo=55,
            cooldown=18.0,
            dano_mult=2.40,
            raio=150,
            cor=LARANJA,
            icone="giro",
        ),
    ],
    "Arqueira": [
        Habilidade(
            id="flecha_dupla",
            nome="Flecha Dupla",
            classe="Arqueira",
            tecla="Q",
            tipo="projetil_duplo",
            descricao="Dispara duas flechas rápidas em um cone estreito.",
            custo_tipo="stamina",
            custo=24,
            cooldown=4.5,
            dano_mult=1.05,
            raio=8,
            cor=VERDE,
            icone="duplo",
        ),
        Habilidade(
            id="chuva_flechas",
            nome="Chuva de Flechas",
            classe="Arqueira",
            tecla="E",
            tipo="aoe_cursor",
            descricao="Uma saraivada cai sobre a área marcada pelo cursor.",
            custo_tipo="stamina",
            custo=42,
            cooldown=9.0,
            dano_mult=1.85,
            raio=92,
            duracao=1.1,
            cor=AMARELO,
            icone="chuva",
        ),
        Habilidade(
            id="tiro_certeiro",
            nome="Tiro Certeiro",
            classe="Arqueira",
            tecla="R",
            tipo="projetil_perfurante",
            descricao="Um único disparo carregado que atravessa todos os inimigos.",
            custo_tipo="stamina",
            custo=48,
            cooldown=14.0,
            dano_mult=3.20,
            raio=11,
            cor=CIANO,
            icone="certeiro",
        ),
        Habilidade(
            id="flecha_explosiva",
            nome="Flecha Explosiva",
            classe="Arqueira",
            tecla="F",
            tipo="projetil",
            descricao="Dispara uma flecha que explode no impacto, atingindo a área ao redor.",
            custo_tipo="stamina",
            custo=54,
            cooldown=16.0,
            dano_mult=2.20,
            raio=11,
            cor=LARANJA,
            icone="fogo",
            extra={"explosao": 84, "visual": "flecha"},
        ),
    ],
    "Maga": [
        Habilidade(
            id="bola_fogo",
            nome="Bola de Fogo",
            classe="Maga",
            tecla="Q",
            tipo="projetil",
            descricao="Lança uma esfera incandescente que explode no impacto.",
            custo_tipo="mp",
            custo=22,
            cooldown=4.0,
            dano_mult=2.45,
            raio=12,
            cor=LARANJA,
            icone="fogo",
            extra={"explosao": 72},
        ),
        Habilidade(
            id="nova_gelo",
            nome="Nova de Gelo",
            classe="Maga",
            tecla="E",
            tipo="nova",
            descricao="Uma onda de frio congela e desacelera os inimigos ao redor.",
            custo_tipo="mp",
            custo=40,
            cooldown=10.0,
            dano_mult=1.75,
            raio=138,
            duracao=3.0,
            cor=CIANO,
            icone="gelo",
        ),
        Habilidade(
            id="raio_cadeia",
            nome="Raio em Cadeia",
            classe="Maga",
            tecla="R",
            tipo="chain",
            descricao="Um relâmpago salta entre até três inimigos próximos.",
            custo_tipo="mp",
            custo=50,
            cooldown=14.0,
            dano_mult=3.30,
            raio=270,
            cor=ROXO,
            icone="raio",
            extra={"saltos": 3},
        ),
        Habilidade(
            id="meteoro",
            nome="Meteoro",
            classe="Maga",
            tecla="F",
            tipo="aoe_cursor",
            descricao="Invoca um meteoro sobre a área marcada, causando dano em massa.",
            custo_tipo="mp",
            custo=56,
            cooldown=18.0,
            dano_mult=3.80,
            raio=110,
            duracao=0.9,
            cor=LARANJA,
            icone="fogo",
        ),
    ],
}


def criar_habilidades(classe: str) -> list[Habilidade]:
    """Cria cópias independentes para o jogador."""
    return [
        Habilidade(**{**h.__dict__, "extra": dict(h.extra)})
        for h in CATALOGO.get(classe, [])
    ]


SOM_POR_HABILIDADE = {
    "golpe_giro": "golpe",
    "investida": "investida",
    "brado": "brado",
    "golpe_sismico": "golpe",
    "flecha_dupla": "arco",
    "chuva_flechas": "arco",
    "tiro_certeiro": "arco",
    "flecha_explosiva": "fogo",
    "bola_fogo": "fogo",
    "nova_gelo": "gelo",
    "raio_cadeia": "raio",
    "meteoro": "fogo",
}


def som_da_habilidade(habilidade: Habilidade) -> str:
    """Efeito curto que combina com o tipo visual da habilidade."""
    return SOM_POR_HABILIDADE.get(habilidade.id, "magia")


def resumo_classe(classe: str) -> list[str]:
    return [f"{h.tecla} · {h.nome}" for h in CATALOGO.get(classe, [])]
