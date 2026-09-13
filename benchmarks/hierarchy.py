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
"""Subdivide coarsely, then refine the boxes that look promising.

A flat subdivision fine enough to resolve the basins spends its budget over the
whole design space. A **hierarchy** spends it where it seems to matter: a coarse
level subdivides the whole space and solves boxes with the usual method, its
boxes are ranked, and the best ones are refined, the same method running again
inside the bounds of one box with its own subdivision. The product of the two
subdivisions is the resolution reached, so a coarse level of two and a fine one
of five resolve as finely as a flat ten, while no master ever sees more than one
level at a time.

The catch is the **ranking**. The value of a box is a local solve started at its
centre, so it is meaningful only when the box holds one basin, which is exactly
what a coarse box does not do. The measurements below follow from that: the
hierarchy pays on a landscape of few broad basins, where the coarse ranking is
trustworthy, and loses on a densely multimodal one, where it is noise.

Every level counts against one budget, so the comparison with a flat run is at
equal cost:

```shell
python -m benchmarks.hierarchy
```
"""

from __future__ import annotations

import logging
import operator
from contextlib import suppress
from heapq import heapify
from heapq import heappop
from heapq import heappush
from statistics import median
from typing import TYPE_CHECKING

from gemseo import create_scenario
from gemseo.algos.design_space import DesignSpace
from gemseo.core.chains.chain import MDOChain
from gemseo.settings.formulations import DisciplinaryOpt_Settings
from gemseo.settings.opt import SLSQP_Settings
from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (  # noqa: E501
    BiLevelMasterOuterApproximation_Settings,
)
from numpy import argsort
from numpy import array
from numpy import full
from numpy.random import default_rng

from benchmarks.baselines import BudgetedCounter
from benchmarks.baselines import BudgetExceededError
from benchmarks.configurations import CONFIGURATIONS
from benchmarks.configurations import DEFAULT_CONFIGURATION
from benchmarks.problems import PROBLEMS
from benchmarks.problems import Objective
from gemseo_box_subdivision.algos.design_space.box_design_space import (
    create_box_samples,
)
from gemseo_box_subdivision.algos.design_space.box_design_space import (
    create_normalized_box_design_space,
)
from gemseo_box_subdivision.algos.design_space.box_subdivision import BoxSubdivision
from gemseo_box_subdivision.disciplines.box_mapping import BoxMapping

if TYPE_CHECKING:
    from numpy import ndarray

    from benchmarks.problems import Problem

DIMENSION = 5
"""The number of design variables."""

BUDGET = 2500
"""The budget in equivalent objective evaluations, shared by the levels."""

SEEDS = (11, 101, 202, 303, 404, 505)
"""The seeds of the starting points."""

CASES = (
    ("2 then 5, refine 1, value", {"coarse": 2, "fine": 5, "n_refined": 1}),
    (
        "2 then 5, refine 1, cuts",
        {"coarse": 2, "fine": 5, "n_refined": 1, "ranking": "cuts"},
    ),
    ("deep, 4 levels of 2, value", {"runner": "deep", "depth": 4}),
    (
        "frontier, 10 expansions, optimistic",
        {"runner": "frontier", "expansions": 10},
    ),
    (
        "frontier, 10 expansions, greedy",
        {"runner": "frontier", "expansions": 10, "score": "greedy"},
    ),
    (
        "frontier, 20 expansions, optimistic",
        {"runner": "frontier", "expansions": 20},
    ),
)
"""The hierarchies to compare, against the flat subdivisions."""


