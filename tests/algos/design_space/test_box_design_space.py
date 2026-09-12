# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
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
"""Tests for the design space of a box-subdivided problem."""

from __future__ import annotations

from copy import deepcopy

import pytest
from gemseo.algos.design_space import DesignSpace
from numpy import allclose
from numpy import array
from numpy.testing import assert_allclose

from gemseo_algos_lab.algos.design_space.box_design_space import create_box_design_space
from gemseo_algos_lab.algos.design_space.box_design_space import create_box_samples
from gemseo_algos_lab.algos.design_space.box_subdivision import BoxSubdivision
from gemseo_algos_lab.disciplines.box_constraint import BoxConstraint


@pytest.fixture
def design_space() -> DesignSpace:
    """A design space with a subdivided vector variable and a plain one."""
    design_space = DesignSpace()
    design_space.add_variable(
        "x", lower_bound=0.0, upper_bound=1.0, size=2, value=array([0.1, 0.9])
    )
    design_space.add_variable("y", lower_bound=-2.0, upper_bound=2.0, value=0.0)
    design_space.add_variable("z", lower_bound=0.0, upper_bound=1.0, value=0.5)
    return design_space


@pytest.fixture
def subdivision(design_space) -> BoxSubdivision:
    """A subdivision of two of the three variables."""
    return BoxSubdivision.from_design_space(design_space, {"x": 4, "y": 2}, ["x", "y"])


@pytest.fixture
def box_design_space(subdivision, design_space):
    """The design space of the box-subdivided problem."""
    return create_box_design_space(subdivision, design_space)


def test_variables(box_design_space) -> None:
    """Check that both levels are gathered in the design space."""
    assert set(box_design_space.variable_names) == {"x", "y", "z", "x_box", "y_box"}
    assert box_design_space.categorical_variables == ["x_box", "y_box"]


def test_one_hot_sizes(box_design_space) -> None:
    """Check the size of the one-hot variables."""
    # x has 2 components with 4 subdivisions, y has 1 component with 2.
    assert box_design_space.variable_sizes["x_box"] == 2 * 4
    assert box_design_space.variable_sizes["y_box"] == 1 * 2


def test_n_members_derivation(box_design_space) -> None:
    """Check the number of members that the main problem derives.

    The outer approximation optimizer computes it as the size of the one-hot
    variable divided by the size of its catalogue, and uses it to build one
    sum-to-one constraint per component.
    """
    n_members = {
        name: int(box_design_space.variable_sizes[name] / n_catalogues)
        for name, n_catalogues in box_design_space.n_catalogues.items()
    }
    assert n_members == {"x_box": 2, "y_box": 1}


def test_bounds_are_relaxed(box_design_space, design_space) -> None:
    """Check that only the subdivided variables have widened bounds."""
    margin = BoxSubdivision.DEFAULT_BOUND_MARGIN
    assert_allclose(box_design_space.get_lower_bounds(["x"]), [-margin] * 2)
    assert_allclose(box_design_space.get_upper_bounds(["x"]), [1.0 + margin] * 2)
    assert_allclose(box_design_space.get_lower_bounds(["z"]), [0.0])
    assert_allclose(box_design_space.get_upper_bounds(["z"]), [1.0])


def test_initial_box_is_located(box_design_space) -> None:
    """Check that the initial box is the one containing the initial value."""
    # x = [0.1, 0.9] lies in the first and in the last subdivision.
    assert_allclose(
        box_design_space.get_current_value(["x_box"]),
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    )
    # y = 0.0 is on the border of the two subdivisions, hence in the first one.
    assert_allclose(box_design_space.get_current_value(["y_box"]), [1.0, 0.0])


def test_one_hot_layout_matches_the_constraint(box_design_space, subdivision) -> None:
    """Check that the constraint reads the one-hot of the design space correctly.

    The design space and the constraint must agree on the component-major
    layout of the one-hot vector, otherwise the box selected by the main problem
    is not the box enforced in the sub-problem.
    """
    discipline = BoxConstraint(subdivision)
    g_box = discipline.execute({
        "x": array([0.1, 0.9]),
        "x_box": box_design_space.get_current_value(["x_box"]),
        "y": array([0.0]),
        "y_box": box_design_space.get_current_value(["y_box"]),
    })["g_box"]
    # The first component is in [0, 0.25] and the second one in [0.75, 1].
    assert_allclose(g_box[:2], [0.1 - 0.25, 0.9 - 1.0])
    assert_allclose(g_box[3:5], [0.0 - 0.1, 0.75 - 0.9])
    assert (g_box <= 0.0).all()


def test_default_weights(box_design_space) -> None:
    """Check that the subdivision indexes are the default weights."""
    assert allclose(box_design_space.get_catalogue_weights("x_box"), [0, 1, 2, 3])


def test_custom_weights(subdivision, design_space) -> None:
    """Check that the weights can be customized."""
    box_design_space = create_box_design_space(
        subdivision, design_space, weights={"x": array([0.0, 10.0, 20.0, 30.0])}
    )
    assert allclose(
        box_design_space.get_catalogue_weights("x_box"), [0.0, 10.0, 20.0, 30.0]
    )


def test_custom_one_hot_names(subdivision, design_space) -> None:
    """Check that the one-hot names can be customized."""
    box_design_space = create_box_design_space(
        subdivision, design_space, one_hot_names={"x": "alpha_x"}
    )
    assert set(box_design_space.categorical_variables) == {"alpha_x", "y_box"}


def test_main_problem_variables(box_design_space) -> None:
    """Check the variables that the Benders formulation keeps in the main problem."""
    main_design_space = deepcopy(box_design_space).filter_non_categorical()
    assert set(main_design_space.variable_names) == {"x_box", "y_box"}


def test_unknown_variable(subdivision) -> None:
    """Check the error raised when a subdivided variable is not in the design space."""
    other_design_space = DesignSpace()
    other_design_space.add_variable("w", lower_bound=0.0, upper_bound=1.0, value=0.5)
    with pytest.raises(ValueError, match=r"not in the design space: \['x', 'y'\]"):
        create_box_design_space(subdivision, other_design_space)


def test_box_samples(subdivision) -> None:
    """Check the one-hot vectors enumerating every box."""
    samples = create_box_samples(subdivision)
    # x has 2 components with 4 subdivisions, y has 1 component with 2.
    assert samples.shape == (4 * 4 * 2, 2 * 4 + 1 * 2)
    assert samples.shape[0] == subdivision.n_boxes
    assert samples.shape[1] == subdivision.n_binaries
    # Each component of each variable selects exactly one subdivision.
    assert (samples.sum(axis=1) == 3).all()
    # No two boxes are the same.
    assert len({tuple(row) for row in samples}) == subdivision.n_boxes


def test_box_samples_match_the_design_space(subdivision, box_design_space) -> None:
    """Check that the samples have the layout of the main problem design space."""
    main_design_space = deepcopy(box_design_space).filter_non_categorical()
    size = sum(
        main_design_space.variable_sizes[name]
        for name in main_design_space.variable_names
    )
    assert create_box_samples(subdivision).shape[1] == size


def test_too_many_boxes(subdivision) -> None:
    """Check the error raised when the boxes cannot be enumerated."""
    with pytest.raises(ValueError, match=r"more than the maximum of 4"):
        create_box_samples(subdivision, max_boxes=4)
