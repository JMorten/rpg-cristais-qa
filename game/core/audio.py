"""Áudio procedural: efeitos e trilhas sintetizados em Python puro.

Nada de arquivo externo: os sons são gerados por código na primeira execução e
ficam em cache na pasta de dados do usuário. Se o mixer não estiver disponível
(máquina sem placa de som, CI, teste headless), tudo vira no-op.
"""
from __future__ import annotations

import io
import logging
import math
import random
import wave
from array import array
from pathlib import Path

import pygame

from core.paths import audio_dir

LOGGER = logging.getLogger(__name__)

TAXA_EFEITO = 22050
TAXA_MUSICA = 11025
VERSAO_AUDIO = 3

EFEITOS = (
    "clique",
    "acerto",
    "critico",
    "magia",
    "flecha",
    "golpe",
    "arco",
    "fogo",
    "gelo",
    "raio",
    "brado",
    "investida",
    "explosao",
    "dano",
    "morte_inimigo",
    "morte_boss",
    "morte_jogador",
    "level_up",
    "loot",
    "pocao",
    "boss",
    "fase_boss",
    "vitoria",
    "passo",
    "esquiva",
    "inimigo_ataque",
    "inimigo_projetil",
    "perigo",
    "forja",
    "encanto",
    "compra",
    "venda",
    "equipar",
    "cristal",
    "missao",
    "descanso",
)
MUSICAS = (
    "clareira", "floresta", "ruinas", "caverna", "pantano",
    "desfiladeiro", "coracao", "eclipse",
)


# --------------------------------------------------------------------------
# síntese
# --------------------------------------------------------------------------


def _novo(segundos: float, taxa: int) -> array:
    return array("h", [0]) * max(1, int(segundos * taxa))


def _somar(buf: array, indice: int, valor: float) -> None:
    if 0 <= indice < len(buf):
        atual = buf[indice] + int(valor)
        buf[indice] = max(-32767, min(32767, atual))


def _oscilar(
    buf: array, taxa: int, inicio: float, duracao: float,
    freq_ini: float, freq_fim: float, volume: float, decaimento: float = 6.0,
    forma: str = "seno", ataque: float = 0.005,
) -> None:
    """Adiciona um tom com varredura de frequência e envelope exponencial."""
    n = max(1, int(duracao * taxa))
    base = int(inicio * taxa)
    fase = 0.0
    for i in range(n):
        t = i / n
        f = freq_ini + (freq_fim - freq_ini) * t
        fase += 2.0 * math.pi * f / taxa
        if forma == "quadrada":
            amostra = 1.0 if math.sin(fase) >= 0.0 else -1.0
        elif forma == "triangular":
            amostra = 2.0 / math.pi * math.asin(math.sin(fase))
        else:
            amostra = math.sin(fase)
        env_ataque = min(1.0, (i / taxa) / max(0.0005, ataque))
        env = env_ataque * math.exp(-decaimento * t)
        _somar(buf, base + i, amostra * volume * env * 32767)


def _ruido(
    buf: array, taxa: int, inicio: float, duracao: float, volume: float,
    decaimento: float = 10.0, semente: int = 7, suavizar: int = 0,
) -> None:
    rnd = random.Random(semente)
    n = max(1, int(duracao * taxa))
    base = int(inicio * taxa)
    anterior = 0.0
    for i in range(n):
        t = i / n
        valor = rnd.uniform(-1.0, 1.0)
        if suavizar > 1:
            anterior = anterior * (1.0 - 1.0 / suavizar) + valor * (1.0 / suavizar)
            valor = anterior
        env = math.exp(-decaimento * t)
        _somar(buf, base + i, valor * volume * env * 32767)


def _normalizar(buf: array, pico: float = 0.75) -> array:
    maior = max((abs(v) for v in buf), default=0)
    if maior == 0:
        return buf
    fator = pico * 32767 / maior
    for i, v in enumerate(buf):
        buf[i] = max(-32767, min(32767, int(v * fator)))
    return buf