class Level:
    """A counter spending a share of the budget of a run.

    The levels of a hierarchy share the budget of the whole run, so that the
    comparison with a flat run is at equal cost, and each one is stopped when its
    own share is spent.
    """

    def __init__(self, shared: BudgetedCounter, dimension: int, allowance: int) -> None:
        """
        Args:
            shared: The counter of the whole run.
            dimension: The number of design variables.
            allowance: The share of the budget of this level.
        """  # noqa: D205, D212
        self.__shared = shared
        self.__dimension = dimension
        self.__allowance = allowance
        self.__start = shared.cost(dimension, adjoint=True)

    def __check(self) -> None:
        """Stop the level when its share is spent.

        Raises:
            BudgetExceededError: When the share of the level is spent.
        """
        spent = self.__shared.cost(self.__dimension, adjoint=True) - self.__start
        if spent >= self.__allowance:
            raise BudgetExceededError

    def objective(self, x: ndarray) -> float:
        """Return the objective, counted against the run and against the level.

        Args:
            x: The design value.

        Returns:
            The objective value.
        """
        self.__check()
        return self.__shared.objective(x)

    def gradient(self, x: ndarray) -> ndarray:
        """Return the gradient, counted against the run and against the level.

        Args:
            x: The design value.

        Returns:
            The gradient.
        """
        self.__check()
        return self.__shared.gradient(x)


def _design_space(
    lower: ndarray, upper: ndarray, dimension: int, value: ndarray
) -> DesignSpace:
    """Return a design space with the given bounds.

    Args:
        lower: The lower bounds.
        upper: The upper bounds.
        dimension: The number of design variables.
        value: The initial value.

    Returns:
        The design space.
    """
    design_space = DesignSpace()
    design_space.add_variable(
        "x", lower_bound=lower, upper_bound=upper, size=dimension, value=value
    )
    return design_space


def _solve_level(
    counter: Level, design_space: DesignSpace, dimension: int, n_subdivisions: int
) -> tuple[BoxSubdivision, list[tuple[ndarray, float, ndarray]]]:
    """Run the method once on a design space.

    Args:
        counter: The counter of the level.
        design_space: The design space of the level.
        dimension: The number of design variables.
        n_subdivisions: The number of subdivisions per variable.

    Returns:
        The subdivision, and the one-hot vector, the value and the post-optimal
        sensitivity of every solved box.
    """
    subdivision = BoxSubdivision.from_design_space(design_space, n_subdivisions)
    scenario = create_scenario(
        [MDOChain([BoxMapping(subdivision), Objective(counter, dimension)])],
        "f",
        create_normalized_box_design_space(subdivision, design_space),
        formulation_name="Benders",
        main_problem_design_variables=["x_box"],
        sub_problem_algo_settings=SLSQP_Settings(max_iter=40),
        sub_problem_formulation_settings=DisciplinaryOpt_Settings(),
    )
    settings = dict(CONFIGURATIONS[DEFAULT_CONFIGURATION])
    settings["max_step"] = subdivision.max_step
    # A budget spent inside a linearization leaves the discipline without its
    # output, which GEMSEO then reports as a missing key.
    with suppress(BudgetExceededError, KeyError):
        scenario.execute(
            BiLevelMasterOuterApproximation_Settings(
                max_iter=10000, ub_tol=1e-4, **settings
            )
        )

    problem = scenario.formulation.optimization_problem
    name = problem.objective.name
    solved = []
    for key, values in problem.database.items():
        value = values.get(name)
        slope = values.get(f"@{name}")
        if value is not None and slope is not None:
            solved.append((
                array(key.unwrap()).ravel(),
                float(value),
                array(slope).ravel(),
            ))

    return subdivision, solved


def _rank_by_value(solved, subdivision):  # noqa: ANN001, ANN201, ARG001
    """Rank the boxes by the value of the sub-problem solved inside them.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vectors, from the most promising.
    """
    return [solved[rank][0] for rank in argsort([value for _, value, _ in solved])]


def _rank_by_cuts(solved, subdivision):  # noqa: ANN001, ANN201
    r"""Rank **every** box of the subdivision by the cut model of the master.

    The cuts the master has gathered define a lower estimate of the value of the
    problem over the whole subdivision,

    $$\\hat u(\alpha) = \\max_i \\, u(\alpha^{(i)})
        + s^{(i)\top}(\alpha - \alpha^{(i)}),$$

    which is defined at the boxes the master never solved as well as at those it
    did. Ranking by it therefore proposes boxes that were never visited, where
    ranking by the value can only propose boxes whose sub-problem was solved,
    that is, at most a few dozen of them.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vectors, from the most promising.
    """
    boxes, model = _cut_model(solved, subdivision)
    return [boxes[rank] for rank in argsort(model)]


