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
"""The methods compared by the benchmarks, behind one interface.

Every method is given the **same budget of objective evaluations** and is stopped
as soon as it is spent, so that the comparison is at equal cost rather than at
equal number of iterations, which means nothing across such different methods.

Because a method using the gradient cannot be compared with one that does not on
the number of objective evaluations alone, the budget is counted in *equivalent*
evaluations, under one of two conventions:

- ``adjoint``, where a gradient costs one evaluation, which is the situation the
  box-subdivision method targets, an adjoint being available;
- ``finite differences``, where a gradient costs as many evaluations as there are
  design variables, which is the situation of a black box.

The methods that do not use the gradient are unaffected by the convention, so
reporting both brackets the comparison instead of picking the flattering one.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gemseo import create_scenario
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.opt.factory import OptimizationLibraryFactory
from gemseo.algos.optimization_problem import OptimizationProblem
from gemseo.core.chains.chain import MDOChain
from gemseo.core.mdo_functions.mdo_function import MDOFunction
from gemseo.settings.formulations import DisciplinaryOpt_Settings
from gemseo.settings.opt import SLSQP_Settings
from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (  # noqa: E501
    BiLevelMasterOuterApproximation_Settings,
)
from numpy import full
from numpy.random import default_rng

from benchmarks.problems import Counter
from benchmarks.problems import Objective
from gemseo_box_subdivision.algos.design_space.box_design_space import (
    create_normalized_box_design_space,
)
from gemseo_box_subdivision.algos.design_space.box_subdivision import BoxSubdivision
from gemseo_box_subdivision.disciplines.box_mapping import BoxMapping

if TYPE_CHECKING:
    from numpy import ndarray

    from benchmarks.problems import Problem

CONVEXIFICATION_CONSTANT = 100.0
"""The convexification tuned for the normalized formulation."""

MAX_BOXES = 100
"""The number of boxes the subdivision aims at, whatever the dimension.

The number of subdivisions per variable cannot be held fixed as the dimension
grows: the boxes being the Cartesian product, a fixed number of them per variable
makes their count explode, and the cut model of the master, built from a handful
of solved boxes, can no longer discriminate between them. Holding the *product*
roughly constant instead keeps the master informative, at the price of coarser
boxes, which is the other requirement, each box having to be close to unimodal
for its local solve to return the box optimum.

These two requirements conflict, and the conflict is what bounds the
applicability of the method: it needs the subdivision to resolve the basins of
the landscape, so it suits a problem with a moderate number of basins rather
than a densely multimodal one.

