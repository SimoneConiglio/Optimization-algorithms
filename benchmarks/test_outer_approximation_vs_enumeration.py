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
"""Compare the box-subdivision outer approximation with enumerating the boxes.

The baseline is the reference the method has to beat: solving the sub-problem of
every box. It is exhaustive over the boxes and embarrassingly parallel, so the
outer approximation is only worth its complexity if it reaches the same optimum
after substantially fewer sub-problems.

Both run the very same sub-problem machinery, through the same ``Benders``
formulation and the same main-problem design space, and differ only by the
driver of the main problem, so that the comparison isolates the exploration
strategy. The budget is counted in executions of the objective discipline, the
quantity that is expensive in an industrial problem.

The two ways of confining the sub-problem to its box are compared as well:

- ``"constraint"`` keeps the design variables and adds the box as a constraint,
  which is jointly convex, and needs a margin on the bounds and a scenario
  adapter to start inside the box;
- ``"normalized"`` solves for the normalized variables of the box, whose bounds
  are the unit interval whatever the box, which needs neither, but makes the
  design variables bilinear in the normalized variables and the box selection.
"""

from __future__ import annotations

import logging

import pytest
from gemseo import create_scenario
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.doe.factory import DOELibraryFactory
from gemseo.core.chains.chain import MDOChain
from gemseo.settings.formulations import DisciplinaryOpt_Settings
from gemseo.settings.opt import SLSQP_Settings
from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (  # noqa: E501
    BiLevelMasterOuterApproximation_Settings,
)
from numpy import median
from numpy.random import default_rng

from benchmarks.problems import RASTRIGIN_LOWER_BOUND
from benchmarks.problems import RASTRIGIN_UPPER_BOUND
from benchmarks.problems import Rastrigin
from gemseo_algos_lab.algos.design_space.box_design_space import create_box_design_space
from gemseo_algos_lab.algos.design_space.box_design_space import create_box_samples
from gemseo_algos_lab.algos.design_space.box_design_space import (
    create_normalized_box_design_space,
)
from gemseo_algos_lab.algos.design_space.box_subdivision import BoxSubdivision
from gemseo_algos_lab.disciplines.box_constraint import BoxConstraint
from gemseo_algos_lab.disciplines.box_mapping import BoxMapping
from gemseo_algos_lab.disciplines.scenario_adapters.box_start import (
    create_box_start_adapter_class,
)

FORMULATIONS = ("constraint", "normalized")
"""The two ways of confining the sub-problem to its box."""

N_SUBDIVISIONS = 10
"""The number of subdivisions per variable, i.e. 100 boxes in two dimensions."""

N_STARTING_POINTS = 3
"""The number of starting points."""

CONVEXIFICATION_CONSTANT = 10.0
"""The convexification constant of the outer approximation."""

GLOBAL_OPTIMUM = 0.0
"""The global minimum of the Rastrigin function."""


def _create_scenario(starting_point, formulation: str):
    """Create the bi-level scenario of the box-subdivided Rastrigin problem.

    Args:
        starting_point: The initial value of the design variables.
        formulation: Either ``"constraint"`` or ``"normalized"``.

    Returns:
        The scenario, the subdivision and the objective discipline.
    """
    design_space = DesignSpace()
    design_space.add_variable(
        "x",
        lower_bound=RASTRIGIN_LOWER_BOUND,
        upper_bound=RASTRIGIN_UPPER_BOUND,
        size=2,
        value=starting_point,
    )
    subdivision = BoxSubdivision.from_design_space(design_space, N_SUBDIVISIONS)
    objective = Rastrigin()
    settings = {
        "formulation_name": "Benders",
        "main_problem_design_variables": ["x_box"],
        "sub_problem_algo_settings": SLSQP_Settings(max_iter=40),
        "sub_problem_formulation_settings": DisciplinaryOpt_Settings(),
    }
    if formulation == "normalized":
        scenario = create_scenario(
            [MDOChain([BoxMapping(subdivision), objective])],
            "f",
            create_normalized_box_design_space(subdivision, design_space),
            **settings,
        )
    else:
        scenario = create_scenario(
            [objective, BoxConstraint(subdivision)],
            "f",
            create_box_design_space(subdivision, design_space),
            scenario_adapter_cls=create_box_start_adapter_class(subdivision),
            **settings,
        )
        scenario.formulation.add_constraint(BoxConstraint.DEFAULT_OUTPUT_NAME)

    return scenario, subdivision, objective


