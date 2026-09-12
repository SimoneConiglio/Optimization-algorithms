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
"""The design space of a box-subdivided problem."""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from gemseo_bilevel_outer_approximation.algos.design_space.catalogue_design_space import (  # noqa: E501
    CatalogueDesignSpace,
)

from gemseo_algos_lab.algos.design_space.box_subdivision import BoxSubdivision

if TYPE_CHECKING:
    from collections.abc import Mapping

    from gemseo.algos.design_space import DesignSpace
    from numpy import ndarray


def create_box_design_space(
    subdivision: BoxSubdivision,
    design_space: DesignSpace,
    margin: float = BoxSubdivision.DEFAULT_BOUND_MARGIN,
    one_hot_names: Mapping[str, str] = MappingProxyType({}),
    weights: Mapping[str, ndarray] = MappingProxyType({}),
) -> CatalogueDesignSpace:
    """Create the design space of a box-subdivided problem.

    The returned design space gathers the variables of both levels:

    - the variables of the original problem, whose bounds are widened by
      :meth:`.BoxSubdivision.create_relaxed_design_space`, and which are solved
      for in the sub-problem;
    - one categorical variable per subdivided variable, selecting a subdivision
      per component, which the main problem decides.

    The ``Benders`` formulation splits the two levels apart on its own, by
    keeping the categorical variables in the main problem.

    The catalogue of a subdivided variable is the range of its subdivision
    indexes, so that the default weights make two consecutive subdivisions
    neighbours in the distance used by the main problem.

    Args:
        subdivision: The Cartesian subdivision of the design space.
        design_space: The design space of the original problem.
        margin: The relative margin applied to the bounds of the subdivided
            variables, so that a box lying against a bound keeps the multiplier
            of its face.
        one_hot_names: The name of the one-hot variable of each subdivided
            variable. If empty, suffix the design variable names with
            :attr:`.BoxSubdivision.ONE_HOT_SUFFIX`.
        weights: The weights of the subdivisions of each variable, used by the
            main problem to measure the distance between two boxes.
            If empty, use the subdivision indexes.

    Returns:
        The design space of the box-subdivided problem.

    Raises:
        ValueError: If a subdivided variable is not in the design space.
    """
    if unknown := set(subdivision.variable_names) - set(design_space.variable_names):
        msg = f"The following variables are not in the design space: {sorted(unknown)}."
        raise ValueError(msg)

    relaxed_design_space = subdivision.create_relaxed_design_space(
        design_space, margin=margin
    )
    box_design_space = CatalogueDesignSpace(name=design_space.name)
    box_design_space.extend(relaxed_design_space)

    names = subdivision.get_one_hot_names(one_hot_names)
    sizes = subdivision.sizes
    n_subdivisions = subdivision.n_subdivisions
    current_value = design_space.get_current_value(as_dict=True)
    for variable_name, one_hot_name in names.items():
        catalogue = list(range(n_subdivisions[variable_name]))
        value = current_value.get(variable_name)
        indexes = (
            subdivision.locate(variable_name, value)
            if value is not None
            else [0] * sizes[variable_name]
        )
        box_design_space.add_categorical_variable(
            one_hot_name,
            [int(index) for index in indexes],
            catalogue,
            weights=weights.get(variable_name),
        )

    return box_design_space
