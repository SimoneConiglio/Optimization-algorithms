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
"""Tune the convexification of the outer approximation, for each formulation.

The cuts of the outer approximation are supporting hyperplanes only on a convex
problem. On a multimodal one they can cut the global optimum off, and the
convexification is what prevents it: too small a constant and the master
converges after a couple of sub-problems on a poor point, too large a one and
the relaxation is so loose that the exploration wanders.

The constant is not transferable from one formulation to the other, so
comparing them at a single value favours whichever formulation that value
happens to suit.

This module is a script rather than a test, since a sweep takes minutes:

```shell
tox -e benchmark -- --no-header -q
python -m benchmarks.tune_convexification
```
"""

from __future__ import annotations

import logging

from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (  # noqa: E501
    BiLevelMasterOuterApproximation_Settings,
)
from numpy import median
from numpy.random import default_rng

from benchmarks.problems import RASTRIGIN_LOWER_BOUND
from benchmarks.problems import RASTRIGIN_UPPER_BOUND
from benchmarks.test_outer_approximation_vs_enumeration import FORMULATIONS
from benchmarks.test_outer_approximation_vs_enumeration import GLOBAL_OPTIMUM
from benchmarks.test_outer_approximation_vs_enumeration import _create_scenario

CONSTANTS = (0.0, 1.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 500.0)
"""The convexification constants to sweep."""

TOLERANCE = 1e-3
"""The tolerance under which the global optimum is considered reached."""


def measure(
    formulation: str, constant: float, adapt: bool, starting_points
) -> tuple[int, float, int]:
    """Measure a configuration of the outer approximation.

    Args:
        formulation: Either ``"constraint"`` or ``"normalized"``.
        constant: The convexification constant.
        adapt: Whether to adapt the convexification.
        starting_points: The starting points.

    Returns:
        The number of starting points from which the global optimum is reached,
        the worst objective value and the median number of executions.
    """
    values = []
    executions = []
    for starting_point in starting_points:
        scenario, _, objective = _create_scenario(starting_point, formulation)
        scenario.execute(
            BiLevelMasterOuterApproximation_Settings(
                max_iter=80,
                ub_tol=1e-4,
                convexification_constant=constant,
                adapt=adapt,
            )
        )
        values.append(float(scenario.optimization_result.f_opt))
        executions.append(objective.n_executions)

    hits = sum(value <= GLOBAL_OPTIMUM + TOLERANCE for value in values)
    return hits, max(values), int(median(executions))


def main(n_starting_points: int = 16, seed: int = 11) -> None:
    """Sweep the convexification of both formulations.

    Args:
        n_starting_points: The number of starting points per configuration.
        seed: The seed of the starting points.
    """
    logging.disable(logging.CRITICAL)
    rng = default_rng(seed)
    starting_points = [
        rng.uniform(RASTRIGIN_LOWER_BOUND, RASTRIGIN_UPPER_BOUND, 2)
        for _ in range(n_starting_points)
    ]
    print(
        f"{'formulation':>12} {'constant':>9} {'adapt':>6} | "
        f"{'hits':>9} {'worst f':>9} {'execs':>7}"
    )
    for formulation in FORMULATIONS:
        for adapt in (True, False):
            for constant in CONSTANTS:
                hits, worst, executions = measure(
                    formulation, constant, adapt, starting_points
                )
                print(
                    f"{formulation:>12} {constant:>9g} {adapt!s:>6} | "
                    f"{hits:>4d}/{n_starting_points:<4d} {worst:>9.4f} "
                    f"{executions:>7d}"
                )


if __name__ == "__main__":
    main()