def _run_enumeration(starting_point, formulation: str):
    """Solve the sub-problem of every box, with the CustomDOE driver.

    Args:
        starting_point: The initial value of the design variables.
        formulation: Either ``"constraint"`` or ``"normalized"``.

    Returns:
        The best objective value, the number of sub-problems and of executions.
    """
    scenario, subdivision, objective = _create_scenario(starting_point, formulation)
    problem = scenario.formulation.optimization_problem
    DOELibraryFactory().execute(
        problem, algo_name="CustomDOE", samples=create_box_samples(subdivision)
    )
    values = problem.database.get_function_history(problem.objective.name)
    return float(min(values)), len(problem.database), objective.n_executions


def _run_outer_approximation(starting_point, formulation: str):
    """Solve the problem with the bi-level outer approximation.

    Args:
        starting_point: The initial value of the design variables.
        formulation: Either ``"constraint"`` or ``"normalized"``.

    Returns:
        The best objective value, the number of sub-problems and of executions.
    """
    scenario, _, objective = _create_scenario(starting_point, formulation)
    scenario.execute(
        BiLevelMasterOuterApproximation_Settings(
            max_iter=60,
            ub_tol=1e-4,
            convexification_constant=CONVEXIFICATION_CONSTANT,
            adapt=True,
        )
    )
    return (
        float(scenario.optimization_result.f_opt),
        len(scenario.formulation.optimization_problem.database),
        objective.n_executions,
    )


@pytest.fixture(scope="module")
def results():
    """Run both methods and both formulations from the same starting points."""
    logging.disable(logging.CRITICAL)
    rng = default_rng(3)
    starting_points = [
        rng.uniform(RASTRIGIN_LOWER_BOUND, RASTRIGIN_UPPER_BOUND, 2)
        for _ in range(N_STARTING_POINTS)
    ]
    rows = {
        formulation: [
            (
                _run_enumeration(starting_point, formulation),
                _run_outer_approximation(starting_point, formulation),
            )
            for starting_point in starting_points
        ]
        for formulation in FORMULATIONS
    }
    logging.disable(logging.NOTSET)
    return rows


def test_report(results) -> None:
    """Print the comparison of the two methods, for both formulations."""
    print(
        f"\n{'formulation':>12} {'run':>4} | {'enumeration':^25}"
        f" | {'outer approximation':^25}"
    )
    print(
        f"{'':>12} {'':>4} | {'f':>7} {'boxes':>6} {'execs':>9}"
        f" | {'f':>7} {'boxes':>6} {'execs':>9}"
    )
    for formulation, rows in results.items():
        for index, (enumeration, outer_approximation) in enumerate(rows):
            print(
                f"{formulation:>12} {index:>4} | {enumeration[0]:>7.4f}"
                f" {enumeration[1]:>6d} {enumeration[2]:>9d}"
                f" | {outer_approximation[0]:>7.4f}"
                f" {outer_approximation[1]:>6d} {outer_approximation[2]:>9d}"
            )


@pytest.mark.parametrize("formulation", FORMULATIONS)
def test_enumeration_finds_the_global_optimum(results, formulation) -> None:
    """Check that the exhaustive baseline finds the global optimum every time.

    Both formulations confine the sub-problem to its box and start it inside,
    so enumerating the boxes finds the global optimum with either.
    """
    for enumeration, _ in results[formulation]:
        assert enumeration[0] == pytest.approx(GLOBAL_OPTIMUM, abs=1e-4)


@pytest.mark.parametrize("formulation", FORMULATIONS)
def test_outer_approximation_solves_fewer_sub_problems(results, formulation) -> None:
    """Check that the outer approximation does not enumerate the boxes."""
    for enumeration, outer_approximation in results[formulation]:
        assert outer_approximation[1] < enumeration[1] / 2


@pytest.mark.parametrize("formulation", FORMULATIONS)
def test_outer_approximation_is_cheaper(results, formulation) -> None:
    """Check that the outer approximation executes the objective less often."""
    for enumeration, outer_approximation in results[formulation]:
        assert outer_approximation[2] < enumeration[2] / 2


def test_normalized_sub_problems_are_cheaper(results) -> None:
    """Check that the normalized formulation solves its boxes for less.

    Its sub-problems start inside their box and are bounded by it, instead of
    having to restore the feasibility of a box constraint.
    """
    constraint = median([enumeration[2] for enumeration, _ in results["constraint"]])
    normalized = median([enumeration[2] for enumeration, _ in results["normalized"]])
    assert normalized < constraint


def test_constraint_formulation_explores_better(results) -> None:
    """Check that the constraint formulation reaches a better optimum.

    Making the design variables bilinear in the normalized variables and the box
    selection, as the normalized formulation does, weakens the
    outer-approximation cuts, and the master converges earlier on a worse point.
    """
    constraint = median([
        outer_approximation[0] for _, outer_approximation in results["constraint"]
    ])
    normalized = median([
        outer_approximation[0] for _, outer_approximation in results["normalized"]
    ])
    assert constraint <= normalized
