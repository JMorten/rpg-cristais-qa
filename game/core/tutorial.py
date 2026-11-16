"""Tutorial/onboarding: objetivos curtos e sequenciais, detectados pelo estado do jogador."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

DISTANCIA_MOVER = 160.0
SALTO_MAXIMO = 120.0
JANELA_CONFIRMAR_PULO = 3.0


@dataclass(frozen=True)
class Etapa:
    id: str
    titulo: str
    detalhe: str
    teclado: str
    controle: str
    teclado_painel: str = ""
    controle_painel: str = ""
    toque: str = ""
    toque_painel: str = ""


ETAPAS: tuple[Etapa, ...] = (
    Etapa(
        "mover", "Mova-se",
        "Explore a Clareira de Lumen.",
        "WASD ou setas", "Analógico esquerdo",
        toque="Arraste o joystick à esquerda",
    ),
    Etapa(
        "atacar", "Ataque",
        "Golpeie o ar ou uma criatura.",
        "Clique ou Espaço", "A ou RT",
        toque="Toque no botão grande de ataque",
    ),
    Etapa(
        "habilidade", "Use uma habilidade",
        "Cada classe tem quatro habilidades.",
        "Q, E, R ou F", "X, Y, B ou RB",
        toque="Toque em Q, E, R ou F",
    ),
    Etapa(
        "cristal", "Encaixe um cristal",
        "Cristais em equipamentos aumentam seus atributos.",
        "Abra o painel com I", "Abra o painel com Back",
        "Aba Cristais: selecione um cristal e clique num encaixe vazio",
        "Aba Cristais (LB/RB): selecione um cristal e confirme num encaixe vazio com A",
        toque="Toque no botão da mochila (I)",
        toque_painel="Aba Cristais: toque num cristal e depois num encaixe vazio",
    ),
    Etapa(
        "boss", "Derrote o primeiro boss",
        "Bosses raros surgem na Floresta de Lumen ao vencer criaturas.",
        "Enfrente o boss e fuja dos círculos de aviso",
        "Enfrente o boss e fuja dos círculos de aviso",
        toque="Enfrente o boss e fuja dos círculos de aviso",
    ),
)


def contar_cristais_encaixados(jogador: Any) -> int:
    total = 0
    for equipamento in jogador.equipamentos.values():
        if equipamento is not None:
            total += sum(1 for c in equipamento.sockets if c is not None)
    return total


class Tutorial:
    def __init__(self, concluido: bool = False) -> None:
        self.concluido = concluido
        self.indice = 0
        self._iniciada = False
        self._pos: tuple[float, float] | None = None
        self._distancia = 0.0
        self._tempo_ataque = 0.0
        self._cooldowns: dict[str, float] = {}
        self._encaixados = 0
        self._confirmar = 0.0

    # ------------------------------------------------------------------ estado
    @property
    def etapa(self) -> Etapa | None:
        if self.concluido or self.indice >= len(ETAPAS):
            return None
        return ETAPAS[self.indice]

    @property
    def total(self) -> int:
        return len(ETAPAS)

    @property
    def aguardando_confirmacao(self) -> bool:
        return self._confirmar > 0

    def progresso(self) -> float | None:
        """Fração 0..1 para etapas com medidor; None para as demais."""
        etapa = self.etapa
        if etapa is not None and etapa.id == "mover":
            return min(1.0, self._distancia / DISTANCIA_MOVER)
        return None

    def dica(self, controle: bool, painel_aberto: bool = False, toque: bool = False) -> str:
        etapa = self.etapa
        if etapa is None:
            return ""
        if toque:
            if painel_aberto and etapa.toque_painel:
                return etapa.toque_painel
            return etapa.toque or etapa.controle
        if painel_aberto and etapa.teclado_painel:
            return etapa.controle_painel if controle else etapa.teclado_painel
        return etapa.controle if controle else etapa.teclado

    # ------------------------------------------------------------------ controle
    def pular(self) -> None:
        self.concluido = True
        self._confirmar = 0.0

    def pedir_pular(self) -> bool:
        """Pede para pular; exige uma segunda chamada dentro da janela de confirmação."""
        if self.concluido:
            return False
        if self._confirmar > 0:
            self.pular()
            return True
        self._confirmar = JANELA_CONFIRMAR_PULO
        return False

    def reiniciar(self) -> None:
        self.concluido = False
        self.indice = 0
        self._iniciada = False
        self._confirmar = 0.0

    # ------------------------------------------------------------------ update
    def atualizar(self, dt: float, jogador: Any) -> list[str]:
        """Avança o tutorial; retorna mensagens para exibir ao jogador."""
        self._confirmar = max(0.0, self._confirmar - dt)
        if self.concluido:
            return []
        mensagens: list[str] = []
        if jogador.bosses > 0:
            self.concluido = True
            return ["Tutorial concluído!"]
        if not self._iniciada:
            mensagens += self._iniciar_etapa(jogador)

        etapa = self.etapa
        if etapa is not None and self._cumpriu(etapa, jogador):
            mensagens.append(f"Objetivo cumprido: {etapa.titulo}")
            mensagens += self._avancar(jogador)

        self._pos = (jogador.x, jogador.y)
        self._tempo_ataque = jogador.tempo_ataque
        self._cooldowns = dict(jogador.cooldowns)
        return mensagens

    def _avancar(self, jogador: Any) -> list[str]:
        self.indice += 1
        self._iniciada = False
        if self.indice >= len(ETAPAS):
            self.concluido = True
            return ["Tutorial concluído!"]
        return self._iniciar_etapa(jogador)

    def pular_etapa(self, jogador: Any) -> list[str]:
        """Pula a etapa atual (sem confirmação)."""
        if self.etapa is None:
            return []
        self._confirmar = 0.0
        return self._avancar(jogador)

    def _iniciar_etapa(self, jogador: Any) -> list[str]:
        self._iniciada = True
        self._distancia = 0.0
        self._pos = (jogador.x, jogador.y)
        self._tempo_ataque = jogador.tempo_ataque
        self._cooldowns = dict(jogador.cooldowns)
        etapa = self.etapa
        if etapa is not None and etapa.id == "cristal":
            mensagens = garantir_material_cristal(jogador)
            self._encaixados = contar_cristais_encaixados(jogador)
            return mensagens
        return []

    def _cumpriu(self, etapa: Etapa, jogador: Any) -> bool:
        if etapa.id == "mover":
            if self._pos is not None:
                passo = math.hypot(jogador.x - self._pos[0], jogador.y - self._pos[1])
                if passo < SALTO_MAXIMO:
                    self._distancia += passo
            return self._distancia >= DISTANCIA_MOVER
        if etapa.id == "atacar":
            return jogador.tempo_ataque > self._tempo_ataque
        if etapa.id == "habilidade":
            return any(
                valor > self._cooldowns.get(chave, 0.0) + 1e-6
                for chave, valor in jogador.cooldowns.items()
            )
        if etapa.id == "cristal":
            return contar_cristais_encaixados(jogador) > self._encaixados
        if etapa.id == "boss":
            return jogador.bosses > 0
        return False


def garantir_material_cristal(jogador: Any) -> list[str]:
    """Garante que dê para encaixar um cristal: um equipamento com encaixe livre e um cristal."""
    from items import SLOTS, Cristal, gerar_cristal, gerar_equipamento

    mensagens: list[str] = []
    if not any(e is not None and e.sockets_livres > 0 for e in jogador.equipamentos.values()):
        vazio = next((s for s in SLOTS if jogador.equipamentos[s] is None), "Anel")
        equipamento = gerar_equipamento(1, jogador.classe, slot=vazio, raridade="Raro")
        if jogador.adicionar_item(equipamento) and jogador.equipar(equipamento):
            mensagens.append(f"Você recebeu {equipamento.nome}, com um encaixe de cristal.")
    if not any(isinstance(i, Cristal) for i in jogador.inventario):
        cristal = gerar_cristal(tier=1)
        if jogador.adicionar_item(cristal):
            mensagens.append(f"Você recebeu um cristal: {cristal.nome}.")
    return mensagens
