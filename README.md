# vessel-fuel-model

Physics-based maritime fuel consumption model for academic and research use.

## Overview

The repository now upgrades a simplified baseline fuel formulation into a more physically grounded pipeline with directional weather handling, component diagnostics, and calibration quality metrics.

Baseline limitations addressed by this library:

- Simplified hydrodynamic decomposition with limited calm-water resistance detail
- Incomplete aerodynamic treatment without full apparent-wind handling
- No detailed multi-zone load-dependent engine consumption behavior
- Limited seawater property sensitivity to SST (sea surface temperature)
- No full auxiliary and boiler decomposition
- No explicit hull fouling growth effects in the baseline path
- Coarse calibration/debug outputs that make component-level error isolation difficult

Proposed upgrade direction implemented here:

- Improved calm-water resistance decomposition using Holtrop & Mennen (1982, 1984)
- Apparent-wind-based aerodynamic resistance using Blendermann (1994)
- Configurable wave-added resistance with STAWAVE-1 or Kwon (2008)
- Time-dependent hull fouling correction following Schultz (2007)
- Propulsion efficiency degradation under sea state
- Load-dependent multi-zone SFOC curve inspired by WindMar-style operating behavior
- Auxiliary and boiler fuel components
- Per-component calibration factors for targeted tuning
- Component diagnostics and fit-quality metrics for research workflows

## Installation

```bash
pip install vessel-fuel-model
```

For full reproducible experiments:


```bash
pip install -e ".[dev]"
# Synthetic benchmark (reproducible)
python scripts/run_research_benchmark.py --use-synthetic --seed 42 --out outputs/repro
# Real-data benchmark (requires CSVs)
python scripts/run_research_benchmark.py \
	--ais data/ais_segments.csv \
	--metocean data/metocean.csv \
	--vessels data/vessel_particulars.csv \
	--noon data/noon_reports.csv \
	--seed 42 --out outputs/real
```

## Getting Started with Real Data

Quick start with automatic free-data acquisition:

```bash
python scripts/run_research_benchmark.py \
	--fetch-data \
	--region north_atlantic \
	--start-date 2024-01-01T00:00:00Z \
	--end-date 2024-01-07T23:00:00Z \
	--seed 42 \
	--out outputs/repro
```

Manual sourcing and formatting guide:

- [docs/data_acquisition.md](docs/data_acquisition.md)

The auto-fetch path downloads AIS/metocean/bathymetry from free public sources and can generate deterministic proxy vessel/noon files when proprietary engine logs are unavailable.

## Quick example

```python
from vessel_fuel import fuel_model

env = {"wind_kn": 12, "wind_angle_deg": 20, "Hs": 1.5, "Tp": 8, "wave_angle_deg": 0, "sst_c": 15}
params = {"L": 120, "B": 20, "T": 7, "S": 4200, "CB": 0.72, "MCR": 10000, "sfoc_at_mcr": 180}
fuel_mt = fuel_model(distance_km=120, speed_tw_kn=12, env=env, vessel_params=params)
print(f"Fuel consumed: {fuel_mt:.3f} MT")
```

Component diagnostics:

```python
from vessel_fuel import fuel_components

components = fuel_components(distance_km=120, speed_tw_kn=12, env=env, vessel_params=params)
print(components["calm_water_resistance_n"], components["total_fuel_mt"])
```

## Model pipeline

| Step | Sub-model | Description |
|---|---|---|
| 1 | Calm-water resistance | Holtrop-Mennen decomposition (1982/1984) |
| 2 | Wind resistance | Blendermann apparent-wind aerodynamic drag |
| 3 | Wave resistance | ISO 15016 STAWAVE-1 or Kwon (2008) |
| 4 | Hull fouling | Schultz (2007) time-dependent $\Delta C_f$ |
| 5 | Propulsion efficiency | Base efficiency with wave-height degradation |
| 6 | Draft/trim and depth effects | Corrective factors for loading and shallow water |
| 7 | Engine SFOC | Five-zone load-dependent $\mathrm{SFOC}$ curve |
| 8 | Total fuel | Main + optional auxiliary + optional boiler |

