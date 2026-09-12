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
"""Multimodal problems used by the benchmarks."""

from __future__ import annotations

from gemseo.core.discipline import Discipline
from numpy import array
from numpy import atleast_2d
from numpy import cos
from numpy import pi
from numpy import sin
from numpy import sum as np_sum
from numpy import zeros

RASTRIGIN_LOWER_BOUND = -4.1
"""The lower bound of the Rastrigin benchmark.

The bounds are deliberately asymmetric, so that the global minimizer is neither
on the border of a box nor at its center.
"""

RASTRIGIN_UPPER_BOUND = 5.9
"""The upper bound of the Rastrigin benchmark."""


class Rastrigin(Discipline):
    """The Rastrigin function, whose local minima are about one unit apart."""

    def __init__(self, size: int = 2) -> None:
        """
        Args:
            size: The number of design variables.
        """  # noqa: D205, D212
        super().__init__()
        self.size = size
        self.n_executions = 0
        self.io.input_grammar.update_from_data({"x": zeros(size)})
        self.io.output_grammar.update_from_data({"f": zeros(1)})
        self.default_input_data = {"x": zeros(size)}

    def _run(self, input_data):  # noqa: ANN001, ANN202
        x = input_data["x"]
        self.n_executions += 1
        return {
            "f": array([10.0 * self.size + np_sum(x**2 - 10.0 * cos(2.0 * pi * x))])
        }

    def _compute_jacobian(self, input_names=(), output_names=()) -> None:  # noqa: ANN001
        self._init_jacobian(input_names, output_names)
        x = self.io.data["x"]
        self.jac["f"]["x"] = atleast_2d(2.0 * x + 20.0 * pi * sin(2.0 * pi * x))
