"""Tests for ocean current and tidal resistance calculations."""

import numpy as np
import pytest

from vessel_fuel.current import (
    current_induced_resistance,
    current_vector_component,
    fuel_savings_from_current,
    speed_over_ground,
    transit_time_hours,
)


class TestCurrentVectorComponent:
    """Test decomposition of current into ship-relative components."""

    def test_following_current_all_longitudinal(self):
        """Current flows along ship heading → all longitudinal component."""
        result = current_vector_component(
            current_kn=2.0,
            current_angle_deg=180.0,  # Following current
            ship_heading_deg=0.0,
        )
        assert np.isclose(result["current_longitudinal_kn"], 2.0)
        assert np.isclose(result["current_transverse_kn"], 0.0, atol=1e-10)

    def test_head_current_all_longitudinal_negative(self):
        """Current flows against ship heading → all longitudinal, negative."""
        result = current_vector_component(
            current_kn=2.0,
            current_angle_deg=0.0,  # Head current
            ship_heading_deg=0.0,
        )
        assert np.isclose(result["current_longitudinal_kn"], -2.0)
        assert np.isclose(result["current_transverse_kn"], 0.0, atol=1e-10)

    def test_cross_current_all_transverse(self):
        """Current perpendicular to heading → all transverse component."""
        result = current_vector_component(
            current_kn=2.0,
            current_angle_deg=90.0,  # Current from East (beam current)
            ship_heading_deg=0.0,
        )
        assert np.isclose(result["current_longitudinal_kn"], 0.0, atol=1e-10)
        assert np.isclose(result["current_transverse_kn"], 2.0)

    def test_diagonal_current_45_degrees(self):
        """Current at 45° off bow → equal long and transverse."""
        result = current_vector_component(
            current_kn=2.0,
            current_angle_deg=45.0,  # NE current
            ship_heading_deg=0.0,
        )
        expected = 2.0 / np.sqrt(2)
        assert np.isclose(result["current_longitudinal_kn"], expected, atol=1e-10)
        assert np.isclose(result["current_transverse_kn"], expected, atol=1e-10)

    def test_ship_heading_offset(self):
        """Current direction and ship heading both matter for decomposition."""
        # Scenario: ship heading 90° (East), current from North (0°)
        # Relative angle = 0° - 90° = -90° (quarter point)
        result = current_vector_component(
            current_kn=2.0,
            current_angle_deg=0.0,  # From North
            ship_heading_deg=90.0,  # Heading East
        )
        # Current from North hitting ship heading East = cross current
        assert np.isclose(result["current_longitudinal_kn"], 0.0, atol=1e-10)
        assert np.isclose(abs(result["current_transverse_kn"]), 2.0)

    def test_zero_current(self):
        """Zero current → all zero components."""
        result = current_vector_component(
            current_kn=0.0,
            current_angle_deg=0.0,
        )
        assert result["current_speed_kn"] == 0.0
        assert result["current_longitudinal_kn"] == 0.0
        assert result["current_transverse_kn"] == 0.0

    def test_array_input_following_current(self):
        """Array of current magnitudes with constant angle."""
        currents = np.array([1.0, 2.0, 3.0])
        result = current_vector_component(
            current_kn=currents,
            current_angle_deg=180.0,  # All following
            ship_heading_deg=0.0,
        )
        assert np.allclose(result["current_longitudinal_kn"], currents)
        assert np.allclose(result["current_transverse_kn"], 0.0, atol=1e-10)

    def test_projected_sog_adjustment_matches_longitudinal(self):
        """projected_sog_adjustment_kn should equal current_longitudinal_kn."""
        result = current_vector_component(
            current_kn=2.5,
            current_angle_deg=150.0,
            ship_heading_deg=10.0,
        )
        assert np.isclose(
            result["projected_sog_adjustment_kn"],
            result["current_longitudinal_kn"],
        )


