"""Evaluation metrics and statistical significance utilities."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def regression_metrics(y_true: Sequence[float], y_pred: Sequence[float]) -> dict[str, float]:
    """Compute standard regression metrics.

    Parameters
    ----------
    y_true : sequence of float
        Observed target values.
    y_pred : sequence of float
        Predicted target values.

    Returns
    -------
    dict
        RMSE, MAE, MAPE, bias, and $R^2$.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    err = yp - yt
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    mape = float(np.mean(np.abs(err) / np.maximum(np.abs(yt), 1e-9)) * 100.0)
    bias = float(np.mean(err))

    ss_res = float(np.sum((yt - yp) ** 2))
    ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
    r2 = 1.0 - ss_res / max(ss_tot, 1e-12)
    return {"rmse": rmse, "mae": mae, "mape": mape, "bias": bias, "r2": float(r2)}


def paired_bootstrap_pvalue(
    y_true: Sequence[float],
    y_pred_a: Sequence[float],
    y_pred_b: Sequence[float],
    metric: str = "mae",
    n_bootstrap: int = 2000,
    seed: int = 42,
) -> dict[str, float]:
    """Paired bootstrap significance test for two models.

    Tests whether model ``b`` improves over model ``a`` for the selected metric.

    Returns
    -------
    dict
        ``delta_mean``, ``p_value``, ``ci_low``, ``ci_high`` where delta is
        ``metric(a) - metric(b)`` so positive values indicate improvement by b.
    """
    yt = np.asarray(y_true, dtype=float)
    ya = np.asarray(y_pred_a, dtype=float)
    yb = np.asarray(y_pred_b, dtype=float)

    n = len(yt)
    rng = np.random.default_rng(seed)

    def _metric(y_t: np.ndarray, y_p: np.ndarray) -> float:
        m = regression_metrics(y_t, y_p)
        return float(m[metric])

    deltas = np.zeros(n_bootstrap, dtype=float)
    for i in range(n_bootstrap):
        idx = rng.integers(0, n, size=n)
        ma = _metric(yt[idx], ya[idx])
        mb = _metric(yt[idx], yb[idx])
        deltas[i] = ma - mb

    p_value = float(np.mean(deltas <= 0.0))
    return {
        "delta_mean": float(np.mean(deltas)),
        "p_value": p_value,
        "ci_low": float(np.quantile(deltas, 0.025)),
        "ci_high": float(np.quantile(deltas, 0.975)),
    }
