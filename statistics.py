"""Módulo de análisis estadístico descriptivo para sorteos de LEIDSA."""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from app.models.draw import DrawData
from app.rules.game_rules import GAME_RULES, GameType


@dataclass
class NumberStats:
    """Estadísticas consolidadas para un número individual dentro de un grupo/rol."""

    number: int
    absolute_frequency: int
    relative_frequency: float
    draws_since_last: Optional[int]  # Cantidad de sorteos transcurridos desde su última aparición (0 = salió en el más reciente)


def filter_draws_by_days(
    draws: List[DrawData], days: int, reference_date: Optional[date] = None
) -> List[DrawData]:
    """Filtra sorteos dentro de los últimos N días respecto a una fecha de referencia."""
    if not draws:
        return []
    ref = reference_date or max(d.draw_date for d in draws)
    cutoff = ref - timedelta(days=days)
    return [d for d in draws if cutoff <= d.draw_date <= ref]


def compute_frequencies(
    draws: List[DrawData], role: str = "main"
) -> Dict[int, int]:
    """Calcula la frecuencia absoluta de aparición para cada número en un rol específico."""
    counts: Counter = Counter()
    for d in draws:
        nums = d.get_numbers_by_role(role)
        counts.update(nums)
    return dict(counts)


def compute_overdue(
    draws: List[DrawData],
    min_val: int,
    max_val: int,
    role: str = "main",
) -> Dict[int, Optional[int]]:
    """Calcula el atraso (cantidad de sorteos transcurridos desde la última aparición).

    Retorna un diccionario mapeando cada número dentro del rango a la cantidad
    de sorteos transcurridos. Si nunca ha salido en el histórico proporcionado, el valor será None.
    """
    sorted_draws = sorted(draws, key=lambda x: x.draw_date, reverse=True)
    overdue: Dict[int, Optional[int]] = {
        val: None for val in range(min_val, max_val + 1)
    }

    for idx, d in enumerate(sorted_draws):
        nums = d.get_numbers_by_role(role)
        for val in nums:
            if min_val <= val <= max_val and overdue[val] is None:
                overdue[val] = idx

    return overdue


def compute_pairs(
    draws: List[DrawData], role: str = "main"
) -> Dict[Tuple[int, int], int]:
    """Calcula la frecuencia de coaparición de pares de números en el mismo sorteo."""
    pair_counts: Counter = Counter()
    for d in draws:
        nums = sorted(set(d.get_numbers_by_role(role)))
        for pair in combinations(nums, 2):
            pair_counts[pair] += 1
    return dict(pair_counts)


def compute_position_frequencies(
    draws: List[DrawData],
) -> Dict[int, Dict[int, int]]:
    """Calcula la frecuencia de números según su posición (para juegos posicionales como Quiniela)."""
    pos_counts: Dict[int, Counter] = {}
    for d in draws:
        for num in d.numbers:
            if num.position is not None:
                if num.position not in pos_counts:
                    pos_counts[num.position] = Counter()
                pos_counts[num.position][num.value] += 1
    return {pos: dict(counter) for pos, counter in pos_counts.items()}


def get_game_statistics(
    draws: List[DrawData],
    game_type: GameType,
    role: str = "main",
    days_window: Optional[int] = None,
) -> List[NumberStats]:
    """Genera métricas descriptivas consolidadas para el conjunto de números de un juego.

    Soporta filtrado por ventanas temporales (ej. últimos 30, 90, 180 días).
    """
    rule = GAME_RULES.get(game_type)
    if not rule:
        raise ValueError(f"Juego no soportado: {game_type}")

    group_rule = rule.get_group(role)
    if not group_rule:
        raise ValueError(f"Rol '{role}' no existe para {game_type}")

    target_draws = draws
    if days_window and draws:
        target_draws = filter_draws_by_days(draws, days=days_window)

    freqs = compute_frequencies(target_draws, role=role)
    overdues = compute_overdue(
        draws, min_val=group_rule.min_val, max_val=group_rule.max_val, role=role
    )

    total_draws = len(target_draws)
    stats: List[NumberStats] = []

    for val in range(group_rule.min_val, group_rule.max_val + 1):
        abs_freq = freqs.get(val, 0)
        rel_freq = (abs_freq / total_draws) if total_draws > 0 else 0.0
        stats.append(
            NumberStats(
                number=val,
                absolute_frequency=abs_freq,
                relative_frequency=rel_freq,
                draws_since_last=overdues.get(val),
            )
        )

    return stats