import numpy as np

from vessel_fuel.research.benchmark import run_benchmark_suite
from vessel_fuel.research.data_pipeline import clean_observations, generate_synthetic_operational_dataset


def test_hybrid_improves_over_physics_on_synthetic(tmp_path):
    data = generate_synthetic_operational_dataset(n_samples=900, seed=7)
    clean = clean_observations(data)
    summary = run_benchmark_suite(clean, out_dir=tmp_path, seed=7)

    metrics = {row["model"]: row for row in summary["metrics"]}
    assert metrics["hybrid"]["mae"] < metrics["physics_only"]["mae"]


def test_uncertainty_and_splits_present(tmp_path):
    data = generate_synthetic_operational_dataset(n_samples=700, seed=11)
    clean = clean_observations(data)
    summary = run_benchmark_suite(clean, out_dir=tmp_path, seed=11)

    assert 0.0 < summary["uncertainty"]["empirical_coverage"] <= 1.0
    assert summary["splits"]["train"] > 0
    assert summary["splits"]["val"] > 0
    assert summary["splits"]["test"] > 0


def test_significance_object_structure(tmp_path):
    data = generate_synthetic_operational_dataset(n_samples=900, seed=17)
    clean = clean_observations(data)
    summary = run_benchmark_suite(clean, out_dir=tmp_path, seed=17)

    sig = summary["significance"]["hybrid_vs_physics"]
    assert "p_value" in sig and "delta_mean" in sig
    assert np.isfinite(sig["p_value"])
