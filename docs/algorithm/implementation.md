<!--
 Copyright 2026 Simone Coniglio

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Implementation

The package contributes building blocks to GEMSEO rather than a monolithic
algorithm: the subdivision, the two ways of confining a sub-problem to a box,
the design spaces of both levels, and a scenario adapter. They are assembled
into a `Benders` scenario, as shown in [Usage](usage.md).

## The subdivision

{py:class}`~gemseo_box_subdivision.algos.design_space.box_subdivision.BoxSubdivision`
describes the Cartesian subdivision: per variable, the lower and upper bounds of
each subdivision of each component, shaped `(size, n_subdivisions)`.

```python
subdivision = BoxSubdivision.from_design_space(design_space, {"x": 10, "y": 4})
subdivision.n_boxes      # exponential in the number of components
subdivision.n_binaries   # linear in it: this is what sizes the master
```

It also carries the helpers the rest of the package shares: `compute_bounds` for
the box selected by a one-hot vector, `locate` for the subdivision containing a
value, and the naming conventions `get_one_hot_names` and `get_normalized_names`
so that every component agrees on the variable names.

## One-hot layout

For a variable of size $s$ with $m$ subdivisions, the one-hot vector has length
$s \times m$ and is **component-major**:

```text
[ comp 0: k=0 .. k=m-1 | comp 1: k=0 .. k=m-1 | ... ]
```

This is the layout that `CatalogueDesignSpace.add_categorical_variable` produces,
and the one the master assumes when it derives
`n_members = variable_size / n_catalogues` and emits one sum-to-one row per
component. Every part of the package must agree with it, otherwise the master
selects one box while the sub-problem enforces another, silently.

## Formulation 1: the box as a constraint

{py:class}`~gemseo_box_subdivision.disciplines.box_constraint.BoxConstraint` computes
$g_{\text{box}}$ as a single vector-valued output of dimension $2n$, upper faces
first, with an analytic Jacobian with respect to both $x$ and $\alpha$.

Keeping the $2n$ components in **one** function keeps the cut bookkeeping to a
single entry per sub-problem solve.

### The bound margin

A box lying against the border of the design space has a face that *coincides*
with a bound of the design space. When the sub-problem optimum lies on that face,
both are active, and GEMSEO attributes the multiplier to the bound. The box
constraint is then left with a multiplier of zero, and the sensitivity of that
box is silently computed as zero — for the first and the last subdivision of
*every* variable.

`BoxSubdivision.create_relaxed_design_space` widens the bounds by a small
relative margin so they stay inactive. On a one-dimensional problem whose exact
multiplier is $5.76$:

| relative margin | multiplier of the box constraint |
|-----------------|----------------------------------|
| $0$ to $10^{-6}$ | $0$, attributed to the bound |
| $10^{-5}$ and above | $5.76$ |

The threshold is the tolerance under which a bound counts as active, hence the
default of $10^{-4}$. The box itself is still enforced by the constraint, so the
design variables stay in the original bounds up to the constraint tolerance.

### The starting point

The sub-problem is solved by a local algorithm, so its starting point decides
which local minimum of the box it reaches. Neither policy offered by GEMSEO
suits a subdivision:

- `reset_x0_before_opt` restarts every sub-problem from the initial value of the
  design space, which lies outside of all the boxes but one;
- warm-starting from the previous sub-problem makes the result depend on the
  order in which the boxes are visited;
- `set_x0_before_opt` cannot help, since the main problem decides the box, not
  the design variables.

This is not a detail: with the default policy, **even the exhaustive enumeration
of the 100 boxes of the benchmark missed the global optimum**, returning $1.92$
instead of $0$, because most sub-problems started outside their own box and the
local solver stalled on a face.

{py:func}`~gemseo_box_subdivision.disciplines.scenario_adapters.box_start.create_box_start_adapter_class`
returns a `Benders` scenario adapter that starts each sub-problem at the center
of the selected box, which is feasible by construction and independent of the
order of the boxes.

## Formulation 2: the box as normalized variables

{py:class}`~gemseo_box_subdivision.disciplines.box_mapping.BoxMapping` maps
$(\xi, \alpha)$ to $x$, again with an analytic Jacobian. Because the bounds of
the sub-problem no longer depend on the box, this formulation needs **neither**
the margin **nor** the scenario adapter: $\xi = 0.5$ is the center of whichever
box.

The discipline is chained before the objective, so the sub-problem solves for
$\xi$ while the disciplines keep receiving $x$.

## The design spaces

Both levels live in one `CatalogueDesignSpace`, which the `Benders` formulation
splits on its own by keeping the categorical variables in the main problem:

{py:func}`~gemseo_box_subdivision.algos.design_space.box_design_space.create_box_design_space`
: the original variables with widened bounds, plus one categorical variable per
  subdivided variable. For the constraint formulation.

{py:func}`~gemseo_box_subdivision.algos.design_space.box_design_space.create_normalized_box_design_space`
: the normalized variables bounded by $0$ and $1$, plus the same categorical
  variables. For the normalized formulation.

In both cases the catalogue of a subdivided variable is the range of its
subdivision indexes, so the default weights make two consecutive subdivisions
neighbours in the distance used by the master, and the initial box is the one
containing the initial value of the design space.

## Enumerating the boxes

{py:func}`~gemseo_box_subdivision.algos.design_space.box_design_space.create_box_samples`
returns the one-hot vector of every box. Passing them to the `CustomDOE` driver
of the main problem solves the sub-problem of every box, which is the reference
the method has to beat — and, being a driver of the same problem, makes the
comparison isolate the exploration strategy.

