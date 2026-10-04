"""Algoritmo de segmentación por backtracking para cadenas de números sin separadores."""

from typing import List, Set, Tuple

from app.models.draw import DrawNumber
from app.rules.game_rules import GAME_RULES, GameRule, GameType, GroupRule


def _get_group_configurations(game_rule: GameRule) -> List[List[GroupRule]]:
    """Genera las variaciones válidas de grupos para un juego (soporta grupos opcionales)."""
    configs: List[List[GroupRule]] = []
    current: List[GroupRule] = []

    for group in game_rule.groups:
        if not group.is_optional:
            current.append(group)
        else:
            if current and current not in configs:
                configs.append(list(current))
            current.append(group)

    if current and current not in configs:
        configs.append(list(current))

    return configs


def _backtrack(
    text: str,
    index: int,
    groups: List[GroupRule],
    group_idx: int,
    num_in_group: int,
    current_group_vals: List[int],
    accumulated: List[DrawNumber],
    has_positions: bool,
    results: List[List[DrawNumber]],
) -> None:
    """Función recursiva de backtracking para segmentar la cadena de dígitos."""
    # Caso base: Hemos procesado todos los grupos de la variante
    if group_idx == len(groups):
        if index == len(text):
            results.append(list(accumulated))
        return

    current_rule = groups[group_idx]

    # Si completamos la cantidad necesaria del grupo actual, avanzar al siguiente
    if num_in_group == current_rule.count:
        _backtrack(
            text=text,
            index=index,
            groups=groups,
            group_idx=group_idx + 1,
            num_in_group=0,
            current_group_vals=[],
            accumulated=accumulated,
            has_positions=has_positions,
            results=results,
        )
        return

    # Probar longitudes de 1 y 2 dígitos
    for length in (1, 2):
        if index + length > len(text):
            continue

        substring = text[index : index + length]
        val = int(substring)

        # 1. Validar rango permitido del grupo
        if val < current_rule.min_val or val > current_rule.max_val:
            continue

        # 2. Validar duplicados dentro del grupo si la regla lo prohíbe
        if not current_rule.allow_duplicates and val in current_group_vals:
            continue

        # 3. Validar orden de menor a mayor si la regla lo exige
        if current_rule.is_ordered and current_group_vals:
            if val <= current_group_vals[-1]:
                continue

        # Asignar posición si el juego es posicional (ej. Quiniela 1ro, 2do, 3ro)
        position = (len(accumulated) + 1) if has_positions else None
        draw_num = DrawNumber(value=val, role=current_rule.name, position=position)

        current_group_vals.append(val)
        accumulated.append(draw_num)

        _backtrack(
            text=text,
            index=index + length,
            groups=groups,
            group_idx=group_idx,
            num_in_group=num_in_group + 1,
            current_group_vals=current_group_vals,
            accumulated=accumulated,
            has_positions=has_positions,
            results=results,
        )

        accumulated.pop()
        current_group_vals.pop()


def segment_numbers(
    text: str, game_type: GameType, rule: GameRule = None
) -> List[List[DrawNumber]]:
    """Segmenta una cadena de dígitos sin separadores en todas sus interpretaciones válidas.

    Args:
        text: Cadena de caracteres numéricos a segmentar.
        game_type: Tipo de juego LEIDSA.
        rule: Regla del juego (opcional).

    Returns:
        Lista de interpretaciones válidas. Cada interpretación es una lista de DrawNumber.
    """
    clean_text = text.strip()
    if not clean_text.isdigit():
        return []

    game_rule = rule or GAME_RULES.get(game_type)
    if not game_rule:
        raise ValueError(f"No hay regla configurada para {game_type}")

    configurations = _get_group_configurations(game_rule)
    all_results: List[List[DrawNumber]] = []
    seen_keys: Set[Tuple] = set()

    for groups in configurations:
        results: List[List[DrawNumber]] = []
        _backtrack(
            text=clean_text,
            index=0,
            groups=groups,
            group_idx=0,
            num_in_group=0,
            current_group_vals=[],
            accumulated=[],
            has_positions=game_rule.has_positions,
            results=results,
        )

        for res in results:
            key = tuple((n.value, n.role, n.position) for n in res)
            if key not in seen_keys:
                seen_keys.add(key)
                all_results.append(res)

    return all_results