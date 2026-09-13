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
"""Sweep the baselines over the problems, the dimensions and the seeds.

This is the full study, which takes minutes, so it is a script rather than a
test:

```shell
python -m benchmarks.run_baselines
```

The budget grows with the dimension, since a fixed budget would favour the
low-dimensional cases of whichever method converges fastest there.
"""

from __future__ import annotations

import logging

from numpy import median

from benchmarks.baselines import METHODS
from benchmarks.baselines import run
from benchmarks.problems import PROBLEMS

DIMENSIONS = (2, 5, 10)
"""The numbers of design variables."""

SEEDS = (11, 101, 202, 303, 404)
"""The seeds of the starting points."""

BUDGET_PER_VARIABLE = 500
"""The budget in equivalent objective evaluations, per design variable."""


def main() -> None:
    """Run every method on every problem, dimension and seed."""
    logging.disable(logging.CRITICAL)
    print(
        f"median gap to the optimum and median cost over {len(SEEDS)} seeds, "
        f"budget {BUDGET_PER_VARIABLE} equivalent evaluations per variable\n"
    )
    header = f"{'problem':>16} {'n':>3} " + " ".join(
        f"{method:>22}" for method in METHODS
    )
    print(header)
    for name, problem in PROBLEMS.items():
        for dimension in DIMENSIONS:
            budget = BUDGET_PER_VARIABLE * dimension
            optimum = problem.optimum(dimension)
            cells = []
            for method in METHODS:
                records = [
                    run(method, problem, dimension, seed, budget) for seed in SEEDS
                ]
                gap = median([record.gap(optimum) for record in records])
                cost = median([record.cost_adjoint for record in records])
                reached = sum(record.gap(optimum) <= 1e-4 for record in records)
                cells.append(f"{gap:>9.3f} {cost:>6.0f} {reached}/{len(SEEDS)}")

            print(f"{name:>16} {dimension:>3} " + " ".join(f"{c:>22}" for c in cells))

    logging.disable(logging.NOTSET)


if __name__ == "__main__":
    main()