def _cut_model(solved, subdivision):  # noqa: ANN001, ANN201
    """Return every box of the subdivision and what the cuts estimate there.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vector of every box, and the value the cuts estimate there.
    """
    boxes = create_box_samples(subdivision)
    values = array([value for _, value, _ in solved])
    alphas = array([alpha for alpha, _, _ in solved])
    slopes = array([slope for _, _, slope in solved])
    # One row per box, one column per cut.
    model = (
        values[None, :] + boxes @ slopes.T - (alphas * slopes).sum(axis=1)[None, :]
    ).max(axis=1)
    return boxes, model


def _rank_mixed(solved, subdivision):  # noqa: ANN001, ANN201
    """Alternate the two rules, the first box from each in turn.

    The two rules fail on opposite landscapes: the value is noise where a coarse
    box holds many basins, and the cut model, being an optimistic estimate,
    extrapolates towards boxes far from anything solved, which is exploration
    where the value ranking already points at the right region. Taking one box
    from each in turn refines both the best box seen and the most promising
    unseen one.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vectors, from the most promising.
    """
    by_value = _rank_by_value(solved, subdivision)
    by_cuts = _rank_by_cuts(solved, subdivision)
    mixed = []
    for value_box, cut_box in zip(by_value, by_cuts, strict=False):
        for box in (value_box, cut_box):
            if not any((box == other).all() for other in mixed):
                mixed.append(box)

    return mixed


RANKINGS = {"value": _rank_by_value, "cuts": _rank_by_cuts, "mixed": _rank_mixed}
"""The rules deciding which boxes to refine, by name."""


def run_hierarchical(
    problem: Problem,
    dimension: int,
    seed: int,
    budget: int,
    coarse: int = 2,
    fine: int = 5,
    n_refined: int = 1,
    coarse_share: float = 0.25,
    ranking: str = "value",
) -> tuple[float, int]:
    """Run the two-level hierarchy.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the starting point.
        budget: The budget in equivalent objective evaluations.
        coarse: The number of subdivisions per variable of the coarse level.
        fine: The number of subdivisions per variable inside a refined box.
        n_refined: The number of boxes refined, the most promising first.
        coarse_share: The share of the budget spent on the coarse level.
        ranking: The rule deciding which boxes to refine, either ``"value"``,
            the value of the sub-problem solved inside the box, or ``"cuts"``,
            the cut model of the master, which estimates every box.

    Returns:
        The best objective value and the cost under the adjoint convention.
    """
    shared = BudgetedCounter(problem, dimension, budget, adjoint=True)
    start = default_rng(seed).uniform(
        problem.lower_bound, problem.upper_bound, dimension
    )
    subdivision = None
    solved: list[tuple[ndarray, float, ndarray]] = []
    with suppress(BudgetExceededError, KeyError):
        subdivision, solved = _solve_level(
            Level(shared, dimension, int(budget * coarse_share)),
            _design_space(
                full(dimension, problem.lower_bound),
                full(dimension, problem.upper_bound),
                dimension,
                start,
            ),
            dimension,
            coarse,
        )

    if not solved:
        return shared.best, shared.cost(dimension, adjoint=True)

    # The ranking of the coarse boxes is what the hierarchy rests on.
    promising = RANKINGS[ranking](solved, subdivision)
    allowance = max(
        1, (budget - shared.cost(dimension, adjoint=True)) // max(1, n_refined)
    )
    for one_hot in promising[:n_refined]:
        lower, upper = subdivision.compute_bounds("x", one_hot)
        with suppress(BudgetExceededError, KeyError):
            _solve_level(
                Level(shared, dimension, allowance),
                _design_space(lower, upper, dimension, 0.5 * (lower + upper)),
                dimension,
                fine,
            )

    return shared.best, shared.cost(dimension, adjoint=True)