## Vessel parameters

| Key | Required | Description |
|---|---|---|
| `L`, `B`, `T`, `S`, `CB` | Yes | Principal dimensions, wetted area, block coefficient |
| `Cp`, `Cm`, `Cwp`, `lcb_frac`, `half_entrance_angle` | No | Hull-form descriptors |
| `transom_area`, `bulb_area`, `bulb_center`, `stern_shape_coeff`, `appendage_factor` | No | Additional resistance geometry factors |
| `A_front`, `A_lateral`, `Cd_air` | No | Aerodynamic properties |
| `design_draft`, `trim_m` | No | Draft/trim correction inputs |
| `MCR`, `sfoc_at_mcr`, `eta_0`, `eta_wave_loss` | No | Main engine and propulsion efficiency inputs |
| `include_aux`, `aux_power_kw`, `aux_sfoc` | No | Auxiliary engine fuel model |
| `include_boiler`, `boiler_power_kw`, `boiler_sfoc` | No | Boiler fuel model |
| `months_since_cleaning` | No | Fouling aging input |

## Tasks covered in this round

- Refactor fuel computation into component outputs via `fuel_components`
- Add full apparent-wind vector handling in the aerodynamic resistance path
- Keep configurable wave-method selection in the main model API
- Add fouling-growth input through `months_since_cleaning`
- Add boiler and standard auxiliary terms to the total-fuel calculation
- Add per-component calibration factors and calibration quality metrics
- Add benchmark-style tests for calm, adverse, slow-steaming, and fouling cases

## Research framework (hybrid + uncertainty)

The framework includes:

- Hybrid residual learning: $\hat{F} = F_{physics} + f_{ML}(x)$
- Strict train/validation/test split by vessel class, route, and season
- Benchmarks: speed-power, pure ML, physics-only, hybrid
- Uncertainty: split-conformal prediction intervals
- Sensitivity ranking: permutation-based delta-MAE
- Ablation study by feature-block removal
- Experiment tracking with fixed random seeds

Real-data fusion helpers are available for AIS, metocean, vessel particulars, and noon/engine reports:

```python
from vessel_fuel import (
	load_ais_segments,
	load_metocean,
	load_vessel_particulars,
	load_engine_noon,
	fuse_operational_data,
	clean_observations,
)

ais = load_ais_segments("data/ais_segments.csv")
met = load_metocean("data/metocean.csv")
ves = load_vessel_particulars("data/vessel_particulars.csv")
noon = load_engine_noon("data/noon_reports.csv")
dataset = clean_observations(fuse_operational_data(ais, met, ves, noon))
```


Generated outputs (in the specified --out directory):

- `results_table.csv` (RMSE, MAE, MAPE, bias, $R^2$)
- `significance.json` (paired bootstrap tests)
- `prediction_intervals.csv`
- `sensitivity_ranking.csv`
- `ablation_table.csv`
- `summary.json`
- `cli_summary.json` (top-level summary for CLI runs)

Example command to reproduce all outputs:

```bash
python scripts/run_research_benchmark.py --use-synthetic --seed 42 --out outputs/repro
```

## Publication package

Draft artifacts are included in [docs/paper/methods.md](docs/paper/methods.md), [docs/paper/experiment_protocol.md](docs/paper/experiment_protocol.md), [docs/paper/limitations_future_work.md](docs/paper/limitations_future_work.md), and [docs/paper/figure_captions.md](docs/paper/figure_captions.md).

## References

- Holtrop, J., and Mennen, G. G. J. (1982, 1984)
- Blendermann, W. (1994)
- Kwon, Y. J. (2008)
- ISO 15016 (STAWAVE-1)
- Schultz, M. P. (2007)
- UNESCO (1983)
- Sharqawy, M. H. et al. (2010)

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for full terms.

## Citation

If you use this library in publications, please cite:

Jean d'Amour Umuhoza (2026), vessel-fuel-model, Université du Québec à Chicoutimi (UQAC).

Author ORCID: https://orcid.org/0009-0008-7067-8817

DOI: to be added. (Replace with your DOI when available)
