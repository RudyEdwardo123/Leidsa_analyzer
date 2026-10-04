"""Módulo de análisis de series temporales basado en los principios de Forecasting: Principles and Practice (fpp3)."""

from dataclasses import dataclass
from typing import Dict, List
import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox

from app.models.draw import DrawData


@dataclass
class TimeSeriesAnalysisResult:
    """Resultado del análisis temporal y pruebas de aleatoriedad para un número o métrica.

    Attributes:
        target_number: Número evaluado.
        total_observations: Cantidad total de sorteos analizados.
        autocorrelations: Coeficientes de autocorrelación por lag (1 a max_lag).
        confidence_bound: Límite de confianza al 95% (1.96 / sqrt(N)).
        is_white_noise: True si no se puede rechazar la hipótesis nula de ruido blanco (proceso aleatorio).
        ljung_box_p_value: p-valor del test de Ljung-Box para la hipótesis nula de independencia.
    """

    target_number: int
    total_observations: int
    autocorrelations: Dict[int, float]
    confidence_bound: float
    is_white_noise: bool
    ljung_box_p_value: float


def build_binary_time_series(
    draws: List[DrawData], target_number: int, role: str = "main"
) -> pd.Series:
    """Construye una serie temporal binaria (1 si el número estuvo presente, 0 si no) ordenada por fecha."""
    if not draws:
        return pd.Series(dtype=float)

    sorted_draws = sorted(draws, key=lambda d: d.draw_date)
    dates = [d.draw_date for d in sorted_draws]
    values = [
        1 if target_number in d.get_numbers_by_role(role) else 0 for d in sorted_draws
    ]

    series = pd.Series(
        data=values, index=pd.to_datetime(dates), name=f"num_{target_number}"
    )
    return series


def analyze_time_series(
    series: pd.Series, target_number: int, max_lag: int = 10
) -> TimeSeriesAnalysisResult:
    """Realiza un análisis de autocorrelación y prueba de ruido blanco (fpp3 Cap. 2 y 5)."""
    n = len(series)
    if n == 0:
        raise ValueError("La serie temporal no contiene observaciones.")

    bound = 1.96 / np.sqrt(n) if n > 0 else 0.0

    # Ajustar retardo máximo según el tamaño de la muestra
    lags = min(max_lag, max(1, (n - 1) // 2))

    autocores: Dict[int, float] = {}

    # Manejo defensivo para muestras pequeñas (N < 4) o series sin varianza
    if series.nunique() <= 1 or n < 4:
        for lag in range(1, lags + 1):
            autocores[lag] = 0.0
        return TimeSeriesAnalysisResult(
            target_number=target_number,
            total_observations=n,
            autocorrelations=autocores,
            confidence_bound=float(bound),
            is_white_noise=True,
            ljung_box_p_value=1.0,
        )

    for lag in range(1, lags + 1):
        ac = series.autocorr(lag=lag)
        autocores[lag] = 0.0 if (pd.isna(ac) or np.isnan(ac)) else float(ac)

    # Test de Ljung-Box para evaluar hipótesis de ruido blanco
    try:
        lb_result = acorr_ljungbox(series, lags=[lags], return_df=True)
        p_value = float(lb_result["lb_pvalue"].iloc[0])
        if np.isnan(p_value):
            p_value = 1.0
    except Exception:
        p_value = 1.0

    is_white_noise = p_value > 0.05

    return TimeSeriesAnalysisResult(
        target_number=target_number,
        total_observations=n,
        autocorrelations=autocores,
        confidence_bound=float(bound),
        is_white_noise=is_white_noise,
        ljung_box_p_value=p_value,
    )


def compute_rolling_frequency(series: pd.Series, window: int = 10) -> pd.Series:
    """Calcula la frecuencia móvil en una ventana de N sorteos."""
    return series.rolling(window=window, min_periods=1).mean()