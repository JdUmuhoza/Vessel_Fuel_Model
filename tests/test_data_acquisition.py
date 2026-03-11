import io
import json
import zipfile
from pathlib import Path

import pytest

from vessel_fuel.research import ingest


class _Resp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_noaa_zip_bytes() -> bytes:
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        csv_text = (
            "MMSI,BaseDateTime,LAT,LON,SOG\n"
            "111111111,2024-01-01T00:00:00Z,45.0,-63.0,12.0\n"
            "111111111,2024-01-01T01:00:00Z,45.1,-62.8,12.5\n"
        )
        zf.writestr("ais.csv", csv_text)
    return mem.getvalue()


def test_download_noaa_ais_archive_mock(monkeypatch):
    zip_blob = _make_noaa_zip_bytes()

    def fake_urlopen(url, timeout=40):
        return _Resp(zip_blob)

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    out_path = ingest.download_noaa_ais_archive("2024-01-01T00:00:00Z", "2024-01-01T23:00:00Z", "north_atlantic")
    p = Path(out_path)
    assert p.exists()
    rows = ingest._read_csv(p)
    assert len(rows) >= 1
    assert "segment_id" in rows[0]
    assert "distance_km" in rows[0]


def test_download_copernicus_era5_mock(monkeypatch):
    payload = {
        "hourly": {
            "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
            "wind_speed_10m": [10.0, 12.0],
            "wind_direction_10m": [100.0, 120.0],
            "wave_height": [1.2, 1.4],
            "wave_period": [7.0, 7.5],
            "sea_surface_temperature": [15.0, 15.2],
        }
    }

    def fake_urlopen(url, timeout=40):
        return _Resp(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(ingest, "urlopen", fake_urlopen)
    out_path = ingest.download_copernicus_era5("-60,20,-5,62", "2024-01-01T00:00:00Z", "2024-01-01T23:00:00Z")
    p = Path(out_path)
    assert p.exists()
    rows = ingest._read_csv(p)
    assert len(rows) == 2
    assert "wind_kn" in rows[0]


def test_align_and_validate_paths():
    ais = [
        {
            "segment_id": "s1",
            "vessel_id": "v1",
            "distance_km": 100.0,
            "speed_tw_kn": 12.0,
            "route_id": "r1",
            "season": "winter",
            "timestamp": "2024-01-01T01:00:00Z",
        }
    ]
    met = [
        {
            "timestamp": "2024-01-01T01:00:00Z",
            "wind_kn": 10.0,
            "wind_angle_deg": 20.0,
            "Hs": 1.2,
            "Tp": 7.0,
            "current_kn": 0.3,
            "current_angle_deg": 180.0,
            "sst_c": 14.0,
            "depth_m": 200.0,
            "wave_angle_deg": 30.0,
        }
    ]
    noon = [
        {
            "timestamp": "2024-01-01T02:00:00Z",
            "fuel_mt": 6.5,
            "trim_m": 0.1,
            "months_since_cleaning": 6,
        }
    ]

    merged = ingest.align_and_merge_temporal_data(ais, met, noon)
    assert len(merged) == 1

    chk = ingest.validate_data_schema(
        merged,
        ["segment_id", "vessel_id", "distance_km", "speed_tw_kn", "fuel_mt"],
    )
    assert chk["ok"] is True
    assert chk["invalid_rows"] == 0


def test_validate_schema_detects_issues():
    bad = [{"segment_id": "s1", "distance_km": -1, "speed_tw_kn": 99}]
    chk = ingest.validate_data_schema(bad, ["segment_id", "distance_km", "speed_tw_kn", "fuel_mt"])
    assert chk["ok"] is False
    assert "fuel_mt" in chk["missing_columns"]
    assert chk["invalid_rows"] >= 1


def test_download_noaa_ais_archive_error(monkeypatch):
    def fail_urlopen(url, timeout=40):
        raise RuntimeError("network down")

    monkeypatch.setattr(ingest, "urlopen", fail_urlopen)
    with pytest.raises(RuntimeError):
        ingest.download_noaa_ais_archive("2024-01-01T00:00:00Z", "2024-01-01T23:00:00Z", "north_atlantic")
