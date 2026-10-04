"""Motor de validación independiente para verificar la integridad de sorteos según las reglas del juego."""

from dataclasses import dataclass, field
from typing import List

from app.models.draw import DrawData
from app.rules.game_rules import GAME_RULES, GameRule, GroupRule


@dataclass
class ValidationResult:
    """Resultado de la validación de un sorteo.

    Attributes:
        is_valid: Indica si el sorteo cumple estrictamente con todas las reglas.
        errors: Lista de mensajes de error descriptivos cuando is_valid es False.
    """

    is_valid: bool
    errors: List[str] = field(default_factory=list)


def validate_draw(draw: DrawData) -> ValidationResult:
    """Valida un objeto DrawData contra la regla formal correspondiente a su juego.

    Args:
        draw: Entidad DrawData a validar.

    Returns:
        ValidationResult indicando si es válido y la lista de errores encontrados.
    """
    errors: List[str] = []

    game_rule: GameRule = GAME_RULES.get(draw.game)
    if not game_rule:
        return ValidationResult(
            is_valid=False, errors=[f"No existe regla configurada para el juego: {draw.game}"]
        )

    # Agrupar números por rol
    numbers_by_role = {}
    for num in draw.numbers:
        numbers_by_role.setdefault(num.role, []).append(num)

    for group_rule in game_rule.groups:
        role_name = group_rule.name
        nums_in_group = numbers_by_role.get(role_name, [])

        # 1. Validar presencia y cantidad de números
        if not nums_in_group:
            if not group_rule.is_optional:
                errors.append(f"Grupo '{role_name}': es obligatorio y no contiene números.")
            continue

        if len(nums_in_group) != group_rule.count:
            errors.append(
                f"Grupo '{role_name}': se esperaban {group_rule.count} números, pero se recibieron {len(nums_in_group)}."
            )

        values = [n.value for n in nums_in_group]

        # 2. Validar rango numérico (min_val, max_val)
        out_of_range = [
            val for val in values if val < group_rule.min_val or val > group_rule.max_val
        ]
        if out_of_range:
            for val in out_of_range:
                errors.append(
                    f"Grupo '{role_name}': el número {val} está fuera del rango {group_rule.min_val}-{group_rule.max_val}."
                )

        # 3. Validar duplicados si la regla los prohíbe
        if not group_rule.allow_duplicates:
            duplicates = [val for val in set(values) if values.count(val) > 1]
            if duplicates:
                errors.append(
                    f"Grupo '{role_name}': contiene números duplicados no permitidos: {sorted(duplicates)}."
                )

        # 4. Validar orden de menor a mayor si es requerido
        if group_rule.is_ordered and len(values) > 1:
            if values != sorted(values):
                errors.append(
                    f"Grupo '{role_name}': los números deben estar ordenados de menor a mayor."
                )

    # 5. Validar posiciones en juegos posicionales (ej. Quiniela)
    if game_rule.has_positions:
        positions = [n.position for n in draw.numbers if n.position is not None]
        expected_positions = list(range(1, len(draw.numbers) + 1))
        if sorted(positions) != expected_positions:
            errors.append(
                f"Posiciones inválidas: se esperaban posiciones {expected_positions}, se recibieron {positions}."
            )

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)