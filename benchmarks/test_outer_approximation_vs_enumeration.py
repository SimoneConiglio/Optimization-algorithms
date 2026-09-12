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
"""

from __future__ import annotations

import logging

import pytest
from gemseo import create_scenario
from gemseo.algos.design_space import DesignSpace
from gemseo.algos.doe.factory import DOELibraryFactory
from gemseo.settings.formulations import DisciplinaryOpt_Settings
from gemseo.settings.opt import SLSQP_Settings
from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (  # noqa: E501
    BiLevelMasterOuterApproximation_Settings,
)
from numpy.random import default_rng

from benchmarks.problems import RASTRIGIN_LOWER_BOUND
from benchmarks.problems import RASTRIGIN_UPPER_BOUND
from benchmarks.problems import Rastrigin
from gemseo_algos_lab.algos.design_space.box_design_space import create_box_design_space
from gemseo_algos_lab.algos.design_space.box_design_space import create_box_samples
from gemseo_algos_lab.algos.design_space.box_subdivision import BoxSubdivision
from gemseo_algos_lab.disciplines.box_constraint import BoxConstraint
from gemseo_algos_lab.disciplines.scenario_adapters.box_start import (
    create_box_start_adapter_class,
)

N_SUBDIVISIONS = 10
"""The number of subdivisions per variable, i.e. 100 boxes in two dimensions."""

N_STARTING_POINTS = 3
"""The number of starting points."""

CONVEXIFICATION_CONSTANT = 10.0
"""The convexification constant of the outer approximation."""

GLOBAL_OPTIMUM = 0.0
"""The global minimum of the Rastrigin function."""


def _create_scenario(starting_point):
    """Create the bi-level scenario of the box-subdivided Rastrigin problem.

    Args:
        starting_point: The initial value of the design variables.

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
    scenario = create_scenario(
        [objective, BoxConstraint(subdivision)],
        "f",
        create_box_design_space(subdivision, design_space),
        formulation_name="Benders",
        main_problem_design_variables=["x_box"],
        sub_problem_algo_settings=SLSQP_Settings(max_iter=40),
        sub_problem_formulation_settings=DisciplinaryOpt_Settings(),
        scenario_adapter_cls=create_box_start_adapter_class(subdivision),
    )
    scenario.formulation.add_constraint(BoxConstraint.DEFAULT_OUTPUT_NAME)
    return scenario, subdivision, objective


def _run_enumeration(starting_point):
    """Solve the sub-problem of every box, with the CustomDOE driver.

    Args:
        starting_point: The initial value of the design variables.

    Returns:
        The best objective value, the number of sub-problems and of executions.
    """
    scenario, subdivision, objective = _create_scenario(starting_point)
    problem = scenario.formulation.optimization_problem
    DOELibraryFactory().execute(
        problem, algo_name="CustomDOE", samples=create_box_samples(subdivision)
    )
    values = problem.database.get_function_history(problem.objective.name)
    return float(min(values)), len(problem.database), objective.n_executions


def _run_outer_approximation(starting_point):
    """Solve the problem with the bi-level outer approximation.

    Args:
        starting_point: The initial value of the design variables.

    Returns:
        The best objective value, the number of sub-problems and of executions.
    """
    scenario, _, objective = _create_scenario(starting_point)
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
    """Run both methods from the same starting points."""
    logging.disable(logging.CRITICAL)
    rng = default_rng(3)
    rows = []
    for _ in range(N_STARTING_POINTS):
        starting_point = rng.uniform(RASTRIGIN_LOWER_BOUND, RASTRIGIN_UPPER_BOUND, 2)
        rows.append((
            _run_enumeration(starting_point),
            _run_outer_approximation(starting_point),
        ))

    logging.disable(logging.NOTSET)
    return rows


def test_report(results) -> None:
    """Print the comparison of the two methods."""
    for _index, (_enumeration, _outer_approximation) in enumerate(results):
        pass


def test_enumeration_finds_the_global_optimum(results) -> None:
    """Check that the exhaustive baseline finds the global optimum every time."""
    for enumeration, _ in results:
        assert enumeration[0] == pytest.approx(GLOBAL_OPTIMUM, abs=1e-4)


def test_outer_approximation_solves_fewer_sub_problems(results) -> None:
    """Check that the outer approximation does not enumerate the boxes."""
    for enumeration, outer_approximation in results:
        assert outer_approximation[1] < enumeration[1] / 2


def test_outer_approximation_is_cheaper(results) -> None:
    """Check that the outer approximation executes the objective less often."""
    for enumeration, outer_approximation in results:
        assert outer_approximation[2] < enumeration[2] / 2


def test_outer_approximation_is_close_to_the_global_optimum(results) -> None:
    """Check the quality reached by the outer approximation.

    It is not exhaustive, so it may stop at a local minimum close to the global
    one; this pins how close it gets on this problem.
    """
    for _, outer_approximation in results:
        assert outer_approximation[0] <= 1.0