class TestSpeedOverGround:
    """Test SOG computation from STW and current."""

    def test_following_current_increases_sog(self):
        """Following current adds to STW."""
        sog = speed_over_ground(
            speed_through_water_kn=12.0,
            current_kn=2.0,
            current_angle_deg=180.0,
        )
        assert np.isclose(sog, 14.0)

    def test_head_current_decreases_sog(self):
        """Head current subtracts from STW."""
        sog = speed_over_ground(
            speed_through_water_kn=12.0,
            current_kn=2.0,
            current_angle_deg=0.0,
        )
        assert np.isclose(sog, 10.0)

    def test_cross_current_no_effect_on_sog_magnitude(self):
        """Cross current should not change SOG magnitude (simplified model)."""
        # In this simplified model, only longitudinal component matters
        sog = speed_over_ground(
            speed_through_water_kn=12.0,
            current_kn=2.0,
            current_angle_deg=90.0,  # Cross current
        )
        assert np.isclose(sog, 12.0)

    def test_strong_head_current_clamps_sog_to_zero(self):
        """If head current exceeds STW, SOG is clamped to 0."""
        sog = speed_over_ground(
            speed_through_water_kn=5.0,
            current_kn=6.0,
            current_angle_deg=0.0,  # Strong head current
        )
        assert sog == 0.0

    def test_zero_stw_zero_sog(self):
        """Zero STW → zero SOG regardless of current."""
        sog = speed_over_ground(
            speed_through_water_kn=0.0,
            current_kn=2.0,
            current_angle_deg=180.0,
        )
        assert sog == 0.0

    def test_no_current_stw_equals_sog(self):
        """No current → SOG = STW."""
        sog = speed_over_ground(
            speed_through_water_kn=12.0,
            current_kn=0.0,
        )
        assert np.isclose(sog, 12.0)

    def test_array_stw_scalar_current(self):
        """Array STW, scalar current."""
        speeds = np.array([8.0, 10.0, 12.0])
        sog = speed_over_ground(
            speed_through_water_kn=speeds,
            current_kn=1.0,
            current_angle_deg=180.0,  # Following
        )
        expected = speeds + 1.0
        assert np.allclose(sog, expected)

    def test_scalar_stw_array_current(self):
        """Scalar STW, array of currents."""
        currents = np.array([0.0, 1.0, 2.0])
        sog = speed_over_ground(
            speed_through_water_kn=12.0,
            current_kn=currents,
            current_angle_deg=180.0,  # Following
        )
        expected = 12.0 + currents
        assert np.allclose(sog, expected)

    def test_opposing_heading_to_current(self):
        """Ship heading into wind/current (180° relative)."""
        sog = speed_over_ground(
            speed_through_water_kn=12.0,
            current_kn=3.0,
            current_angle_deg=0.0,  # Current from North, ship heading North
            ship_heading_deg=0.0,
        )
        assert np.isclose(sog, 9.0)


class TestTransitTimeHours:
    """Test transit time computation from distance and SOG."""

    def test_typical_voyage(self):
        """Typical 500 km voyage at 12 knots."""
        # 500 km = 269.9 nm
        time = transit_time_hours(distance_km=500.0, speed_over_ground_kn=12.0)
        expected = 269.9 / 12.0  # nm / kn = hours
        assert np.isclose(time, expected, rtol=1e-3)

    def test_zero_distance(self):
        """Zero distance → zero time."""
        time = transit_time_hours(distance_km=0.0, speed_over_ground_kn=12.0)
        assert time == 0.0

    def test_zero_sog(self):
        """Zero SOG → zero time (no motion)."""
        time = transit_time_hours(distance_km=500.0, speed_over_ground_kn=0.0)
        assert time == 0.0

    def test_array_distances_scalar_sog(self):
        """Array of distances, constant SOG."""
        distances = np.array([100.0, 250.0, 500.0])
        times = transit_time_hours(distance_km=distances, speed_over_ground_kn=12.0)
        expected = (distances / 1.852) / 12.0
        assert np.allclose(times, expected)

    def test_scalar_distance_array_sog(self):
        """Constant distance, array of SOG values."""
        sogs = np.array([8.0, 10.0, 12.0, 14.0])
        times = transit_time_hours(distance_km=500.0, speed_over_ground_kn=sogs)
        expected = (500.0 / 1.852) / sogs
        assert np.allclose(times, expected)

    def test_faster_sog_reduces_time(self):
        """Increasing SOG reduces transit time."""
        time_slow = transit_time_hours(distance_km=500.0, speed_over_ground_kn=10.0)
        time_fast = transit_time_hours(distance_km=500.0, speed_over_ground_kn=14.0)
        assert time_slow > time_fast


