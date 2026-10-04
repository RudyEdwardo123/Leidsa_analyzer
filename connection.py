"""Gestor de conexión y creación de esquemas para SQLite."""

import sqlite3
from pathlib import Path


def get_connection(db_path: str = "data/leidsa.db") -> sqlite3.Connection:
    """Crea y retorna una conexión a la base de datos SQLite con claves foráneas habilitadas."""
    # Asegurar que el directorio de la BD exista
    db_file = Path(db_path)
    if db_file.parent and not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = "data/leidsa.db") -> None:
    """Inicializa el esquema de tablas en la base de datos si no existen."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Tabla principal de Sorteos
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL,
            draw_date TEXT NOT NULL,
            source TEXT NOT NULL,
            variant TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(game, draw_date)
        );
        """
    )

    # Tabla de Números del Sorteo
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS draw_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draw_id INTEGER NOT NULL,
            value INTEGER NOT NULL,
            role TEXT NOT NULL,
            position INTEGER,
            FOREIGN KEY (draw_id) REFERENCES draws (id) ON DELETE CASCADE
        );
        """
    )

    # Índices para consultas eficientes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_draws_game_date ON draws(game, draw_date);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_numbers_draw_id ON draw_numbers(draw_id);"
    )

    conn.commit()
    conn.close()