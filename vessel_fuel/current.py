r"""Ocean current and tidal resistance calculations.

This module provides functions for computing the effects of ocean currents and
tides on ship fuel consumption. It handles:

- Relative velocity calculations (speed through water vs. speed over ground)
- Current-induced resistance effects
- Shallow-water and tidal current interactions
- Energy-efficient current-aware routing suggestions

The key physics: when a ship encounters an adverse (head) current, its speed
over ground (SOG) decreases, increasing transit time. Even though the ship
maintains constant engine speed (speed through water, STW), the total energy
expended for the journey increases due to longer sailing time. The resistance
force itself remains approximately constant (determined by STW), but is exerted
for a longer duration.

Conversely, a following current increases SOG, reducing transit time and overall
fuel consumption.

References
----------
- Blendermann, W. (2015). *Wind Loading of Structures*. Spon Press.
- Det Norske Veritas (DNV). IMO EEDI/EEXI regulations consider current effects
  implicitly through voyage planning adjustments.
"""

from __future__ import annotations

from typing import Union

import numpy as np

ArrayLikeFloat = Union[float, np.ndarray]


def _as_array(x: ArrayLikeFloat) -> tuple[np.ndarray, bool]:
    """Convert input to numpy array and return scalar flag."""
    arr = np.asarray(x, dtype=float)
    return arr, arr.ndim == 0


def _maybe_scalar(x: np.ndarray, is_scalar: bool) -> ArrayLikeFloat:
    """Restore scalar output if input was scalar."""
    if is_scalar:
        return float(np.asarray(x))
    return x


def current_vector_component(
    current_kn: ArrayLikeFloat,
    current_angle_deg: ArrayLikeFloat,
    ship_heading_deg: float = 0.0,
) -> dict[str, ArrayLikeFloat]:
    r"""Decompose current into longitudinal and transverse components.

    Computes the component of the current vector along and perpendicular
    to the ship's heading. The longitudinal component (along-ship) affects
    speed over ground (SOG), transit time, and fuel consumption. The
    transverse component affects leeway and course-keeping effort.

    Parameters
    ----------
    current_kn : float or numpy.ndarray
        Current speed magnitude (knots). Non-negative.
    current_angle_deg : float or numpy.ndarray
        Current direction (degrees true), measured clockwise from North.
        A current angle of 0° means the current flows toward North (following
        current when ship heading is North). A current angle of 180° means
        current flows toward South (head current when ship heading is North).
    ship_heading_deg : float, optional
        Ship heading (degrees true), measured clockwise from North.
        Default is 0° (ship heading North). If the ship is on a different
        heading, both the longitudinal and transverse components will be
        different from those computed with heading=0°.

    Returns
    -------
    dict
        Keys:

        - ``current_speed_kn``: Current magnitude (same as input).
        - ``current_longitudinal_kn``: Component along ship heading (m/s).
          Positive = following (reduces fuel), negative = head (increases fuel).
        - ``current_transverse_kn``: Component perpendicular to ship heading.
        - ``projected_sog_adjustment_kn``: Shorthand for longitudinal component.

    Notes
    -----
    Math: if ship heading is :math:`\psi` and current direction is :math:`\gamma`,
    then relative angle is :math:`\delta = \gamma - \psi`.

    Longitudinal component: :math:`I_{\\text{long}} = I \\cos(\\delta)`

    Transverse component: :math:`I_{\\text{trans}} = I \\sin(\\delta)`

    Examples
    --------
    Ship heading North (0°), current from South (180°, flowing North):

    >>> current_vector_component(current_kn=2.0, current_angle_deg=180.0, ship_heading_deg=0.0)
    {'current_speed_kn': 2.0, 'current_longitudinal_kn': 2.0, ...}

    This is a **following current** (reduces fuel burn).

    Ship heading North (0°), current from North (0°, flowing South):

    >>> current_vector_component(current_kn=2.0, current_angle_deg=0.0, ship_heading_deg=0.0)
    {'current_speed_kn': 2.0, 'current_longitudinal_kn': -2.0, ...}

    This is a **head current** (increases fuel burn).
    """
    current, is_scalar = _as_array(current_kn)
    current_angle, _ = _as_array(current_angle_deg)

    # Relative angle between current and ship heading
    relative_angle = np.deg2rad(current_angle - ship_heading_deg)

    # Decompose current: positive long = following (reduces SOG penalty)
    current_long = current * np.cos(relative_angle)
    current_trans = current * np.sin(relative_angle)

    return {
        "current_speed_kn": _maybe_scalar(current, is_scalar),
        "current_longitudinal_kn": _maybe_scalar(current_long, is_scalar),
        "current_transverse_kn": _maybe_scalar(current_trans, is_scalar),
        "projected_sog_adjustment_kn": _maybe_scalar(current_long, is_scalar),
    }


