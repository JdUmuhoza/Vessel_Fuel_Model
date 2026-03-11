# Experiment Protocol

## Inputs
- AIS-like operational features (speed-through-water, segment distance)
- Meteocean features (wind speed/direction, wave height/period, current, SST, depth)
- Vessel particulars and operating state (dimensions, block coefficient, draft/trim, fouling age)
- Optional engine/noon-report aligned fields

## Workflow
1. Data ingestion and schema validation
2. Quality flag generation and filtering
3. Missing-value imputation and anomaly filtering
4. Group-aware train/validation/test split by vessel class, route, and season
5. Train four model families (speed-power, pure ML, physics-only, hybrid)
6. Compute metrics on held-out test set
7. Estimate hybrid uncertainty bands with conformal calibration
8. Run ablation by removing one feature block at a time
9. Compute paired bootstrap significance for hybrid-vs-baselines
10. Export reproducible tables and diagnostics files

## Reproducibility controls
- Fixed seeds (`--seed`)
- Deterministic split function
- Versioned output artifacts in one directory

## Command
python scripts/run_research_benchmark.py --use-synthetic --seed 42 --out outputs/repro