def run_deep(
    problem: Problem,
    dimension: int,
    seed: int,
    budget: int,
    branching: int = 2,
    depth: int = 4,
    ranking: str = "value",
) -> tuple[float, int]:
    r"""Refine the same box again and again, splitting each variable in two.

    The two-level hierarchy gains nothing in the statistics of its cut model: its
    fine level still carries as many coefficients, $n \times m$, as cuts it can
    afford. A **deep and narrow** hierarchy keeps every level small, splitting
    each variable in two, so each level has $2n$ coefficients against the score
    of boxes it can afford, and the resolution reached is $2^{\text{depth}}$ per
    variable.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the starting point.
        budget: The budget in equivalent objective evaluations.
        branching: The number of subdivisions per variable at every level.
        depth: The number of levels.
        ranking: The rule deciding which box to refine.

    Returns:
        The best objective value and the cost under the adjoint convention.
    """
    shared = BudgetedCounter(problem, dimension, budget, adjoint=True)
    lower = full(dimension, problem.lower_bound)
    upper = full(dimension, problem.upper_bound)
    value = default_rng(seed).uniform(
        problem.lower_bound, problem.upper_bound, dimension
    )
    allowance = max(1, budget // depth)
    for _ in range(depth):
        subdivision = None
        solved: list[tuple[ndarray, float, ndarray]] = []
        with suppress(BudgetExceededError, KeyError):
            subdivision, solved = _solve_level(
                Level(shared, dimension, allowance),
                _design_space(lower, upper, dimension, value),
                dimension,
                branching,
            )

        if not solved:
            break

        one_hot = RANKINGS[ranking](solved, subdivision)[0]
        lower, upper = subdivision.compute_bounds("x", one_hot)
        value = 0.5 * (lower + upper)

    return shared.best, shared.cost(dimension, adjoint=True)


def run_frontier(
    problem: Problem,
    dimension: int,
    seed: int,
    budget: int,
    branching: int = 2,
    expansions: int = 10,
    score: str = "optimistic",
    max_depth: int = 8,
    n_children: int = 4,
) -> tuple[float, int]:
    """Search the boxes of every level best first, so that a run can backtrack.

    The hierarchies above descend: the box refined at one level is the only space
    the next level sees, so a wrong choice is never undone. This one keeps a
    **frontier** of open boxes from every level at once. It repeatedly takes the
    most promising box of the frontier, subdivides it, solves what it can inside
    it, and puts its children back on the frontier with their own scores. A box
    passed over early is still there to be taken later, which is what the
    descending hierarchies cannot do, and which makes this a spatial
    branch-and-bound over the subdivision.

    A box is scored either by the value of the sub-problem solved inside it, an
    upper bound on the optimum of the box, or by what the cuts of its parent
    estimate there, an optimistic estimate defined even for a box never solved:

    ``"greedy"``
        the value where it is known, and the estimate of the cuts otherwise.

    ``"optimistic"``
        the estimate of the cuts, as a branch-and-bound would, the box whose
        bound is the lowest being the one that may still hold the optimum.

    ``"solved"``
        the value, and only the boxes whose sub-problem was solved go on the
        frontier, so that it compares measurements rather than extrapolations.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the starting point.
        budget: The budget in equivalent objective evaluations.
        branching: The number of subdivisions per variable of an expansion.
        expansions: The number of boxes expanded, which sets the budget of each.
        score: The rule scoring a box, ``"optimistic"``, ``"greedy"`` or
            ``"solved"``.
        max_depth: The number of levels below which a box is not subdivided.
        n_children: The number of children of an expansion put on the frontier,
            the most promising first.

    Returns:
        The best objective value and the cost under the adjoint convention.
    """
    shared = BudgetedCounter(problem, dimension, budget, adjoint=True)
    allowance = max(1, budget // expansions)
    lower = full(dimension, problem.lower_bound)
    upper = full(dimension, problem.upper_bound)
    default_rng(seed).uniform(problem.lower_bound, problem.upper_bound, dimension)
    # The heap holds (score, tie breaker, depth, lower bounds, upper bounds).
    frontier: list[tuple[float, int, int, ndarray, ndarray]] = [
        (0.0, 0, 0, lower, upper)
    ]
    heapify(frontier)
    tie = 1
    while frontier and shared.cost(dimension, adjoint=True) < budget:
        _, _, depth, lower, upper = heappop(frontier)
        if depth >= max_depth:
            continue

        subdivision = None
        solved: list[tuple[ndarray, float, ndarray]] = []
        with suppress(BudgetExceededError, KeyError):
            subdivision, solved = _solve_level(
                Level(shared, dimension, allowance),
                _design_space(lower, upper, dimension, 0.5 * (lower + upper)),
                dimension,
                branching,
            )

        if not solved:
            continue

        observed = {tuple(alpha): value for alpha, value, _ in solved}
        boxes, model = _cut_model(solved, subdivision)
        children = []
        for one_hot, estimate in zip(boxes, model, strict=True):
            known = observed.get(tuple(one_hot))
            if score == "solved":
                # Only the boxes actually solved, scored by a measured value:
                # the frontier then compares values rather than extrapolations.
                if known is None:
                    continue

                children.append((known, one_hot))
            elif score == "greedy":
                children.append((estimate if known is None else known, one_hot))
            else:
                children.append((estimate, one_hot))

        # Push the most promising children only, a whole level of a fine
        # subdivision flooding the frontier with extrapolated estimates.
        children.sort(key=operator.itemgetter(0))
        for child, one_hot in children[:n_children]:
            child_lower, child_upper = subdivision.compute_bounds("x", one_hot)
            heappush(frontier, (float(child), tie, depth + 1, child_lower, child_upper))
            tie += 1

    return shared.best, shared.cost(dimension, adjoint=True)


RUNNERS = {
    "two_level": run_hierarchical,
    "deep": run_deep,
    "frontier": run_frontier,
}
"""The shapes of hierarchy, by name."""


def main() -> None:
    """Compare the hierarchies with the flat subdivisions they are made of."""
    logging.disable(logging.CRITICAL)
    from benchmarks.baselines import run_box_subdivision

    print(
        f"{DIMENSION} variables, budget {BUDGET}, "
        f"median over {len(SEEDS)} starting points\n"
    )
    print(f"{'problem':>18} {'method':>22} {'gap':>9} {'cost':>7} {'reached':>8}")
    for name in ("rastrigin", "ackley", "styblinski_tang"):
        problem = PROBLEMS[name]
        optimum = problem.optimum(DIMENSION)
        for label, n_subdivisions in (("flat m=2", 2), ("flat m=10", 10)):
            outcomes = [
                run_box_subdivision(
                    problem,
                    DIMENSION,
                    seed,
                    BUDGET,
                    adjoint=True,
                    n_subdivisions=n_subdivisions,
                )
                for seed in SEEDS
            ]
            _report(
                name,
                label,
                [outcome.gap(optimum) for outcome in outcomes],
                [outcome.cost_adjoint for outcome in outcomes],
            )

        for label, settings in CASES:
            # Copy, the cases being shared by the problems of the loop.
            arguments = dict(settings)
            runner = RUNNERS[arguments.pop("runner", "two_level")]
            outcomes = [
                runner(problem, DIMENSION, seed, BUDGET, **arguments) for seed in SEEDS
            ]
            _report(
                name,
                label,
                [best - optimum for best, _ in outcomes],
                [cost for _, cost in outcomes],
            )

    logging.disable(logging.NOTSET)


def _report(problem: str, label: str, gaps: list[float], costs: list[int]) -> None:
    """Print one row of the comparison.

    Args:
        problem: The name of the problem.
        label: The name of the method.
        gaps: The distances to the optimum.
        costs: The costs.
    """
    print(
        f"{problem:>18} {label:>22} {median(gaps):>9.3f} {median(costs):>7.0f}"
        f" {sum(gap <= 1e-4 for gap in gaps)}/{len(gaps)}"
    )


if __name__ == "__main__":
    main()