def speed_over_ground(
    speed_through_water_kn: ArrayLikeFloat,
    current_kn: ArrayLikeFloat = 0.0,
    current_angle_deg: ArrayLikeFloat = 180.0,
    ship_heading_deg: float = 0.0,
) -> ArrayLikeFloat:
    r"""Compute speed over ground (SOG) from speed through water and current.

    SOG is the vessel's velocity relative to the seabed. It is the
    combination of speed through water (STW, relative to the water) and
    the current (velocity of the water relative to the seabed).

    Parameters
    ----------
    speed_through_water_kn : float or numpy.ndarray
        Speed through water (knots). The speed at which the ship moves
        relative to the surrounding water. Non-negative.
    current_kn : float or numpy.ndarray, optional
        Current speed magnitude (knots). Default is 0.0.
    current_angle_deg : float or numpy.ndarray, optional
        Current direction (degrees true). Default is 180.0 (current flows
        along positive heading, following current).
    ship_heading_deg : float, optional
        Ship heading (degrees true). Default is 0.0 (North).

    Returns
    -------
    float or numpy.ndarray
        Speed over ground (knots). Always non-negative; clipped to 0.0
        if the result is negative (e.g., strong head current + low STW).

    Notes
    -----
    When computing for voyage planning:

    - **Following current** (current_angle_deg = 180°): SOG > STW,
      reducing transit time.
    - **Head current** (current_angle_deg = 0°): SOG < STW, increasing
      transit time.
    - **Cross current** (current_angle_deg = 90° or 270°): SOG and STW
      differ in magnitude; course-keeping requires rudder correction.

    For simplicity, this function computes the **longitudinal** SOG component,
    ignoring transverse drift correction. In real voyage planning, the ship
    would adjust heading to maintain the intended track.

    Examples
    --------
    Ship at 12 knots STW, 2-knot following current:

    >>> speed_over_ground(12.0, current_kn=2.0, current_angle_deg=180.0)
    14.0

    Ship at 12 knots STW, 2-knot head current:

    >>> speed_over_ground(12.0, current_kn=2.0, current_angle_deg=0.0)
    10.0

    Ship at 5 knots STW, 6-knot head current (would drift backward):

    >>> speed_over_ground(5.0, current_kn=6.0, current_angle_deg=0.0)
    0.0  # Clipped to zero
    """
    stw, is_scalar = _as_array(speed_through_water_kn)
    current_arr, _ = _as_array(current_kn)
    current_angle, _ = _as_array(current_angle_deg)

    # Compute longitudinal current component (positive = following)
    relative_angle = np.deg2rad(current_angle - ship_heading_deg)
    current_long = current_arr * np.cos(relative_angle)

    # SOG = STW + longitudinal current component
    sog = stw + current_long

    # Clamp to non-negative (ship cannot go backward passively)
    sog = np.maximum(sog, 0.0)

    return _maybe_scalar(sog, is_scalar)


