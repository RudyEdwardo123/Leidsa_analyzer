"""Patrón Repository para abstraer la persistencia y consulta de sorteos históricos."""

import sqlite3
from datetime import date
from typing import List, Optional

from app.database.connection import get_connection
from app.models.draw import DrawData, DrawNumber
from app.rules.game_rules import GameType


class DrawRepository:
    """Repositorio para gestionar operaciones CRUD y consultas de DrawData."""

    def __init__(self, db_path: str = "data/leidsa.db"):
        self.db_path = db_path

    def exists(self, game: GameType, draw_date: date) -> bool:
        """Verifica si ya existe un sorteo registrado para el juego y fecha indicados."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM draws WHERE game = ? AND draw_date = ? LIMIT 1;",
            (game.value, draw_date.isoformat()),
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def save_draw(self, draw: DrawData) -> bool:
        """Guarda un nuevo sorteo y sus números asociados.

        Returns:
            True si fue guardado exitosamente.
            False si ya existía un sorteo duplicado (mismo juego y fecha).
        """
        if self.exists(draw.game, draw.draw_date):
            return False

        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO draws (game, draw_date, source, variant, source_url)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    draw.game.value,
                    draw.draw_date.isoformat(),
                    draw.source,
                    draw.variant,
                    draw.source_url,
                ),
            )
            draw_id = cursor.lastrowid

            for idx, num in enumerate(draw.numbers):
                cursor.execute(
                    """
                    INSERT INTO draw_numbers (draw_id, value, role, position)
                    VALUES (?, ?, ?, ?);
                    """,
                    (draw_id, num.value, num.role, num.position),
                )

            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_draw(self, game: GameType, draw_date: date) -> Optional[DrawData]:
        """Recupera un sorteo por su tipo de juego y fecha."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, game, draw_date, source, variant, source_url FROM draws WHERE game = ? AND draw_date = ?;",
            (game.value, draw_date.isoformat()),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        draw_id = row["id"]
        cursor.execute(
            "SELECT value, role, position FROM draw_numbers WHERE draw_id = ? ORDER BY id ASC;",
            (draw_id,),
        )
        num_rows = cursor.fetchall()
        conn.close()

        numbers = [
            DrawNumber(
                value=nr["value"],
                role=nr["role"],
                position=nr["position"],
            )
            for nr in num_rows
        ]

        return DrawData(
            game=GameType(row["game"]),
            draw_date=date.fromisoformat(row["draw_date"]),
            numbers=numbers,
            source=row["source"],
            variant=row["variant"],
            source_url=row["source_url"],
        )

    def get_draws_by_game(
        self, game: GameType, limit: Optional[int] = None
    ) -> List[DrawData]:
        """Obtiene la lista histórica de sorteos de un juego específico, ordenados descendentemente por fecha."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        query = "SELECT id, game, draw_date, source, variant, source_url FROM draws WHERE game = ? ORDER BY draw_date DESC"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (game.value,))
        rows = cursor.fetchall()

        draws: List[DrawData] = []
        for r in rows:
            draw_id = r["id"]
            cursor.execute(
                "SELECT value, role, position FROM draw_numbers WHERE draw_id = ? ORDER BY id ASC;",
                (draw_id,),
            )
            num_rows = cursor.fetchall()
            numbers = [
                DrawNumber(
                    value=nr["value"], role=nr["role"], position=nr["position"]
                )
                for nr in num_rows
            ]
            draws.append(
                DrawData(
                    game=GameType(r["game"]),
                    draw_date=date.fromisoformat(r["draw_date"]),
                    numbers=numbers,
                    source=r["source"],
                    variant=r["variant"],
                    source_url=r["source_url"],
                )
            )

        conn.close()
        return draws

    def delete_draw(self, game: GameType, draw_date: date) -> bool:
        """Elimina un sorteo específico identificado por su juego y fecha.

        Returns:
            True si el sorteo existía y fue eliminado, False si no se encontró.
        """
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM draws WHERE game = ? AND draw_date = ?;",
            (game.value, draw_date.isoformat()),
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def clear_all_draws(self) -> int:
        """Elimina todos los sorteos y números de la base de datos."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM draws;")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM draws;")
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('draws', 'draw_numbers');")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()
        return count

    def delete_draws_by_game(self, game: GameType) -> int:
        """Elimina todos los sorteos de un juego específico."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM draws WHERE game = ?;", (game.value,))
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM draws WHERE game = ?;", (game.value,))
        conn.commit()
        conn.close()
        return count