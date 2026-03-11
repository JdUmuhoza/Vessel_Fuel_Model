# Research Goals: External Validation

## Overview

To establish credibility for publication, this project pursues two critical objectives:

1. **Real measured data validation** — Move from synthetic to real-world fuel consumption data
2. **External model comparison** — Benchmark against published, independent models (not models built by this project)

---

## Goal 1: Real Measured Data Validation

### Primary Dataset: UCI Naval Propulsion Plants
- **Status**: Available, peer-reviewed, citable
- **Citation**: Coraddu, A., Oneto, L., Ghio, A., Savio, S., Anguita, D., & Figari, M. (2014)
- **DOI**: [10.24432/C5K31K](https://doi.org/10.24432/C5K31K)
- **Size**: 11,934 samples × 16 features
- **Target variable**: Fuel flow [kg/s]
- **Features**: Lever position, ship speed [knots], GT torque, pressures, temperatures, turbine control, decay coefficients
- **Source**: Numerical simulator validated against real frigate propulsion plants (CODLAG type)

### Installation & Loading
```python
pip install ucimlrepo

from ucimlrepo import fetch_ucirepo
ds = fetch_ucirepo(id=316)
X = ds.data.features  # 16 features
y = ds.data.targets   # fuel flow [kg/s]
```

### Integration Steps
- [ ] Create `vessel_fuel/research/datasets.py` with `load_uci_naval_propulsion()` function
- [ ] Add UCI data to `run_benchmark_suite()` as validation option: `--dataset uci`
- [ ] Compare synthetic vs real performance on identical model/feature sets
- [ ] Validate that physics-based models generalize to real propulsion data

### Secondary Real-World Datasets
| Source | Type | Features | Status |
|--------|------|----------|--------|
| **THETIS-MRV** | EU maritime emissions | CO₂, fuel, vessel type, route | Public, requires download |
| **PONTOS ferries** | Operational telemetry | Speed, fuel, location, battery SOC | Kaggle, 10-day sample |
| **Ship Performance Clustering** | Fleet data | Speed efficiency metrics | Kaggle, 4,709 downloads |

---

## Goal 2: External Model Comparisons

### Current Problem
The benchmark suite compares only models built by this project:
- `SpeedPowerBaseline` — your code
- `PhysicsOnlyModel` — your code
- `PureMLModel` (Ridge) — your code
- `HybridResidualModel` — your code

**Issue**: A reviewer will say "You only compared against your own weaker versions."

### Solution: Published External Baselines

| Model | Reference | Type | Implementation |
|-------|-----------|------|-----------------|
| **Coraddu et al. (2014) SVR** | Peer-reviewed, DOI:10.24432/C5K31K | ML baseline | Reported accuracies in their paper |
| **Coraddu et al. (2014) Random Forest** | Peer-reviewed, DOI:10.24432/C5K31K | ML baseline | Reported accuracies in their paper |
| **XGBoost** | Chen & Guestrin (2016) | Gradient boosting | `pip install xgboost`, train on same data |
| **LightGBM** | Ke et al. (2017) | Gradient boosting | `pip install lightgbm`, train on same data |
| **Generalized Additive Model (GAM)** | Serven & Brummitt (2018), DOI:10.5281/zenodo.1208723 | Statistical | `pip install pygam` or `statsmodels GLMGam` |
| **Admiralty Coefficient Formula** | IMO standard | Physics empirical | $F \propto \Delta^{2/3} \cdot v^3$ |
| **IMO EEDI** | MEPC.212(63) resolution | Regulatory | Energy Efficiency Design Index |

### Implementation Plan

**Phase 1 — Add ML Baselines** (This Month)
```bash
pip install xgboost lightgbm pygam
```

Create `vessel_fuel/research/comparators.py`:
- `XGBoostModel(BaseModel)` — gradient boosting comparator
- `LightGBMModel(BaseModel)` — lightgbm comparator
- `GAMModel(BaseModel)` — pyGAM LinearGAM comparator

Register in `run_benchmark_suite()`:
```python
models = {
    'speed_power_baseline': SpeedPowerBaseline(),
    'physics_only': PhysicsOnlyModel(),
    'pure_ml_ridge': PureMLModel(),
    'xgboost': XGBoostModel(),  # NEW: external
    'lightgbm': LightGBMModel(),  # NEW: external
    'gam': GAMModel(),  # NEW: external
    'hybrid': HybridResidualModel(),  # YOUR main contribution
}
```

**Phase 2 — Comparison Against Published Numbers**
- Train all 7 models on UCI dataset
- Report RMSE, MAE, R², bias
- Compare your `HybridResidualModel` results to Coraddu et al. (2014) published numbers
- If your model beats XGBoost + LightGBM + GAM → publication-ready claim

**Phase 3 — Regulatory Baselines** (Optional, for discussion)
- Implement Admiralty formula as physics-only baseline
- Compare to IMO EEDI for context on regulatory gaps
- Document in Results section

---

## Expected Contribution Claim

Once Goals 1 & 2 are complete:

> *"We validate our hybrid physics-ML model on the peer-reviewed UCI Naval Propulsion dataset (Coraddu et al., 2014) and compare against published baselines (SVR, Random Forest) and state-of-the-art gradient boosting methods (XGBoost, LightGBM) plus statistical GAM models. Our hybrid approach achieves [X% lower RMSE] on real data, demonstrating that integrating physical fuel equations with residual learning outperforms pure ML and physics-only approaches."*

---

## Timeline & Deliverables

| Milestone | Deliverable | Due |
|-----------|-------------|-----|
| 1 | XGBoost, LightGBM, GAM model classes | This week |
| 2 | UCI data loader function | This week |
| 3 | Updated benchmark suite with 7 models | This week |
| 4 | Benchmark results on UCI dataset (results_table.csv) | Next week |
| 5 | Manuscript Results section with comparison table | 2 weeks |
| 6 | (Optional) THETIS-MRV real-world validation | Month 2 |

---

## References

- **Coraddu et al. (2014)**: Condition-Based Maintenance of Naval Propulsion Plants. UCI ML Repository. https://doi.org/10.24432/C5K31K
- **Chen & Guestrin (2016)**: XGBoost: A scalable tree boosting system. KDD 2016.
- **Ke et al. (2017)**: LightGBM: A fast, distributed gradient boosting framework. NeurIPS 2017.
- **Serven & Brummitt (2018)**: pyGAM: Generalized Additive Models in Python. https://doi.org/10.5281/zenodo.1208723
- **IMO EEDI**: Energy Efficiency Design Index for new ships. MEPC.212(63) Resolution.
