# Methods Section Draft

## Overview
We model vessel segment fuel consumption with an interpretable physics core and a residual learning layer:

$$
\hat{F} = F_{\text{physics}} + f_{\text{ML}}(x)
$$

where $F_{\text{physics}}$ is a modular deterministic model (calm-water resistance, aerodynamic resistance with apparent wind, wave-added resistance, fouling, propulsion efficiency, load-dependent SFOC, auxiliary and boiler terms), and $f_{\text{ML}}$ is constrained to learn only residual structure.

## Physics Core
The physics model computes segment fuel from distance, speed-through-water, environment, and vessel parameters. It includes:
- Calm-water resistance decomposition (Holtrop-Mennen style)
- Wind resistance using apparent wind (Blendermann style)
- Wave added resistance (STAWAVE-1 or Kwon, configurable)
- Fouling increment via time-dependent $\Delta C_f$
- Draft/trim and shallow-water correction factors
- Main engine load and 5-zone SFOC curve
- Auxiliary and boiler fuel components

## Residual Learner
The residual model is a regularized tabular regressor trained on:

$$
r = y - F_{\text{physics}}
$$

with engineered operational features from AIS-like, metocean, and vessel-state signals. Final prediction is clamped non-negative.

## Data Quality and Splitting
Records pass through quality flags, imputation, and anomaly filtering. Splits are group-aware by vessel class, route, and season to limit leakage across operational contexts.

## Uncertainty and Sensitivity
Uncertainty intervals use split conformal prediction on a calibration set, yielding empirical finite-sample coverage. Sensitivity ranking uses permutation-based MAE degradation.

## Baselines and Evaluation
We compare:
1. Speed-power baseline
2. Pure ML baseline
3. Physics-only model
4. Hybrid physics+residual model

Metrics: RMSE, MAE, MAPE, bias, and $R^2$. Statistical significance of hybrid improvements is tested with paired bootstrap on held-out data.
