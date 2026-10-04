"""Modelos del dominio principal para el sistema LEIDSA Analyzer."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from app.rules.game_rules import GameType


@dataclass(frozen=True)
class DrawNumber:
    """Representa un número individual dentro de un sorteo.

    Attributes:
        value: Valor numérico entero.
        role: Rol del número dentro del sorteo ('main', 'plus', 'super_plus').
        position: Posición asignada cuando el juego depende de posiciones (1, 2, 3).
    """

    value: int
    role: str = "main"
    position: Optional[int] = None

    def formatted_value(self, width: int = 2) -> str:
        """Retorna el número formateado con ancho fijo rellenado con ceros a la izquierda."""
        return f"{self.value:0{width}d}"


@dataclass
class DrawData:
    """Representa la información completa de un sorteo histórico.

    Attributes:
        game: Tipo de juego al que pertenece el sorteo.
        draw_date: Fecha de celebración del sorteo.
        numbers: Lista de números que conforman el resultado.
        source: Nombre de la fuente de origen (ej. 'Yelu').
        variant: Variante descriptiva detectada (ej. 'Loto + Más + Súper Más').
        source_url: URL opcional de procedencia del registro.
    """

    game: GameType
    draw_date: date
    numbers: List[DrawNumber] = field(default_factory=list)
    source: str = "Yelu"
    variant: Optional[str] = None
    source_url: Optional[str] = None

    def get_numbers_by_role(self, role: str) -> List[int]:
        """Retorna la lista de valores enteros pertenecientes a un rol específico."""
        return [n.value for n in self.numbers if n.role == role]

    @property
    def main_numbers(self) -> List[int]:
        """Obtiene los números del grupo principal ('main')."""
        return self.get_numbers_by_role("main")

    @property
    def plus_number(self) -> Optional[int]:
        """Obtiene el valor del número 'plus' si existe."""
        nums = self.get_numbers_by_role("plus")
        return nums[0] if nums else None

    @property
    def super_plus_number(self) -> Optional[int]:
        """Obtiene el valor del número 'super_plus' si existe."""
        nums = self.get_numbers_by_role("super_plus")
        return nums[0] if nums else None

    def formatted_numbers_str(self, width: int = 2) -> str:
        """Devuelve una representación legible separada por espacios rellenados con ceros."""
        return " ".join([n.formatted_value(width=width) for n in self.numbers])

    def to_dict(self) -> Dict[str, Any]:
        """Serializa la entidad a un diccionario estructurado."""
        return {
            "game": self.game.value,
            "draw_date": self.draw_date.isoformat(),
            "numbers": [
                {"value": n.value, "role": n.role, "position": n.position}
                for n in self.numbers
            ],
            "source": self.source,
            "variant": self.variant,
            "source_url": self.source_url,
        }