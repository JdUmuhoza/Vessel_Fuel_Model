# Real Maritime Data Acquisition Guide

This guide explains how to source free public data for the real-data benchmark path in vessel-fuel-model.

## Scope

Data families used by the pipeline:

- AIS trajectories/positions (NOAA AIS archive)
- Meteocean forcing (free marine weather endpoints; ERA5-like variables)
- Bathymetry/depth context (GEBCO)
- Vessel particulars and noon/engine records (public defaults + user operational logs)

## 1) NOAA AIS archive (free)

Primary source:
- https://coast.noaa.gov/htdata/CMSP/AISDataHandler/

Typical file naming (monthly zip):
- AIS_YYYY_MM_<REGION>.zip

Example fetch (PowerShell/curl style):

```bash
curl -L -o AIS_2024_01_Atlantic.zip "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2024/AIS_2024_01_Atlantic.zip"
```

The ingestion utility `download_noaa_ais_archive(start_date, end_date, region)` will:
- try common NOAA URL variants,
- read zipped CSVs,
- extract vessel ID, timestamp, position, SOG,
- generate normalized segment-level file compatible with `load_ais_segments()`.

Expected output columns:
- `segment_id`, `vessel_id`, `distance_km`, `speed_tw_kn`, `route_id`, `season`
- optional metadata: `timestamp`, `lat`, `lon`

## 2) Meteocean variables (free, no key)

For no-key workflows, the code uses a public marine archive endpoint to produce ERA5-like variables:
- wind speed/direction,
- significant wave height,
- wave period,
- sea-surface temperature.

Utility:
- `download_copernicus_era5(bbox, start_date, end_date)`

Output columns (compatible with `load_metocean()` after alignment):
- `wind_kn`, `wind_angle_deg`, `Hs`, `Tp`, `current_kn`, `current_angle_deg`, `sst_c`, `depth_m`, `wave_angle_deg`
- plus `timestamp` before segment alignment.

## 3) GEBCO bathymetry

Source:
- https://www.gebco.net/

Utility:
- `download_gebco_bathymetry(bbox)`

Output columns:
- `lat`, `lon`, `depth_m`

Depth is used to enrich metocean/environmental context (e.g., shallow-water effects).

## 4) Temporal alignment strategy

Use `align_and_merge_temporal_data(ais_df, met_df, noon_df)`.

Recommended policy:
- AIS segment timestamp is the reference.
- Match metocean by nearest timestamp within ±6 hours.
- Match noon/engine reports by nearest timestamp within ±12 hours.
- Drop unmatched segments (document dropped fraction).

## 5) Vessel particulars and noon/engine logs

Real vessel particulars can come from:
- operator fleet sheets,
- vessel public registries,
- class/technical documents.

Noon/engine logs are typically proprietary. For fully public reproducible runs, the CLI can generate deterministic proxy noon/vessel files when only AIS+metocean are available.

## 6) Date range and coverage recommendations

For publication-grade evaluation:
- Minimum: 3 months continuous period.
- Preferred: 6–12 months spanning multiple seasons.
- Include 5–10 route groups (container/tanker/bulk where available).

Quality caveats:
- AIS gaps near coastal handover or satellite outages.
- Position spikes and implausible SOG values.
- Meteocean spatial mismatch when using coarse bbox-centroid extraction.
- Noon logs may be sparse or missing for some voyages.

## 7) Manual workflow

If you prefer manual sourcing:
1. Download AIS monthly archives from NOAA.
2. Download metocean archive for same date range and AOI.
3. Prepare vessel/noon CSVs with required columns.
4. Run:

```bash
python scripts/run_research_benchmark.py \
  --ais data/ais_segments.csv \
  --metocean data/metocean.csv \
  --vessels data/vessel_particulars.csv \
  --noon data/noon_reports.csv \
  --seed 42 --out outputs/real
```

## 8) Auto-fetch workflow

```bash
python scripts/run_research_benchmark.py \
  --fetch-data \
  --region north_atlantic \
  --start-date 2024-01-01T00:00:00Z \
  --end-date 2024-01-07T23:00:00Z \
  --seed 42 --out outputs/repro
```

If fetching fails due to endpoint availability, provide local CSVs explicitly and re-run.
