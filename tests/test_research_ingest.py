from vessel_fuel.research.ingest import fuse_operational_data


def test_fuse_operational_data_basic():
    ais = [{"segment_id": "s1", "vessel_id": "v1", "distance_km": 100.0, "speed_tw_kn": 12.0, "route_id": "r1", "season": "winter"}]
    met = {"s1": {"wind_kn": 12.0, "wind_angle_deg": 30.0, "Hs": 1.5, "Tp": 8.0, "current_kn": 1.0, "current_angle_deg": 180.0, "sst_c": 15.0, "depth_m": 50.0, "wave_angle_deg": 0.0}}
    ves = {"v1": {"L": 120.0, "B": 20.0, "T": 7.0, "S": 4200.0, "CB": 0.72, "MCR": 10000.0, "sfoc_at_mcr": 180.0, "A_front": 120.0, "A_lateral": 700.0, "design_draft": 7.0}}
    noon = {"s1": {"trim_m": 0.2, "months_since_cleaning": 10.0, "include_aux": True, "aux_power_kw": 400.0, "aux_sfoc": 205.0, "include_boiler": False, "boiler_power_kw": 200.0, "boiler_sfoc": 280.0, "fuel_mt": 7.1}}

    fused = fuse_operational_data(ais, met, ves, noon)
    assert len(fused) == 1
    assert fused[0]["fuel_mt"] == 7.1
    assert fused[0]["vessel_params"]["trim_m"] == 0.2
