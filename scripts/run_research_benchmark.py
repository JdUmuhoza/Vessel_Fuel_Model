"""Run reproducible benchmark experiments for vessel-fuel-model.

Usage
-----
python scripts/run_research_benchmark.py --use-synthetic --seed 42 --out outputs/repro
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vessel_fuel.research.benchmark import run_benchmark_suite
from vessel_fuel.research.data_pipeline import clean_observations, generate_synthetic_operational_dataset



def main() -> None:
    parser = argparse.ArgumentParser(description="Run hybrid benchmark suite")
    parser.add_argument("--use-synthetic", action="store_true", help="Generate synthetic operational dataset")
    parser.add_argument("--ais", type=str, help="Path to AIS segments CSV")
    parser.add_argument("--metocean", type=str, help="Path to metocean CSV")
    parser.add_argument("--vessels", type=str, help="Path to vessel particulars CSV")
    parser.add_argument("--noon", type=str, help="Path to noon/engine reports CSV")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-samples", type=int, default=1800)
    parser.add_argument("--out", type=str, default="outputs/repro")
    args = parser.parse_args()

    # Import ingestion utilities here to avoid circular import
    from vessel_fuel.research.ingest import (
        load_ais_segments, load_metocean, load_vessel_particulars, load_engine_noon, fuse_operational_data
    )

    if args.use_synthetic:
        data = generate_synthetic_operational_dataset(n_samples=args.n_samples, seed=args.seed)
        clean = clean_observations(data)
    else:
        # All real-data CSVs must be provided
        if not (args.ais and args.metocean and args.vessels and args.noon):
            raise ValueError("For real-data mode, you must provide --ais, --metocean, --vessels, and --noon CSV paths.")
        ais = load_ais_segments(args.ais)
        met = load_metocean(args.metocean)
        ves = load_vessel_particulars(args.vessels)
        noon = load_engine_noon(args.noon)
        fused = fuse_operational_data(ais, met, ves, noon)
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
