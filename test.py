import math

import pytest
from hypothesis import assume, given, strategies as st

from crafts import *

tiny = 1e-3
huge = 1e3

positives = st.floats(min_value=tiny, max_value=huge, allow_nan=False, allow_infinity=False)
nonnegatives = st.floats(min_value=0, max_value=huge, allow_nan=False, allow_infinity=False)
negatives = st.floats(min_value=-huge, max_value=-tiny, allow_nan=False, allow_infinity=False)
nonpositives = st.floats(min_value=-huge, max_value=0, allow_nan=False, allow_infinity=False)
finite = st.floats(min_value=-huge, max_value=huge, allow_nan=False, allow_infinity=False)
floats = st.floats(min_value=-huge, max_value=huge, allow_nan=True, allow_infinity=True)
fractions = st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False)
interior_fractions = st.floats(min_value=tiny, max_value=1.0-tiny, allow_nan=False, allow_infinity=False)

@st.composite
def crafts(draw):
    dry_mass = draw(positives)
    max_fuel_mass = draw(positives)
    fuel_mass = draw(fractions)*max_fuel_mass
    vacuum_exhaust = 10**draw(st.floats(min_value=-1, max_value=2, allow_nan=False, allow_infinity=False))
    vacuum_thrust = 10**draw(st.floats(min_value=-1, max_value=2, allow_nan=False, allow_infinity=False))
    sealevel_exhaust = draw(interior_fractions)*vacuum_exhaust
    sealevel_thrust = draw(interior_fractions)*vacuum_thrust
    return Craft(
        heatshield=draw(st.one_of(*[st.just(x) for x in ['interplanetary', 'orbital', '']])),
        lander=draw(st.booleans()),
        fuel_mass=fuel_mass,
        max_fuel_mass=max_fuel_mass,
        dry_mass=dry_mass,
        sealevel_thrust=sealevel_thrust,
        sealevel_exhaust=sealevel_exhaust,
        vacuum_thrust=vacuum_thrust,
        vacuum_exhaust=vacuum_exhaust,
        min_throttle=draw(fractions),
        unpressurized_volume=draw(nonnegatives),
        pressurized_volume=draw(nonnegatives),
        habitable_volume=draw(nonnegatives),
    )

def assert_equal(a, b):
    assert a.heatshield == b.heatshield
    assert a.lander == b.lander
    assert math.isclose(a.fuel_mass, b.fuel_mass, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.max_fuel_mass, b.max_fuel_mass, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.dry_mass, b.dry_mass, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.sealevel_thrust, b.sealevel_thrust, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.vacuum_thrust, b.vacuum_thrust, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.sealevel_exhaust, b.sealevel_exhaust, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.vacuum_exhaust, b.vacuum_exhaust, rel_tol=tiny, abs_tol=tiny)
    assert math.isclose(a.min_throttle, b.min_throttle, rel_tol=tiny, abs_tol=tiny)

@given(crafts())
def test_copy_invariants(craft):
    copied = craft.copy()
    assert copied is not craft
    assert_equal(copied, craft)

@given(crafts())
def test_empty_and_fill_invariant(craft):
    assert craft.empty().fuel_mass == 0
    assert craft.fill().fuel_mass == craft.max_fuel_mass
    assert craft.empty().total_mass() == craft.dry_mass
    assert craft.fill().total_mass() == craft.launch_mass()

@given(crafts(), fractions)
def test_total_mass_and_launch_mass(craft, fraction):
    craft = craft.with_fuel_mass(craft.max_fuel_mass * fraction)
    assert craft.dry_mass <= craft.total_mass() <= craft.launch_mass()

@given(crafts(), crafts())
def test_addition_commutativity(a, b):
    ab = a + b
    ba = b + a
    assert_equal(ab,ba)

@given(crafts(), crafts(), crafts())
def test_addition_associativity(a, b, c):
    ab_c = (a+b)+c
    a_bc = a+(b+c)
    assert_equal(ab_c,a_bc)

@given(positives, crafts(), crafts())
def test_scaling_distributivity(s, u, v):
    s_uv = s*(u+v)
    su_sv = s*u + s*v
    assert_equal(s_uv, su_sv)

@given(crafts(), fractions, interior_fractions) # fractions is not used due to slight precision errors
def test_burn_monotonicity(craft, atmospheres, fraction):
    burnt = craft.burn(fraction * craft.range(atmospheres), atmospheres)
    assert burnt.fuel_mass <= craft.fuel_mass * (1+tiny)+tiny
    assert burnt.total_mass() <= craft.total_mass() * (1+tiny)+tiny

