"""vessel-fuel-model public API."""

from .engine import auxiliary_fuel, boiler_fuel, sfoc_curve
from .environment import sw_density, sw_viscosity
from .fouling import fouling_delta_cf
from .model import calibrate_model, calibration_report, fuel_components, fuel_model, validate_model
from .resistance import (
    blendermann_wind_resistance,
    holtrop_mennen_resistance,
    kwon_resistance,
    stawave1_resistance,
)
from .research import (
    HybridResidualModel,
    PhysicsOnlyModel,
    PureMLModel,
    SpeedPowerBaseline,
    build_feature_matrix,
    clean_observations,
    conformal_interval,
    generate_synthetic_operational_dataset,
    fuse_operational_data,
    load_ais_segments,
    load_engine_noon,
    load_metocean,
    load_vessel_particulars,
    permutation_sensitivity,
    run_benchmark_suite,
    split_train_val_test,
)

__all__ = [
    "auxiliary_fuel",
    "boiler_fuel",
    "sfoc_curve",
    "sw_density",
    "sw_viscosity",
    "fouling_delta_cf",
    "fuel_model",
    "fuel_components",
    "calibrate_model",
    "calibration_report",
    "validate_model",
    "holtrop_mennen_resistance",
    "blendermann_wind_resistance",
    "stawave1_resistance",
    "kwon_resistance",
    "run_benchmark_suite",
    "build_feature_matrix",
    "clean_observations",
    "generate_synthetic_operational_dataset",
    "load_ais_segments",
    "load_metocean",
    "load_vessel_particulars",
    "load_engine_noon",
    "fuse_operational_data",
    "split_train_val_test",
    "HybridResidualModel",
    "PhysicsOnlyModel",
    "PureMLModel",
    "SpeedPowerBaseline",
    "conformal_interval",
    "permutation_sensitivity",
]
