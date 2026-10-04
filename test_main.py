"""Prueba de integración para la ejecución de main.py."""

from main import run_cli_pipeline


def test_main_pipeline_execution():
    """Verifica que el pipeline CLI se ejecute de principio a fin sin excepciones."""
    run_cli_pipeline()