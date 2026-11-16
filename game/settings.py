"""Cristais de Aether — constantes visuais e de balanceamento."""
from __future__ import annotations

TITULO = "Cristais de Aether"
VERSAO = "0.1.67"

LARGURA, ALTURA = 1280, 720
FPS = 60

# Protótipo da missão 02: aviso visual (telegraph) antes de golpes fortes.
# Desligado por padrão; ligar apenas em testes/dev (cone idêntico à área real).
TELEGRAPH_COMBATE = False
TILE = 64

# Iluminação em duas passadas (ambiente + luzes). False volta ao overlay antigo
# e existe para comparação via `python main.py --luz-simples`.
LUZ_AVANCADA = True

# ------------------------------------------------------------------ paleta
FUNDO = (10, 10, 14)
PAINEL = (20, 20, 26)
PAINEL_CLARO = (32, 32, 40)
PAINEL_ESCURO = (10, 10, 14)
BORDA = (154, 124, 82)
BORDA_FRACA = (68, 64, 70)
TEXTO = (228, 222, 210)
TEXTO_FRACO = (150, 144, 134)
DOURADO = (214, 176, 104)
VERDE = (104, 190, 138)
AZUL = (92, 150, 210)
VERMELHO = (214, 82, 86)
ROXO = (178, 124, 236)
AMARELO = (230, 198, 104)
CIANO = (104, 210, 210)
LARANJA = (230, 148, 88)
BRANCO = (244, 240, 232)

# ------------------------------------------------------------------ raridades
RARIDADES = {
    "Comum":    {"cor": (176, 182, 194), "mult": 1.00, "sockets": 0},
    "Raro":     {"cor": (92, 168, 250),  "mult": 1.35, "sockets": 1},
    "Épico":    {"cor": (190, 116, 242), "mult": 1.85, "sockets": 2},
    "Lendário": {"cor": (250, 192, 88),  "mult": 2.60, "sockets": 3},
}

# ------------------------------------------------------------------ classes
CLASSES = {
    "Cavaleiro": {
        "cor": (96, 148, 232),
        "cor2": (226, 232, 244),
        "descricao": "Resistente e direto. Converte stamina em golpes pesados.",
        "hp": 160, "mp": 40, "stamina": 100,
        "ataque": 14, "defesa": 8, "critico": 5, "velocidade": 210,
        "arma": "Espada",
        "habilidades": ["Golpe Giratório", "Investida", "Brado de Guerra", "Golpe Sísmico"],
    },
    "Arqueira": {
        "cor": (92, 204, 142),
        "cor2": (226, 214, 170),
        "descricao": "Ágil e precisa. Ataca à distância e explora o crítico.",
        "hp": 110, "mp": 60, "stamina": 120,
        "ataque": 12, "defesa": 4, "critico": 15, "velocidade": 240,
        "arma": "Arco",
        "habilidades": ["Flecha Dupla", "Chuva de Flechas", "Tiro Certeiro", "Flecha Explosiva"],
    },
    "Maga": {
        "cor": (178, 124, 236),
        "cor2": (120, 200, 240),
        "descricao": "Frágil e devastadora. Controla o campo com magia elemental.",
        "hp": 90, "mp": 140, "stamina": 80,
        "ataque": 10, "defesa": 3, "critico": 8, "velocidade": 200,
        "arma": "Cajado",
        "habilidades": ["Bola de Fogo", "Nova de Gelo", "Raio em Cadeia", "Meteoro"],
    },
}

# ------------------------------------------------------------------ progressão
XP_BASE = 60.0
XP_EXPOENTE = 1.52


def xp_para_nivel(nivel: int) -> int:
    """XP necessário para sair do nível informado."""
    return int(XP_BASE * (nivel ** XP_EXPOENTE))


# ------------------------------------------------------------------ mundo
MUNDO_LARGURA = 124 * TILE
MUNDO_ALTURA = 44 * TILE

# ------------------------------------------------------------------ combate
DANO_VARIACAO = 0.12
CRITICO_MULT = 1.75
REGEN_HP = 0.8
REGEN_MP = 2.4
REGEN_STAMINA = 7.0
CUSTO_CORRIDA = 14.0
# Depois de gastar o recurso, a regeneração fica pausada por este tempo.
ATRASO_REGEN_MP = 2.5
ATRASO_REGEN_STAMINA = 1.8

# Esquiva (soulslike): curta, com invencibilidade e custo de stamina.
CUSTO_ESQUIVA = 16.0
DURACAO_ESQUIVA = 0.22
INVULNERABILIDADE_ESQUIVA = 0.18
VELOCIDADE_ESQUIVA = 520.0
COOLDOWN_ESQUIVA = 0.65

# Fração do ouro perdida ao morrer e recuperável no Eco de Aether.
ECO_MORTE = 0.50
CHANCE_ELITE = 0.10
# Economia da forja: custo em ouro e em cristais por raridade.
CUSTO_FORJA = {"Raro": 250, "Épico": 600, "Lendário": 2000}
CRISTAIS_FORJA = {"Raro": 2, "Épico": 2, "Lendário": 4}
# Tempo mínimo entre poções (evita curar tudo instantaneamente).
COOLDOWN_POCAO = 0.8
VEL_CORRIDA = 1.38
