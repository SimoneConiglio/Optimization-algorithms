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
        max_step=2,
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
| `number_of_parallel_points` | $4$ | the master probes one radius per point, so that a feasible master stays available. A single point still works, from six starting points out of eight against eight; eight points are as reliable as four and nearly twice as expensive |
| `max_step` | $2$ | the radius of the trust region of the master, counted in **components changed**, the design spaces of this package weighing every subdivision alike. Keep it small: widening it to {py:attr}`~gemseo_box_subdivision.algos.design_space.box_subdivision.BoxSubdivision.max_step`, where the region stops constraining, loses Rastrigin at five variables, and removing the region is worse still, see [annex C](tuning.md#how-wide-the-radius-should-be) |
| `ub_tol` | $10^{-4}$ | convergence tolerance on the upper bound |
| `max_iter` | $\ge 80$ | master iterations, not sub-problem iterations |

And one choice that is not a setting of the algorithm but of the subdivision:

| Choice | Recommended | Why |
|--------|-------------|-----|
| `n_subdivisions` | fine enough to resolve the basins, over the variables the objective is multimodal in | a box that still holds several basins defeats the local solve, and the number of boxes costs evaluations rather than master size, the binaries growing linearly. See [the benchmark](benchmark.md#the-density-of-the-subdivision-decides) |

## Which methodology to set up

Five constructions are available, and they are not alternatives to be tried at
random: each answers a different reason for the flat subdivision to be out of
reach. Read down the first column until one matches the problem.

| If the problem is | then use | because |
|-------------------|----------|---------|
| multimodal in every variable, few enough variables that $n m$ binaries stay affordable | the **flat subdivision**, below | it is the cheapest and the most reliable of the five |
| multimodal in a few variables and smooth in the rest | **subdividing some variables only** | a variable left out keeps all its basins inside every box, which is harmless when it has none |
| needing a resolution whose $n m$ binaries the budget cannot identify | the **multi-resolution encoding** | it reaches $m^L$ subdivisions per component for $n m L$ binaries |
| one broad basin that no affordable density separates | a **hierarchy**, deep and narrow | each level is small enough to be determined by a quarter of the budget |
| solved already, but too slowly | the **settings**, above | the density and the trust-region radius move results further than any of the constructions |

The rule behind the table is the one the methodology derives: what a budget buys
is a few dozen sub-problem solves, and the cut model has one coefficient per
binary, so a subdivision is usable while its binaries stay below the cuts that
can be afforded. Every construction here is a different way of spending fewer
binaries on the same resolution.

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

## A resolution the binaries cannot afford: the multi-resolution encoding

When the density needed would cost more binaries than the budget can identify,
choose a box with **one categorical variable per level** instead of one over the
whole subdivision. The levels are the digits of the box index in base $m$, so
$L$ levels of $m$ subdivisions reach $m^L$ subdivisions per component for
$n m L$ binaries, and the whole thing stays in a single master.

```python
from numpy import array

from gemseo_box_subdivision.algos.design_space.multi_resolution import MultiResolution
from gemseo_box_subdivision.disciplines.multi_resolution_mapping import (
    MultiResolutionMapping,
)

subdivision = MultiResolution(
    {"x": array([-4.1, -4.1])},
    {"x": array([5.9, 5.9])},
    branching=4,
    levels=2,
)
subdivision.resolution  # 16 subdivisions per component
subdivision.n_binaries  # 16, against the 80 a flat subdivision would need
subdivision.n_boxes  # 256

scenario = create_scenario(
    [MDOChain([MultiResolutionMapping(subdivision), objective_discipline])],
    "f",
    subdivision.create_design_space(),
    formulation_name="Benders",
    main_problem_design_variables=[
        subdivision.get_one_hot_name("x", level)
        for level in range(1, subdivision.levels + 1)
    ],
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
        # One one-hot group per level per variable, so two whole variables is
        # 2 * levels groups, not 2.
        max_step=2 * subdivision.levels,
    )
)
```

The mapping is chained before the objective discipline exactly as `BoxMapping`
is, and the objective keeps receiving `x` under its own name.

:::{important}
`max_step` must be scaled by the number of levels. The distance counts the
one-hot groups a candidate changes and this encoding has $nL$ of them, so the
radius of two that suits a flat subdivision would let the master move two
**digits** rather than two variables. Leaving it at
{py:attr}`~gemseo_box_subdivision.algos.design_space.multi_resolution.MultiResolution.max_step`,
where the region stops constraining, is markedly worse still.
:::

Two limits are worth knowing before choosing it. The cut model is linear in the
one-hot variables, so over the digits it is **additive**: it cannot express that
what a fine digit is worth depends on the coarse digit it sits inside, and
adding levels makes that assumption bind harder. And weighting the levels by
what their digit is worth, rather than alike, is the worst configuration
measured. What it achieves is in
[the results](benchmark.md#the-extensions-and-what-they-are-worth).

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

The three shapes described in
[the methodology](methodology.md#hierarchies-of-subdivisions) are wired up in
`benchmarks/hierarchy.py`, sharing one budget between the levels. Unlike the
constructions above, they live in the benchmarks rather than in the package, so
applying them to another problem means copying that module rather than importing
it:

```python
from benchmarks.hierarchy import run_deep, run_frontier, run_hierarchical

run_hierarchical(problem, 5, seed=11, budget=2500, coarse=2, fine=5, ranking="cuts")
run_deep(problem, 5, seed=11, budget=2500, branching=2, depth=4)
run_frontier(problem, 5, seed=11, budget=2500, expansions=10, score="optimistic")
```

:::{warning}
None of the three beats the flat subdivision on a problem a flat subdivision can
resolve, and each node restarts a master and discards its parent's cuts. Reach
for one only in the case they answer, a basin too broad for any affordable
density, where the deep shape reaches an optimum the flat method does not, see
[the results](benchmark.md#the-extensions-and-what-they-are-worth). If what you
need is resolution rather than a change of region, the multi-resolution encoding
above keeps every level in one master and discards nothing.
:::

## Applying this to a new problem

The order below is the one the measurements support, and it is deliberately not
the order in which the constructions were built.

1. **Start flat and coarse.** A subdivision of two or four per variable, the
   `adaptive` configuration, `max_step=2`. This is cheap and tells you whether
   the landscape is one the method suits at all.
2. **Scale the convexity margin to the objective.** `min_dfk` is subtracted from
   an objective difference, so it is absolute, in the units of *your* objective,
   and a value tuned on another problem means nothing. Take the range of the
   objective over the design space as a first value. It crosses a threshold and
   then saturates, so erring high costs sub-problems rather than quality.
3. **Sweep the density before anything else.** It moves results further than any
   other choice, and it has a floor and a ceiling: fine enough to separate the
   basins, coarse enough that the binaries stay below the sub-problem solves the
   budget affords. Refining past the basins actively degrades the ranking, so
   more is not safer.
4. **Then try the radius either side of two.** It is the second most decisive
   setting and it is cheap to test.
5. **Only then reach for a construction**, using the table above to choose
   which; each answers one specific reason for the flat subdivision to fail.

Both mechanism sweeps are in `benchmarks/tune_convexification.py`, which sweeps
each separately, and the budget question is worth settling too: a run whose cost
equals its budget was stopped rather than finished, so raise the budget until the
cost stops moving before comparing anything, see
[the results](benchmark.md#does-more-budget-change-the-answer).
