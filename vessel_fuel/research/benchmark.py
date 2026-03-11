"""End-to-end benchmark and ablation orchestration."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .data_pipeline import build_feature_matrix, split_train_val_test
from .hybrid import HybridResidualModel, PhysicsOnlyModel, PureMLModel, SpeedPowerBaseline
from .metrics import paired_bootstrap_pvalue, regression_metrics
from .tracking import ExperimentTracker
from .uncertainty import conformal_interval, interval_coverage, permutation_sensitivity


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if len(rows) == 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_benchmark_suite(
    observations: list[dict[str, Any]],
    out_dir: str | Path,
    seed: int = 42,
    alpha: float = 0.1,
) -> dict[str, Any]:
    """Run baseline comparison, significance, uncertainty, and ablation.

    Returns
    -------
    dict
        Structured results for publication tables.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tracker = ExperimentTracker(out, run_name="experiment_log")
    tracker.log({"event": "start", "seed": seed, "n_samples": len(observations)})

    splits = split_train_val_test(observations, seed=seed)
    train, val, test = splits["train"], splits["val"], splits["test"]

    x_train, y_train, feature_names = build_feature_matrix(train)
    x_val, y_val, _ = build_feature_matrix(val)
    x_test, y_test, _ = build_feature_matrix(test)

    # Baseline 1: speed-power law
    baseline = SpeedPowerBaseline().fit(train)
    y_b = baseline.predict(test)

    # Baseline 2: pure ML
    pure_ml = PureMLModel(reg_lambda=0.05).fit(x_train, y_train)
    y_ml = pure_ml.predict_from_matrix(x_test)

    # Baseline 3: physics only
    physics = PhysicsOnlyModel().fit(train)
    y_phys = physics.predict(test)

    # Target model: hybrid residual
    hybrid = HybridResidualModel(reg_lambda=0.05).fit(train, x_train, y_train)
    y_h = hybrid.predict(test, x_test)

    # Metrics
    rows = []
    for name, pred in [
        ("speed_power", y_b),
        ("pure_ml", y_ml),
        ("physics_only", y_phys),
        ("hybrid", y_h),
    ]:
        m = regression_metrics(y_test, pred)
        rows.append({"model": name, **{k: float(v) for k, v in m.items()}})
    _write_csv(out / "results_table.csv", rows)

    # Statistical significance: hybrid vs physics-only and pure ML
    sig_phys = paired_bootstrap_pvalue(y_test, y_phys, y_h, metric="mae", seed=seed)
    sig_ml = paired_bootstrap_pvalue(y_test, y_ml, y_h, metric="mae", seed=seed)

    with (out / "significance.json").open("w", encoding="utf-8") as f:
        json.dump({"hybrid_vs_physics": sig_phys, "hybrid_vs_pure_ml": sig_ml}, f, indent=2)

    # Uncertainty with split conformal (calibration split = val)
    y_val_h = hybrid.predict(val, x_val)
    lo, hi = conformal_interval(y_val, y_val_h, y_h, alpha=alpha)
    coverage = interval_coverage(y_test, lo, hi)

    interval_rows = [
        {"y_true": float(t), "y_pred": float(p), "lo": float(l), "hi": float(h)}
        for t, p, l, h in zip(y_test, y_h, lo, hi)
    ]
    _write_csv(out / "prediction_intervals.csv", interval_rows)

    # Sensitivity on hybrid residual term
    sens = permutation_sensitivity(lambda xx: hybrid.predict(test, xx), x_test, y_test, feature_names, seed=seed)
    _write_csv(out / "sensitivity_ranking.csv", [{"feature": k, "delta_mae": v} for k, v in sens])

    # Ablation: remove one feature block at a time from hybrid residual learner
    blocks = {
        "no_wind_features": ["wind_kn", "cos_wind", "sin_wind"],
        "no_wave_features": ["Hs", "Tp"],
        "no_current_features": ["current_kn", "cos_current", "sin_current"],
        "no_loading_features": ["T", "CB", "trim_m", "design_draft"],
        "no_fouling_feature": ["months_since_cleaning"],
    }

    name_to_idx = {n: i for i, n in enumerate(feature_names)}
    ablation_rows = []
    for label, feats in blocks.items():
        keep_idx = [i for n, i in name_to_idx.items() if n not in feats]
        xtr = x_train[:, keep_idx]
        xte = x_test[:, keep_idx]

        ab_model = HybridResidualModel(reg_lambda=0.05).fit(train, xtr, y_train)
        yp = ab_model.predict(test, xte)
        m = regression_metrics(y_test, yp)
        ablation_rows.append({"ablation": label, **m})

    _write_csv(out / "ablation_table.csv", ablation_rows)

    summary = {
        "metrics": rows,
        "significance": {"hybrid_vs_physics": sig_phys, "hybrid_vs_pure_ml": sig_ml},
        "uncertainty": {"alpha": alpha, "empirical_coverage": coverage},
        "splits": {"train": len(train), "val": len(val), "test": len(test)},
    }

    with (out / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    tracker.log({"event": "end", **summary})
    return summary