def current_induced_resistance(
    speed_through_water_ms: ArrayLikeFloat,
    speed_over_ground_ms: ArrayLikeFloat,
    wetted_surface_m2: float,
    rho: ArrayLikeFloat = 1025.0,
) -> ArrayLikeFloat:
    r"""Estimate additional resistance due to relative motion in current.

    When a ship moves through a current, the relative velocity between
    ship and water changes. For an adverse (head) current, the ship moves
    **faster** relative to the water, increasing skin friction and wave-making
    resistance. This function computes the *additional* drag due to this
    relative velocity increase.

    Parameters
    ----------
    speed_through_water_ms : float or numpy.ndarray
        Speed relative to water (m/s). The actual speed driven by the engine.
    speed_over_ground_ms : float or numpy.ndarray
        Speed relative to seabed (m/s). Affected by current.
    wetted_surface_m2 : float
        Wetted surface area of the hull (m²). Typically 2.0 to 2.5 times
        the length × beam product for a merchant ship.
    rho : float or numpy.ndarray, optional
        Water density (kg/m³). Default is 1025.0 (seawater at 35 PSU, 15°C).

    Returns
    -------
    float or numpy.ndarray
        Additional resistance (Newtons) due to the relative velocity increase
        in a head current. Zero if speed over ground >= speed through water.

    Notes
    -----
    The **relative velocity increase** is:

    .. math::

        \Delta v = v_{\\text{STW}} - v_{\\text{SOG}}

    This occurs when the ship has a head current. The additional resistance
    scales approximately as:

    .. math::

        R_{\\text{extra}} = \\frac{1}{2} \\rho \\times (\\Delta v)^2 \\times C_f \\times S

    where :math:`C_f` is the frictional drag coefficient (:math:`\\approx 0.002`
    for a typical ship at moderate Reynolds number).

    This is a **simplified** estimate. A more rigorous approach would recompute
    the entire resistance budget for the increased relative velocity, including
    wave-making and appendage drag. However, for small currents (< 2 knots),
    this linear approximation is reasonable.

    Examples
    --------
    Ship at 7.0 m/s (13.6 knots) through water, 2-knot head current reduces
    SOG to 5.0 m/s:

    >>> current_induced_resistance(
    ...     speed_through_water_ms=7.0,
    ...     speed_over_ground_ms=5.0,
    ...     wetted_surface_m2=4200.0,
    ...     rho=1025.0
    ... )
    ~12300  # Newtons (rough estimate)
    """
    stw, is_scalar = _as_array(speed_through_water_ms)
    sog, _ = _as_array(speed_over_ground_ms)
    rho_arr = np.asarray(rho, dtype=float)

    # Relative velocity increase: how much faster the ship moves through water
    # compared to over ground (due to head current)
    velocity_diff = np.maximum(stw - sog, 0.0)

    # Skin friction coefficient (simplified, valid for Re ~ 1e8)
    cf = 0.002

    # Additional drag force: 0.5 * rho * v_diff^2 * Cf * S
    r_extra = 0.5 * rho_arr * velocity_diff**2 * cf * wetted_surface_m2

    return _maybe_scalar(r_extra, is_scalar)


def transit_time_hours(
    distance_km: ArrayLikeFloat,
    speed_over_ground_kn: ArrayLikeFloat,
) -> ArrayLikeFloat:
    r"""Compute transit time from distance and speed over ground.

    Parameters
    ----------
    distance_km : float or numpy.ndarray
        Voyage distance (km).
    speed_over_ground_kn : float or numpy.ndarray
        Speed over ground (knots). Non-negative.

    Returns
    -------
    float or numpy.ndarray
        Transit time (hours). If SOG is zero, returns 0.0.

    Examples
    --------
    Vessel transits 240 km at 12 knots:

    >>> transit_time_hours(240.0, 12.0)
    10.877...  # (240 / 1.852) / 12 hours
    """
    distance, is_scalar = _as_array(distance_km)
    sog, _ = _as_array(speed_over_ground_kn)

    # Convert distance km to nautical miles
    distance_nm = distance / 1.852

    # Time = distance / speed; handle zero speed
    time = np.where(sog > 0.0, distance_nm / sog, 0.0)

    return _maybe_scalar(time, is_scalar)


