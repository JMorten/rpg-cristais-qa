"""Ponto único de importação das entidades do jogo."""
from __future__ import annotations

from combat import AreaPerigo, Drop, Efeito, Projetil
from enemies import Inimigo
from player import Jogador

__all__ = ["Jogador", "Inimigo", "Projetil", "Drop", "AreaPerigo", "Efeito"]
