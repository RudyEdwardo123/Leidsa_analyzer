"""Definición formal e inmutable de las reglas de los juegos de lotería LEIDSA."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class GameType(str, Enum):
    KINO_TV = "Kino TV"
    LOTO = "Loto"
    LOTO_POOL = "Loto Pool"
    QUINIELA = "Quiniela"
    PEGA_3_MAS = "Pega 3 Más"


@dataclass(frozen=True)
class GroupRule:
    """Reglas específicas para un grupo de números dentro de un sorteo.

    Attributes:
        name: Identificador del grupo ('main', 'plus', 'super_plus').
        count: Cantidad de números que aparecen en el resultado del sorteo.
        generation_count: Cantidad de números que selecciona el jugador.
            Si es None, se utiliza count.
        min_val: Valor entero mínimo permitido (inclusive).
        max_val: Valor entero máximo permitido (inclusive).
        allow_duplicates: Define si se permiten números repetidos dentro del grupo.
        is_ordered: Define si los números aparecen ordenados de menor a mayor en la fuente.
        fixed_width: Ancho de dígitos esperado al formatear o analizar.
        is_optional: Si True, el grupo puede no estar presente en algunas fuentes históricas.
    """

    name: str
    count: int
    min_val: int
    max_val: int
    allow_duplicates: bool = False
    is_ordered: bool = True
    fixed_width: int = 2
    is_optional: bool = False
    generation_count: Optional[int] = None


@dataclass(frozen=True)
class GameRule:
    """Definición formal de un juego de lotería completo.

    Attributes:
        game_type: Tipo de juego asignado.
        groups: Lista ordenada de grupos de números que componen el sorteo.
        has_positions: Si True, el orden representa posiciones independientes.
    """

    game_type: GameType
    groups: List[GroupRule]
    has_positions: bool = False

    def get_group(self, name: str) -> Optional[GroupRule]:
        """Obtiene la regla de un grupo específico por su nombre."""
        for group in self.groups:
            if group.name == name:
                return group
        return None


# Catálogo formal e inmutable de las reglas del dominio LEIDSA
GAME_RULES: Dict[GameType, GameRule] = {

    GameType.KINO_TV: GameRule(
        game_type=GameType.KINO_TV,
        groups=[
            GroupRule(
                name="main",
                count=20,
                min_val=1,
                max_val=84,
                allow_duplicates=False,
                is_ordered=True,
                fixed_width=2,
                is_optional=False,
                generation_count=10,
            )
        ],
        has_positions=False,
    ),

    GameType.LOTO: GameRule(
        game_type=GameType.LOTO,
        groups=[
            GroupRule(
                name="main",
                count=6,
                min_val=1,
                max_val=40,
                allow_duplicates=False,
                is_ordered=True,
                fixed_width=2,
                is_optional=False,
            ),
            GroupRule(
                name="plus",
                count=1,
                min_val=1,
                max_val=12,
                allow_duplicates=False,
                is_ordered=False,
                fixed_width=2,
                is_optional=True,
            ),
            GroupRule(
                name="super_plus",
                count=1,
                min_val=1,
                max_val=15,
                allow_duplicates=False,
                is_ordered=False,
                fixed_width=2,
                is_optional=True,
            ),
        ],
        has_positions=False,
    ),

    GameType.LOTO_POOL: GameRule(
        game_type=GameType.LOTO_POOL,
        groups=[
            GroupRule(
                name="main",
                count=5,
                min_val=0,
                max_val=31,
                allow_duplicates=False,
                is_ordered=True,
                fixed_width=2,
                is_optional=False,
            )
        ],
        has_positions=False,
    ),

    GameType.QUINIELA: GameRule(
        game_type=GameType.QUINIELA,
        groups=[
            GroupRule(
                name="main",
                count=3,
                min_val=0,
                max_val=99,
                allow_duplicates=True,
                is_ordered=False,
                fixed_width=2,
                is_optional=False,
            )
        ],
        has_positions=True,
    ),

    GameType.PEGA_3_MAS: GameRule(
        game_type=GameType.PEGA_3_MAS,
        groups=[
            GroupRule(
                name="main",
                count=3,
                min_val=0,
                max_val=99,
                allow_duplicates=True,
                is_ordered=False,
                fixed_width=2,
                is_optional=False,
            )
        ],
        has_positions=True,
    ),
}


# Mapeo para normalizar nombres variables provenientes de fuentes externas (ej. Yelu)
RAW_NAME_MAPPING: Dict[str, GameType] = {
    "kino tv": GameType.KINO_TV,
    "kinotv": GameType.KINO_TV,
    "kino": GameType.KINO_TV,

    "loto pool": GameType.LOTO_POOL,
    "lotopool": GameType.LOTO_POOL,

    "quiniela": GameType.QUINIELA,
    "quiniela palé": GameType.QUINIELA,
    "quinielapale": GameType.QUINIELA,
    "pale": GameType.QUINIELA,

    "loto": GameType.LOTO,
    "loto más": GameType.LOTO,
    "loto mas": GameType.LOTO,
    "súper más": GameType.LOTO,
    "super mas": GameType.LOTO,
    "loto más domingo": GameType.LOTO,
    "loto mas domingo": GameType.LOTO,
    "loto más jueves": GameType.LOTO,
    "loto mas jueves": GameType.LOTO,
}


def normalize_game_name(raw_name: str) -> Optional[GameType]:
    """Mapea una cadena arbitraria de juego a su GameType correspondiente."""
    cleaned = raw_name.strip().lower()
    return RAW_NAME_MAPPING.get(cleaned)


def get_game_rule(game_type: GameType) -> GameRule:
    """Obtiene la definición formal de reglas para un GameType."""
    if game_type not in GAME_RULES:
        raise ValueError(f"Juego no soportado: {game_type}")
    return GAME_RULES[game_type]