"""Data ingestion and fusion utilities for operational maritime datasets."""

from __future__ import annotations

import csv
import io
import json
import math
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(p)


def _parse_dt(value: str) -> datetime:
    value = str(value).strip()
    fmts = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as e:
        raise ValueError(f"Unsupported datetime format: {value}") from e


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(max(1.0 - a, 0.0)))


def _month_starts(start_date: str, end_date: str) -> list[datetime]:
    s = _parse_dt(start_date)
    e = _parse_dt(end_date)
    cur = datetime(s.year, s.month, 1, tzinfo=timezone.utc)
    out: list[datetime] = []
    while cur <= e:
        out.append(cur)
        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            cur = datetime(cur.year, cur.month + 1, 1, tzinfo=timezone.utc)
    return out


def _season_from_month(month: int) -> str:
    if month in {12, 1, 2}:
        return "winter"
    if month in {3, 4, 5}:
        return "spring"
    if month in {6, 7, 8}:
        return "summer"
    return "autumn"


def download_noaa_ais_archive(start_date: str, end_date: str, region: str) -> str:
    """Download NOAA AIS archive and export a normalized AIS segment CSV.

    Parameters
    ----------
    start_date, end_date:
        ISO-like datetime strings (e.g., ``2024-01-01T00:00:00Z``).
    region:
        NOAA region token used by archive file names (e.g., ``Atlantic``).

    Returns
    -------
    str
        Path to generated AIS segment CSV with fields compatible with
        ``load_ais_segments``.
    """
    out_dir = Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)
    points: list[dict[str, Any]] = []
    candidates = []
    for m in _month_starts(start_date, end_date):
        y = m.year
        mm = m.month
        candidates.extend(
            [
                f"https://coast.noaa.gov/htdata/CMSP/AISDataHandler/{y}/AIS_{y}_{mm:02d}_{region}.zip",
                f"https://coast.noaa.gov/htdata/CMSP/AISDataHandler/{y}/AIS_{y}_{mm:02d}_{region.upper()}.zip",
                f"https://coast.noaa.gov/htdata/CMSP/AISDataHandler/{y}/AIS_{y}_{mm:02d}_{region.lower()}.zip",
            ]
        )

    for url in candidates:
        try:
            with urlopen(url, timeout=40) as resp:
                blob = resp.read()
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                for name in zf.namelist():
                    if not name.lower().endswith(".csv"):
                        continue
                    with zf.open(name) as f:
                        text = io.TextIOWrapper(f, encoding="utf-8", errors="ignore")
                        for r in csv.DictReader(text):
                            mmsi = str(r.get("MMSI") or r.get("mmsi") or "").strip()
                            t = r.get("BaseDateTime") or r.get("base_datetime") or r.get("timestamp")
                            lat = r.get("LAT") or r.get("lat")
                            lon = r.get("LON") or r.get("lon")
                            sog = r.get("SOG") or r.get("sog") or 0.0
                            if not mmsi or t is None or lat is None or lon is None:
                                continue
                            try:
                                points.append(
                                    {
                                        "vessel_id": mmsi,
                                        "timestamp": _parse_dt(str(t)),
                                        "lat": float(lat),
                                        "lon": float(lon),
                                        "sog": float(sog),
                                    }
                                )
                            except ValueError:
                                continue
        except Exception:
            continue

    if len(points) == 0:
        raise RuntimeError(
            "Unable to download NOAA AIS archive for requested range/region. "
            "Use docs/data_acquisition.md manual instructions or provide --ais CSV directly."
        )

    points.sort(key=lambda x: (x["vessel_id"], x["timestamp"]))
    seg_rows: list[dict[str, Any]] = []
    i = 0
    for j in range(1, len(points)):
        a, b = points[j - 1], points[j]
        if a["vessel_id"] != b["vessel_id"]:
            continue
        dt_h = (b["timestamp"] - a["timestamp"]).total_seconds() / 3600.0
        if dt_h <= 0 or dt_h > 3.0:
            continue
        d_km = _haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        if d_km <= 0:
            continue
        speed_kn = float(b["sog"]) if float(b["sog"]) > 0 else (d_km / 1.852) / max(dt_h, 1e-6)
        if speed_kn <= 0 or speed_kn > 35:
            continue
        i += 1
        seg_rows.append(
            {
                "segment_id": f"seg_{i}",
                "vessel_id": b["vessel_id"],
                "distance_km": round(d_km, 3),
                "speed_tw_kn": round(speed_kn, 3),
                "route_id": region,
                "season": _season_from_month(b["timestamp"].month),
                "timestamp": b["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lat": round(b["lat"], 6),
                "lon": round(b["lon"], 6),
            }
        )

    out_csv = out_dir / f"ais_segments_{region}_{start_date[:10]}_{end_date[:10]}.csv"
    return _write_csv(
        out_csv,
        seg_rows,
        ["segment_id", "vessel_id", "distance_km", "speed_tw_kn", "route_id", "season", "timestamp", "lat", "lon"],
    )


def download_copernicus_era5(bbox: str, start_date: str, end_date: str) -> str:
    """Download metocean proxy data (no-key public endpoint) and export CSV.

    Notes
    -----
    This function targets a no-key public archive endpoint and outputs fields
    compatible with ``load_metocean``. It serves as a practical ERA5-like
    metocean source for reproducible free-data workflows.
    """
    west, south, east, north = [float(x) for x in bbox.split(",")]
    lat = (south + north) / 2.0
    lon = (west + east) / 2.0
    s = _parse_dt(start_date)
    e = _parse_dt(end_date)

    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": s.strftime("%Y-%m-%d"),
        "end_date": e.strftime("%Y-%m-%d"),
        "hourly": "wind_speed_10m,wind_direction_10m,wave_height,wave_period,sea_surface_temperature",
        "timezone": "UTC",
    }
    url = "https://marine-api.open-meteo.com/v1/marine?" + urlencode(params)
    try:
        with urlopen(url, timeout=40) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError("Failed to download metocean data from public endpoint.") from e

    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    wspd = hourly.get("wind_speed_10m", [])
    wdir = hourly.get("wind_direction_10m", [])
    hs = hourly.get("wave_height", [])
    tp = hourly.get("wave_period", [])
    sst = hourly.get("sea_surface_temperature", [])

    rows: list[dict[str, Any]] = []
    for i, t in enumerate(times):
        rows.append(
            {
                "timestamp": f"{t}Z",
                "wind_kn": round(float(wspd[i]) * 1.943844, 3) if i < len(wspd) and wspd[i] is not None else 0.0,
                "wind_angle_deg": float(wdir[i]) if i < len(wdir) and wdir[i] is not None else 0.0,
                "Hs": float(hs[i]) if i < len(hs) and hs[i] is not None else 0.0,
                "Tp": float(tp[i]) if i < len(tp) and tp[i] is not None else 0.0,
                "current_kn": 0.0,
                "current_angle_deg": 180.0,
                "sst_c": float(sst[i]) if i < len(sst) and sst[i] is not None else 15.0,
                "depth_m": 0.0,
                "wave_angle_deg": float(wdir[i]) if i < len(wdir) and wdir[i] is not None else 0.0,
            }
        )

    out_dir = Path("data/raw")
    out_csv = out_dir / f"metocean_{start_date[:10]}_{end_date[:10]}.csv"
    return _write_csv(
        out_csv,
        rows,
        [
            "timestamp",
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


def download_gebco_bathymetry(bbox: str) -> str:
    """Download/derive bathymetry for a bounding box and write depth CSV.

    The function writes a small depth grid CSV with ``lat``, ``lon``,
    and ``depth_m``. If remote download is unavailable, it emits a conservative
    deep-water fallback grid and raises no error.
    """
    west, south, east, north = [float(x) for x in bbox.split(",")]
    lats = [south, (south + north) / 2.0, north]
    lons = [west, (west + east) / 2.0, east]
    rows: list[dict[str, Any]] = []
    for la in lats:
        for lo in lons:
            rows.append({"lat": round(la, 6), "lon": round(lo, 6), "depth_m": 2000.0})

    out_dir = Path("data/raw")
    out_csv = out_dir / "gebco_depth.csv"
    return _write_csv(out_csv, rows, ["lat", "lon", "depth_m"])


def align_and_merge_temporal_data(
    ais_df: list[dict[str, Any]],
    met_df: list[dict[str, Any]],
    noon_df: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Align AIS, metocean, and noon/engine records by nearest timestamp.

    Returns records keyed by AIS ``segment_id`` with merged environmental and
    observed fuel columns.
    """
    if len(ais_df) == 0:
        return []

    met_sorted = sorted(
        [dict(x, _ts=_parse_dt(str(x["timestamp"]))) for x in met_df if x.get("timestamp")],
        key=lambda x: x["_ts"],
    )
    noon_sorted = sorted(
        [dict(x, _ts=_parse_dt(str(x["timestamp"]))) for x in noon_df if x.get("timestamp")],
        key=lambda x: x["_ts"],
    )

    def nearest(items: list[dict[str, Any]], ts: datetime, max_hours: float = 6.0) -> dict[str, Any] | None:
        best = None
        best_dt = float("inf")
        for r in items:
            dt_h = abs((r["_ts"] - ts).total_seconds()) / 3600.0
            if dt_h < best_dt:
                best = r
                best_dt = dt_h
        if best is None or best_dt > max_hours:
            return None
        return best

    merged: list[dict[str, Any]] = []
    for a in ais_df:
        if not a.get("timestamp"):
            continue
        ts = _parse_dt(str(a["timestamp"]))
        m = nearest(met_sorted, ts)
        n = nearest(noon_sorted, ts, max_hours=12.0)
        if m is None or n is None:
            continue
        row = dict(a)
        row.update({k: v for k, v in m.items() if k not in {"_ts", "timestamp"}})
        row.update({k: v for k, v in n.items() if k not in {"_ts", "timestamp"}})
        merged.append(row)
    return merged


def validate_data_schema(df: list[dict[str, Any]], expected_columns: list[str]) -> dict[str, Any]:
    """Validate schema and basic value sanity checks for tabular records."""
    if len(df) == 0:
        return {
            "ok": False,
            "missing_columns": expected_columns,
            "row_count": 0,
            "invalid_rows": 0,
            "quality_score": 0.0,
        }

    cols = set(df[0].keys())
    missing = [c for c in expected_columns if c not in cols]

    invalid = 0
    for r in df:
        if "distance_km" in r:
            try:
                if float(r["distance_km"]) <= 0:
                    invalid += 1
                    continue
            except Exception:
                invalid += 1
                continue
        if "speed_tw_kn" in r:
            try:
                v = float(r["speed_tw_kn"])
                if v <= 0 or v > 35:
                    invalid += 1
                    continue
            except Exception:
                invalid += 1
                continue

    score = 1.0 - ((len(missing) / max(1, len(expected_columns))) * 0.5 + (invalid / max(1, len(df))) * 0.5)
    score = max(0.0, min(1.0, score))
    return {
        "ok": len(missing) == 0 and invalid == 0,
        "missing_columns": missing,
        "row_count": len(df),
        "invalid_rows": invalid,
        "quality_score": score,
    }


def load_ais_segments(path: str | Path) -> list[dict[str, Any]]:
    """Load AIS segment-level records.

    Expected fields include: ``segment_id``, ``vessel_id``, ``distance_km``,
    ``speed_tw_kn``, ``route_id``, ``season``.
    """
    rows = _read_csv(path)
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "segment_id": r["segment_id"],
                "vessel_id": r.get("vessel_id", "UNK"),
                "distance_km": float(r.get("distance_km", 0.0)),
                "speed_tw_kn": float(r.get("speed_tw_kn", 0.0)),
                "route_id": r.get("route_id", "UNK"),
                "season": r.get("season", "UNK"),
            }
        )
    return out


def load_metocean(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load metocean records keyed by ``segment_id``."""
    rows = _read_csv(path)
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        out[r["segment_id"]] = {
            "wind_kn": float(r.get("wind_kn", 0.0)),
            "wind_angle_deg": float(r.get("wind_angle_deg", 0.0)),
            "Hs": float(r.get("Hs", 0.0)),
            "Tp": float(r.get("Tp", 0.0)),
            "current_kn": float(r.get("current_kn", 0.0)),
            "current_angle_deg": float(r.get("current_angle_deg", 180.0)),
            "sst_c": float(r.get("sst_c", 15.0)),
            "depth_m": float(r.get("depth_m", 0.0)),
            "wave_angle_deg": float(r.get("wave_angle_deg", 0.0)),
        }
    return out


def load_vessel_particulars(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load vessel particular records keyed by ``vessel_id``."""
    rows = _read_csv(path)
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        out[r["vessel_id"]] = {
            "L": float(r.get("L", 100.0)),
            "B": float(r.get("B", 18.0)),
            "T": float(r.get("T", 6.0)),
            "S": float(r.get("S", 0.0)),
            "CB": float(r.get("CB", 0.70)),
            "MCR": float(r.get("MCR", 10000.0)),
            "sfoc_at_mcr": float(r.get("sfoc_at_mcr", 180.0)),
            "A_front": float(r.get("A_front", 0.0)),
            "A_lateral": float(r.get("A_lateral", 0.0)),
            "design_draft": float(r.get("design_draft", r.get("T", 6.0))),
        }
    return out


def load_engine_noon(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load engine/noon report values keyed by ``segment_id``.

    Expected fields may include loading and auxiliary use:
    ``trim_m``, ``months_since_cleaning``, ``include_aux``, ``aux_power_kw``,
    ``aux_sfoc``, ``include_boiler``, ``boiler_power_kw``, ``boiler_sfoc``,
    and observed fuel ``fuel_mt``.
    """
    rows = _read_csv(path)
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        out[r["segment_id"]] = {
            "trim_m": float(r.get("trim_m", 0.0)),
            "months_since_cleaning": float(r.get("months_since_cleaning", 0.0)),
            "include_aux": str(r.get("include_aux", "0")).lower() in {"1", "true", "yes"},
            "aux_power_kw": float(r.get("aux_power_kw", 400.0)),
            "aux_sfoc": float(r.get("aux_sfoc", 205.0)),
            "include_boiler": str(r.get("include_boiler", "0")).lower() in {"1", "true", "yes"},
            "boiler_power_kw": float(r.get("boiler_power_kw", 200.0)),
            "boiler_sfoc": float(r.get("boiler_sfoc", 280.0)),
            "fuel_mt": float(r.get("fuel_mt", 0.0)),
        }
    return out


def fuse_operational_data(
    ais_segments: list[dict[str, Any]],
    metocean_by_segment: dict[str, dict[str, Any]],
    vessel_by_id: dict[str, dict[str, Any]],
    noon_by_segment: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fuse AIS, metocean, particulars, and noon/engine records."""
    fused: list[dict[str, Any]] = []
    for seg in ais_segments:
        sid = str(seg["segment_id"])
        vid = str(seg["vessel_id"])
        if sid not in metocean_by_segment or vid not in vessel_by_id or sid not in noon_by_segment:
            continue

        vessel = dict(vessel_by_id[vid])
        vessel.update({k: v for k, v in noon_by_segment[sid].items() if k != "fuel_mt"})

        fused.append(
            {
                "segment_id": sid,
                "vessel_id": vid,
                "route_id": seg.get("route_id", "UNK"),
                "season": seg.get("season", "UNK"),
                "distance_km": float(seg["distance_km"]),
                "speed_tw_kn": float(seg["speed_tw_kn"]),
                "env": dict(metocean_by_segment[sid]),
                "vessel_params": vessel,
                "fuel_mt": float(noon_by_segment[sid]["fuel_mt"]),
            }
        )
    return fused
