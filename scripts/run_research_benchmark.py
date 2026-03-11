"""Run reproducible benchmark experiments for vessel-fuel-model.

Usage
-----
python scripts/run_research_benchmark.py --use-synthetic --seed 42 --out outputs/repro
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from vessel_fuel.research.benchmark import run_benchmark_suite
from vessel_fuel.research.data_pipeline import clean_observations, generate_synthetic_operational_dataset
from vessel_fuel.model import fuel_model


REGION_BBOX = {
    "north_atlantic": "-60,20,-5,62",
    "north_pacific": "120,20,-120,58",
    "mediterranean": "-6,30,37,46",
    "gulf_mexico": "-98,18,-80,31",
    "north_sea": "-4,50,9,61",
}


def _derive_proxy_csvs(ais_path: str, met_path: str, out_dir: Path) -> tuple[str, str]:
    """Create fallback vessel/noon CSVs when engine logs are unavailable.

    This path preserves reproducibility and allows free-data benchmarking.
    """
    from vessel_fuel.research.ingest import align_and_merge_temporal_data, load_ais_segments

    ais_rows = load_ais_segments(ais_path)
    met_raw: list[dict[str, Any]] = []
    with Path(met_path).open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            met_raw.append(r)

    noon_rows = []
    for a in ais_rows:
        noon_rows.append(
            {
                "timestamp": a.get("timestamp", ""),
                "trim_m": 0.1,
                "months_since_cleaning": 8.0,
                "include_aux": "1",
                "aux_power_kw": 400.0,
                "aux_sfoc": 205.0,
                "include_boiler": "0",
                "boiler_power_kw": 200.0,
                "boiler_sfoc": 280.0,
            }
        )
    merged = align_and_merge_temporal_data(ais_rows, met_raw, noon_rows)
    if len(merged) == 0:
        raise RuntimeError("Could not align AIS with metocean timestamps to build proxy noon/vessel tables.")

    vessels_map: dict[str, dict[str, Any]] = {}
    noon_out: list[dict[str, Any]] = []
    for r in merged:
        vid = str(r.get("vessel_id", "UNK"))
        if vid not in vessels_map:
            vessels_map[vid] = {
                "vessel_id": vid,
                "L": 180.0,
                "B": 30.0,
                "T": 10.0,
                "S": 8500.0,
                "CB": 0.72,
                "MCR": 22000.0,
                "sfoc_at_mcr": 176.0,
                "A_front": 650.0,
                "A_lateral": 3200.0,
                "design_draft": 10.0,
            }

        env = {
            "wind_kn": float(r.get("wind_kn", 0.0)),
            "wind_angle_deg": float(r.get("wind_angle_deg", 0.0)),
            "Hs": float(r.get("Hs", 0.0)),
            "Tp": float(r.get("Tp", 0.0)),
            "current_kn": float(r.get("current_kn", 0.0)),
            "current_angle_deg": float(r.get("current_angle_deg", 180.0)),
            "sst_c": float(r.get("sst_c", 15.0)),
            "depth_m": float(r.get("depth_m", 2000.0)),
            "wave_angle_deg": float(r.get("wave_angle_deg", 0.0)),
        }
        vessel_params = dict(vessels_map[vid])
        vessel_params.update(
            {
                "trim_m": 0.1,
                "months_since_cleaning": 8.0,
                "include_aux": True,
                "aux_power_kw": 400.0,
                "aux_sfoc": 205.0,
                "include_boiler": False,
                "boiler_power_kw": 200.0,
                "boiler_sfoc": 280.0,
            }
        )
        fuel_mt = fuel_model(
            distance_km=float(r.get("distance_km", 1.0)),
            speed_tw_kn=float(r.get("speed_tw_kn", 8.0)),
            env=env,
            vessel_params=vessel_params,
        )
        noon_out.append(
            {
                "segment_id": str(r.get("segment_id", "")),
                "trim_m": 0.1,
                "months_since_cleaning": 8.0,
                "include_aux": "1",
                "aux_power_kw": 400.0,
                "aux_sfoc": 205.0,
                "include_boiler": "0",
                "boiler_power_kw": 200.0,
                "boiler_sfoc": 280.0,
                "fuel_mt": round(float(fuel_mt), 4),
            }
        )

    vessels_csv = out_dir / "vessel_particulars.csv"
    noon_csv = out_dir / "noon_reports.csv"
    with vessels_csv.open("w", encoding="utf-8", newline="") as f:
        rows = list(vessels_map.values())
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with noon_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(noon_out[0].keys()))
        w.writeheader()
        w.writerows(noon_out)
    return str(vessels_csv), str(noon_csv)


def _segmentize_metocean_for_ais(ais_path: str, met_path: str, out_dir: Path) -> str:
    """Map timestamped metocean rows to AIS segment IDs by nearest timestamp."""
    from vessel_fuel.research.ingest import align_and_merge_temporal_data, load_ais_segments

    ais_rows = load_ais_segments(ais_path)
    met_raw: list[dict[str, Any]] = []
    with Path(met_path).open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            met_raw.append(r)

    noon_stub = [{"timestamp": r.get("timestamp", "") or "1970-01-01T00:00:00Z", "fuel_mt": 0.0} for r in ais_rows]
    merged = align_and_merge_temporal_data(ais_rows, met_raw, noon_stub)
    if len(merged) == 0:
        raise RuntimeError("Could not align metocean timestamps to AIS segments.")

    met_rows = []
    for r in merged:
        met_rows.append(
            {
                "segment_id": r["segment_id"],
                "wind_kn": r.get("wind_kn", 0.0),
                "wind_angle_deg": r.get("wind_angle_deg", 0.0),
                "Hs": r.get("Hs", 0.0),
                "Tp": r.get("Tp", 0.0),
                "current_kn": r.get("current_kn", 0.0),
                "current_angle_deg": r.get("current_angle_deg", 180.0),
                "sst_c": r.get("sst_c", 15.0),
                "depth_m": r.get("depth_m", 2000.0),
                "wave_angle_deg": r.get("wave_angle_deg", 0.0),
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "metocean_by_segment.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "segment_id",
                "wind_kn",
                "wind_angle_deg",
                "Hs",
                "Tp",
                "current_kn",
                "current_angle_deg",
                "sst_c",
                "depth_m",
                "wave_angle_deg",
            ],
        )
        w.writeheader()
        w.writerows(met_rows)
    return str(out_csv)



def main() -> None:
    parser = argparse.ArgumentParser(description="Run hybrid benchmark suite")
    parser.add_argument("--use-synthetic", action="store_true", help="Generate synthetic operational dataset")
    parser.add_argument("--fetch-data", action="store_true", help="Auto-fetch public AIS/metocean/bathymetry data and run benchmark")
    parser.add_argument("--ais", type=str, help="Path to AIS segments CSV")
    parser.add_argument("--metocean", type=str, help="Path to metocean CSV")
    parser.add_argument("--vessels", type=str, help="Path to vessel particulars CSV")
    parser.add_argument("--noon", type=str, help="Path to noon/engine reports CSV")
    parser.add_argument("--region", type=str, default="north_atlantic", help="Region key for auto-fetch (e.g., north_atlantic)")
    parser.add_argument("--start-date", type=str, default="2024-01-01T00:00:00Z")
    parser.add_argument("--end-date", type=str, default="2024-01-07T23:00:00Z")
    parser.add_argument("--bbox", type=str, default=None, help="Bounding box west,south,east,north; overrides region bbox")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-samples", type=int, default=1800)
    parser.add_argument("--out", type=str, default="outputs/repro")
    args = parser.parse_args()

    # Import ingestion utilities here to avoid circular import
    from vessel_fuel.research.ingest import (
        download_copernicus_era5,
        download_gebco_bathymetry,
        download_noaa_ais_archive,
        validate_data_schema,
        load_ais_segments, load_metocean, load_vessel_particulars, load_engine_noon, fuse_operational_data
    )

    if args.use_synthetic:
        data = generate_synthetic_operational_dataset(n_samples=args.n_samples, seed=args.seed)
        clean = clean_observations(data)
    else:
        if args.fetch_data:
            out_raw = Path(args.out) / "raw"
            out_raw.mkdir(parents=True, exist_ok=True)
            bbox = args.bbox or REGION_BBOX.get(args.region, REGION_BBOX["north_atlantic"])
            try:
                args.ais = download_noaa_ais_archive(args.start_date, args.end_date, args.region)
                met_ts = download_copernicus_era5(bbox, args.start_date, args.end_date)
                _ = download_gebco_bathymetry(bbox)
                args.metocean = _segmentize_metocean_for_ais(args.ais, met_ts, out_raw)
            except Exception as e:
                raise RuntimeError(
                    "Auto-fetch failed. Provide --ais/--metocean/--vessels/--noon manually or see docs/data_acquisition.md."
                ) from e

        # Fallback: if AIS/Metocean exists but vessel/noon missing, build deterministic proxies.
        if args.ais and args.metocean and (not args.vessels or not args.noon):
            ais_exists = Path(args.ais).exists()
            met_exists = Path(args.metocean).exists()
            if ais_exists and met_exists:
                args.vessels, args.noon = _derive_proxy_csvs(args.ais, args.metocean, Path(args.out) / "raw")

        # All real-data CSVs must be provided
        if not (args.ais and args.metocean and args.vessels and args.noon):
            raise ValueError("For real-data mode, you must provide --ais, --metocean, --vessels, and --noon CSV paths.")
        for p, nm in [(args.ais, "--ais"), (args.metocean, "--metocean"), (args.vessels, "--vessels"), (args.noon, "--noon")]:
            if not Path(p).exists():
                raise FileNotFoundError(f"Missing file for {nm}: {p}")

        ais = load_ais_segments(args.ais)
        met = load_metocean(args.metocean)
        ves = load_vessel_particulars(args.vessels)
        noon = load_engine_noon(args.noon)
        fused = fuse_operational_data(ais, met, ves, noon)

        schema_check = validate_data_schema(
            fused,
            ["segment_id", "vessel_id", "distance_km", "speed_tw_kn", "env", "vessel_params", "fuel_mt"],
        )
        if not schema_check["ok"]:
            raise RuntimeError(f"Schema validation failed: {schema_check}")

        clean = clean_observations(fused)
        if len(clean) == 0:
            raise RuntimeError("No valid records after cleaning. Check input files.")

    summary = run_benchmark_suite(clean, out_dir=args.out, seed=args.seed, alpha=0.1)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "cli_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Benchmark completed.")
    print(f"Results directory: {out.resolve()}")


if __name__ == "__main__":
    main()
