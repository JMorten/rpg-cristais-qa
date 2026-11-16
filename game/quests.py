"""Missões simples dadas por Mestre Aldrin na vila."""
from __future__ import annotations

from typing import Any

# item: ("pocao", tipo, quantidade) ou ("equipamento", raridade)
MISSOES: tuple[dict[str, Any], ...] = (
    {
        "id": "gosma",
        "nome": "Gosma para estudo",
        "descricao": "Mestre Aldrin quer entender por que os slimes prosperam na Clareira.",
        "tipo": "abate",
        "alvo": "slime",
        "rotulo": "Slimes abatidos",
        "quantidade": 6,
        "ouro": 60,
        "xp": 80,
        "item": ("pocao", "vida", 2),
    },
    {
        "id": "fragmentos",
        "nome": "Fragmentos para o altar",
        "descricao": "Cristais carregam memória. Traga alguns para o cronista estudar.",
        "tipo": "cristal",
        "alvo": "",
        "rotulo": "Cristais coletados",
        "quantidade": 4,
        "ouro": 120,
        "xp": 150,
        "item": ("equipamento", "Raro"),
    },
    {
        "id": "rei_slime",
        "nome": "O Rei do Lodo",
        "descricao": "O Rei Slime anda inquieto. Derrote-o para acalmar a Floresta.",
        "tipo": "boss",
        "alvo": "Rei Slime",
        "rotulo": "Rei Slime derrotado",
        "quantidade": 1,
        "ouro": 250,
        "xp": 400,
        "item": ("equipamento", "Épico"),
    },
    {
        "id": "veyra",
        "nome": "Rumo a Veyra",
        "descricao": "Dizem que o Pântano de Veyra guarda a origem dos cristais. Vá até lá.",
        "tipo": "visitar",
        "alvo": "Pântano de Veyra",
        "rotulo": "Pântano visitado",
        "quantidade": 1,
        "ouro": 400,
        "xp": 600,
        "item": ("equipamento", "Lendário"),
    },
    {
        "id": "rainha_lodo",
        "nome": "A Rainha do Lodo",
        "descricao": "A Rainha do Lodo devora os cristais do pântano. Encerre o ciclo.",
        "tipo": "boss",
        "alvo": "Rainha do Lodo",
        "rotulo": "Rainha do Lodo derrotada",
        "quantidade": 1,
        "ouro": 800,
        "xp": 1200,
        "item": ("equipamento", "Lendário"),
    },
    {
        "id": "coracao_aether",
        "nome": "O Coração de Aether",
        "descricao": "Além do Desfiladeiro, uma fenda pulsa com a origem dos cristais. Vá até lá.",
        "tipo": "visitar",
        "alvo": "Coração de Aether",
        "rotulo": "Coração visitado",
        "quantidade": 1,
        "ouro": 1400,
        "xp": 2000,
        "item": ("equipamento", "Lendário"),
    },
    {
        "id": "avatar_aether",
        "nome": "O Avatar de Aether",
        "descricao": "O guardião do Coração despertou. Derrote o Avatar e liberte a fonte.",
        "tipo": "boss",
        "alvo": "Avatar de Aether",
        "rotulo": "Avatar de Aether derrotado",
        "quantidade": 1,
        "ouro": 2200,
        "xp": 3200,
        "item": ("equipamento", "Lendário"),
    },
)


class Missoes:
    """Corrente linear de missões, com progresso persistido no save."""

    def __init__(self) -> None:
        self.indice = 0
        self.progresso = 0
        self.concluidas: list[str] = []
        self.avisada = False

    @property
    def atual(self) -> dict[str, Any] | None:
        if 0 <= self.indice < len(MISSOES):
            return MISSOES[self.indice]
        return None

    @property
    def completa(self) -> bool:
        missao = self.atual
        return missao is not None and self.progresso >= int(missao["quantidade"])

    def texto_progresso(self) -> str:
        missao = self.atual
        if missao is None:
            return "Todas as missões concluídas."
        if self.completa:
            return f"{missao['rotulo']} — concluída! Fale com Mestre Aldrin."
        if missao["tipo"] == "visitar":
            return f"Visite: {missao['alvo']}"
        return f"{missao['rotulo']}: {self.progresso}/{missao['quantidade']}"

    def _avancar(self, quantidade: int = 1) -> bool:
        """Soma progresso e devolve True quando a missão acabou de completar."""
        missao = self.atual
        if missao is None or self.completa:
            return False
        self.progresso = min(int(missao["quantidade"]), self.progresso + quantidade)
        if self.completa and not self.avisada:
            self.avisada = True
            return True
        return False

    def registrar_abate(self, tipo: str) -> bool:
        missao = self.atual
        if missao is None or missao["tipo"] != "abate" or missao["alvo"] != tipo:
            return False
        return self._avancar()

    def registrar_cristal(self) -> bool:
        missao = self.atual
        if missao is None or missao["tipo"] != "cristal":
            return False
        return self._avancar()

    def registrar_boss(self, nome: str) -> bool:
        missao = self.atual
        if missao is None or missao["tipo"] != "boss" or missao["alvo"] != nome:
            return False
        return self._avancar()

    def registrar_zona(self, nome: str) -> bool:
        missao = self.atual
        if missao is None or missao["tipo"] != "visitar" or missao["alvo"] != nome:
            return False
        return self._avancar()

    def entregar(self) -> dict[str, Any] | None:
        if not self.completa:
            return None
        missao = self.atual
        assert missao is not None
        self.concluidas.append(str(missao["id"]))
        self.indice += 1
        self.progresso = 0
        self.avisada = False
        return missao

    def to_dict(self) -> dict[str, Any]:
        return {
            "indice": self.indice,
            "progresso": self.progresso,
            "concluidas": list(self.concluidas),
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any] | None) -> "Missoes":
        estado = cls()
        if not dados:
            return estado
        estado.indice = max(0, min(len(MISSOES), int(dados.get("indice", 0))))
        estado.progresso = max(0, int(dados.get("progresso", 0)))
        estado.concluidas = [str(x) for x in dados.get("concluidas", [])]
        missao = estado.atual
        if missao is not None:
            estado.progresso = min(estado.progresso, int(missao["quantidade"]))
        estado.avisada = estado.completa
        return estado
