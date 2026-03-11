# Quick Start: Testing PRIORITY 1

## Verify the Implementation Works

### Option 1: Run the Full Test Suite (Recommended)

```bash
# Install development dependencies if needed
pip install pytest pytest-cov

# Run only the current module tests
pytest tests/test_current.py -v

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/test_current.py --cov=vessel_fuel.current
```

### Option 2: Quick Interactive Test

```python
# Open a Python shell in the workspace
python

# Test the imports
from vessel_fuel import (
    current_vector_component,
    speed_over_ground,
    transit_time_hours,
    current_induced_resistance,
    fuel_savings_from_current,
)

# Test 1: Following current scenario
result = current_vector_component(
    current_kn=2.0,
    current_angle_deg=180.0,
    ship_heading_deg=0.0,
)
print(f"Following current: {result['current_longitudinal_kn']} kn")
# Expected: 2.0

# Test 2: Speed over ground
sog = speed_over_ground(12.0, 2.0, 180.0)
print(f"SOG with 2-kn following current: {sog} kn")
# Expected: 14.0

# Test 3: Fuel savings
fuel_result = fuel_savings_from_current(
    sfoc_main_gkwh=180.0,
    shaft_power_kw=3000.0,
    current_kn=2.0,
    current_angle_deg=180.0,  # Following
    distance_km=500.0,
    speed_through_water_kn=12.0,
)
print(f"Fuel saved with following current: {fuel_result['fuel_saved_mt']:.3f} MT")
# Expected: positive (savings)
```

### Option 3: Run Existing Model Tests

Verify that the current implementation didn't break existing functionality:

```bash
# Test that the existing fuel_model() still works
pytest tests/test_model.py -v

# The test `test_current_and_depth_affect_transit_time_and_fuel` 
# already tests current integration
```

## What to Check

1. **All 52 tests pass** ✅ (test_current.py)
2. **No breaking changes** ✅ (test_model.py still passes)
3. **Imports work** ✅ (functions available in vessel_fuel namespace)
4. **Physics makes sense** ✅ (following current saves fuel, head current costs fuel)

## Physics Verification

### Sanity Check 1: Following Current

```python
# 12-knot ship, 2-knot following current
sog = speed_over_ground(12.0, 2.0, 180.0)
assert sog == 14.0  # ✅ SOG increased
# Transit time decreased → fuel decreased
```

### Sanity Check 2: Head Current

```python
# 12-knot ship, 2-knot head current
sog = speed_over_ground(12.0, 2.0, 0.0)
assert sog == 10.0  # ✅ SOG decreased
# Transit time increased → fuel increased
```

### Sanity Check 3: Scaling Laws

```python
# Resistance scales with (velocity difference)²
# Double the velocity difference → 4x the resistance
r1 = current_induced_resistance(7.0, 6.0, 4200.0)  # 1 m/s diff
r2 = current_induced_resistance(8.0, 6.0, 4200.0)  # 2 m/s diff
assert abs(r2 / r1 - 4.0) < 0.15  # ✅ Roughly 4x
```

## Documentation Files

| File | Purpose | Location |
|------|---------|----------|
| Implementation details | Technical guide to functions | `docs/PRIORITY_1_CURRENT_IMPLEMENTATION.md` |
| Test examples | See how tests verify physics | `tests/test_current.py` |
| Research goals | Context for why this matters | `docs/research_goals.md` |
| Status summary | This checklist | `PRIORITY_1_STATUS.md` |

## Proceed to PRIORITY 2?

Once you've confirmed PRIORITY 1 is working:

**I can immediately start PRIORITY 2: Emissions Module**

This will add:
- `vessel_fuel/emissions.py` with CO2, SOx, NOx calculations
- IMO CII (Carbon Intensity Indicator) rating system
- Support for 5 ship types and 4 fuel types
- 40+ test cases
- Full integration with existing fuel_model()

**Estimated time**: 2-3 hours for complete implementation + tests + documentation

Ready to proceed? Let me know! 🚀
