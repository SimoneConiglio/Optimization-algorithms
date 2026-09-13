<!--
 Copyright 2026 Simone Coniglio

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
        max_iter=80,
        ub_tol=1e-4,
        adapt=True,
        min_dfk=100.0,
        number_of_parallel_points=4,
        max_step=subdivision.max_step,
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
Left to their defaults, the master's two safeguards are both off: the cuts are
then invalid on a multimodal problem, the master converges after two or three
sub-problems and reports success on a point far from the optimum. One of them
**must** be set, see [Convexification](methodology.md#convexification).
:::

The master offers **two different mechanisms** against the non-convexity of the
relaxed problem, and they are not meant to be combined:

`adaptive`
: `adapt=True` with a convexity margin `min_dfk`, the constant left at zero. The
  master repairs its cut slopes against the boxes it has already solved. This is
  the recommended configuration.

`pure_convexification`
: `adapt=False` with `convexification_constant` $\kappa > 0$, the margin left at
  zero. The master adds $\kappa\, C(\alpha)$ to the relaxed problem, which is the
  configuration carrying the convergence guarantee, at the price of a lower bound
  degraded by $\kappa$, see [annex C](tuning.md#the-master-has-two-mechanisms-and-they-must-not-be-combined).

| Setting | Recommended | Why |
|---------|-------------|-----|
| `adapt` | `True` | repairs the cut slopes against the boxes already solved |
| `min_dfk` | the range of the objective over the design space, roughly | the convexity margin the repair enforces; it is an **absolute** quantity in the units of the objective and has to be scaled to the problem |
| `convexification_constant` | $0$ with `adapt=True`; otherwise the order of the variation of the objective | the other mechanism; use it *instead of*, not with, the adaptive repair. Raising it beyond that order buys nothing and decays the result, see [annex C](tuning.md#the-pure-convexification-and-the-range-where-it-is-worth-using) |
| `number_of_parallel_points` | $4$ | decisive: with a single point the master stops after two or three boxes |
| `max_step` | `subdivision.max_step` | the radius of the trust region of the master, in the distance induced by the weights of the boxes. Its own default of $10$ is unrelated to the design space, whose diameter is $\sum_j (m_j - 1)$: at five variables and ten subdivisions that is $45$, and leaving the radius at ten is the difference between solving Rastrigin and returning a gap of sixteen, see [annex C](tuning.md#the-trust-region-is-a-compromise-and-its-default-is-not-the-design-space) |
| `ub_tol` | $10^{-4}$ | convergence tolerance on the upper bound |
| `max_iter` | $\ge 80$ | master iterations, not sub-problem iterations |

And one choice that is not a setting of the algorithm but of the subdivision:

| Choice | Recommended | Why |
|--------|-------------|-----|
| `n_subdivisions` | fine enough to resolve the basins, over the variables the objective is multimodal in | a box that still holds several basins defeats the local solve, and the number of boxes costs evaluations rather than master size, the binaries growing linearly. See [the benchmark](benchmark.md#the-density-of-the-subdivision-decides) |

## Subdividing some of the variables only

The number of boxes being the Cartesian product of the subdivisions, subdividing
every variable is out of reach as soon as there are a few of them. Pass the
variables to subdivide, and the others stay ordinary variables of the
sub-problem:

```python
subdivision = BoxSubdivision.from_design_space(design_space, 10, ["x_split"])
```

This is worth it when the objective is close to unimodal in the variables left
out: one of them keeps all of its basins inside every box, and the local solve
returns the one it starts in. See
[annex C](tuning.md#refining-some-variables-only-and-when-it-pays),
where it solves a problem that subdividing every variable coarsely does not, and
loses on the problems that are multimodal in every variable.

## Refining a box, and hierarchies

A box of a subdivision is an ordinary design space, so refining it is running the
method again inside its bounds:

```python
lower, upper = subdivision.compute_bounds("x", one_hot)

refined = DesignSpace()
refined.add_variable("x", lower_bound=lower, upper_bound=upper, size=lower.size)
refined_subdivision = BoxSubdivision.from_design_space(refined, 5)
```

Which box to refine is the whole question, and the two scores available are the
value of the sub-problem solved inside a box, read from the database of the
master, and the cut model of the master, which estimates every box:

```python
problem = scenario.formulation.optimization_problem
name = problem.objective.name
solved = [
    (array(key.unwrap()).ravel(), values[name], values[f"@{name}"])
    for key, values in problem.database.items()
    if values.get(name) is not None and values.get(f"@{name}") is not None
]
```

`benchmarks/hierarchy.py` wires this into the three shapes described in
[the methodology](methodology.md#hierarchies-of-subdivisions), sharing one budget
between the levels:

```python
from benchmarks.hierarchy import run_deep, run_frontier, run_hierarchical

run_hierarchical(problem, 5, seed=11, budget=2500, coarse=2, fine=5, ranking="cuts")
run_deep(problem, 5, seed=11, budget=2500, branching=2, depth=4)
run_frontier(problem, 5, seed=11, budget=2500, expansions=10, score="optimistic")
```

:::{warning}
None of the three beats the flat subdivision on the problems measured, see
[the results](benchmark.md#the-extensions-and-what-they-are-worth). They are
built as benchmarks, not as a recommended way of running the method.
:::

## Sweeping the settings

`min_dfk` is problem-dependent, being expressed in the units of the objective.
Sweep it with `benchmarks/tune_convexification.py`, which sweeps each mechanism
separately, before trusting a result on a new problem.