class TestCurrentInducedResistance:
    """Test additional resistance in head current scenario."""

    def test_no_current_zero_resistance(self):
        """When STW = SOG (no current), no extra resistance."""
        resistance = current_induced_resistance(
            speed_through_water_ms=7.0,
            speed_over_ground_ms=7.0,
            wetted_surface_m2=4200.0,
        )
        assert np.isclose(resistance, 0.0)

    def test_head_current_adds_resistance(self):
        """Head current (STW > SOG) creates additional resistance."""
        resistance = current_induced_resistance(
            speed_through_water_ms=7.0,
            speed_over_ground_ms=5.0,  # Head current slows SOG
            wetted_surface_m2=4200.0,
        )
        assert resistance > 0.0

    def test_following_current_no_extra_resistance(self):
        """Following current (SOG > STW) doesn't add drag in this model."""
        resistance = current_induced_resistance(
            speed_through_water_ms=7.0,
            speed_over_ground_ms=9.0,  # Following current speeds up SOG
            wetted_surface_m2=4200.0,
        )
        assert np.isclose(resistance, 0.0)

    def test_resistance_scales_with_velocity_difference_squared(self):
        """Resistance scales ~ (v_diff)^2."""
        # Case 1: 1 m/s difference
        r1 = current_induced_resistance(
            speed_through_water_ms=7.0,
            speed_over_ground_ms=6.0,
            wetted_surface_m2=4200.0,
        )
        # Case 2: 2 m/s difference
        r2 = current_induced_resistance(
            speed_through_water_ms=8.0,
            speed_over_ground_ms=6.0,
            wetted_surface_m2=4200.0,
        )
        # r2 should be ~4x larger (2^2 / 1^2)
        assert np.isclose(r2 / r1, 4.0, rtol=0.1)

    def test_resistance_scales_with_wetted_surface(self):
        """Resistance is proportional to wetted surface area."""
        r_small = current_induced_resistance(
            speed_through_water_ms=7.0,
            speed_over_ground_ms=5.0,
            wetted_surface_m2=2000.0,
        )
        r_large = current_induced_resistance(
            speed_through_water_ms=7.0,
            speed_over_ground_ms=5.0,
            wetted_surface_m2=4000.0,
        )
        assert np.isclose(r_large / r_small, 2.0)

    def test_array_velocity_differences(self):
        """Array of velocity differences."""
        stws = np.array([6.0, 7.0, 8.0])
        sogs = np.array([5.0, 5.0, 5.0])  # All same SOG
        resistances = current_induced_resistance(
            speed_through_water_ms=stws,
            speed_over_ground_ms=sogs,
            wetted_surface_m2=4200.0,
        )
        # Higher STW → larger velocity diff → more resistance
        assert np.all(np.diff(resistances) > 0)


class TestFuelSavingsFromCurrent:
    """Test voyage-level fuel impact assessment."""

    def test_following_current_saves_fuel(self):
        """Following current reduces transit time → saves fuel."""
        result = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=2.0,
            current_angle_deg=180.0,  # Following
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        assert result["time_saved_h"] > 0.0
        assert result["fuel_saved_mt"] > 0.0

    def test_head_current_costs_fuel(self):
        """Head current increases transit time → costs extra fuel."""
        result = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=2.0,
            current_angle_deg=0.0,  # Head current
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        assert result["time_saved_h"] < 0.0
        assert result["fuel_saved_mt"] < 0.0

    def test_no_current_zero_difference(self):
        """No current → fuel and time savings = 0."""
        result = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=0.0,
            current_angle_deg=0.0,
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        assert np.isclose(result["fuel_saved_mt"], 0.0)
        assert np.isclose(result["time_saved_h"], 0.0)

    def test_cross_current_negligible_effect(self):
        """Pure cross current should have negligible fuel impact (simplified model)."""
        result = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=2.0,
            current_angle_deg=90.0,  # Pure cross current
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        # In simplified model, cross current doesn't affect longitudinal SOG
        assert np.isclose(result["fuel_saved_mt"], 0.0, atol=0.01)

    def test_stronger_current_greater_impact(self):
        """Stronger following current → greater fuel savings."""
        result_weak = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=1.0,
            current_angle_deg=180.0,
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        result_strong = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=3.0,
            current_angle_deg=180.0,
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        assert result_strong["fuel_saved_mt"] > result_weak["fuel_saved_mt"]

    def test_fuel_without_vs_with_current_relationship(self):
        """Fuel with current should account for time difference."""
        result = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=2.0,
            current_angle_deg=180.0,  # Following
            distance_km=500.0,
            speed_through_water_kn=12.0,
        )
        # Verify relationship: fuel = power * time * sfoc / 1e6
        expected_no_current = (3000.0 * result["transit_time_without_current_h"] * 180.0) / 1e6
        expected_with_current = (3000.0 * result["transit_time_with_current_h"] * 180.0) / 1e6
        assert np.isclose(result["fuel_without_current_mt"], expected_no_current, rtol=1e-5)
        assert np.isclose(result["fuel_with_current_mt"], expected_with_current, rtol=1e-5)

    def test_array_inputs(self):
        """Array of distances with scalar current."""
        distances = np.array([200.0, 500.0, 1000.0])
        result = fuel_savings_from_current(
            sfoc_main_gkwh=180.0,
            shaft_power_kw=3000.0,
            current_kn=2.0,
            current_angle_deg=180.0,
            distance_km=distances,
            speed_through_water_kn=12.0,
        )
        # Longer voyages should see more absolute fuel savings
        assert np.all(np.diff(result["fuel_saved_mt"]) >= 0)
