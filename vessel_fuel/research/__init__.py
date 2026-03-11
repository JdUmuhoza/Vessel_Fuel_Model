"""Research framework for hybrid vessel fuel modeling."""

from .benchmark import run_benchmark_suite
from .data_pipeline import (
    build_feature_matrix,
    clean_observations,
    generate_synthetic_operational_dataset,
    split_train_val_test,
)
from .ingest import (
    fuse_operational_data,
    load_ais_segments,
    load_engine_noon,
    load_metocean,
    load_vessel_particulars,
)
from .hybrid import HybridResidualModel, PhysicsOnlyModel, PureMLModel, SpeedPowerBaseline
from .tracking import ExperimentTracker
from .uncertainty import conformal_interval, permutation_sensitivity

__all__ = [
    "run_benchmark_suite",
    "build_feature_matrix",
    "clean_observations",
    "generate_synthetic_operational_dataset",
    "split_train_val_test",
    "load_ais_segments",
    "load_metocean",
    "load_vessel_particulars",
    "load_engine_noon",
    "fuse_operational_data",
    "HybridResidualModel",
    "PhysicsOnlyModel",
    "PureMLModel",
    "SpeedPowerBaseline",
    "ExperimentTracker",
    "conformal_interval",
    "permutation_sensitivity",
]