@given(crafts(), positives, negatives)
def test_boil_monotonicity(craft, days, bel_boiloff_rate):
    boiloff_rate = 10**bel_boiloff_rate
    boiled = craft.boil(days, boiloff_rate)
    assert boiled.fuel_mass <= craft.fuel_mass * (1+tiny)+tiny
    assert boiled.total_mass() <= craft.total_mass() * (1+tiny)+tiny

@given(crafts(), fractions, interior_fractions) # fractions is not used due to slight precision errors
def test_burn_invertibility(craft, atmospheres, fraction):
    assume(tiny < craft.fuel_mass < craft.max_fuel_mass * (1-tiny)-tiny)
    speed_change = fraction * craft.range(atmospheres)
    burnt = craft.burn(speed_change, atmospheres)
    deburnt = burnt.deburn(speed_change, atmospheres)
    assert_equal(craft, deburnt)

@given(crafts(), 
    st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False), 
    st.floats(min_value=-3, max_value=-2, allow_nan=False, allow_infinity=False)) # this one is squirreley because deboil may involve dividing by tiny numbers
def test_boil_invertibility(craft, days, bel_boiloff_rate):
    assume(tiny < craft.fuel_mass < craft.max_fuel_mass * (1-tiny)-tiny)
    boiloff_rate = 10**bel_boiloff_rate
    boiled = craft.boil(days, boiloff_rate)
    deboiled = boiled.deboil(days, boiloff_rate)
    assert_equal(craft, deboiled)

@given(crafts(), fractions)
def test_exhaust_domain(craft, fraction):
    assert min(craft.sealevel_exhaust, craft.vacuum_exhaust) * (1.0-tiny)-tiny <= craft.exhaust(fraction) <= max(craft.sealevel_exhaust, craft.vacuum_exhaust) * (1.0+tiny)+tiny
    assert craft.exhaust(0) == pytest.approx(craft.vacuum_exhaust)
    assert craft.exhaust(1) == pytest.approx(craft.sealevel_exhaust)

@given(crafts(), fractions)
def test_thrust_domain(craft, fraction):
    assert min(craft.sealevel_thrust, craft.vacuum_thrust) * (1.0-tiny)-tiny <= craft.thrust(fraction) <= max(craft.sealevel_thrust, craft.vacuum_thrust) * (1.0+tiny)+tiny
    assert craft.thrust(0) == pytest.approx(craft.vacuum_thrust)
    assert craft.thrust(1) == pytest.approx(craft.sealevel_thrust)

@given(crafts())
def test_range_increasing_with_fuel_mass(craft):
    empty = craft.empty()
    full = craft.fill()
    assert empty.range(0) <= craft.range(0) <= full.range(0)
    assert empty.range(1) <= craft.range(1) <= full.range(1)

@given(crafts(), interior_fractions) # fractions is not used due to slight precision errors
def test_range_decreasing_with_pressure(craft, atmospheres):
    assert craft.range(0) >= craft.range(atmospheres) >= craft.range(1)

@given(crafts(), positives)
def test_with_fuel_mass_rejects_excess(crafts, excess):
    with pytest.raises(AssertionError):
        crafts.with_fuel_mass(crafts.max_fuel_mass + excess)

@given(crafts(), positives)
def test_with_fuel_mass_rejects_deficit(crafts, deficit):
    with pytest.raises(AssertionError):
        crafts.with_fuel_mass(-deficit)

@given(crafts())
def test_craft_vector_codec_invertibility(craft):
    codec = CraftVectorCodec()
    filled = craft.fill()
    decoded = codec.decode(codec.encode(filled))
    assert_equal(filled, decoded)

cells = st.text(
    alphabet=st.characters(blacklist_characters="\n\t"),
    min_size=1,
    max_size=20,
)

tables = st.lists(
    st.lists(cells, min_size=1, max_size=8),
    min_size=1,
    max_size=20,
)

@given(tables)
def test_delimited_table_codec_invertibility(table):
    codec = DelimitedTableTextCodec(header_count=0)
    assert codec.decode(codec.encode(table)) == [
        [cell.strip() for cell in row]
        for row in table
    ]

class MockVectorCodec:
    def encode(self, x):
        return [x]
    def decode(self, xs):
        return int(xs[1])

class IdentityCodec:
    def encode(self, x):
        return x
    def decode(self, x):
        return x

@given(st.lists(st.integers()))
def test_list_vector_codec_invertibility(xs):
    codec = ListVectorCodec(IdentityCodec())
    assert codec.decode(codec.encode(xs)) == xs

@given(st.dictionaries(st.text(min_size=1, max_size=10), st.integers(), min_size=1, max_size=20))
def test_lookup_vector_codec_invertibility(lookup):
    codec = LookupVectorCodec(MockVectorCodec(), key_id=0)
    encoded = codec.encode(lookup.items())
    decoded = codec.decode(encoded)
    assert decoded == lookup
