"""End-to-end real-data benchmark example.

Workflow:
1) Download public AIS + metocean + bathymetry
2) Optionally generate deterministic proxy vessel/noon tables
3) Run benchmark suite
"""

from __future__ import annotations

from pathlib import Path

from vessel_fuel.research import (
    clean_observations,
    download_copernicus_era5,
    download_gebco_bathymetry,
    download_noaa_ais_archive,
    fuse_operational_data,
    load_ais_segments,
    load_engine_noon,
    load_metocean,
    load_vessel_particulars,
    run_benchmark_suite,
)


def main() -> None:
    out = Path("outputs/real_example")
    out.mkdir(parents=True, exist_ok=True)

    # Keep date range short for demo runtime.
    ais_csv = download_noaa_ais_archive("2024-01-01T00:00:00Z", "2024-01-03T23:00:00Z", "north_atlantic")
    met_csv = download_copernicus_era5("-60,20,-5,62", "2024-01-01T00:00:00Z", "2024-01-03T23:00:00Z")
    _ = download_gebco_bathymetry("-60,20,-5,62")

    # Replace these with real operator or public tables when available.
    vessels_csv = out / "vessel_particulars.csv"
    noon_csv = out / "noon_reports.csv"
    if not vessels_csv.exists() or not noon_csv.exists():
        raise RuntimeError(
            "Create vessel_particulars.csv and noon_reports.csv in outputs/real_example "
            "or use CLI --fetch-data path to auto-generate deterministic proxy files."
        )

    ais = load_ais_segments(ais_csv)
    met = load_metocean(met_csv)
    ves = load_vessel_particulars(vessels_csv)
    noon = load_engine_noon(noon_csv)
    fused = fuse_operational_data(ais, met, ves, noon)
    clean = clean_observations(fused)

    summary = run_benchmark_suite(clean, out_dir=out, seed=42)
    print("Completed real-data benchmark.")
    print(summary)


if __name__ == "__main__":
    main()
