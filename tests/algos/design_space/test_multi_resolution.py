# Copyright 2026 Simone Coniglio
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""Tests for the multi-resolution subdivision of a design space."""

from __future__ import annotations

import pytest
from numpy import allclose
from numpy import array
from numpy import linspace
from numpy.testing import assert_allclose

from gemseo_box_subdivision.algos.design_space.multi_resolution import MultiResolution


@pytest.fixture
def subdivision() -> MultiResolution:
    """A subdivision of a two-dimensional design space into four levels of two."""
    return MultiResolution(
        {"x": array([-4.1, -4.1])}, {"x": array([5.9, 5.9])}, branching=2, levels=4
    )


def test_counts(subdivision) -> None:
    """Check the resolution, the binaries and the boxes."""
    assert subdivision.resolution == 16
    # Two components, two subdivisions, four levels.
    assert subdivision.n_binaries == 16
    assert subdivision.n_boxes == 16**2
    assert subdivision.max_step == 8


def test_fewer_binaries_than_flat(subdivision) -> None:
    """The encoding must cost fewer binaries than a flat one of equal resolution."""
    flat = 2 * subdivision.resolution
    assert subdivision.n_binaries < flat


@pytest.mark.parametrize("position", linspace(0.0, 1.0, 23))
def test_locate_is_inverse_of_compute_bounds(subdivision, position) -> None:
    """Every box returned must contain the value that selected it."""
    lower = array([-4.1, -4.1])
    point = lower + position * (array([5.9, 5.9]) - lower)
    lower_bound, upper_bound = subdivision.compute_bounds(
        "x", subdivision.locate("x", point)
    )
    assert (lower_bound <= point + 1e-9).all()
    assert (point <= upper_bound + 1e-9).all()


def test_every_box_has_the_smallest_width(subdivision) -> None:
    """The width must be the range divided by the resolution, whatever the box."""
    expected = (array([5.9, 5.9]) - array([-4.1, -4.1])) / subdivision.resolution
    for position in linspace(0.0, 1.0, 11):
        point = array([-4.1, -4.1]) + position * expected * subdivision.resolution
        lower_bound, upper_bound = subdivision.compute_bounds(
            "x", subdivision.locate("x", point)
        )
        assert_allclose(upper_bound - lower_bound, expected)


def test_design_space_names_and_weights(subdivision) -> None:
    """The levels must be registered under their one-hot names, weighted by ones."""
    space = subdivision.create_design_space()
    for level in range(1, subdivision.levels + 1):
        name = subdivision.get_one_hot_name("x", level)
        assert name in space
        assert allclose(space.get_catalogue_weights(name), 1.0)

    assert subdivision.get_normalized_name("x") in space


@pytest.mark.parametrize(
    ("branching", "levels", "message"),
    [
        (1, 2, "The branching must be at least two"),
        (2, 0, "The number of levels must be at least one"),
    ],
)
def test_invalid_settings(branching, levels, message) -> None:
    """Check that the settings are validated."""
    with pytest.raises(ValueError, match=message):
        MultiResolution(
            {"x": array([0.0])}, {"x": array([1.0])}, branching=branching, levels=levels
        )


def test_mismatched_bounds() -> None:
    """Check that the bounds must describe the same variables."""
    with pytest.raises(ValueError, match="the same variables"):
        MultiResolution({"x": array([0.0])}, {"y": array([1.0])}, 2, 2)
