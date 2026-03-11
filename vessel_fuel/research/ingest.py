"""Data ingestion and fusion utilities for operational maritime datasets."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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
