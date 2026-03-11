"""Baseline, pure-ML, physics-only, and hybrid residual models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from vessel_fuel.model import fuel_model


class SpeedPowerBaseline:
    r"""Simple speed-power baseline: $F = a\,d\,v^b$."""

    def __init__(self) -> None:
        self.a = 1.0
        self.b = 3.0

    def fit(self, observations: Sequence[dict[str, Any]]) -> "SpeedPowerBaseline":
        d = np.asarray([float(o["distance_km"]) for o in observations], dtype=float)
        v = np.asarray([max(float(o["speed_tw_kn"]), 1e-3) for o in observations], dtype=float)
        y = np.asarray([max(float(o["fuel_mt"]), 1e-6) for o in observations], dtype=float)

        # log(y / d) = log(a) + b log(v)
        x = np.log(v)
        t = np.log(y / np.maximum(d, 1e-6))
        A = np.column_stack([np.ones_like(x), x])
        coef, *_ = np.linalg.lstsq(A, t, rcond=None)
        self.a = float(np.exp(coef[0]))
        self.b = float(coef[1])
        return self

    def predict(self, observations: Sequence[dict[str, Any]]) -> np.ndarray:
        d = np.asarray([float(o["distance_km"]) for o in observations], dtype=float)
        v = np.asarray([max(float(o["speed_tw_kn"]), 1e-3) for o in observations], dtype=float)
        return self.a * d * (v**self.b)


class PhysicsOnlyModel:
    """Wrapper around physics-based fuel model."""

    def __init__(self, calib: dict[str, float] | None = None) -> None:
        self.calib = calib

    def fit(self, observations: Sequence[dict[str, Any]]) -> "PhysicsOnlyModel":
        _ = observations
        return self

    def predict(self, observations: Sequence[dict[str, Any]]) -> np.ndarray:
        return np.asarray(
            [
                float(fuel_model(o["distance_km"], o["speed_tw_kn"], o["env"], o["vessel_params"], self.calib))
                for o in observations
            ],
            dtype=float,
        )


@dataclass
class _RidgeRegressor:
    lam: float = 1e-2

    def fit(self, x: np.ndarray, y: np.ndarray) -> "_RidgeRegressor":
        xx = np.asarray(x, dtype=float)
        yy = np.asarray(y, dtype=float)
        mu = xx.mean(axis=0)
        sd = xx.std(axis=0) + 1e-12
        xs = (xx - mu) / sd
        X = np.column_stack([np.ones(len(xs)), xs])
        reg = self.lam * np.eye(X.shape[1])
        reg[0, 0] = 0.0
        self.coef_ = np.linalg.solve(X.T @ X + reg, X.T @ yy)
        self.mu_ = mu
        self.sd_ = sd
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        xx = np.asarray(x, dtype=float)
        xs = (xx - self.mu_) / self.sd_
        X = np.column_stack([np.ones(len(xs)), xs])
        return X @ self.coef_


class PureMLModel:
    """Pure ML model (no physics term) using engineered feature regression."""

    def __init__(self, reg_lambda: float = 0.03) -> None:
        self.reg = _RidgeRegressor(lam=reg_lambda)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "PureMLModel":
        self.reg.fit(x, y)
        return self

    def predict_from_matrix(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(self.reg.predict(x), 0.0)


class HybridResidualModel:
    r"""Hybrid model: $\hat{F} = F_{physics} + f_{ML}(x)$."""

    def __init__(self, reg_lambda: float = 0.03, physics_calib: dict[str, float] | None = None) -> None:
        self.reg = _RidgeRegressor(lam=reg_lambda)
        self.physics_model = PhysicsOnlyModel(calib=physics_calib)

    def fit(self, observations: Sequence[dict[str, Any]], x: np.ndarray, y: np.ndarray) -> "HybridResidualModel":
        y_phys = self.physics_model.predict(observations)
        residual = y - y_phys
        self.reg.fit(x, residual)
        return self

    def predict(self, observations: Sequence[dict[str, Any]], x: np.ndarray) -> np.ndarray:
        y_phys = self.physics_model.predict(observations)
        y_res = self.reg.predict(x)
        return np.maximum(y_phys + y_res, 0.0)
