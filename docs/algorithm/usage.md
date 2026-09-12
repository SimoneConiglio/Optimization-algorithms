<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Usage in GEMSEO scenarios

Both formulations build an ordinary GEMSEO scenario with the `Benders`
formulation, and are solved by the `BiLevelMasterOuterApproximation` algorithm.

## Normalized formulation

The recommended one: fewer moving parts, and the better explorer on the
benchmark.

```python
from gemseo import create_scenario
from gemseo.algos.design_space import DesignSpace
from gemseo.core.chains.chain import MDOChain
from gemseo.settings.formulations import DisciplinaryOpt_Settings
from gemseo.settings.opt import SLSQP_Settings
from gemseo_bilevel_outer_approximation.algos.opt.bilevel_master_outer_approximation.bilevel_master_outer_approximation_settings import (
    BiLevelMasterOuterApproximation_Settings,
)

from gemseo_box_subdivision.algos.design_space.box_design_space import (
    create_normalized_box_design_space,
)
from gemseo_box_subdivision.algos.design_space.box_subdivision import BoxSubdivision
from gemseo_box_subdivision.disciplines.box_mapping import BoxMapping

design_space = DesignSpace()
design_space.add_variable("x", lower_bound=-4.1, upper_bound=5.9, size=2, value=0.0)

subdivision = BoxSubdivision.from_design_space(design_space, 10)

scenario = create_scenario(
    [MDOChain([BoxMapping(subdivision), objective_discipline])],
    "f",
    create_normalized_box_design_space(subdivision, design_space),
    formulation_name="Benders",
    main_problem_design_variables=["x_box"],
    sub_problem_algo_settings=SLSQP_Settings(max_iter=40),
    sub_problem_formulation_settings=DisciplinaryOpt_Settings(),
)
scenario.execute(
    BiLevelMasterOuterApproximation_Settings(
        max_iter=80, ub_tol=1e-4, convexification_constant=100.0, adapt=True
    )
)
```

`BoxMapping` is chained **before** the objective discipline, so the sub-problem
solves for `x_normalized` while the objective keeps receiving `x`.

## Constraint formulation

```python
from gemseo_box_subdivision.algos.design_space.box_design_space import create_box_design_space
from gemseo_box_subdivision.disciplines.box_constraint import BoxConstraint
from gemseo_box_subdivision.disciplines.scenario_adapters.box_start import (
    create_box_start_adapter_class,
)

scenario = create_scenario(
    [objective_discipline, BoxConstraint(subdivision)],
    "f",
    create_box_design_space(subdivision, design_space),
    formulation_name="Benders",
    main_problem_design_variables=["x_box"],
    sub_problem_algo_settings=SLSQP_Settings(max_iter=40),
    sub_problem_formulation_settings=DisciplinaryOpt_Settings(),
    scenario_adapter_cls=create_box_start_adapter_class(subdivision),
)
scenario.formulation.add_constraint(BoxConstraint.DEFAULT_OUTPUT_NAME)
```

The two extra pieces, the adapter and the explicit constraint, are what the
normalized formulation makes unnecessary.

## Constraints of the original problem

A box may contain no point satisfying the original constraints. Declare such a
constraint with `main_level=True` so an infeasible sub-problem produces a
feasibility cut instead of stalling the master:

```python
scenario.formulation.add_constraint("g", main_level=True)
```

## Enumerating the boxes instead

The same scenario, driven exhaustively, which is the reference to compare
against:

```python
from gemseo.algos.doe.factory import DOELibraryFactory

from gemseo_box_subdivision.algos.design_space.box_design_space import create_box_samples

DOELibraryFactory().execute(
    scenario.formulation.optimization_problem,
    algo_name="CustomDOE",
    samples=create_box_samples(subdivision),
)
```

## Settings that matter

:::{warning}
`convexification_constant` defaults to `0.0`, which on a multimodal problem makes
the cuts invalid: the master converges after two or three sub-problems and
reports success on a point far from the optimum. It **must** be set, see
[Convexification](methodology.md#convexification).
:::

| Setting | Recommended | Why |
|---------|-------------|-----|
| `convexification_constant` | $100$ normalized, $\sim 25$ to $500$ constraint | keeps the cuts valid; tune per problem |
| `adapt` | `True` | repairs the slopes against the observed history |
| `ub_tol` | $10^{-4}$ | convergence tolerance on the upper bound |
| `max_iter` | $\ge 80$ | master iterations, not sub-problem iterations |
| `number_of_parallel_points` | $>1$ | solves several boxes per master iteration |

And one choice that is not a setting of the algorithm but of the subdivision:

| Choice | Recommended | Why |
|--------|-------------|-----|
| `n_subdivisions` | such that $\prod_i m_i$ stays in the hundreds | too many boxes and the cuts cannot tell them apart; too few and a box is no longer unimodal. See [the benchmark](benchmark.md#the-subdivision-has-to-resolve-the-basins) |

The constant is problem-dependent. Sweep it with
`benchmarks/tune_convexification.py` before trusting a result on a new problem.
