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
r"""One entry point for every shape of box-subdivision run.

Composing the method by hand means chaining the mapping before the objective,
building the design space from the *same* subdivision, naming the one-hot
variables of the master, choosing the formulation and sizing the trust region.
None of those is a decision: they are invariants, and every one of them is a way
to get a silently wrong run.

This module owns them. What it leaves to the caller is what the measurements say
actually matters: **which variables to subdivide and how finely**, and the
**convexity margin**, which is in the units of the objective and transfers
between problems no better than a length does.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

from gemseo import create_scenario
from gemseo.core.chains.chain import MDOChain
from gemseo.settings.formulations import DisciplinaryOpt_Settings
from gemseo.settings.opt import SLSQP_Settings

from gemseo_box_subdivision.design_spaces import create_box_design_space
from gemseo_box_subdivision.design_spaces import create_normalized_box_design_space
from gemseo_box_subdivision.disciplines.box_constraint import BoxConstraint
from gemseo_box_subdivision.disciplines.box_mapping import BoxMapping
from gemseo_box_subdivision.disciplines.multi_resolution_mapping import (
    MultiResolutionMapping,
)
from gemseo_box_subdivision.disciplines.scenario_adapters.box_start import (
    create_box_start_adapter_class,
)
from gemseo_box_subdivision.settings import BoxSubdivisionSettings
from gemseo_box_subdivision.subdivisions.box import BoxSubdivision
from gemseo_box_subdivision.subdivisions.multi_resolution import MultiResolution

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from collections.abc import Sequence

    from gemseo.algos.design_space import DesignSpace
    from gemseo.core.discipline import Discipline
    from gemseo.scenarios.mdo_scenario import MDOScenario
    from numpy import ndarray


def create_box_subdivision_scenario(
    disciplines: Sequence[Discipline],
    objective_name: str,
    design_space: DesignSpace,
    n_subdivisions: int | Mapping[str, int] = 10,
    variable_names: Iterable[str] = (),
    levels: int = 1,
    formulation: str = "normalized",
    weights: Mapping[str, ndarray] = MappingProxyType({}),
    settings: BoxSubdivisionSettings | None = None,
) -> MDOScenario:
    r"""Return a scenario solving a problem by subdividing its design space.

    Args:
        disciplines: The disciplines computing the objective, and the
            constraints if any. The mapping of the boxes is chained in front of
            them, so they keep receiving the design variables under their own
            names.
        objective_name: The name of the objective output.
        design_space: The design space of the original problem.
        n_subdivisions: The number of subdivisions of every subdivided variable,
            or of each of them. With ``levels`` above one this is the branching
            of a level, and the resolution reached is
            ``n_subdivisions ** levels``.
        variable_names: The variables to subdivide. If empty, subdivide every
            variable of the design space. Subdividing only the variables the
            objective is multimodal in is what makes a problem of more than a
            handful of variables affordable.
        levels: The number of levels of the multi-resolution encoding. One, the
            default, is the flat subdivision. Above one, a box is chosen by one
            categorical variable per level, which reaches a resolution of
            ``n_subdivisions ** levels`` for ``levels`` times the binaries of a
            single level instead of an exponential number of them.
        formulation: ``"normalized"``, the recommended one, in which the
            sub-problem is written in the normalized variables of its box, or
            ``"constraint"``, in which the box is a constraint of the
            sub-problem.
        weights: The weights of the subdivisions of each variable, which set the
            distance the trust region of the master measures. If empty, weigh
            every subdivision alike, so that the distance is the number of
            components a candidate changes. This is the metric the measurements
            support; the alternative exists to be swept, not to be used.
        settings: The settings of the run. If ``None``, use the defaults of
            :class:`.BoxSubdivisionSettings`, whose convexity margin only suits
            an objective of the scale of the benchmark.

    Returns:
        The scenario, ready to execute. It is an ordinary GEMSEO scenario, so
        anything that can be done to one can be done to it: adding a constraint
        of the original problem with ``main_level=True``, changing the
        sub-problem algorithm, or reading its database afterwards.

    Raises:
        ValueError: When the formulation is unknown, or when the multi-resolution
            encoding is asked for together with the constraint formulation, which
            it does not support.
    """
    settings = settings or BoxSubdivisionSettings()
    if formulation not in {"normalized", "constraint"}:
        msg = (
            "The formulation must be 'normalized' or 'constraint'; "
            f"got {formulation!r}."
        )
        raise ValueError(msg)

    if levels > 1:
        if formulation == "constraint":
            msg = (
                "The multi-resolution encoding supports the normalized "
                "formulation only."
            )
            raise ValueError(msg)

        return _create_multi_resolution_scenario(
            disciplines,
            objective_name,
            design_space,
            n_subdivisions,
            variable_names,
            levels,
            settings,
        )

    subdivision = BoxSubdivision.from_design_space(
        design_space, n_subdivisions, variable_names
    )
    # The names the master must optimize over are the one-hot variables of the
    # subdivision, never a literal: they follow the names of the design space.
    main_variables = list(subdivision.get_one_hot_names({}).values())
    common = {
        "formulation_name": "Benders",
        "main_problem_design_variables": main_variables,
        "sub_problem_algo_settings": SLSQP_Settings(
            max_iter=settings.sub_problem_max_iter
        ),
        "sub_problem_formulation_settings": DisciplinaryOpt_Settings(),
    }
    if formulation == "normalized":
        # The mapping is chained *before* the objective, so the sub-problem
        # solves for the normalized variables while the disciplines keep
        # receiving the design variables.
        scenario = create_scenario(
            [MDOChain([BoxMapping(subdivision), *disciplines])],
            objective_name,
            create_normalized_box_design_space(
                subdivision, design_space, weights=weights
            ),
            **common,
        )
    else:
        scenario = create_scenario(
            [*disciplines, BoxConstraint(subdivision)],
            objective_name,
            create_box_design_space(subdivision, design_space, weights=weights),
            scenario_adapter_cls=create_box_start_adapter_class(subdivision),
            **common,
        )
        # The box is enforced by a constraint of the sub-problem, which the
        # formulation only knows about once it is declared.
        scenario.formulation.add_constraint(BoxConstraint.DEFAULT_OUTPUT_NAME)

    scenario.subdivision = subdivision
    scenario.box_subdivision_settings = settings
    return scenario


def _create_multi_resolution_scenario(
    disciplines: Sequence[Discipline],
    objective_name: str,
    design_space: DesignSpace,
    branching: int | Mapping[str, int],
    variable_names: Iterable[str],
    levels: int,
    settings: BoxSubdivisionSettings,
) -> MDOScenario:
    """Return a scenario using one categorical variable per level.

    Args:
        disciplines: The disciplines computing the objective.
        objective_name: The name of the objective output.
        design_space: The design space of the original problem.
        branching: The number of subdivisions of a component at each level.
        variable_names: The variables to subdivide.
        levels: The number of levels.
        settings: The settings of the run.

    Returns:
        The scenario, ready to execute.

    Raises:
        ValueError: When the branching differs between variables, which this
            encoding does not support.
    """
    names = tuple(variable_names) or tuple(design_space.variable_names)
    if not isinstance(branching, int):
        values = {branching[name] for name in names}
        if len(values) > 1:
            msg = (
                "The multi-resolution encoding needs the same branching for "
                f"every variable; got {sorted(values)}."
            )
            raise ValueError(msg)

        branching = values.pop()

    subdivision = MultiResolution(
        {name: design_space.get_lower_bounds([name]) for name in names},
        {name: design_space.get_upper_bounds([name]) for name in names},
        branching,
        levels,
    )
    main_variables = [
        subdivision.get_one_hot_name(name, level)
        for name in names
        for level in range(1, levels + 1)
    ]
    scenario = create_scenario(
        [MDOChain([MultiResolutionMapping(subdivision), *disciplines])],
        objective_name,
        subdivision.create_design_space(),
        formulation_name="Benders",
        main_problem_design_variables=main_variables,
        sub_problem_algo_settings=SLSQP_Settings(
            max_iter=settings.sub_problem_max_iter
        ),
        sub_problem_formulation_settings=DisciplinaryOpt_Settings(),
    )
    scenario.subdivision = subdivision
    scenario.box_subdivision_settings = settings
    return scenario


def execute_box_subdivision_scenario(scenario: MDOScenario) -> MDOScenario:
    """Execute a scenario built by :func:`.create_box_subdivision_scenario`.

    The radius of the trust region is scaled where the distance of the master
    counts something other than design variables: the multi-resolution encoding
    has one one-hot group per level per variable, so two whole variables is
    twice the number of levels.

    Args:
        scenario: The scenario to execute.

    Returns:
        The executed scenario.
    """
    from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (  # noqa: E501, PLC0415
        BiLevelMasterOuterApproximation_Settings,
    )

    settings = scenario.box_subdivision_settings
    subdivision = scenario.subdivision
    radius = None
    if isinstance(subdivision, MultiResolution):
        radius = settings.trust_region_radius * subdivision.levels

    scenario.execute(
        BiLevelMasterOuterApproximation_Settings(**settings.to_master_settings(radius))
    )
    return scenario
