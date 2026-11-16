"""Itens, cristais, equipamentos e geração de loot."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from settings import RARIDADES

# --------------------------------------------------------------------------
# constantes
# --------------------------------------------------------------------------

SLOTS = ("Arma", "Armadura", "Anel", "Amuleto")
SLOTS_ORDEM = {nome: i for i, nome in enumerate(SLOTS)}

ROMANOS = ("", "I", "II", "III", "IV", "V")

STAT_NOMES = {
    "ataque": "Ataque",
    "defesa": "Defesa",
    "hp_max": "Vida máx.",
    "mp_max": "Mana máx.",
    "stamina_max": "Stamina máx.",
    "critico": "Crítico",
    "velocidade": "Velocidade",
    "regen_hp": "Regen. vida",
    "regen_mp": "Regen. mana",
}

STAT_SUFIXO = {
    "critico": "%",
    "velocidade": "",
    "regen_hp": "/s",
    "regen_mp": "/s",
}

# --------------------------------------------------------------------------
# cristais
# --------------------------------------------------------------------------

TIPOS_CRISTAL = {
    "Rubi": {
        "stat": "ataque",
        "cor": (238, 86, 96),
        "base": 2.4,
        "nome": "Rubi de Força",
        "descricao": "Aumenta o ataque físico.",
    },
    "Safira": {
        "stat": "mp_max",
        "cor": (86, 148, 244),
        "base": 9.0,
        "nome": "Safira de Mana",
        "descricao": "Aumenta a mana máxima.",
    },
    "Esmeralda": {
        "stat": "hp_max",
        "cor": (82, 204, 138),
        "base": 14.0,
        "nome": "Esmeralda de Vida",
        "descricao": "Aumenta a vida máxima.",
    },
    "Topázio": {
        "stat": "critico",
        "cor": (244, 206, 92),
        "base": 1.6,
        "nome": "Topázio de Precisão",
        "descricao": "Aumenta a chance de crítico.",
    },
    "Ametista": {
        "stat": "regen_mp",
        "cor": (176, 118, 236),
        "base": 0.55,
        "nome": "Ametista de Foco",
        "descricao": "Acelera a regeneração de mana.",
    },
    "Eclipse": {
        "stat": "ataque",
        "cor": (176, 110, 236),
        "base": 3.6,
        "nome": "Cristal do Eclipse",
        "descricao": "Aumenta o ataque com a energia do eclipse.",
    },
    "Vazio": {
        "stat": "defesa",
        "cor": (96, 110, 150),
        "base": 2.2,
        "nome": "Cristal do Vazio",
        "descricao": "Aumenta a defesa com a escuridão do vazio.",
    },
}


@dataclass
class Cristal:
    tipo: str
    tier: int = 1

    @property
    def dados(self) -> dict[str, Any]:
        return TIPOS_CRISTAL[self.tipo]

    @property
    def stat(self) -> str:
        return self.dados["stat"]

    @property
    def cor(self) -> tuple[int, int, int]:
        return self.dados["cor"]

    @property
    def valor(self) -> float:
        return round(self.dados["base"] * self.tier, 2)

    @property
    def nome(self) -> str:
        return f"{self.dados['nome']} {ROMANOS[min(self.tier, 5)]}"

    @property
    def descricao(self) -> str:
        return f"+{self.formatar_valor()} {STAT_NOMES[self.stat]}"

    def formatar_valor(self) -> str:
        v = self.valor
        if self.stat == "critico":
            return f"{v:.1f}%"
        if self.stat in ("regen_hp", "regen_mp"):
            return f"{v:.1f}/s"
        return f"{v:.0f}"

    def to_dict(self) -> dict[str, Any]:
        return {"tipo": self.tipo, "tier": self.tier}

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "Cristal":
        return cls(str(dados.get("tipo", "Rubi")), int(dados.get("tier", 1)))


# --------------------------------------------------------------------------
# equipamentos
# --------------------------------------------------------------------------

BASES_ARMA = {
    "Espada": ("Lâmina", "Espada", "Sabre", "Montante"),
    "Arco": ("Arco", "Arco Longo", "Arco Élfico"),
    "Cajado": ("Cajado", "Cetro", "Bastão Arcano"),
}

PREFIXOS = {
    "Comum": ("", "Gasta", "Simples"),
    "Raro": ("Afiado", "Robusto", "Runado", "Élfico"),
    "Épico": ("Ancestral", "Sombrio", "Cristalino", "Esquecido"),
    "Lendário": ("de Aether", "do Vazio", "Primordial", "do Coração"),
}

SUFIXOS = {
    "Arma": ("do Caçador", "do Guardião", "das Chamas", "do Inverno"),
    "Armadura": ("do Baluarte", "da Floresta", "do Titã", "do Eclipse"),
    "Anel": ("do Sábio", "da Tempestade", "do Vazio", "da Aurora"),
    "Amuleto": ("de Lumen", "do Oráculo", "da Ruína", "de Aether"),
}


@dataclass
class Equipamento:
    nome: str
    slot: str
    raridade: str
    nivel: int
    stats: dict[str, float]
    sockets: list[Cristal | None] = field(default_factory=list)
    icone: str = "espada"
    classe: str | None = None
    melhorias: int = 0
    encantamentos: int = 0

    @property
    def cor(self) -> tuple[int, int, int]:
        return RARIDADES.get(self.raridade, RARIDADES["Comum"])["cor"]

    @property
    def sockets_livres(self) -> int:
        return sum(1 for s in self.sockets if s is None)

    def stats_totais(self) -> dict[str, float]:
        totais = dict(self.stats)
        for cristal in self.sockets:
            if cristal is not None:
                totais[cristal.stat] = totais.get(cristal.stat, 0.0) + cristal.valor
        return totais

    def encaixar(self, cristal: Cristal) -> bool:
        for i, atual in enumerate(self.sockets):
            if atual is None:
                self.sockets[i] = cristal
                return True
        return False

    def remover_cristal(self, indice: int) -> Cristal | None:
        if 0 <= indice < len(self.sockets):
            cristal = self.sockets[indice]
            self.sockets[indice] = None
            return cristal
        return None

    def linhas(self) -> list[tuple[str, tuple[int, int, int]]]:
        linhas: list[tuple[str, tuple[int, int, int]]] = [(self.nome, self.cor)]
        linhas.append((f"{self.slot} · Nível {self.nivel} · {self.raridade}", (150, 156, 174)))
        if self.melhorias or self.encantamentos:
            linhas.append((
                f"Reforços: +{self.melhorias} · Encantamentos: {self.encantamentos}/3",
                (220, 200, 140),
            ))
        for stat, valor in self.stats.items():
            linhas.append((f"+{_fmt_stat(stat, valor)} {STAT_NOMES.get(stat, stat)}", (206, 214, 228)))
        for i, cristal in enumerate(self.sockets):
            if cristal is None:
                linhas.append((f"◇ Encaixe vazio {i + 1}", (110, 118, 136)))
            else:
                linhas.append((f"◆ {cristal.nome}: {cristal.descricao}", cristal.cor))
        if self.classe:
            linhas.append((f"Classe: {self.classe}", (120, 190, 240)))
        return linhas

    def to_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "slot": self.slot,
            "raridade": self.raridade,
            "nivel": self.nivel,
            "stats": self.stats,
            "sockets": [c.to_dict() if c else None for c in self.sockets],
            "icone": self.icone,
            "classe": self.classe,
            "melhorias": self.melhorias,
            "encantamentos": self.encantamentos,
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "Equipamento":
        sockets = [
            Cristal.from_dict(c) if isinstance(c, dict) else None
            for c in dados.get("sockets", [])
        ]
        return cls(
            nome=str(dados.get("nome", "Item")),
            slot=str(dados.get("slot", "Arma")),
            raridade=str(dados.get("raridade", "Comum")),
            nivel=int(dados.get("nivel", 1)),
            stats={k: float(v) for k, v in dados.get("stats", {}).items()},
            sockets=sockets,
            icone=str(dados.get("icone", "espada")),
            classe=dados.get("classe"),
            melhorias=int(dados.get("melhorias", 0)),
            encantamentos=int(dados.get("encantamentos", 0)),
        )


def _fmt_stat(stat: str, valor: float) -> str:
    if stat in ("critico",):
        return f"{valor:.1f}%"
    if stat in ("regen_hp", "regen_mp"):
        return f"{valor:.1f}/s"
    return f"{valor:.0f}"


# --------------------------------------------------------------------------
# poções
# --------------------------------------------------------------------------

TIPOS_POCAO = {
    "vida": {
        "nome": "Poção de Vida",
        "cor": (232, 82, 96),
        "icone": "pocao_vida",
        "descricao": "Restaura 35% da vida máxima.",
    },
    "mana": {
        "nome": "Poção de Mana",
        "cor": (82, 148, 244),
        "icone": "pocao_mana",
        "descricao": "Restaura 40% da mana máxima.",
    },
    "stamina": {
        "nome": "Elixir de Fôlego",
        "cor": (244, 206, 92),
        "icone": "pocao_stamina",
        "descricao": "Restaura 60 de stamina.",
    },
}

# Conteúdo externalizado (data/items.json) expande/sobrepõe os padrões acima.
from core.content import carregar_itens  # noqa: E402

_DADOS_ITENS = carregar_itens()
if _DADOS_ITENS:
    for _secao in ("cristais", "pocoes"):
        for _dados in _DADOS_ITENS.get(_secao, {}).values():
            _dados["cor"] = tuple(_dados["cor"])
    TIPOS_CRISTAL.update(_DADOS_ITENS.get("cristais", {}))
    TIPOS_POCAO.update(_DADOS_ITENS.get("pocoes", {}))
    BASES_ARMA.update(_DADOS_ITENS.get("bases_arma", {}))
    PREFIXOS.update(_DADOS_ITENS.get("prefixos", {}))
    SUFIXOS.update(_DADOS_ITENS.get("sufixos", {}))


@dataclass
class Pocao:
    tipo: str
    quantidade: int = 1

    @property
    def dados(self) -> dict[str, Any]:
        return TIPOS_POCAO[self.tipo]

    @property
    def nome(self) -> str:
        return self.dados["nome"]

    @property
    def cor(self) -> tuple[int, int, int]:
        return self.dados["cor"]

    @property
    def icone(self) -> str:
        return self.dados["icone"]

    @property
    def descricao(self) -> str:
        return self.dados["descricao"]

    def to_dict(self) -> dict[str, Any]:
        return {"tipo": self.tipo, "quantidade": self.quantidade}

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "Pocao":
        return cls(str(dados.get("tipo", "vida")), int(dados.get("quantidade", 1)))


Item = Equipamento | Cristal | Pocao


def preco_venda(item: Item) -> int:
    """Preço de venda equilibrado por tipo, nível e raridade."""
    if isinstance(item, Equipamento):
        base = 12 + item.nivel * 5
        mult = {"Comum": 1.0, "Raro": 1.8, "Épico": 3.0, "Lendário": 5.0}
        return int(base * mult.get(item.raridade, 1.0))
    if isinstance(item, Cristal):
        return 10 * item.tier * item.tier
    if isinstance(item, Pocao):
        return {"vida": 15, "mana": 20, "stamina": 18}.get(item.tipo, 15)
    return 5


# --------------------------------------------------------------------------
# geração
# --------------------------------------------------------------------------


def _rolar_raridade(boss: bool = False, bonus: float = 0.0) -> str:
    r = random.random() - bonus
    if boss:
        r -= 0.20
    if r < 0.035:
        return "Lendário"
    if r < 0.15:
        return "Épico"
    if r < 0.42:
        return "Raro"
    return "Comum"


def _stats_base(slot: str, nivel: int) -> dict[str, float]:
    escala = 1.0 + (nivel - 1) * 0.16
    if slot == "Arma":
        return {"ataque": round((6.0 + nivel * 1.15) * escala, 1)}
    if slot == "Armadura":
        return {
            "defesa": round((3.0 + nivel * 0.75) * escala, 1),
            "hp_max": round((12.0 + nivel * 4.0) * escala, 1),
        }
    if slot == "Anel":
        return {
            "critico": round((2.5 + nivel * 0.18) * escala, 1),
            "ataque": round((1.5 + nivel * 0.35) * escala, 1),
        }
    return {
        "mp_max": round((10.0 + nivel * 2.4) * escala, 1),
        "regen_mp": round((0.4 + nivel * 0.08) * escala, 2),
        "hp_max": round((5.0 + nivel * 1.5) * escala, 1),
    }


def _nome_equipamento(slot: str, raridade: str, classe: str | None) -> str:
    if slot == "Arma":
        tipo = "Espada"
        if classe == "Arqueira":
            tipo = "Arco"
        elif classe == "Maga":
            tipo = "Cajado"
        base = random.choice(BASES_ARMA[tipo])
    else:
        base = {
            "Armadura": random.choice(("Peitoral", "Manto", "Couraça", "Cota", "Vestes")),
            "Anel": random.choice(("Anel", "Selo", "Aliança", "Sinete")),
            "Amuleto": random.choice(("Amuleto", "Talismã", "Pingente", "Relicário")),
        }[slot]
    prefixo = random.choice(PREFIXOS[raridade])
    sufixo = random.choice(SUFIXOS[slot]) if raridade in ("Épico", "Lendário") else ""
    partes = [p for p in (prefixo, base, sufixo) if p]
    return " ".join(partes)


def gerar_equipamento(
    nivel: int,
    classe: str | None = None,
    slot: str | None = None,
    raridade: str | None = None,
    boss: bool = False,
) -> Equipamento:
    nivel = max(1, int(nivel))
    if slot is None:
        slot = random.choice(SLOTS)
    if raridade is None:
        raridade = _rolar_raridade(boss=boss, bonus=min(0.12, nivel * 0.004))
    mult = RARIDADES[raridade]["mult"]
    stats = {k: round(v * mult, 2) for k, v in _stats_base(slot, nivel).items()}
    # bônus aleatório secundário para dar variedade
    if random.random() < 0.45:
        extra = random.choice(("critico", "velocidade", "regen_hp", "regen_mp", "defesa"))
        valor = {
            "critico": round(random.uniform(1.0, 4.0) * mult, 1),
            "velocidade": round(random.uniform(2.0, 8.0) * mult, 1),
            "regen_hp": round(random.uniform(0.2, 1.0) * mult, 2),
            "regen_mp": round(random.uniform(0.2, 1.0) * mult, 2),
            "defesa": round(random.uniform(1.0, 4.0) * mult, 1),
        }[extra]
        stats[extra] = round(stats.get(extra, 0.0) + valor, 2)

    qtd_sockets = RARIDADES[raridade]["sockets"]
    icone = "espada"
    if slot == "Arma":
        icone = "arco" if classe == "Arqueira" else "cajado" if classe == "Maga" else "espada"
    elif slot == "Armadura":
        icone = "armadura"
    elif slot == "Anel":
        icone = "anel"
    else:
        icone = "amuleto"

    return Equipamento(
        nome=_nome_equipamento(slot, raridade, classe),
        slot=slot,
        raridade=raridade,
        nivel=nivel,
        stats=stats,
        sockets=[None] * qtd_sockets,
        icone=icone,
        classe=classe if slot == "Arma" else None,
    )


def gerar_reliquia_eclipse(classe: str | None = None) -> Equipamento:
    """Arma lendária exclusiva do Guardião do Eclipse."""
    arma = "Arco" if classe == "Arqueira" else "Cajado" if classe == "Maga" else "Espada"
    nomes = {
        "Espada": "Lâmina do Eclipse",
        "Arco": "Arco do Eclipse",
        "Cajado": "Cajado do Eclipse",
    }
    icones = {"Espada": "espada", "Arco": "arco", "Cajado": "cajado"}
    ataque = _stats_base("Arma", 42)["ataque"] * RARIDADES["Lendário"]["mult"] * 1.25
    return Equipamento(
        nome=nomes[arma],
        slot="Arma",
        raridade="Lendário",
        nivel=42,
        stats={"ataque": round(ataque, 1), "critico": 8.0},
        sockets=[None, None, None],
        icone=icones[arma],
        classe=classe,
    )


def gerar_amuleto_eclipse() -> Equipamento:
    """Amuleto lendário exclusivo do Guardião do Eclipse."""
    return Equipamento(
        nome="Selo do Eclipse",
        slot="Amuleto",
        raridade="Lendário",
        nivel=42,
        stats={"hp_max": 260.0, "defesa": 30.0, "critico": 10.0, "regen_mp": 1.0},
        sockets=[None, None],
        icone="amuleto",
        classe=None,
    )


def gerar_cristal(nivel: int = 1, tier: int | None = None, boss: bool = False) -> Cristal:
    tipos = [
        t for t in TIPOS_CRISTAL
        if (t != "Nucleo" or nivel >= 30)
        and (t not in ("Eclipse", "Vazio") or nivel >= 38)
    ]
    tipo = random.choice(tipos or list(TIPOS_CRISTAL))
    if tier is None:
        pesos = [0.46, 0.27, 0.16, 0.08, 0.03]
        if boss:
            pesos = [0.05, 0.15, 0.30, 0.32, 0.18]
        elif nivel > 8:
            pesos = [0.30, 0.28, 0.22, 0.14, 0.06]
        tier = random.choices((1, 2, 3, 4, 5), weights=pesos, k=1)[0]
    return Cristal(tipo, int(tier))


def gerar_pocao(tipo: str | None = None, quantidade: int = 1) -> Pocao:
    return Pocao(tipo or random.choice(list(TIPOS_POCAO)), quantidade)


def rolar_loot(nivel: int, classe: str | None, boss: bool = False) -> list[Item | tuple[str, int]]:
    """Retorna uma lista de itens; ('ouro', N) representa moedas."""
    resultado: list[Item | tuple[str, int]] = []
    ouro = random.randint(8 + nivel * 2, 18 + nivel * 4)
    if boss:
        ouro = random.randint(180 + nivel * 18, 320 + nivel * 24)
    resultado.append(("ouro", ouro))

    if boss:
        resultado.append(gerar_equipamento(nivel, classe, boss=True))
        resultado.append(gerar_equipamento(nivel, classe, boss=True))
        resultado.append(gerar_cristal(nivel, boss=True))
        resultado.append(gerar_pocao(random.choice(list(TIPOS_POCAO)), 2))
        return resultado

    if random.random() < 0.22:
        resultado.append(gerar_pocao())
    if random.random() < 0.10:
        resultado.append(gerar_equipamento(nivel, classe))
    if random.random() < 0.07:
        resultado.append(gerar_cristal(nivel))
    return resultado
