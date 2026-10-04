"""Módulo para la generación de jugadas candidatas basadas en criterios estadísticos."""

import random
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Optional

from app.analysis.statistics import compute_frequencies, compute_overdue
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GAME_RULES, GameRule, GameType


class GenerationStrategy(str, Enum):
    """Estrategias de selección estadística para la generación de combinaciones."""

    RANDOM_UNIFORM = "random_uniform"
    HOT_NUMBERS = "hot_numbers"
    COLD_OVERDUE = "cold_overdue"
    BALANCED = "balanced"


DISCLAIMER_TEXT = (
    "IMPORTANTE: Esta combinación ha sido generada exclusivamente mediante análisis "
    "estadístico de datos históricos. NO constituye una predicción garantizada ni asegura "
    "la obtención de premios en sorteos futuros."
)


@dataclass
class GeneratedPlay:
    """Representación de una jugada generada con su contexto y aviso metodológico."""

    draw_data: DrawData
    strategy: GenerationStrategy
    disclaimer: str = DISCLAIMER_TEXT


class PlayGenerator:
    """Generador de combinaciones que respeta estrictamente la estructura de cada sorteo."""

    def generate_play(
        self,
        game_type: GameType,
        strategy: GenerationStrategy = GenerationStrategy.BALANCED,
        historical_draws: Optional[List[DrawData]] = None,
    ) -> GeneratedPlay:
        """Genera una combinación válida para el juego especificado."""

        rule: GameRule = GAME_RULES.get(game_type)

        if not rule:
            raise ValueError(f"Juego no soportado: {game_type}")

        numbers: List[DrawNumber] = []

        for group_rule in rule.groups:
            selected_vals = self._select_group_numbers(
                group_rule=group_rule,
                strategy=strategy,
                draws=historical_draws or [],
                has_positions=rule.has_positions,
            )

            # Asignar posiciones en juegos posicionales (ej. Quiniela)
            for idx, val in enumerate(selected_vals):
                position = (idx + 1) if rule.has_positions else None

                numbers.append(
                    DrawNumber(
                        value=val,
                        role=group_rule.name,
                        position=position,
                    )
                )

        draw_data = DrawData(
            game=game_type,
            draw_date=date.today(),
            numbers=numbers,
            source="Generator",
            variant=f"Estrategia: {strategy.value}",
        )

        return GeneratedPlay(
            draw_data=draw_data,
            strategy=strategy,
        )

    def _select_group_numbers(
        self,
        group_rule,
        strategy: GenerationStrategy,
        draws: List[DrawData],
        has_positions: bool,
    ) -> List[int]:
        """Selecciona los enteros para un grupo específico según la regla y la estrategia."""

        valid_range = list(
            range(
                group_rule.min_val,
                group_rule.max_val + 1,
            )
        )

        # Para la generación se utiliza generation_count cuando está definido.
        # Si no está definido, se utiliza count.
        count = (
            group_rule.generation_count
            if group_rule.generation_count is not None
            else group_rule.count
        )

        if strategy == GenerationStrategy.RANDOM_UNIFORM or not draws:
            if group_rule.allow_duplicates:
                selected = [
                    random.choice(valid_range)
                    for _ in range(count)
                ]
            else:
                selected = random.sample(
                    valid_range,
                    count,
                )

            return (
                sorted(selected)
                if group_rule.is_ordered
                else selected
            )

        freqs = compute_frequencies(
            draws,
            role=group_rule.name,
        )

        overdues = compute_overdue(
            draws,
            min_val=group_rule.min_val,
            max_val=group_rule.max_val,
            role=group_rule.name,
        )

        weights = []

        for val in valid_range:
            f = freqs.get(val, 0)
            o = overdues.get(val) or 0

            if strategy == GenerationStrategy.HOT_NUMBERS:
                weight = f + 1.0

            elif strategy == GenerationStrategy.COLD_OVERDUE:
                weight = o + 1.0

            else:
                # BALANCED
                weight = (
                    (f * 0.5)
                    + (o * 0.5)
                    + 1.0
                )

            weights.append(weight)

        selected: List[int] = []

        if group_rule.allow_duplicates:
            selected = random.choices(
                valid_range,
                weights=weights,
                k=count,
            )

        else:
            # Muestra ponderada sin reemplazo
            available = list(valid_range)
            curr_weights = list(weights)

            for _ in range(count):
                chosen = random.choices(
                    available,
                    weights=curr_weights,
                    k=1,
                )[0]

                idx = available.index(chosen)

                selected.append(chosen)

                available.pop(idx)
                curr_weights.pop(idx)

        return (
            sorted(selected)
            if group_rule.is_ordered
            else selected
        )