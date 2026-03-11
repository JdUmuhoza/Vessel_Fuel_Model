import subprocess
import sys
from pathlib import Path
import pytest

def test_synthetic_cli_runs(tmp_path):
    out_dir = tmp_path / "synthetic"
    cmd = [
        sys.executable,
        "scripts/run_research_benchmark.py",
        "--use-synthetic",
        "--seed", "123",
        "--n-samples", "50",
        "--out", str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert (out_dir / "cli_summary.json").exists()


def test_real_data_cli_argument_validation():
    # Should fail if any real-data arg is missing
    cmd = [
        sys.executable,
        "scripts/run_research_benchmark.py",
        "--ais", "fake.csv",
        "--metocean", "fake.csv",
        # missing --vessels and --noon
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode != 0
    assert "must provide --ais, --metocean, --vessels, and --noon" in result.stderr.lower()

@pytest.mark.skip("Requires real CSVs to fully test real-data path.")
def test_real_data_cli_runs(tmp_path):
    # This is a placeholder for when real CSVs are available
    pass