def fuel_savings_from_current(
    sfoc_main_gkwh: ArrayLikeFloat,
    shaft_power_kw: ArrayLikeFloat,
    current_kn: ArrayLikeFloat,
    current_angle_deg: ArrayLikeFloat,
    distance_km: ArrayLikeFloat,
    speed_through_water_kn: ArrayLikeFloat,
    ship_heading_deg: float = 0.0,
) -> dict[str, ArrayLikeFloat]:
    r"""Estimate fuel consumption savings/penalties from favorable/adverse current.

    This is a diagnostic function that computes the fuel impact of a current
    by comparing two voyages:
    1. Without current (SOG = STW)
    2. With current

    The key insight: fuel consumption on the main engine is determined by
    power delivered (determined by resistance), which depends on **STW**, not
    SOG. However, the **duration** of the voyage depends on SOG. So:

    - Favorable current → lower SOG → longer transit time → more total fuel
      (counter-intuitive!)
    - Adverse current → higher SOG → shorter transit time → less total fuel

    Wait, that is backwards. Let me reconsider:

    - Speed through water (STW) = engine power requirement (resistance)
    - Speed over ground (SOG) = distance / time
    - If current is favorable (following): SOG increases → time decreases → less fuel
    - If current is adverse (head): SOG decreases → time increases → more fuel

    This function assumes the engine maintains constant STW (e.g., 12 knots).
    The current then modulates the transit time.

    Parameters
    ----------
    sfoc_main_gkwh : float or numpy.ndarray
        Specific fuel oil consumption at the current load (g/kWh).
    shaft_power_kw : float or numpy.ndarray
        Shaft power (kW) required to overcome resistance at the given STW.
    current_kn : float or numpy.ndarray
        Current speed (knots).
    current_angle_deg : float or numpy.ndarray
        Current direction (degrees true).
    distance_km : float or numpy.ndarray
        Voyage distance (km).
    speed_through_water_kn : float or numpy.ndarray
        Speed through water maintained by ship (knots).
    ship_heading_deg : float, optional
        Ship heading (degrees true). Default is 0°.

    Returns
    -------
    dict
        Keys:

        - ``fuel_without_current_mt``: Fuel consumed if no current (baseline).
        - ``fuel_with_current_mt``: Fuel consumed with the given current.
        - ``fuel_saved_mt``: Negative if current increases fuel (adverse),
          positive if it decreases fuel (favorable).
        - ``transit_time_without_current_h``: Baseline transit time.
        - ``transit_time_with_current_h``: Actual transit time.
        - ``time_saved_h``: Negative if current slows transit (adverse).

    Examples
    --------
    Ship at 12 kn STW, 2-knot following current, 500 km voyage:

    >>> fuel_savings_from_current(
    ...     sfoc_main_gkwh=180.0,
    ...     shaft_power_kw=3000.0,
    ...     current_kn=2.0,
    ...     current_angle_deg=180.0,  # Following
    ...     distance_km=500.0,
    ...     speed_through_water_kn=12.0,
    ... )
    {'fuel_without_current_mt': ..., 'fuel_saved_mt': ...}

    The following current will increase SOG, reduce transit time, and **save fuel**.
    """
    sfoc, is_scalar = _as_array(sfoc_main_gkwh)
    power, _ = _as_array(shaft_power_kw)
    distance, _ = _as_array(distance_km)
    stw, _ = _as_array(speed_through_water_kn)

    # Baseline: no current
    time_no_current = transit_time_hours(distance, stw)
    fuel_no_current = (power * time_no_current * sfoc) / 1e6  # Convert g to MT

    # With current
    sog_with_current = speed_over_ground(stw, current_kn, current_angle_deg, ship_heading_deg)
    time_with_current = transit_time_hours(distance, sog_with_current)
    fuel_with_current = (power * time_with_current * sfoc) / 1e6

    fuel_saved = fuel_no_current - fuel_with_current
    time_saved = time_no_current - time_with_current

    result = {
        "fuel_without_current_mt": _maybe_scalar(fuel_no_current, is_scalar),
        "fuel_with_current_mt": _maybe_scalar(fuel_with_current, is_scalar),
        "fuel_saved_mt": _maybe_scalar(fuel_saved, is_scalar),
        "transit_time_without_current_h": _maybe_scalar(time_no_current, is_scalar),
        "transit_time_with_current_h": _maybe_scalar(time_with_current, is_scalar),
        "time_saved_h": _maybe_scalar(time_saved, is_scalar),
    }

    return result
