"""Inimigos em pixel art para o jogo principal (experimental).

Usa o pack CC0 **0x72 - DungeonTileset II** (16x16, ampliado 2x). Cada tipo de
inimigo do jogo aponta para o sprite mais próximo do pack; quando o pack não tem
o bicho, o sprite recebe uma tinta da cor do inimigo para manter a identidade.

O desenho vetorial continua sendo o padrão: isto só entra com a opção
**Configurações -> Vídeo -> Arte pixel** ligada.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

import pygame

import pixel_arte

PASTA = pixel_arte.RAIZ / "assets" / "pixel" / "ox72" / "monstros"

# tipo: (sprite base, escala, tinta, flutuante)
TIPOS: dict[str, tuple[str, int, tuple[int, int, int] | None, bool]] = {
    "slime": ("slug", 3, None, False),
    "slime_cristal": ("slug", 3, (150, 96, 206), False),
    "rei_slime": ("slug", 5, (86, 206, 130), False),
    "goblin": ("goblin", 4, None, False),
    "golem": ("ogre", 2, (122, 128, 146), False),
    "golem_obsidiana": ("ogre", 2, (112, 58, 72), False),
    "golem_anciao": ("ogre", 3, (132, 138, 158), False),
    "colosso_obsidiana": ("ogre", 3, (140, 60, 74), False),
    "wisp": ("angel", 3, (120, 210, 240), True),
    "espectro_aether": ("angel", 3, (186, 164, 250), True),
    "avatar_aether": ("angel", 4, (196, 232, 255), True),
    "morcego": ("imp", 4, (128, 96, 178), True),
    "mosquito": ("imp", 4, (164, 138, 92), True),
    "aranha": ("aranha_predadora", 1, None, False),
    "lodo": ("swampy", 3, (104, 138, 84), False),
    "rainha_lodo": ("swampy", 5, (120, 190, 130), False),
    "sapo": ("sapo_lodo", 1, None, False),
    "serpente": ("lizard_m", 3, (110, 220, 190), False),
    "serpente_aether": ("lizard_m", 3, (132, 240, 222), False),
    "serpente_vazio": ("lizard_m", 3, (90, 180, 170), False),
    "serpente_colossal": ("lizard_m", 4, (120, 230, 180), False),
    "elemental_cristal": ("wizzard_m", 3, (110, 210, 240), False),
    "sentinela_aether": ("knight_m", 3, (176, 232, 255), False),
    "sombra_eclipse": ("necromancer", 3, (120, 80, 180), True),
    "ceifador_espelhado": ("necromancer", 3, (190, 200, 230), True),
    "ceifador_nevoa": ("necromancer", 4, (150, 200, 230), True),
    "senhor_fragmentos": ("necromancer", 4, (156, 96, 218), True),
    "guardiao_eclipse": ("knight_m", 4, (160, 120, 220), False),
    "devorador": ("big_demon", 3, (196, 82, 168), False),
    "escorpiao": ("chort", 3, (156, 68, 92), False),
}

_cache: dict[tuple[str, int, tuple[int, int, int] | None], tuple[list[pygame.Surface], list[pygame.Surface]]] = {}

PASTA_LOBO = pixel_arte.RAIZ / "assets/pixel/custom/lobo_sombrio/sprites"
PASTA_LOBO_SPRITESHEETS = pixel_arte.RAIZ / "assets/pixel/custom/lobo_sombrio/spritesheets"

# EXPERIMENTAL: animação de caminhada do Lobo Sombrio (v0.1.68-dev).
# Arte ainda NÃO aprovada em definitivo; o lobo idle estático continua como
# fallback se os quadros de caminhada faltarem ou forem inválidos.
LOBO_ANDAR = True
_cache_lobo: dict[Path, pygame.Surface] = {}
_cache_lobo_listas: dict[bool, tuple[list[pygame.Surface], list[pygame.Surface]]] = {}

# Cache de direcao horizontal de TODOS os inimigos pixel (flip apenas de
# renderizacao; nao altera IA/movimento). O nome historico _lobo_flip_cache
# permanece como alias (o mesmo objeto) para compatibilidade dos testes da
# Missao 03.x.
_direcao_cache: "WeakKeyDictionary[Any, bool]" = WeakKeyDictionary()
_lobo_flip_cache = _direcao_cache

# EXPERIMENTAL (missao 05.10): salto do Sapo do Lodo — translacoes + squash
# (rendering-only; IA, colisoes e dano intocados). Ciclo de 6 fases a 8 fps:
# (deslocamento vertical, compressao vertical em px, avanco horizontal em px).
# O avanco segue o sinal do facing (a orientacao da Missao 05.3).
SAPO_SALTO = ((0, 0, 0), (2, 4, 0), (-5, 0, 1), (-8, 0, 3), (-3, 2, 2), (1, 4, 1))

# Missao 05.11: estado do salto por inimigo (distancia percorrida + ultima
# posicao logica). O ciclo do salto avanca com o DESLOCAMENTO REAL do inimigo
# (SAPO_PASSO_FASE px por fase); parado, o sapo fica no chao (fase de apoio).
# Limpado automaticamente quando o inimigo morre (chaves fracas).
_salto_cache: "WeakKeyDictionary[Any, tuple[float, float, float]]" = WeakKeyDictionary()
SAPO_PASSO_FASE = 10.0


def _quadro_lobo_valido(caminho: Path) -> pygame.Surface | None:
    """Carrega um PNG 64x64 de arte própria; None se inválido ou ausente."""
    if caminho in _cache_lobo:
        return _cache_lobo[caminho]
    if not caminho.is_file():
        return None
    try:
        bruto = pygame.image.load(str(caminho))
        if bruto.get_size() != (64, 64) or not bruto.get_flags() & pygame.SRCALPHA:
            return None
        alfas = {bruto.get_at((x, y)).a for x in range(64) for y in range(64)}
        if alfas != {0, 255}:
            return None
        sprite = pygame.transform.scale(bruto.convert_alpha(), (48, 48))
    except (OSError, pygame.error):
        return None
    _cache_lobo[caminho] = sprite
    return sprite


# EXPERIMENTAL (missão 04.9): caminhada procedural em 6 quadros. Usada só se a
# sequência completa existir na pasta; caso contrário, vale a caminhada da
# missão 02 (walk_f0..f3) e, sem ela, o idle estático.
NOMES_WALK_PROCEDURAL = tuple(f"lobo_sombrio_walkp_f{i}.png" for i in range(6))


def _carregar_lobo() -> tuple[list[pygame.Surface], list[pygame.Surface]]:
    """Retorna (idle, andar) do lobo. Sem walk válida, ele anda com o idle."""
    if not LOBO_ANDAR:
        idle = _quadro_lobo_valido(PASTA_LOBO / "lobo_sombrio_idle_f0.png")
        return ([idle] if idle is not None else [], [])
    cache = _cache_lobo_listas.get(LOBO_ANDAR)
    if cache is not None:
        return cache
    idle = _quadro_lobo_valido(PASTA_LOBO / "lobo_sombrio_idle_f0.png")
    if idle is None:
        return [], []
    procedurais = [
        q
        for nome in NOMES_WALK_PROCEDURAL
        if (q := _quadro_lobo_valido(PASTA_LOBO / nome)) is not None
    ]
    if len(procedurais) == len(NOMES_WALK_PROCEDURAL):
        resultado = ([idle], procedurais)
        _cache_lobo_listas[LOBO_ANDAR] = resultado
        return resultado
    passos = [
        q
        for nome in ("lobo_sombrio_walk_f0.png", "lobo_sombrio_walk_f1.png",
                     "lobo_sombrio_walk_f2.png", "lobo_sombrio_walk_f3.png")
        if (q := _quadro_lobo_valido(PASTA_LOBO / nome)) is not None
    ]
    resultado = ([idle], passos)
    _cache_lobo_listas[LOBO_ANDAR] = resultado
    return resultado


def _extrair_spritesheet(caminho: Path) -> list[pygame.Surface]:
    """Extrai 4 frames de 64x64 de um spritesheet 256x64. Retorna lista vazia se falhar."""
    if not caminho.is_file():
        return []
    try:
        sheet = pygame.image.load(str(caminho)).convert_alpha()
        if sheet.get_size() != (256, 64):
            return []
        frames = []
        for i in range(4):
            frame = sheet.subsurface(pygame.Rect(i * 64, 0, 64, 64)).copy()
            frame = pygame.transform.scale(frame, (48, 48))
            frames.append(frame)
        return frames
    except (OSError, pygame.error):
        return []


def _carregar_lobo_frente() -> list[pygame.Surface]:
    """Carrega frames de caminhada frontal do Lobo (4 frames de 48x48)."""
    caminho = PASTA_LOBO_SPRITESHEETS / "lobo_sombrio_walk_frente_spritesheet.png"
    return _extrair_spritesheet(caminho)


def _carregar_lobo_costas() -> list[pygame.Surface]:
    """Carrega frames de caminhada traseira do Lobo (4 frames de 48x48)."""
    caminho = PASTA_LOBO_SPRITESHEETS / "lobo_sombrio_walk_costas_spritesheet.png"
    return _extrair_spritesheet(caminho)


def _arquivos(base: str, tipo: str) -> list[Path]:
    if tipo == "anim":
        padrao = f"{base}_anim_f*.png"
    else:
        padrao = f"{base}_{tipo}_anim_f*.png"
    arquivos = sorted(PASTA.glob(padrao), key=lambda p: int(p.stem.rsplit("f", 1)[-1]))
    return arquivos


def _tingir(sprite: pygame.Surface, cor: tuple[int, int, int]) -> pygame.Surface:
    """Recolore mantendo o sombreado: preto continua preto, claro vira a cor."""
    largura, altura = sprite.get_size()
    saida = pygame.Surface((largura, altura), pygame.SRCALPHA)
    for x in range(largura):
        for y in range(altura):
            r, g, b, a = sprite.get_at((x, y))
            if a == 0:
                continue
            lum = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0
            fator = 0.45 + 0.75 * lum
            nr = min(255, int(cor[0] * fator * 0.9 + r * 0.1))
            ng = min(255, int(cor[1] * fator * 0.9 + g * 0.1))
            nb = min(255, int(cor[2] * fator * 0.9 + b * 0.1))
            saida.set_at((x, y), (nr, ng, nb, a))
    return saida


def _carregar(base: str, escala: int, tinta: tuple[int, int, int] | None) -> tuple[list[pygame.Surface], list[pygame.Surface]]:
    chave = (base, escala, tinta)
    if chave in _cache:
        return _cache[chave]

    idle = _arquivos(base, "idle") or _arquivos(base, "anim") or _arquivos(base, "run")
    run = _arquivos(base, "run") or idle
    if not idle:
        direto = PASTA / f"{base}.png"
        idle = run = [direto] if direto.exists() else []

    def montar(arquivos: list[Path]) -> list[pygame.Surface]:
        quadros = []
        for caminho in arquivos:
            bruto = pygame.image.load(str(caminho)).convert_alpha()
            if tinta is not None:
                bruto = _tingir(bruto, tinta)
            quadros.append(pygame.transform.scale(
                bruto, (bruto.get_width() * escala, bruto.get_height() * escala)
            ))
        return quadros

    resultado = (montar(idle), montar(run))
    _cache[chave] = resultado
    return resultado


def _patas(surf: pygame.Surface, x: float, y: float, cor: tuple[int, int, int],
           espelhar: bool = False) -> None:
    """Pernas extras para a aranha (o pack não tem aranha).

    Desenhadas em surface própria para que o espelhamento por direção
    (Missão 05.3) espelhe as patas junto com o corpo, pixel a pixel."""
    escuro = (26, 20, 36)
    patas = pygame.Surface((40, 36), pygame.SRCALPHA)
    ox, oy = 20, 29
    for i, (dx, dy, comprimento) in enumerate((
        (-6, -14, 10), (-7, -9, 12), (-7, -4, 12), (-6, 1, 10),
        (6, -14, 10), (7, -9, 12), (7, -4, 12), (6, 1, 10),
    )):
        lado = -1 if dx < 0 else 1
        base = (ox + dx, oy + dy)
        meio = (int(ox + dx + lado * comprimento * 0.6), int(oy + dy - 4 - (i % 2) * 2))
        ponta = (int(ox + dx + lado * comprimento), int(oy + dy + 4))
        pygame.draw.lines(patas, escuro, False, [base, meio, ponta], 3)
        pygame.draw.lines(patas, cor, False, [base, meio, ponta], 1)
    if espelhar:
        patas = pygame.transform.flip(patas, True, False)
        surf.blit(patas, (int(x) - 20, int(y) - 29))
    else:
        surf.blit(patas, (int(x) - 20, int(y) - 29))


def _cauda(surf: pygame.Surface, x: float, y: float, cor: tuple[int, int, int],
           espelhar: bool = False) -> None:
    """Cauda com ferrão para o escorpião (o pack não tem escorpião).

    Desenhada em surface própria para que o espelhamento por direção
    (Missão 05.3) inverta a cauda junto com o corpo, pixel a pixel."""
    escuro = (26, 20, 36)
    cauda = pygame.Surface((26, 40), pygame.SRCALPHA)
    pontos = [(10, 36), (19, 32), (23, 20), (17, 12)]
    pygame.draw.lines(cauda, escuro, False, pontos, 5)
    pygame.draw.lines(cauda, cor, False, pontos, 3)
    pygame.draw.polygon(cauda, escuro, [(17, 12), (24, 4), (21, 14)])
    if espelhar:
        cauda = pygame.transform.flip(cauda, True, False)
        surf.blit(cauda, (int(x) - 24, int(y) - 42))
    else:
        surf.blit(cauda, (int(x) - 2, int(y) - 42))


def _olhos_sapo(surf: pygame.Surface, x: int, y: int, largura: int, altura: int) -> None:
    """Olhos saltados para o sapo (o sprite base é um monte de lodo)."""
    for lado in (-1, 1):
        cx = x + largura // 2 + lado * 7
        cy = y + 9
        pygame.draw.circle(surf, (26, 30, 26), (cx, cy), 4)
        pygame.draw.circle(surf, (236, 240, 200), (cx, cy), 3)
        pygame.draw.circle(surf, (30, 26, 24), (cx + lado, cy), 1)


def desenhar(inimigo: Any, surf: pygame.Surface, sx: float, sy: float, flash: bool = False) -> bool:
    """Desenha o inimigo em pixel art. Retorna False se o tipo não tem sprite."""
    espelhar = False
    tipo = getattr(inimigo, "tipo", "")
    # direcao comum a todos os inimigos (Missao 05.3): mesmo mecanismo do Lobo
    # (zona morta de 0,1 e memoria da ultima direcao horizontal).
    facing = getattr(inimigo, "facing", (0.0, 1.0))
    fx = float(facing[0]) if isinstance(facing, (tuple, list)) and len(facing) >= 1 else 0.0
    if abs(fx) > 0.1:
        _direcao_cache[inimigo] = (fx < 0)
    espelhar = _direcao_cache.get(inimigo, False)
    if tipo == "lobo":
        idle, passos = _carregar_lobo()
        run = passos if passos else idle
        flutuante = False
        # Missao: caminhada 4 direcoes (frente, costas, direita, esquerda via flip)
        _lobo_frente = _carregar_lobo_frente()
        _lobo_costas = _carregar_lobo_costas()
    else:
        dados = TIPOS.get(tipo)
        if dados is None:
            return False
        base, escala, tinta, flutuante = dados
        idle, run = _carregar(base, escala, tinta)
    if not idle:
        return False

    andando = getattr(inimigo, "estado", "") == "chase"
    if tipo == "lobo" and andando:
        # Seleciona conjunto de caminhada por direcao principal
        fy = float(facing[1]) if isinstance(facing, (tuple, list)) and len(facing) >= 2 else 0.0
        if abs(fx) > abs(fy):
            # Movimento horizontal: usa walk direita + flip
            quadros = run if run else idle
            # espelhar ja definido acima
        elif fy >= 0:
            # Movimento frontal (para baixo): usa walk frente
            quadros = _lobo_frente if _lobo_frente else (run if run else idle)
            espelhar = False
        else:
            # Movimento traseiro (para cima): usa walk costas
            quadros = _lobo_costas if _lobo_costas else (run if run else idle)
            espelhar = False
    else:
        quadros = run if andando and run else idle
    if not quadros:
        quadros = idle
    indice = int(getattr(inimigo, "tempo", 0.0) * 8) % len(quadros)
    sprite = quadros[indice]
    if espelhar and sprite is not None:
        sprite = pygame.transform.flip(sprite, True, False)

    sombra = pygame.Surface((sprite.get_width(), 10), pygame.SRCALPHA)
    pygame.draw.ellipse(sombra, (10, 10, 14, 90), sombra.get_rect())
    surf.blit(sombra, (int(sx) - sprite.get_width() // 2, int(sy) - 5))

    if inimigo.tipo == "aranha" and base != "aranha_predadora":
        # Missão 05.18: com o sprite próprio (aranha_predadora.png, 64x64) as patas
        # já fazem parte da arte; o overlay _patas vale apenas para o fallback
        # tiny_slug do pack (que não tem aranha).
        _patas(surf, sx, sy - 10, inimigo.cor, espelhar)
    if inimigo.tipo == "escorpiao":
        _cauda(surf, sx, sy, inimigo.cor, espelhar)

    x = int(sx) - sprite.get_width() // 2
    y = int(sy) - sprite.get_height()
    if flutuante:
        y -= 14 + int(math.sin(getattr(inimigo, "tempo", 0.0) * 2.4) * 4)
    if inimigo.tipo == "sapo" and andando:
        # missao 05.10/05.11: salto experimental condicionado ao DESLOCAMENTO REAL
        # (translacoes + squash; IA intocada). O ciclo avanca com a passada;
        # parado (sem deslocamento real, ex.: no alcance de ataque), o sapo fica
        # no chao em vez de pular no lugar.
        reg = _salto_cache.get(inimigo)
        dist, ux, uy = reg if reg is not None else (0.0, inimigo.x, inimigo.y)
        desloc = math.hypot(inimigo.x - ux, inimigo.y - uy)
        if desloc > 0.5:  # houve deslocamento real neste quadro
            dist += desloc
            fase = int(dist / SAPO_PASSO_FASE) % 6
            dy, squash, dx = SAPO_SALTO[fase]
        else:             # sem deslocamento real: sapo no chao (fase de apoio)
            dy, squash, dx = 0, 0, 0
            fase = 0
        _salto_cache[inimigo] = (dist, inimigo.x, inimigo.y)
        avanco = dx * (1 if fx > 0 else -1) if dx and abs(fx) > 0.1 else 0
        if squash:
            sv = max(1, sprite.get_height() - squash)
            sw = sprite.get_width() + squash // 2
            sprite = pygame.transform.scale(sprite, (sw, sv))  # nearest: sem suavizacao
            # missao 05.11: com largura impar (squash 2 -> sw impar), o eixo do
            # espelho (sx - 0,5, entre dois pixels) exige floor a direita e ceil
            # a esquerda para o espelho fechar exato; largura par nao muda nada.
            meio = sw // 2 if fx > 0 else (sw + 1) // 2
            x = int(sx) - meio + avanco
            y = int(sy) - sv + dy
        else:
            x += avanco
            y += dy
    surf.blit(sprite, (x, y))
    if inimigo.tipo == "sapo" and base != "sapo_lodo":
        _olhos_sapo(surf, x, y, sprite.get_width(), sprite.get_height())

    if flash:
        silhueta = pygame.mask.from_surface(sprite).to_surface(
            setcolor=(255, 255, 255, 210), unsetcolor=(0, 0, 0, 0)
        )
        surf.blit(silhueta, (x, y))
    return True
