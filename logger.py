"""Módulo centralizado de logging para LEIDSA ANALYZER."""

import logging
from pathlib import Path


def setup_logger(
    name: str = "leidsa_analyzer", log_file: str = "logs/importer.log"
) -> logging.Logger:
    """Configura un logger centralizado que registra errores e información en archivo y consola."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # Handler para archivo de texto acumulativo
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Handler para consola
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()