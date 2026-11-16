"""Iluminação 2D em duas passadas: ambiente (multiply) + luzes (add).

Um único light map multiplicado só escurece: a área iluminada nunca fica mais
clara que a cor original da arte. Separando em duas passadas, a luz soma brilho
absoluto e o contraste funciona mesmo com a paleta escura do jogo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

import pixel_arte
from settings import ALTURA, LARGURA

_CACHE: dict[tuple[int, tuple[int, int, int], int, float], pygame.Surface] = {}
_CACHE_MAX = 192


@dataclass(frozen=True)
class Luz:
    """Fonte de luz pontual, em coordenadas de tela."""

    x: float
    y: float
    raio: int
    cor: tuple[int, int, int]
    intensidade: int


def gradiente_luz(raio: int, cor, intensidade: int, potencia: float = 1.9) -> pygame.Surface:
    """Gradiente radial com RGB em falloff e alpha 255 (para BLEND_ADD).

    Raio e intensidade são quantizados para o cache acertar entre frames —
    luzes pulsantes mudam de intensidade o tempo todo.
    """
    raio_q = max(8, (int(raio) // 8) * 8)
    intensidade_q = max(0, min(255, (int(intensidade) // 12) * 12))
    cor = tuple(int(c) for c in cor[:3])
    pixel = pixel_arte.ATIVO
    chave = (raio_q, cor, intensidade_q, round(potencia, 2), pixel)
    cache = _CACHE.get(chave)
    if cache is not None:
        return cache

    n = 96 if not pixel else max(32, min(120, raio_q // 2))
    niveis = 16
    base = pygame.Surface((n, n), pygame.SRCALPHA)
    for y in range(n):
        dy = (y + 0.5) / (n * 0.5) - 1.0
        for x in range(n):
            dx = (x + 0.5) / (n * 0.5) - 1.0
            d = math.hypot(dx, dy)
            if d >= 1.0:
                base.set_at((x, y), (0, 0, 0, 255))
                continue
            k = ((1.0 - d) ** potencia) * (intensidade_q / 255.0)
            if pixel:
                # Faixas de luz: o brilho vira degraus em vez de gradiente.
                k = round(k * niveis) / niveis
            base.set_at((x, y), (int(cor[0] * k), int(cor[1] * k), int(cor[2] * k), 255))

    if pixel:
        img = pygame.transform.scale(base, (raio_q * 2, raio_q * 2))
    else:
        img = pygame.transform.smoothscale(base, (raio_q * 2, raio_q * 2))
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[chave] = img
    return img


class Iluminacao:
    """Aplica ambiente e luzes reutilizando superfícies (sem alocar por frame)."""

    def __init__(self, largura: int = LARGURA, altura: int = ALTURA) -> None:
        self.largura = largura
        self.altura = altura
        self._ambiente = pygame.Surface((largura, altura))
        self._aditivo = pygame.Surface((largura, altura))
        self.bloom = True
        self.intensidade_bloom = 0.45
        self.limiar_bloom = 0.22
        self._bloom_frame = 0
        self._bloom_pequeno = pygame.Surface((largura // 8, altura // 8))
        self._bloom_borrado = pygame.Surface((largura // 8, altura // 8))
        self._bloom_grande = pygame.Surface((largura, altura))

    def desenhar(
        self,
        surf: pygame.Surface,
        luzes: list[Luz],
        ambiente: tuple[int, int, int] | None = None,
    ) -> None:
        if ambiente is not None:
            self._ambiente.fill(ambiente)
            surf.blit(self._ambiente, (0, 0), special_flags=pygame.BLEND_MULT)

        if not luzes:
            return

        self._aditivo.fill((0, 0, 0))
        for luz in luzes:
            img = gradiente_luz(luz.raio, luz.cor, luz.intensidade)
            r = img.get_width() // 2
            self._aditivo.blit(
                img,
                (int(luz.x - r), int(luz.y - r)),
                special_flags=pygame.BLEND_ADD,
            )

        surf.blit(self._aditivo, (0, 0), special_flags=pygame.BLEND_ADD)
        if self.bloom:
            # Bloom é suave: atualizar em 30 Hz economiza metade do custo.
            self._bloom_frame += 1
            if self._bloom_frame % 2 == 1:
                self._atualizar_bloom()
            surf.blit(self._bloom_grande, (0, 0), special_flags=pygame.BLEND_ADD)

    def _atualizar_bloom(self) -> None:
        """Borra o buffer aditivo em 1/8 e monta o halo em tamanho real."""
        pygame.transform.smoothscale(
            self._aditivo, self._bloom_pequeno.get_size(), self._bloom_pequeno
        )
        # Limiar: só o núcleo claro das luzes brilha, não a borda inteira.
        limiar = int(255 * self.limiar_bloom)
        self._bloom_pequeno.fill((limiar, limiar, limiar), special_flags=pygame.BLEND_SUB)
        pygame.transform.box_blur(
            self._bloom_pequeno, 4, dest_surface=self._bloom_borrado
        )
        if pixel_arte.ATIVO:
            pygame.transform.scale(
                self._bloom_borrado, (self.largura, self.altura), self._bloom_grande
            )
        else:
            pygame.transform.smoothscale(
                self._bloom_borrado, (self.largura, self.altura), self._bloom_grande
            )
        k = int(255 * self.intensidade_bloom)
        self._bloom_grande.fill((k, k, k), special_flags=pygame.BLEND_MULT)