## The extensions

Four extensions of the method are implemented, all of them in the package, so
that each can be applied to another problem by importing it rather than by
copying a benchmark.

### Subdividing some of the variables only

{py:meth}`~gemseo_box_subdivision.algos.design_space.box_subdivision.BoxSubdivision.from_design_space`
takes the variables to subdivide, and
{py:func}`~gemseo_box_subdivision.algos.design_space.box_design_space.create_normalized_box_design_space`
keeps the others as they are, so a variable left out of the subdivision stays an
ordinary variable of the sub-problem, solved by the local solver at every box:

```python
subdivision = BoxSubdivision.from_design_space(design_space, 10, ["x_split"])
```

Nothing else changes: {class}`.BoxMapping` maps the subdivided variables alone,
and the master carries binaries for them alone.

### The multi-resolution encoding

{py:class}`~gemseo_box_subdivision.algos.design_space.multi_resolution.MultiResolution`
is the counterpart of `BoxSubdivision` for a box chosen by one categorical
variable per level, and
{py:class}`~gemseo_box_subdivision.disciplines.multi_resolution_mapping.MultiResolutionMapping`
the counterpart of `BoxMapping` for it. The pair is used exactly as the flat one
is, the mapping chained before the objective discipline:

```python
subdivision = MultiResolution(lower_bounds, upper_bounds, branching=4, levels=2)
space = subdivision.create_design_space()
```

Three details carry the construction.

**`locate` is a base conversion.** Placing a design value means writing its
position in the range in base $m$ and reading off $L$ digits, each of which
becomes the one-hot vector of a level. `compute_bounds` is the inverse, summing
what each digit contributes.

**The Jacobian blocks are constant.** The width $\Delta_j m^{-L}$ does not depend
on the levels, so the derivative with respect to a level is the value that digit
contributes and the derivative with respect to the normalized point is the width
of the smallest box. Neither depends on the other inputs, which is what keeps the
post-optimal sensitivity of the `Benders` formulation valid.

**The catalogue weights are ones.** `create_design_space` sets them explicitly,
so that the distance of the trust region counts the digits a candidate changes
rather than what those digits are worth.

### The radius of the trust region

{py:attr}`~gemseo_box_subdivision.algos.design_space.box_subdivision.BoxSubdivision.max_step`
returns the radius at which the region stops constraining the master, which with
unit catalogue weights is the number of subdivided components. It is a property
of the subdivision rather than a setting, and its docstring records that it is
**not** the radius to use.
{py:attr}`~gemseo_box_subdivision.algos.design_space.multi_resolution.MultiResolution.max_step`
returns the same quantity for the multi-resolution encoding, which has one
one-hot group per level per component and therefore a radius scaled by the number
of levels.

### The hierarchies

{py:mod}`~gemseo_box_subdivision.algos.opt.hierarchy` holds the scoring rules and
the three shapes. A shape is a **loop around the method** rather than a change to
it, so it is driven by a callable that solves one level and reports the boxes it
solved, leaving the caller its own scenario and its own accounting of the budget:

```python
def solve(lower_bound, upper_bound, n_subdivisions):
    ...  # build and execute a scenario over these bounds
    return subdivision, read_solved_boxes(problem)


refine_deep(solve, lower_bound, upper_bound, branching=2, depth=4)
```

Returning **no solved box** ends the search, which is how a caller reports that
its budget is spent or that its master became infeasible. Each shape returns the
bounds of every region it visited.

{py:func}`~gemseo_box_subdivision.algos.opt.hierarchy.read_solved_boxes`
: reads back the value and the post-optimal sensitivity of every box a master
  solved, from the database of its problem, as
  {py:class}`~gemseo_box_subdivision.algos.opt.hierarchy.SolvedBox` records.

{py:func}`~gemseo_box_subdivision.algos.opt.hierarchy.compute_cut_model`
: evaluates the cuts of a master over **every** box of its subdivision, including
  those it never solved, which is what lets a ranking propose an unvisited box.

`rank_by_value`, `rank_by_cuts`, `rank_mixed`
: the three rules, collected in
  {py:data}`~gemseo_box_subdivision.algos.opt.hierarchy.RANKINGS`.

`refine_deep`, `refine_two_levels`, `refine_frontier`
: the three shapes, collected in
  {py:data}`~gemseo_box_subdivision.algos.opt.hierarchy.SHAPES`. Only the
  frontier can return to a box it passed over, holding a priority queue of open
  boxes from every level.

`benchmarks/hierarchy.py` is then only the GEMSEO wiring and the budget
accounting: `Level`, a counter spending a share of the budget of a run and
raising when that share is gone, so that a hierarchy and a flat run are compared
at equal cost.

## What is checked

- The Jacobians of `BoxConstraint` and `BoxMapping` are verified against finite
  differences and complex step, at **relaxed** one-hot values, since the master
  relaxes them.
- The sensitivity is verified end to end: the multiplier of an active face of a
  sub-problem is compared with the exact slope of the objective.
- The one-hot layout of the design space and of the disciplines are
  cross-checked, so a disagreement cannot pass silently.
- The Jacobian of `MultiResolutionMapping` is verified against finite
  differences, and `locate` against `compute_bounds`: every box returned must
  contain the value that selected it.
- The border-box degeneracy is pinned by a regression test that asserts both the
  broken behaviour without a margin and the correct one with it.
