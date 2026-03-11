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

## References

- Holtrop, J., and Mennen, G. G. J. (1982, 1984)
- Blendermann, W. (1994)
- Kwon, Y. J. (2008)
- ISO 15016 (STAWAVE-1)
- Schultz, M. P. (2007)
- UNESCO (1983)
- Sharqawy, M. H. et al. (2010)

## License

This project is released under an academic non-commercial license. Commercial use requires written permission from the author.

## Citation

If you use this library in publications, please cite:

Jean d'Amour Umuhoza (2026), vessel-fuel-model, Université du Québec à Chicoutimi (UQAC).

Author ORCID: https://orcid.org/0009-0008-7067-8817

DOI: to be added.
