# Limitations and Future Work

## Current limitations
- Demonstration pipeline currently ships with synthetic operational data generation; real-data ingestion adapters are user-specific.
- Physics core is calibrated to practical research defaults and should be tuned per vessel family and sensor stack.
- Residual learner is linear-ridge for interpretability and robustness; non-linear ensembles may improve fit further.
- Conformal intervals are marginal (global) and can be expanded to conditional intervals by regime.

## Future work
- Add direct readers for AIS, metocean APIs, and noon/engine logs.
- Extend route-aware covariates using geospatial context and bathymetry products.
- Add richer probabilistic residual learners and regime-specific uncertainty.
- Add external multi-fleet benchmark datasets and hierarchical transfer learning.