This value was read off the sweep, not derived: it reproduces ten subdivisions
in two dimensions and two in five, which are the best observed there. The
number of subdivisions that suits a problem depends on the spacing of its
basins, not on its dimension alone, so no rule in the dimension alone is
right; this one only keeps the default sane as the dimension grows.
"""


def default_n_subdivisions(dimension: int, max_boxes: int = MAX_BOXES) -> int:
    """Return the number of subdivisions keeping the number of boxes bounded.

    Args:
        dimension: The number of design variables.
        max_boxes: The number of boxes aimed at.

    Returns:
        The number of subdivisions per variable, at least two.
    """
    return max(2, int(max_boxes ** (1.0 / dimension)))


METHODS = ("box_subdivision", "multistart", "cmaes", "direct")
"""The methods compared."""


class BudgetExceededError(Exception):
    """Raised to stop a method once its budget of evaluations is spent."""


@dataclass(frozen=True)
class Result:
    """The outcome of one run of one method."""

    method: str
    problem: str
    dimension: int
    seed: int
    best: float
    n_objective: int
    n_gradient: int
    cost_adjoint: int
    cost_finite_differences: int

    def gap(self, optimum: float) -> float:
        """Return the distance to the global minimum.

        Args:
            optimum: The global minimum.

        Returns:
            The distance to the global minimum.
        """
        return self.best - optimum


class BudgetedCounter(Counter):
    """A counter that stops a method once its budget is spent."""

    def __init__(
        self, problem: Problem, dimension: int, budget: int, adjoint: bool
    ) -> None:
        """
        Args:
            problem: The problem to count the calls to.
            dimension: The number of design variables.
            budget: The budget in equivalent objective evaluations.
            adjoint: Whether a gradient costs one objective evaluation.
        """  # noqa: D205, D212
        super().__init__(problem)
        self.__dimension = dimension
        self.__budget = budget
        self.__adjoint = adjoint

    def __check(self) -> None:
        """Stop the method when the budget is spent.

        Raises:
            BudgetExceededError: When the budget is spent.
        """
        if self.cost(self.__dimension, self.__adjoint) >= self.__budget:
            raise BudgetExceededError

    def objective(self, x: ndarray) -> float:  # noqa: D102
        self.__check()
        return super().objective(x)

    def gradient(self, x: ndarray) -> ndarray:  # noqa: D102
        self.__check()
        return super().gradient(x)


def _design_space(problem: Problem, dimension: int, value: ndarray) -> DesignSpace:
    """Return the design space of a problem.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        value: The initial value.

    Returns:
        The design space.
    """
    design_space = DesignSpace()
    design_space.add_variable(
        "x",
        lower_bound=problem.lower_bound,
        upper_bound=problem.upper_bound,
        size=dimension,
        value=value,
    )
    return design_space


def _starting_point(problem: Problem, dimension: int, seed: int) -> ndarray:
    """Return a starting point drawn at random in the bounds.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the draw.

    Returns:
        The starting point.
    """
    return default_rng(seed).uniform(
        problem.lower_bound, problem.upper_bound, dimension
    )


def run_box_subdivision(
    problem: Problem,
    dimension: int,
    seed: int,
    budget: int,
    adjoint: bool,
    n_subdivisions: int = 0,
) -> Result:
    """Run the box-subdivision outer approximation.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the starting point.
        budget: The budget in equivalent objective evaluations.
        adjoint: Whether a gradient costs one objective evaluation.
        n_subdivisions: The number of subdivisions per variable.
            If zero, use :func:`.default_n_subdivisions`.

    Returns:
        The outcome of the run.
    """
    counter = BudgetedCounter(problem, dimension, budget, adjoint)
    design_space = _design_space(
        problem, dimension, _starting_point(problem, dimension, seed)
    )
    subdivision = BoxSubdivision.from_design_space(
        design_space, n_subdivisions or default_n_subdivisions(dimension)
    )
    scenario = create_scenario(
        [MDOChain([BoxMapping(subdivision), Objective(counter, dimension)])],
        "f",
        create_normalized_box_design_space(subdivision, design_space),
        formulation_name="Benders",
        main_problem_design_variables=["x_box"],
        sub_problem_algo_settings=SLSQP_Settings(max_iter=40),
        sub_problem_formulation_settings=DisciplinaryOpt_Settings(),
    )
    with suppress(BudgetExceededError):
        scenario.execute(
            BiLevelMasterOuterApproximation_Settings(
                max_iter=10000,
                ub_tol=1e-4,
                convexification_constant=CONVEXIFICATION_CONSTANT,
                adapt=True,
            )
        )

    return _result("box_subdivision", problem, dimension, seed, counter, adjoint)


def run_multistart(
    problem: Problem,
    dimension: int,
    seed: int,
    budget: int,
    adjoint: bool,
    n_start: int = 50,
) -> Result:
    """Run the multistart of a local solver, the reference of this problem class.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the design of experiments of the starting points.
        budget: The budget in equivalent objective evaluations.
        adjoint: Whether a gradient costs one objective evaluation.
        n_start: The number of starting points.

    Returns:
        The outcome of the run.
    """
    counter = BudgetedCounter(problem, dimension, budget, adjoint)
    design_space = _design_space(
        problem, dimension, _starting_point(problem, dimension, seed)
    )
    optimization_problem = OptimizationProblem(design_space)
    optimization_problem.objective = MDOFunction(
        counter.objective, "f", jac=counter.gradient
    )
    with suppress(BudgetExceededError):
        OptimizationLibraryFactory().execute(
            optimization_problem,
            algo_name="MultiStart",
            n_start=n_start,
            # MultiStart apportions its own max_iter across the starts, so the
            # settings of the sub-optimization must not carry one.
            opt_algo_settings={},
            doe_algo_settings={"seed": seed},
            max_iter=10000,
        )

    return _result("multistart", problem, dimension, seed, counter, adjoint)


def run_cmaes(
    problem: Problem, dimension: int, seed: int, budget: int, adjoint: bool
) -> Result:
    """Run CMA-ES, which does not use the gradient.

    Its budget is enforced by its own ``maxfevals``, which is exact.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the strategy.
        budget: The budget in objective evaluations.
        adjoint: Unused, CMA-ES using no gradient.

    Returns:
        The outcome of the run.
    """
    import cma

    counter = Counter(problem)
    lower, upper = problem.lower_bound, problem.upper_bound
    with suppress(BudgetExceededError):
        cma.fmin(
            counter.objective,
            _starting_point(problem, dimension, seed),
            (upper - lower) / 4.0,
            options={
                "bounds": [lower, upper],
                "maxfevals": budget,
                "seed": seed,
                "verbose": -9,
                "verb_disp": 0,
                "verb_log": 0,
            },
        )

    return _result("cmaes", problem, dimension, seed, counter, adjoint)


def run_direct(
    problem: Problem, dimension: int, seed: int, budget: int, adjoint: bool
) -> Result:
    """Run DIRECT, which is deterministic and ignores the starting point.

    Its budget is enforced by its own ``maxfun``, which is exact. Raising from
    its objective is not an option, since it is called from a C extension.

    Args:
        problem: The problem.
        dimension: The number of design variables.
        seed: Recorded for the report; DIRECT does not use it.
        budget: The budget in objective evaluations.
        adjoint: Unused, DIRECT using no gradient.

    Returns:
        The outcome of the run.
    """
    from scipy.optimize import direct

    counter = Counter(problem)
    bounds = list(
        zip(
            full(dimension, problem.lower_bound),
            full(dimension, problem.upper_bound),
            strict=True,
        )
    )
    with suppress(BudgetExceededError):
        direct(counter.objective, bounds, maxfun=budget, maxiter=budget)

    return _result("direct", problem, dimension, seed, counter, adjoint)


def _result(
    method: str,
    problem: Problem,
    dimension: int,
    seed: int,
    counter: Counter,
    adjoint: bool,  # noqa: ARG001
) -> Result:
    """Assemble the outcome of a run.

    Args:
        method: The name of the method.
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the run.
        counter: The counter of the calls.
        adjoint: Unused, both conventions being reported.

    Returns:
        The outcome of the run.
    """
    return Result(
        method=method,
        problem=problem.name,
        dimension=dimension,
        seed=seed,
        best=counter.best,
        n_objective=counter.n_objective,
        n_gradient=counter.n_gradient,
        cost_adjoint=counter.cost(dimension, adjoint=True),
        cost_finite_differences=counter.cost(dimension, adjoint=False),
    )


RUNNERS = {
    "box_subdivision": run_box_subdivision,
    "multistart": run_multistart,
    "cmaes": run_cmaes,
    "direct": run_direct,
}
"""The runner of each method."""


def run(
    method: str,
    problem: Problem,
    dimension: int,
    seed: int,
    budget: int,
    adjoint: bool = True,
) -> Result:
    """Run one method on one problem.

    Args:
        method: The name of the method.
        problem: The problem.
        dimension: The number of design variables.
        seed: The seed of the run.
        budget: The budget in equivalent objective evaluations.
        adjoint: Whether a gradient costs one objective evaluation.

    Returns:
        The outcome of the run.
    """
    logging.disable(logging.CRITICAL)
    try:
        return RUNNERS[method](problem, dimension, seed, budget, adjoint)
    finally:
        logging.disable(logging.NOTSET)