def _wav_bytes(buf: array, taxa: int) -> bytes:
    memoria = io.BytesIO()
    with wave.open(memoria, "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa)
        arquivo.writeframes(buf.tobytes())
    return memoria.getvalue()


def gerar_efeito(nome: str) -> bytes:
    """Sintetiza um efeito curto e devolve os bytes de um WAV mono."""
    taxa = TAXA_EFEITO
    if nome == "clique":
        buf = _novo(0.06, taxa)
        _oscilar(buf, taxa, 0.0, 0.05, 900, 700, 0.5, decaimento=30)
    elif nome == "acerto":
        buf = _novo(0.22, taxa)
        _oscilar(buf, taxa, 0.0, 0.16, 150, 70, 0.8, decaimento=14, forma="quadrada")
        _oscilar(buf, taxa, 0.0, 0.14, 72, 46, 0.55, decaimento=18)
        _oscilar(buf, taxa, 0.0, 0.07, 2400, 1400, 0.18, decaimento=34)
        _ruido(buf, taxa, 0.0, 0.12, 0.45, decaimento=22, semente=11, suavizar=3)
    elif nome == "critico":
        buf = _novo(0.30, taxa)
        _oscilar(buf, taxa, 0.0, 0.18, 240, 90, 0.75, decaimento=12, forma="quadrada")
        _oscilar(buf, taxa, 0.0, 0.24, 62, 38, 0.65, decaimento=13)
        _oscilar(buf, taxa, 0.0, 0.22, 1400, 900, 0.35, decaimento=9)
        _oscilar(buf, taxa, 0.02, 0.20, 2200, 1800, 0.18, decaimento=6)
        _ruido(buf, taxa, 0.0, 0.18, 0.5, decaimento=16, semente=23, suavizar=2)
    elif nome == "magia":
        buf = _novo(0.42, taxa)
        _oscilar(buf, taxa, 0.0, 0.40, 380, 980, 0.5, decaimento=5)
        _oscilar(buf, taxa, 0.02, 0.38, 760, 1500, 0.25, decaimento=7)
        _ruido(buf, taxa, 0.0, 0.30, 0.18, decaimento=8, semente=31, suavizar=4)
    elif nome == "flecha":
        buf = _novo(0.20, taxa)
        _ruido(buf, taxa, 0.0, 0.16, 0.45, decaimento=18, semente=41, suavizar=2)
        _oscilar(buf, taxa, 0.0, 0.12, 1800, 600, 0.22, decaimento=16)
    elif nome == "dano":
        buf = _novo(0.30, taxa)
        _oscilar(buf, taxa, 0.0, 0.26, 220, 90, 0.7, decaimento=10, forma="triangular")
        _ruido(buf, taxa, 0.0, 0.18, 0.35, decaimento=14, semente=53, suavizar=5)
    elif nome == "morte_inimigo":
        buf = _novo(0.55, taxa)
        _oscilar(buf, taxa, 0.0, 0.5, 520, 90, 0.55, decaimento=6, forma="triangular")
        _ruido(buf, taxa, 0.05, 0.4, 0.25, decaimento=8, semente=61, suavizar=4)
    elif nome == "morte_jogador":
        buf = _novo(1.20, taxa)
        for i, freq in enumerate((392, 330, 262)):
            _oscilar(buf, taxa, i * 0.18, 0.75, freq, freq * 0.92, 0.45, decaimento=3)
        _ruido(buf, taxa, 0.0, 0.8, 0.12, decaimento=3, semente=71, suavizar=6)
    elif nome == "level_up":
        buf = _novo(0.85, taxa)
        for i, freq in enumerate((523, 659, 784, 1047)):
            _oscilar(buf, taxa, i * 0.11, 0.45, freq, freq, 0.4, decaimento=5)
            _oscilar(buf, taxa, i * 0.11, 0.35, freq * 2, freq * 2, 0.12, decaimento=7)
    elif nome == "loot":
        buf = _novo(0.35, taxa)
        _oscilar(buf, taxa, 0.0, 0.16, 880, 880, 0.35, decaimento=8)
        _oscilar(buf, taxa, 0.10, 0.22, 1320, 1320, 0.3, decaimento=7)
    elif nome == "pocao":
        buf = _novo(0.45, taxa)
        _oscilar(buf, taxa, 0.0, 0.40, 300, 720, 0.4, decaimento=4, forma="triangular")
        _oscilar(buf, taxa, 0.06, 0.34, 450, 900, 0.2, decaimento=5)
    elif nome == "golpe":
        buf = _novo(0.30, taxa)
        _ruido(buf, taxa, 0.0, 0.22, 0.38, decaimento=13, semente=101, suavizar=2)
        _oscilar(buf, taxa, 0.0, 0.20, 220, 80, 0.55, decaimento=12, forma="triangular")
        _oscilar(buf, taxa, 0.0, 0.09, 2600, 900, 0.22, decaimento=28)
    elif nome == "arco":
        buf = _novo(0.24, taxa)
        _oscilar(buf, taxa, 0.0, 0.18, 340, 170, 0.45, decaimento=16, forma="triangular")
        _ruido(buf, taxa, 0.0, 0.14, 0.30, decaimento=20, semente=103, suavizar=2)
        _oscilar(buf, taxa, 0.0, 0.10, 1500, 700, 0.18, decaimento=22)
    elif nome == "fogo":
        buf = _novo(0.60, taxa)
        _oscilar(buf, taxa, 0.0, 0.50, 180, 55, 0.55, decaimento=5, forma="triangular")
        _ruido(buf, taxa, 0.0, 0.55, 0.35, decaimento=4.5, semente=107, suavizar=3)
        _oscilar(buf, taxa, 0.02, 0.35, 420, 240, 0.18, decaimento=7)
    elif nome == "gelo":
        buf = _novo(0.58, taxa)
        for i, freq in enumerate((1320, 1760, 2340)):
            _oscilar(buf, taxa, i * 0.03, 0.45, freq, freq * 0.92, 0.22, decaimento=7)
        _ruido(buf, taxa, 0.0, 0.40, 0.18, decaimento=9, semente=109, suavizar=5)
    elif nome == "raio":
        buf = _novo(0.42, taxa)
        _ruido(buf, taxa, 0.0, 0.16, 0.55, decaimento=20, semente=113, suavizar=1)
        _oscilar(buf, taxa, 0.0, 0.22, 1900, 380, 0.35, decaimento=12, forma="quadrada")
        _oscilar(buf, taxa, 0.0, 0.28, 90, 50, 0.40, decaimento=9)
    elif nome == "brado":
        buf = _novo(0.62, taxa)
        _oscilar(buf, taxa, 0.0, 0.55, 110, 165, 0.55, decaimento=3.5, forma="triangular")
        _oscilar(buf, taxa, 0.0, 0.45, 220, 330, 0.20, decaimento=5)
        _ruido(buf, taxa, 0.0, 0.35, 0.18, decaimento=7, semente=127, suavizar=6)
    elif nome == "investida":
        buf = _novo(0.36, taxa)
        _ruido(buf, taxa, 0.0, 0.28, 0.35, decaimento=10, semente=131, suavizar=2)
        _oscilar(buf, taxa, 0.0, 0.24, 160, 70, 0.35, decaimento=11, forma="triangular")
    elif nome == "explosao":
        buf = _novo(0.70, taxa)
        _oscilar(buf, taxa, 0.0, 0.55, 95, 38, 0.85, decaimento=5, forma="seno")
        _ruido(buf, taxa, 0.0, 0.45, 0.55, decaimento=7, semente=137, suavizar=2)
        _oscilar(buf, taxa, 0.02, 0.35, 300, 90, 0.25, decaimento=8, forma="triangular")
    elif nome == "morte_boss":
        buf = _novo(1.90, taxa)
        _oscilar(buf, taxa, 0.0, 1.50, 80, 30, 0.85, decaimento=2.2, forma="seno")
        _oscilar(buf, taxa, 0.0, 1.30, 160, 60, 0.35, decaimento=2.5, forma="triangular")
        for i, freq in enumerate((392, 311, 262, 196)):
            _oscilar(buf, taxa, i * 0.16, 1.0, freq, freq * 0.9, 0.28, decaimento=2.6)
        _ruido(buf, taxa, 0.0, 1.20, 0.30, decaimento=2.4, semente=139, suavizar=5)
        _oscilar(buf, taxa, 0.6, 0.9, 1568, 1046, 0.10, decaimento=4)
    elif nome == "fase_boss":
        buf = _novo(1.10, taxa)
        _oscilar(buf, taxa, 0.0, 0.95, 65, 130, 0.75, decaimento=2.6, forma="quadrada")
        _oscilar(buf, taxa, 0.0, 0.85, 130, 260, 0.30, decaimento=3.2, forma="triangular")
        _ruido(buf, taxa, 0.0, 0.75, 0.30, decaimento=4, semente=149, suavizar=5)
        _oscilar(buf, taxa, 0.15, 0.60, 880, 660, 0.12, decaimento=5)
    elif nome == "inimigo_ataque":
        buf = _novo(0.20, taxa)
        _ruido(buf, taxa, 0.0, 0.15, 0.35, decaimento=18, semente=151, suavizar=2)
        _oscilar(buf, taxa, 0.0, 0.14, 180, 80, 0.35, decaimento=16, forma="triangular")
    elif nome == "inimigo_projetil":
        buf = _novo(0.30, taxa)
        _oscilar(buf, taxa, 0.0, 0.24, 520, 920, 0.30, decaimento=10)
        _ruido(buf, taxa, 0.0, 0.20, 0.18, decaimento=12, semente=157, suavizar=4)
    elif nome == "perigo":
        buf = _novo(0.22, taxa)
        _oscilar(buf, taxa, 0.0, 0.10, 900, 1200, 0.25, decaimento=18)
        _oscilar(buf, taxa, 0.09, 0.10, 1200, 1500, 0.18, decaimento=18)
    elif nome == "forja":
        buf = _novo(0.40, taxa)
        _oscilar(buf, taxa, 0.0, 0.10, 2400, 1400, 0.35, decaimento=28, forma="quadrada")
        _oscilar(buf, taxa, 0.0, 0.28, 120, 55, 0.55, decaimento=12, forma="triangular")
        _ruido(buf, taxa, 0.0, 0.22, 0.30, decaimento=18, semente=163, suavizar=2)
    elif nome == "encanto":
        buf = _novo(0.60, taxa)
        for i, freq in enumerate((660, 880, 1320)):
            _oscilar(buf, taxa, i * 0.08, 0.40, freq, freq, 0.30, decaimento=6)
        _ruido(buf, taxa, 0.0, 0.30, 0.10, decaimento=10, semente=167, suavizar=6)
    elif nome == "compra":
        buf = _novo(0.28, taxa)
        _oscilar(buf, taxa, 0.0, 0.10, 1760, 1760, 0.35, decaimento=16)
        _oscilar(buf, taxa, 0.08, 0.14, 2340, 2340, 0.25, decaimento=14)
    elif nome == "venda":
        buf = _novo(0.28, taxa)
        _oscilar(buf, taxa, 0.0, 0.10, 1320, 1320, 0.35, decaimento=16)
        _oscilar(buf, taxa, 0.08, 0.14, 1760, 1760, 0.25, decaimento=14)
    elif nome == "equipar":
        buf = _novo(0.26, taxa)
        _ruido(buf, taxa, 0.0, 0.18, 0.28, decaimento=14, semente=173, suavizar=5)
        _oscilar(buf, taxa, 0.0, 0.14, 320, 180, 0.25, decaimento=14, forma="triangular")
    elif nome == "cristal":
        buf = _novo(0.50, taxa)
        for i, freq in enumerate((1046, 1568, 2093)):
            _oscilar(buf, taxa, i * 0.05, 0.38, freq, freq, 0.26, decaimento=7)
    elif nome == "missao":
        buf = _novo(1.00, taxa)
        for i, freq in enumerate((523, 659, 784, 1047)):
            _oscilar(buf, taxa, i * 0.12, 0.55, freq, freq, 0.32, decaimento=4)
            _oscilar(buf, taxa, i * 0.12, 0.35, freq * 1.5, freq * 1.5, 0.10, decaimento=6)
    elif nome == "descanso":
        buf = _novo(0.90, taxa)
        _ruido(buf, taxa, 0.0, 0.70, 0.18, decaimento=3.0, semente=179, suavizar=7)
        for i, freq in enumerate((392, 523, 659)):
            _oscilar(buf, taxa, i * 0.10, 0.55, freq, freq, 0.24, decaimento=4)
    elif nome == "boss":
        buf = _novo(1.40, taxa)
        _oscilar(buf, taxa, 0.0, 1.3, 70, 45, 0.85, decaimento=2.2, forma="quadrada")
        _oscilar(buf, taxa, 0.0, 1.2, 140, 90, 0.35, decaimento=2.5, forma="triangular")
        _ruido(buf, taxa, 0.0, 1.1, 0.25, decaimento=2.5, semente=83, suavizar=8)
    elif nome == "vitoria":
        buf = _novo(1.60, taxa)
        for i, freq in enumerate((523, 659, 784, 1047, 1319)):
            _oscilar(buf, taxa, i * 0.14, 0.7, freq, freq, 0.4, decaimento=3)
            _oscilar(buf, taxa, i * 0.14, 0.5, freq * 1.5, freq * 1.5, 0.12, decaimento=4)
    elif nome == "passo":
        buf = _novo(0.12, taxa)
        _ruido(buf, taxa, 0.0, 0.10, 0.22, decaimento=12, semente=91, suavizar=6)
        _oscilar(buf, taxa, 0.0, 0.07, 95, 55, 0.20, decaimento=14, forma="seno")
    elif nome == "esquiva":
        buf = _novo(0.30, taxa)
        _ruido(buf, taxa, 0.0, 0.24, 0.18, decaimento=9, semente=57, suavizar=4)
        _oscilar(buf, taxa, 0.0, 0.18, 420, 180, 0.10, decaimento=8, forma="triangular")
    else:
        raise KeyError(f"efeito desconhecido: {nome}")
    return _wav_bytes(_normalizar(buf), taxa)


def gerar_musica(nome: str) -> bytes:
    """Sintetiza um loop de ambiente, mono e curto, para tocar em repetição."""
    taxa = TAXA_MUSICA
    segundos = 8.0
    if nome == "clareira":
        raiz, quinta, cor = 196.0, 293.66, (0.30, 0.22, 0.16)
    elif nome == "floresta":
        raiz, quinta, cor = 174.61, 261.63, (0.28, 0.20, 0.20)
    elif nome == "ruinas":
        raiz, quinta, cor = 146.83, 220.0, (0.30, 0.24, 0.14)
    elif nome == "caverna":
        raiz, quinta, cor = 110.0, 164.81, (0.26, 0.18, 0.22)
    elif nome == "pantano":
        raiz, quinta, cor = 130.81, 196.0, (0.24, 0.22, 0.14)
    elif nome == "desfiladeiro":
        raiz, quinta, cor = 98.0, 146.83, (0.32, 0.20, 0.18)
    elif nome == "coracao":
        raiz, quinta, cor = 220.0, 329.63, (0.24, 0.28, 0.34)
    elif nome == "eclipse":
        raiz, quinta, cor = 82.41, 123.47, (0.30, 0.16, 0.28)
    else:
        raise KeyError(f"música desconhecida: {nome}")

    buf = _novo(segundos, taxa)
    total = len(buf)

    # pad lento: três osciladores levemente desafinados, com LFO de amplitude
    for detune, volume in ((0.0, cor[0]), (0.7, cor[1]), (-0.9, cor[2])):
        fase = 0.0
        for i in range(total):
            t = i / taxa
            lfo = 0.6 + 0.4 * math.sin(2.0 * math.pi * 0.11 * t + detune)
            fase += 2.0 * math.pi * (raiz + detune) / taxa
            _somar(buf, i, math.sin(fase) * volume * lfo * 32767 * 0.5)

    # quinta suave, entra e sai devagar
    fase = 0.0
    for i in range(total):
        t = i / taxa
        env = 0.5 + 0.5 * math.sin(2.0 * math.pi * 0.07 * t)
        fase += 2.0 * math.pi * quinta / taxa
        _somar(buf, i, math.sin(fase) * 0.12 * env * 32767)

    # vento/eco: ruído suavizado, bem baixo
    rnd = random.Random(97)
    anterior = 0.0
    for i in range(total):
        t = i / taxa
        anterior = anterior * 0.995 + rnd.uniform(-1.0, 1.0) * 0.005
        env = 0.35 + 0.25 * math.sin(2.0 * math.pi * 0.05 * t + 1.3)
        _somar(buf, i, anterior * env * 32767 * 1.6)

    # pulso grave marcando o tempo (2 batidas por loop)
    for inicio in (0.0, 4.0):
        _oscilar(buf, taxa, inicio, 1.6, raiz / 2, raiz / 2, 0.28, decaimento=2.0, forma="triangular")

    _ambiente_musica(buf, taxa, nome)
    _fade_bordas(buf, taxa, 0.35)
    return _wav_bytes(_normalizar(buf, 0.55), taxa)


def _ambiente_musica(buf: array, taxa: int, nome: str) -> None:
    """Camadas curtas de ambiência por bioma, misturadas ao loop."""
    if nome == "clareira":
        # pássaros: dois assobios curtos e agudos
        for inicio, f1, f2 in (
            (1.1, 2100, 2900), (2.6, 2500, 3300), (5.2, 1900, 2700), (6.4, 2300, 3100),
        ):
            _oscilar(buf, taxa, inicio, 0.12, f1, f2, 0.10, decaimento=18)
            _oscilar(buf, taxa, inicio + 0.09, 0.10, f2, f1, 0.08, decaimento=20)
    elif nome == "floresta":
        # folhas ao vento e um pássaro distante
        for inicio in (0.7, 2.3, 4.5, 6.8):
            _ruido(
                buf, taxa, inicio, 0.5, 0.06, decaimento=5,
                semente=211 + int(inicio * 10), suavizar=7,
            )
        for inicio in (1.6, 5.9):
            _oscilar(buf, taxa, inicio, 0.10, 2400, 3000, 0.06, decaimento=20)
    elif nome == "ruinas":
        # vento constante e um metal distante
        _ruido(buf, taxa, 0.0, 7.0, 0.04, decaimento=0.2, semente=223, suavizar=9)
        for inicio in (1.9, 5.4):
            _oscilar(buf, taxa, inicio, 0.35, 900, 700, 0.05, decaimento=6)
            _oscilar(buf, taxa, inicio, 0.30, 1350, 1100, 0.03, decaimento=8)
    elif nome == "caverna":
        # gotas d'água com eco curto
        for inicio, freq in ((1.0, 1600), (2.8, 2100), (4.2, 1400), (6.1, 1900)):
            _oscilar(buf, taxa, inicio, 0.16, freq, freq * 0.7, 0.10, decaimento=14)
            _oscilar(buf, taxa, inicio + 0.10, 0.12, freq * 0.5, freq * 0.4, 0.05, decaimento=12)
    elif nome == "pantano":
        # sapos e insetos distantes
        for inicio in (0.8, 2.5, 4.7, 6.3):
            _oscilar(buf, taxa, inicio, 0.22, 190, 120, 0.08, decaimento=7, forma="triangular")
            _oscilar(buf, taxa, inicio + 0.06, 0.18, 230, 140, 0.05, decaimento=9, forma="triangular")
        for inicio in (1.4, 3.6, 5.8):
            _oscilar(buf, taxa, inicio, 0.08, 3400, 3200, 0.03, decaimento=20)
    elif nome == "desfiladeiro":
        # brasas estalando e um trovão distante
        for inicio in (0.4, 1.3, 2.2, 3.8, 5.1, 6.6):
            _ruido(
                buf, taxa, inicio, 0.12, 0.08, decaimento=22,
                semente=241 + int(inicio * 10), suavizar=2,
            )
        _oscilar(buf, taxa, 0.0, 7.5, 55, 45, 0.10, decaimento=0.1, forma="triangular")
        for inicio in (2.0, 5.6):
            _oscilar(buf, taxa, inicio, 0.30, 700, 520, 0.06, decaimento=7, forma="quadrada")
    elif nome == "coracao":
        # batimento lento e brilho etéreo
        for i in range(4):
            base = i * 2.0
            _oscilar(buf, taxa, base, 0.20, 70, 50, 0.16, decaimento=8)
            _oscilar(buf, taxa, base + 0.22, 0.18, 62, 44, 0.11, decaimento=9)
        for i in range(8):
            _oscilar(buf, taxa, i * 1.0, 0.9, 1760 + (i % 3) * 220, 1760, 0.03, decaimento=2.5)
        _oscilar(buf, taxa, 0.0, 7.5, 2637, 2610, 0.02, decaimento=0.1)
    elif nome == "eclipse":
        # batimento grave, brilho dissonante e sussurros
        for i in range(4):
            base = i * 2.0
            _oscilar(buf, taxa, base, 0.30, 55, 40, 0.18, decaimento=6)
            _oscilar(buf, taxa, base + 0.35, 0.25, 48, 36, 0.12, decaimento=7)
        for i in range(6):
            _oscilar(buf, taxa, i * 1.2, 0.8, 880 + (i % 3) * 110, 820, 0.035, decaimento=2.2)
        _oscilar(buf, taxa, 0.0, 7.5, 1760, 1740, 0.015, decaimento=0.1)
        for inicio in (1.6, 4.8, 6.9):
            _ruido(
                buf, taxa, inicio, 0.4, 0.05, decaimento=5,
                semente=311 + int(inicio * 10), suavizar=8,
            )


def _fade_bordas(buf: array, taxa: int, segundos: float) -> None:
    """Suaviza o começo e o fim para o loop não estalar."""
    n = max(1, int(segundos * taxa))
    n = min(n, len(buf) // 2)
    for i in range(n):
        f = i / n
        buf[i] = int(buf[i] * f)
        buf[-1 - i] = int(buf[-1 - i] * f)


# --------------------------------------------------------------------------
# cache em disco
# --------------------------------------------------------------------------


def _arquivo(nome: str, tipo: str) -> Path:
    return audio_dir() / f"{tipo}_{nome}_v{VERSAO_AUDIO}.wav"


def obter_efeito(nome: str) -> bytes:
    caminho = _arquivo(nome, "sfx")
    if caminho.exists():
        try:
            return caminho.read_bytes()
        except OSError:
            pass
    dados = gerar_efeito(nome)
    _gravar(caminho, dados)
    return dados


def obter_musica(nome: str) -> bytes:
    caminho = _arquivo(nome, "mus")
    if caminho.exists():
        try:
            return caminho.read_bytes()
        except OSError:
            pass
    dados = gerar_musica(nome)
    _gravar(caminho, dados)
    return dados


def _gravar(caminho: Path, dados: bytes) -> None:
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_bytes(dados)
        temporario.replace(caminho)
    except OSError:
        LOGGER.warning("Não foi possível gravar o áudio em cache: %s", caminho)


# --------------------------------------------------------------------------
# reprodução
# --------------------------------------------------------------------------


class Sons:
    """Carrega, toca e mistura os sons. Silencioso se o mixer não abrir."""

    def __init__(
        self,
        ativo: bool = True,
        volume_geral: float = 0.8,
        volume_musica: float = 0.6,
        volume_efeitos: float = 0.8,
    ) -> None:
        self.disponivel = False
        self.mudo = False
        self.volume_geral = _limitar(volume_geral)
        self.volume_musica = _limitar(volume_musica)
        self.volume_efeitos = _limitar(volume_efeitos)
        self.ducking = 1.0
        self._efeitos: dict[str, pygame.mixer.Sound] = {}
        self._musica_atual: str | None = None
        self._ultimo: dict[str, float] = {}
        if ativo:
            self._iniciar()


    def _iniciar(self) -> None:
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=TAXA_EFEITO, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(16)
            for nome in EFEITOS:
                self._efeitos[nome] = pygame.mixer.Sound(buffer=obter_efeito(nome))
            self.disponivel = True
        except (pygame.error, OSError, KeyError) as exc:  # pragma: no cover - depende do driver
            LOGGER.warning("Áudio indisponível: %s", exc)
            self.disponivel = False

    # ------------------------------------------------------------------ volumes
    def definir_volumes(
        self, geral: float | None = None, musica: float | None = None, efeitos: float | None = None,
    ) -> None:
        if geral is not None:
            self.volume_geral = _limitar(geral)
        if musica is not None:
            self.volume_musica = _limitar(musica)
        if efeitos is not None:
            self.volume_efeitos = _limitar(efeitos)
        self._aplicar_volumes()

    def _aplicar_volumes(self) -> None:
        if not self.disponivel:
            return
        try:
            pygame.mixer.music.set_volume(
                0.0 if self.mudo else self.volume_geral * self.volume_musica * self.ducking
            )
        except pygame.error:  # pragma: no cover
            pass

    def definir_ducking(self, fator: float) -> None:
        """Abaixa a música temporariamente (boss, vida baixa) sem mudar o volume salvo."""
        novo = _limitar(fator)
        if abs(novo - self.ducking) < 0.01:
            return
        self.ducking = novo
        self._aplicar_volumes()

    def alternar_mudo(self) -> bool:
        self.mudo = not self.mudo
        self._aplicar_volumes()
        return self.mudo

    # ------------------------------------------------------------------ tocar
    def tocar(self, nome: str, volume: float = 1.0, intervalo: float = 0.0) -> None:
        if not self.disponivel or self.mudo:
            return
        if intervalo > 0:
            agora = pygame.time.get_ticks() / 1000.0
            if agora - self._ultimo.get(nome, -999.0) < intervalo:
                return
            self._ultimo[nome] = agora
        som = self._efeitos.get(nome)
        if som is None:
            return
        try:
            som.set_volume(_limitar(self.volume_geral * self.volume_efeitos * volume * random.uniform(0.92, 1.08)))
            som.play()
        except pygame.error:  # pragma: no cover
            pass

    def tocar_musica(self, nome: str | None) -> None:
        if not self.disponivel:
            return
        if nome == self._musica_atual:
            return
        self._musica_atual = nome
        try:
            if nome is None:
                pygame.mixer.music.stop()
                return
            caminho = _arquivo(nome, "mus")
            if not caminho.exists():
                _gravar(caminho, gerar_musica(nome))
            pygame.mixer.music.load(str(caminho))
            pygame.mixer.music.set_volume(
                0.0 if self.mudo else self.volume_geral * self.volume_musica * self.ducking
            )
            try:
                pygame.mixer.music.play(-1, fade_ms=700)
            except TypeError:  # pragma: no cover - pygame antigo sem fade_ms
                pygame.mixer.music.play(-1)
        except (pygame.error, OSError) as exc:  # pragma: no cover
            LOGGER.warning("Falha ao tocar a música %s: %s", nome, exc)
            self._musica_atual = None

    def parar(self) -> None:
        if not self.disponivel:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:  # pragma: no cover
            pass
        self._musica_atual = None


def _limitar(valor: float) -> float:
    return max(0.0, min(1.0, float(valor)))
