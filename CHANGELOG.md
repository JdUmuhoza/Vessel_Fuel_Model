# Changelog

## [Unreleased]

### Added
- CLI in `scripts/run_research_benchmark.py` now supports real-data CSVs via `--ais`, `--metocean`, `--vessels`, `--noon` arguments, in addition to `--use-synthetic`.
- Real-data ingestion, fusion, and cleaning using existing utilities.
- All required output artifacts are generated in the specified output directory, including `results_table.csv`, `significance.json`, `prediction_intervals.csv`, `sensitivity_ranking.csv`, `ablation_table.csv`, `summary.json`, and `cli_summary.json`.
- New test: `test_research_benchmark_cli.py` for CLI argument validation and synthetic run.
- README usage examples for both synthetic and real-data runs.
- Citation section in README and `CITATION.cff` clarifies DOI placeholder and preserves ORCID.
- Real-data acquisition helpers in `vessel_fuel/research/ingest.py`:
	- `download_noaa_ais_archive`
	- `download_copernicus_era5`
	- `download_gebco_bathymetry`
	- `align_and_merge_temporal_data`
	- `validate_data_schema`
- New guide: `docs/data_acquisition.md` (free public sourcing + formatting + alignment).
- New example: `examples/real_data_benchmark.py`.
- New tests: `tests/test_data_acquisition.py` for download mocking, alignment, schema checks, and error handling.

### Changed
- README and documentation updated for new CLI and output artifacts.
- `scripts/run_research_benchmark.py` now supports `--fetch-data` with `--region`, `--start-date`, `--end-date`, and robust fallback/error handling.

### Pending/External
- DOI value is still a placeholder; update `README.md` and `CITATION.cff` with actual DOI when available.
- Real-data CLI test is skipped until real CSVs are provided.

### Quality
- All changes are backward compatible.
- Deterministic behavior is preserved with seed control.
- CI and static checks pass.
