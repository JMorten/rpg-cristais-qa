"""Utilidades visuais e matemáticas compartilhadas pelo jogo."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Sequence

import pygame

import pixel_arte
from settings import (
    ALTURA, BORDA, BRANCO, LARGURA, PAINEL, TEXTO,
)

# --------------------------------------------------------------------------
# matemática
# --------------------------------------------------------------------------


def clamp(valor: float, minimo: float, maximo: float) -> float:
    return minimo if valor < minimo else maximo if valor > maximo else valor


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def suave(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def comprimento(x: float, y: float) -> float:
    return math.hypot(x, y)


def normalizar(x: float, y: float) -> tuple[float, float]:
    d = math.hypot(x, y)
    if d < 1e-9:
        return 0.0, 0.0
    return x / d, y / d


def distancia(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def angulo_para(a: Sequence[float], b: Sequence[float]) -> float:
    return math.atan2(b[1] - a[1], b[0] - a[0])


def cor_multiplicada(cor: Sequence[int], fator: float) -> tuple[int, int, int]:
    return tuple(int(clamp(c * fator, 0, 255)) for c in cor[:3])


def cor_com_alpha(cor: Sequence[int], alpha: int) -> tuple[int, int, int, int]:
    return (int(cor[0]), int(cor[1]), int(cor[2]), int(clamp(alpha, 0, 255)))


# --------------------------------------------------------------------------
# fontes e texto
# --------------------------------------------------------------------------

_FONTES: dict[tuple[str, int, bool], pygame.font.Font] = {}

# Escala global do texto, ajustável nas configurações (acessibilidade).
ESCALA_TEXTO = 1.0


def definir_escala_texto(escala: float) -> None:
    """Aplica a escala global de texto e limpa o cache de fontes."""
    global ESCALA_TEXTO
    nova = max(0.5, min(2.0, float(escala)))
    if abs(nova - ESCALA_TEXTO) < 1e-6:
        return
    ESCALA_TEXTO = nova
    _FONTES.clear()


def escala_texto() -> float:
    return ESCALA_TEXTO


def fonte(tamanho: int, negrito: bool = False, familia: str = "inter") -> pygame.font.Font:
    tamanho = max(6, int(round(int(tamanho) * ESCALA_TEXTO)))
    if pixel_arte.ATIVO and familia_pixel(familia):
        # Silkscreen é mais larga que a Inter no mesmo corpo; 0,78x empata a
        # largura e mantém os textos dentro dos painéis.
        familia = "pixel_negrito" if negrito else "pixel"
        tamanho = max(8, int(round(tamanho * 0.78)))
        negrito = False
    chave = (familia, int(tamanho), bool(negrito))
    if chave not in _FONTES:
        _FONTES[chave] = _carregar_fonte(familia, tamanho, negrito)
    return _FONTES[chave]


_FONTES_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "assets" / "fonts"
_ARQUIVOS_FONTE = {
    "inter": "Inter.ttf",
    "cinzel": "Cinzel.ttf",
    "pixel": "Silkscreen-Regular.ttf",
    "pixel_negrito": "Silkscreen-Bold.ttf",
}


def familia_pixel(familia: str) -> bool:
    """Diz se esta família troca pela fonte de pixel quando a arte está ligada."""
    return familia == "inter"


# A Silkscreen não tem ícones; sem isto o texto mostra quadradinhos vazios.
_SIMBOLOS_PIXEL = {
    "◀": "<", "▶": ">", "▼": "v", "▲": "^",
    "←": "<", "→": ">", "⚠": "!", "★": "*", "☆": "*",
    "✦": "*", "✧": "*", "◆": "*", "●": "o", "✓": "v",
    "♥": "<3", "♦": "*", "⬥": "*", "•": "-",
}


def texto_seguro(conteudo: str) -> str:
    """Troca símbolos que a fonte de pixel não tem por equivalentes em ASCII."""
    if not pixel_arte.ATIVO:
        return conteudo
    return "".join(_SIMBOLOS_PIXEL.get(c, c) for c in conteudo)


def _carregar_fonte(familia: str, tamanho: int, negrito: bool) -> pygame.font.Font:
    arquivo = _ARQUIVOS_FONTE.get(familia)
    try:
        if arquivo is None:
            raise FileNotFoundError(familia)
        fonte_carregada = pygame.font.Font(str(_FONTES_DIR / arquivo), tamanho)
        fonte_carregada.set_bold(negrito)
        return fonte_carregada
    except (FileNotFoundError, OSError, pygame.error):
        return pygame.font.SysFont("segoeui", tamanho, bold=negrito)


def texto(
    surf: pygame.Surface,
    conteudo: object,
    pos: Sequence[float],
    tamanho: int = 18,
    cor: Sequence[int] = TEXTO,
    negrito: bool = False,
    alinhamento: str = "left",
    sombra: bool = True,
    familia: str = "inter",
    largura_max: int | None = None,
) -> pygame.Rect:
    """Desenha texto com sombra suave e retorna o retângulo ocupado."""
    txt = str(conteudo)
    suave = not (pixel_arte.ATIVO and familia_pixel(familia))
    if not suave:
        txt = texto_seguro(txt)
    f = fonte(tamanho, negrito, familia)
    if largura_max is not None:
        while tamanho > 6 and f.size(txt)[0] > largura_max:
            tamanho -= 1
            f = fonte(tamanho, negrito, familia)
        # a fonte de pixel não desce de 8 px: aí só resta encurtar o texto
        while len(txt) > 2 and f.size(txt)[0] > largura_max:
            txt = txt[:-1].rstrip()
        if f.size(txt)[0] > largura_max and len(txt) <= 2:
            txt = txt[:1]
    imagem = f.render(txt, suave, tuple(cor[:3]))
    rect = imagem.get_rect()
    x, y = int(pos[0]), int(pos[1])
    if alinhamento == "center":
        rect.midtop = (x, y)
    elif alinhamento == "right":
        rect.topright = (x, y)
    elif alinhamento == "midleft":
        rect.midleft = (x, y)
    elif alinhamento == "midright":
        rect.midright = (x, y)
    elif alinhamento == "center_all":
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    if sombra:
        sombra_img = f.render(txt, suave, (0, 0, 0))
        surf.blit(sombra_img, (rect.x + 1, rect.y + 2))
    surf.blit(imagem, rect)
    return rect


def texto_contornado(
    surf: pygame.Surface,
    conteudo: object,
    pos: Sequence[float],
    tamanho: int,
    cor: Sequence[int],
    contorno: Sequence[int] = (8, 10, 14),
    negrito: bool = True,
    alinhamento: str = "center",
) -> pygame.Rect:
    if pixel_arte.ATIVO:
        texto_px = texto_seguro(str(conteudo))
        f = fonte(max(10, int(round(tamanho * 0.70))), False, "pixel_negrito")
        imagem = f.render(texto_px, False, tuple(cor[:3]))
        borda = f.render(texto_px, False, tuple(contorno[:3]))
        rect = imagem.get_rect()
        x, y = int(pos[0]), int(pos[1])
        if alinhamento == "center":
            rect.midtop = (x, y)
        elif alinhamento == "right":
            rect.topright = (x, y)
        elif alinhamento == "center_all":
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            surf.blit(borda, (rect.x + dx, rect.y + dy))
        surf.blit(imagem, rect)
        return rect
    f = fonte(tamanho, negrito, "cinzel")
    imagem = f.render(str(conteudo), True, tuple(cor[:3]))
    borda = f.render(str(conteudo), True, tuple(contorno[:3]))
    rect = imagem.get_rect()
    x, y = int(pos[0]), int(pos[1])
    if alinhamento == "center":
        rect.midtop = (x, y)
    elif alinhamento == "right":
        rect.topright = (x, y)
    elif alinhamento == "center_all":
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)):
        surf.blit(borda, (rect.x + dx, rect.y + dy))
    surf.blit(imagem, rect)
    return rect


def etiqueta(
    surf: pygame.Surface,
    conteudo: object,
    centro: Sequence[float],
    tamanho: int = 10,
    cor: Sequence[int] = (230, 236, 246),
) -> pygame.Rect:
    """Texto curto com fundo translúcido, usado para nomes acima de inimigos."""
    f = fonte(tamanho, True)
    imagem = f.render(str(conteudo), True, tuple(cor[:3]))
    r = imagem.get_rect(center=(int(centro[0]), int(centro[1])))
    fundo = pygame.Surface((r.width + 10, r.height + 5), pygame.SRCALPHA)
    pygame.draw.rect(fundo, (8, 10, 16, 165), fundo.get_rect(), border_radius=5)
    surf.blit(fundo, (r.x - 5, r.y - 2))
    surf.blit(imagem, r)
    return r


# --------------------------------------------------------------------------
# formas
# --------------------------------------------------------------------------


def painel(
    surf: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    alpha: int = 228,
    cor: Sequence[int] = PAINEL,
    borda: Sequence[int] | None = BORDA,
    raio: int = 14,
    largura_borda: int = 2,
) -> pygame.Rect:
    if pixel_arte.ATIVO:
        from pixel_ui import painel as _painel_pixel
        return _painel_pixel(surf, rect, alpha, cor, borda, raio, largura_borda)
    r = pygame.Rect(rect)
    temp = pygame.Surface(r.size, pygame.SRCALPHA)
    pygame.draw.rect(temp, cor_com_alpha(cor, alpha), temp.get_rect(), border_radius=raio)
    # brilho interno superior
    brilho = pygame.Surface((max(1, r.width - 8), max(1, r.height // 3)), pygame.SRCALPHA)
    pygame.draw.rect(brilho, (255, 255, 255, 8), brilho.get_rect(), border_radius=raio)
    temp.blit(brilho, (4, 3))
    if borda is not None:
        pygame.draw.rect(temp, cor_com_alpha(borda, 255), temp.get_rect(), width=largura_borda, border_radius=raio)
    surf.blit(temp, r.topleft)
    return r


def raio_ui(raio: int) -> int:
    """Zera os cantos arredondados quando a arte pixel está ligada."""
    return 0 if pixel_arte.ATIVO else int(raio)


def modo_pixel() -> bool:
    """Atalho para saber se a arte pixel experimental está ligada."""
    return bool(pixel_arte.ATIVO)


def cantos_ornamentados(
    surf: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    cor: Sequence[int] = (232, 192, 112),
    tamanho: int = 14,
) -> None:
    """Cantos dourados em L, para dar acabamento de fantasia aos painéis."""
    if pixel_arte.ATIVO:
        from pixel_ui import cantos_ornamentados as _cantos_pixel
        _cantos_pixel(surf, rect, cor, tamanho)
        return
    r = pygame.Rect(rect)
    cor = tuple(cor[:3])
    for cx, cy, dx, dy in (
        (r.x + 6, r.y + 6, 1, 1),
        (r.right - 6, r.y + 6, -1, 1),
        (r.x + 6, r.bottom - 6, 1, -1),
        (r.right - 6, r.bottom - 6, -1, -1),
    ):
        pygame.draw.line(surf, cor, (cx, cy), (cx + tamanho * dx, cy), 2)
        pygame.draw.line(surf, cor, (cx, cy), (cx, cy + (tamanho - 4) * dy), 2)
        pygame.draw.circle(surf, cor, (cx, cy), 2)


def barra(
    surf: pygame.Surface,
    rect: pygame.Rect | Sequence[int],
    valor: float,
    maximo: float,
    cor: Sequence[int],
    fundo: Sequence[int] = (18, 22, 30),
    borda: Sequence[int] = (0, 0, 0),
    rotulo: str | None = None,
    tamanho_fonte: int = 12,
    raio: int | None = None,
) -> pygame.Rect:
    r = pygame.Rect(rect)
    if pixel_arte.ATIVO:
        from pixel_ui import barra as _barra_pixel
        return _barra_pixel(
            surf, r, valor, maximo, cor, fundo, borda, rotulo, tamanho_fonte, raio,
        )
    if raio is None:
        raio = r.height // 2
    pygame.draw.rect(surf, tuple(fundo[:3]), r, border_radius=raio)
    if maximo > 0 and valor > 0:
        w = int(r.width * clamp(valor / maximo, 0.0, 1.0))
        if w >= 2:
            preenchimento = pygame.Rect(r.x, r.y, w, r.height)
            pygame.draw.rect(surf, tuple(cor[:3]), preenchimento, border_radius=raio)
            # faixa de brilho no topo
            if r.height >= 5:
                brilho = pygame.Rect(r.x + 2, r.y + 1, max(1, w - 4), max(1, r.height // 3))
                pygame.draw.rect(
                    surf,
                    tuple(int(clamp(c + 55, 0, 255)) for c in cor[:3]),
                    brilho,
                    border_radius=max(1, brilho.height // 2),
                )
    pygame.draw.rect(surf, tuple(borda[:3]), r, width=1, border_radius=raio)
    if rotulo:
        texto(
            surf, rotulo, (r.centerx, r.centery - tamanho_fonte // 2),
            tamanho_fonte, BRANCO, negrito=True, alinhamento="center", sombra=True,
        )
    return r


_HALO_BASE: pygame.Surface | None = None
_HALO_CACHE: dict[tuple[int, int, int, int, int], pygame.Surface] = {}
_HALO_PIXEL: dict[tuple[int, tuple[int, int, int], int], pygame.Surface] = {}


def _halo_pixel(
    surf: pygame.Surface,
    centro: Sequence[float],
    raio: float,
    cor: Sequence[int],
    alpha: int,
) -> None:
    """Halo em três anéis chapados, sem gradiente (modo pixel)."""
    raio = max(2, int(raio))
    cor = (int(cor[0]), int(cor[1]), int(cor[2]))
    alpha = max(1, int(alpha))
    chave = (raio, cor, alpha)
    halo = _HALO_PIXEL.get(chave)
    if halo is None:
        halo = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
        for f, peso in ((1.0, 0.35), (0.68, 0.65), (0.40, 1.0)):
            pygame.draw.circle(
                halo, (*cor, max(1, int(alpha * peso))), (raio + 1, raio + 1),
                max(2, int(raio * f)),
            )
        if len(_HALO_PIXEL) > 256:
            _HALO_PIXEL.clear()
        _HALO_PIXEL[chave] = halo
    surf.blit(halo, (int(centro[0]) - raio - 1, int(centro[1]) - raio - 1))


def _halo_base() -> pygame.Surface:
    global _HALO_BASE
    if _HALO_BASE is None:
        n = 64
        _HALO_BASE = pygame.Surface((n, n), pygame.SRCALPHA)
        for y in range(n):
            for x in range(n):
                dx = (x + 0.5) / (n / 2) - 1.0
                dy = (y + 0.5) / (n / 2) - 1.0
                d = math.hypot(dx, dy)
                if d <= 1.0:
                    _HALO_BASE.set_at((x, y), (255, 255, 255, int(255 * (1.0 - d) ** 2)))
    return _HALO_BASE


def halo_suave(
    surf: pygame.Surface,
    centro: Sequence[float],
    raio: float,
    cor: Sequence[int],
    alpha: int = 90,
) -> None:
    """Halo radial com bordas realmente suaves (sem disco sólido)."""
    if pixel_arte.ATIVO:
        _halo_pixel(surf, centro, raio, cor, alpha)
        return
    raio = max(2, int(raio))
    chave = (int(cor[0]), int(cor[1]), int(cor[2]), int(alpha), raio)
    halo = _HALO_CACHE.get(chave)
    if halo is None:
        base = _halo_base().copy()
        base.fill(
            (int(cor[0]), int(cor[1]), int(cor[2]), int(alpha)),
            special_flags=pygame.BLEND_RGBA_MULT,
        )
        halo = pygame.transform.smoothscale(base, (raio * 2, raio * 2))
        if len(_HALO_CACHE) > 256:
            _HALO_CACHE.clear()
        _HALO_CACHE[chave] = halo
    surf.blit(halo, (int(centro[0]) - raio, int(centro[1]) - raio))


def circulo_brilhante(
    surf: pygame.Surface,
    centro: Sequence[float],
    raio: float,
    cor: Sequence[int],
    alpha: int = 90,
    camadas: int = 4,
) -> None:
    """Compatibilidade: halo suave desenhado em uma superfície temporária."""
    halo_suave(surf, centro, raio, cor, alpha)


def gradiente_vertical(tamanho: tuple[int, int], topo: Sequence[int], base: Sequence[int]) -> pygame.Surface:
    w, h = max(1, int(tamanho[0])), max(1, int(tamanho[1]))
    coluna = pygame.Surface((1, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        coluna.set_at((0, y), tuple(int(lerp(topo[i], base[i], t)) for i in range(3)))
    return pygame.transform.scale(coluna, (w, h))


def linha_grossa(
    surf: pygame.Surface,
    cor: Sequence[int],
    inicio: Sequence[float],
    fim: Sequence[float],
    largura: int = 4,
) -> None:
    pygame.draw.line(surf, tuple(cor[:3]), (int(inicio[0]), int(inicio[1])), (int(fim[0]), int(fim[1])), largura)


# --------------------------------------------------------------------------
# sombras
# --------------------------------------------------------------------------

_SOMBRA_BASE: pygame.Surface | None = None
_SOMBRA_CACHE: dict[tuple[int, int, int], pygame.Surface] = {}
_SOMBRA_PIXEL: dict[tuple[int, int, int], pygame.Surface] = {}


def _sombra_base() -> pygame.Surface:
    global _SOMBRA_BASE
    if _SOMBRA_BASE is None:
        s = pygame.Surface((64, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 90), s.get_rect())
        _SOMBRA_BASE = s
    return _SOMBRA_BASE


def _sombra_pixel(surf: pygame.Surface, x: float, y: float, rx: float, ry: float, alpha: int) -> None:
    """Sombra em três anéis, sem gradiente: combina com a arte pixel."""
    largura = max(4, int(rx * 2))
    altura = max(4, int(ry * 2))
    chave = (largura, altura, int(alpha))
    img = _SOMBRA_PIXEL.get(chave)
    if img is None:
        img = pygame.Surface((largura, altura), pygame.SRCALPHA)
        for f, peso in ((1.0, 0.34), (0.72, 0.55), (0.44, 0.85)):
            w = max(2, int(largura * f))
            h = max(2, int(altura * f))
            pygame.draw.ellipse(
                img, (0, 0, 0, int(alpha * peso)),
                ((largura - w) // 2, (altura - h) // 2, w, h),
            )
        _SOMBRA_PIXEL[chave] = img
    surf.blit(img, (int(x - rx), int(y - ry)))


def sombra(surf: pygame.Surface, x: float, y: float, rx: float, ry: float, alpha: int = 90) -> None:
    if pixel_arte.ATIVO:
        _sombra_pixel(surf, x, y, rx, ry, alpha)
        return
    chave = (max(4, int(rx * 2)), max(4, int(ry * 2)), int(alpha))
    img = _SOMBRA_CACHE.get(chave)
    if img is None:
        img = pygame.transform.smoothscale(_sombra_base(), chave[:2])
        img.set_alpha(int(alpha))
        _SOMBRA_CACHE[chave] = img
    surf.blit(img, (int(x - rx), int(y - ry)))


# --------------------------------------------------------------------------
# luz
# --------------------------------------------------------------------------

_LUZ_CACHE: dict[tuple[int, tuple[int, int, int], int, bool], pygame.Surface] = {}


def superficie_luz(raio: int, cor: Sequence[int] = (255, 236, 190), intensidade: int = 150) -> pygame.Surface:
    pixel = pixel_arte.ATIVO
    chave = (int(raio), tuple(int(c) for c in cor[:3]), int(intensidade), pixel)
    if chave not in _LUZ_CACHE:
        if pixel:
            # Degraus de luz, ampliados sem suavizar.
            n = 24
            base = pygame.Surface((n, n), pygame.SRCALPHA)
            for y in range(n):
                for x in range(n):
                    d = math.hypot(x - n / 2, y - n / 2) / (n / 2)
                    k = max(0.0, 1.0 - d) ** 2.2
                    k = round(k * 5) / 5
                    base.set_at((x, y), cor_com_alpha(cor, int(intensidade * k)))
            _LUZ_CACHE[chave] = pygame.transform.scale(base, (raio * 2, raio * 2))
        else:
            base = pygame.Surface((80, 80), pygame.SRCALPHA)
            for y in range(80):
                for x in range(80):
                    d = math.hypot(x - 40, y - 40) / 40.0
                    a = int(intensidade * max(0.0, 1.0 - d) ** 2.2)
                    base.set_at((x, y), cor_com_alpha(cor, a))
            _LUZ_CACHE[chave] = pygame.transform.smoothscale(base, (raio * 2, raio * 2))
    return _LUZ_CACHE[chave]


# --------------------------------------------------------------------------
# partículas
# --------------------------------------------------------------------------


class Particula:
    __slots__ = ("x", "y", "vx", "vy", "vida", "vida_max", "cor", "tamanho", "gravidade", "arrasto")

    def __init__(
        self, x: float, y: float, vx: float, vy: float, cor: Sequence[int],
        tamanho: float, vida: float, gravidade: float = 0.0, arrasto: float = 2.0,
    ) -> None:
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.cor = tuple(cor[:3])
        self.tamanho = tamanho
        self.vida = vida
        self.vida_max = vida
        self.gravidade = gravidade
        self.arrasto = arrasto


class SistemaParticulas:
    def __init__(self, maximo: int = 900) -> None:
        self.lista: list[Particula] = []
        self.maximo = maximo

    def emitir(
        self, x: float, y: float, cor: Sequence[int], quantidade: int = 8,
        velocidade: float = 90.0, tamanho: float = 4.0, vida: float = 0.55,
        gravidade: float = 0.0, espalhar: float = math.tau, direcao: float | None = None,
        arrasto: float = 2.5,
    ) -> None:
        if len(self.lista) + quantidade > self.maximo:
            quantidade = max(0, self.maximo - len(self.lista))
        for _ in range(quantidade):
            ang = random.uniform(0, espalhar) + (direcao if direcao is not None else 0.0)
            vel = random.uniform(velocidade * 0.35, velocidade)
            self.lista.append(
                Particula(
                    x, y, math.cos(ang) * vel, math.sin(ang) * vel,
                    cor, random.uniform(tamanho * 0.5, tamanho),
                    random.uniform(vida * 0.6, vida), gravidade, arrasto,
                )
            )

    def emitir_direcional(
        self, x: float, y: float, cor: Sequence[int], direcao: float,
        quantidade: int = 6, velocidade: float = 120.0, tamanho: float = 4.0, vida: float = 0.4,
    ) -> None:
        self.emitir(
            x, y, cor, quantidade, velocidade, tamanho, vida,
            espalhar=0.9, direcao=direcao,
        )

    def update(self, dt: float) -> None:
        vivos: list[Particula] = []
        for p in self.lista:
            p.vida -= dt
            if p.vida <= 0:
                continue
            p.vy += p.gravidade * dt
            p.vx -= p.vx * p.arrasto * dt
            p.vy -= p.vy * p.arrasto * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            vivos.append(p)
        self.lista = vivos

    def draw(self, surf: pygame.Surface, camera: "Camera") -> None:
        pixel = pixel_arte.ATIVO
        for p in self.lista:
            sx, sy = camera.aplicar((p.x, p.y))
            if sx < -30 or sy < -30 or sx > LARGURA + 30 or sy > ALTURA + 30:
                continue
            t = clamp(p.vida / p.vida_max, 0.0, 1.0)
            cor = cor_multiplicada(p.cor, 0.35 + 0.65 * t)
            raio = max(1, int(p.tamanho * (0.5 + 0.5 * t)))
            if pixel:
                # Quadradinhos na grade de 2 px, como o resto da arte pixel.
                lado = max(2, min(6, raio))
                lado -= lado % 2
                x = (int(sx) - lado // 2) & ~1
                y = (int(sy) - lado // 2) & ~1
                surf.fill(cor, (x, y, lado, lado))
            else:
                pygame.draw.circle(surf, cor, (int(sx), int(sy)), raio)


class TextoFlutuante:
    def __init__(
        self, x: float, y: float, conteudo: str, cor: Sequence[int] = BRANCO,
        tamanho: int = 18, vida: float = 0.9, vy: float = -55.0, negrito: bool = True,
    ) -> None:
        self.x, self.y = x, y
        self.conteudo = conteudo
        self.cor = tuple(cor[:3])
        self.tamanho = tamanho
        self.vida = vida
        self.vida_max = vida
        self.vy = vy
        self.negrito = negrito

    def update(self, dt: float) -> None:
        self.vida -= dt
        self.y += self.vy * dt
        self.vy += 55 * dt

    def draw(self, surf: pygame.Surface, camera: "Camera") -> None:
        if self.vida <= 0:
            return
        sx, sy = camera.aplicar((self.x, self.y))
        alpha = int(255 * clamp(self.vida / self.vida_max, 0.0, 1.0))
        cor = tuple(int(c * (0.5 + 0.5 * alpha / 255)) for c in self.cor)
        decorrido = 1.0 - clamp(self.vida / self.vida_max, 0.0, 1.0)
        escala = 1.0 + 0.45 * max(0.0, 1.0 - decorrido * 7.0)
        tamanho = max(6, int(self.tamanho * escala))
        texto(surf, self.conteudo, (sx, sy), tamanho, cor, self.negrito, "center", True)


# --------------------------------------------------------------------------
# câmera
# --------------------------------------------------------------------------


class Camera:
    def __init__(self, largura: int, altura: int) -> None:
        self.largura, self.altura = largura, altura
        self.x = 0.0
        self.y = 0.0
        self.ox = 0.0
        self.oy = 0.0
        self.shake_t = 0.0
        self.shake_forca = 0.0

    def seguir(self, alvo: Sequence[float], dt: float, limites: tuple[float, float, float, float]) -> None:
        alvo_x = alvo[0] - self.largura / 2
        alvo_y = alvo[1] - self.altura / 2
        fator = min(1.0, dt * 7.0)
        self.x = lerp(self.x, alvo_x, fator)
        self.y = lerp(self.y, alvo_y, fator)
        min_x, min_y, max_x, max_y = limites
        self.x = clamp(self.x, min_x, max(min_x, max_x - self.largura))
        self.y = clamp(self.y, min_y, max(min_y, max_y - self.altura))

        if self.shake_t > 0:
            self.shake_t -= dt
            intensidade = self.shake_forca * max(0.0, self.shake_t / 0.35)
            self.ox = random.uniform(-intensidade, intensidade)
            self.oy = random.uniform(-intensidade, intensidade)
        else:
            self.ox = self.oy = 0.0

    def tremer(self, forca: float = 8.0, tempo: float = 0.25) -> None:
        self.shake_forca = max(self.shake_forca, forca)
        self.shake_t = max(self.shake_t, tempo)

    def aplicar(self, pos: Sequence[float]) -> tuple[float, float]:
        return (pos[0] - self.x + self.ox, pos[1] - self.y + self.oy)

    def mundo(self, pos: Sequence[float]) -> tuple[float, float]:
        return (pos[0] + self.x - self.ox, pos[1] + self.y - self.oy)

    def visivel(self, x: float, y: float, margem: float = 96.0) -> bool:
        return -margem <= x - self.x <= self.largura + margem and -margem <= y - self.y <= self.altura + margem
