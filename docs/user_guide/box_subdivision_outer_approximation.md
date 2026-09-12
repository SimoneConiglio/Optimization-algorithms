<!--
Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Box-subdivision outer approximation

Design note for a bi-level algorithm targeting **multimodal NLP** problems, in
which the exploration and the exploitation of the design space are handled by
two distinct levels.

## Problem

$$
\min_{x \in [L, U] \subset \mathbb{R}^n} f(x)
\quad \text{s.t.} \quad g(x) \le 0
$$

with $f$ and/or $g$ non-convex, so that the problem admits several local minima.

## Subdivision and encoding

Each variable $x_i$ is split into $m_i$ contiguous subdivisions
$[l_{i,k}, u_{i,k}]$, $k = 1 \dots m_i$. The Cartesian product of the
subdivisions defines $\prod_i m_i$ boxes.

The box is selected by **one categorical variable per design variable**, encoded
one-hot as $\alpha_{i,k} \in \{0, 1\}$ with $\sum_k \alpha_{i,k} = 1$.

!!! note "The encoding is linear in the number of variables"

    The master problem carries $\sum_i m_i$ binaries, not $\prod_i m_i$. The
    Cartesian structure is never enumerated. This is the property that makes
    the approach tractable, and it maps directly onto
    `CatalogueDesignSpace.add_categorical_variable`, which accepts several
    categorical variables, each with its own catalogue.

The selected box bounds are **affine** in $\alpha$:

$$
\ell_i(\alpha) = \sum_k l_{i,k}\, \alpha_{i,k},
\qquad
u_i(\alpha) = \sum_k u_{i,k}\, \alpha_{i,k}.
$$

## Bi-level split

| Level | Decides | Solved by | Role |
|-------|---------|-----------|------|
| Main | which box, i.e. $\alpha$ | MILP master (outer approximation) | exploration |
| Sub | $x$ inside the box | NLP | exploitation |

$$
\min_\alpha\ u(\alpha)
\quad \text{where} \quad
u(\alpha) = \min_x \{ f(x) : g(x) \le 0,\ \ell(\alpha) \le x \le u(\alpha) \}
$$

This is the `Benders` formulation of `gemseo-bilevel-outer-approximation`, with
the box-selection variables as the main-problem (categorical) variables.

## Why the box bounds must be constraints, not bounds

`gemseo-bilevel-outer-approximation` builds the sub-problem design space **once**,
at formulation time (`Benders.__build_sub_problem_dspace` filters a copy of the
original design space), so the sub-problem bounds cannot depend on $\alpha$.

GEMSEO's `MDOScenarioAdapter` does offer a `set_bounds_before_opt` option that
exposes `<var>_lower_bnd` / `<var>_upper_bnd` as adapter inputs. **It is not
usable here**: in `_compute_jacobian` the bound inputs are excluded from the
differentiated inputs and the corresponding Jacobian blocks are explicitly
filled with zeros, under the documented assumption that

> The bound-constraints on the scenario optimization variables are assumed
> independent of the other scenario inputs.

Driving the bounds that way would therefore yield $\mathrm{d}u/\mathrm{d}\alpha = 0$
and degenerate outer-approximation cuts.

The workaround is to move the box into the sub-problem **constraints**, as a
single vector-valued function of dimension $2n$:

$$
g_{\text{box}}(x, \alpha) =
\begin{bmatrix} x - u(\alpha) \\ \ell(\alpha) - x \end{bmatrix} \le 0 .
$$

This is not merely a way around a missing feature: it is what makes the
sensitivity available. GEMSEO's `PostOptimalAnalysis` computes

$$
\frac{\mathrm{d} f(x^\ast(p), p)}{\mathrm{d} p}
= \frac{\partial f}{\partial p}
+ \lambda_g^\top \frac{\partial g}{\partial p}
+ \lambda_h^\top \frac{\partial h}{\partial p},
$$

in which the bounds $\ell \le x \le u$ appear in the problem statement but
**not** in the total derivative, precisely because they are assumed constant
with respect to the parameter. With the box expressed as $g_{\text{box}}$ and
$f$ independent of $\alpha$, the cut gradient is exact and analytic:

$$
\frac{\mathrm{d} u}{\mathrm{d} \alpha_{i,k}}
= -\lambda^{u}_i\, u_{i,k} + \lambda^{\ell}_i\, l_{i,k},
$$

where $\lambda^{u}_i, \lambda^{\ell}_i \ge 0$ are the multipliers of the upper
and lower faces of the box for variable $i$ — the shadow price of moving a box
face. Keeping all $2n$ components in **one** function keeps the cut bookkeeping
to a single entry per sub-problem solve.

Two further properties are worth noting:

- $g_{\text{box}}$ is linear in $x$ and affine in $\alpha$, hence **jointly
  convex**. All the non-convexity stays in $f$ and the original $g$, so the
  convexification only ever has to treat the original functions.
- A box may be infeasible with respect to the original $g$. This must be routed
  through `Benders.add_constraint(..., main_level=True)` so that an infeasible
  sub-problem produces a feasibility cut rather than stalling the master.

## Why subdivision helps the convexification

With an $\alpha$BB-style underestimator, the relaxation gap over a box scales as

$$
\tfrac14 \sum_i \alpha_i\, (u_i - l_i)^2 ,
$$

so halving the box widths divides the gap by four. The subdivision is therefore
not just exploration bookkeeping: it **tightens the convexification
quadratically in the box width**, which is the main theoretical argument for the
approach.

Seen this way the algorithm is a **spatial branch-and-bound whose branching tree
is fixed a priori and flattened into a single MILP master**, rather than
explored adaptively.

## Border boxes need a margin on the design space bounds

Enforcing the box through the constraint only, and leaving the sub-problem
design space at its original bounds, is enough to confine the sub-problem: in
the one-dimensional experiment of `tests/disciplines/`, every box optimum stayed
inside its box.

The bounds are nevertheless not neutral. A box lying against the border of the
design space has a face that *coincides* with a bound. When the optimum lies on
that face, both are active, and GEMSEO attributes the multiplier to the bound:
the box constraint is left with a multiplier of zero, so the sensitivity of the
box optimum is silently computed as zero. On the test problem, the exact
multiplier of the lower face of the first box is the objective slope at the
origin, $6 - 0.6 \times 0.4 = 5.76$, and the measured value is:

| margin (relative) | multiplier of the box constraint |
|-------------------|----------------------------------|
| $0$ to $10^{-6}$  | $0$ (attributed to the bound)    |
| $10^{-5}$ and above | $5.76$                         |

The threshold is the tolerance under which a bound counts as active.
`BoxSubdivision.create_relaxed_design_space` therefore widens the bounds by a
relative margin, $10^{-4}$ by default, an order of magnitude above the
threshold. The box constraint still confines the design variables to the
original bounds, up to the constraint tolerance.

This matters for every variable, since the first and the last subdivision of
each variable always touch a bound.

## Open questions

1. **Static vs. adaptive subdivision.** A fixed subdivision is either too coarse
   (weak lower bound, many iterations) or too fine (large master, many boxes).
   Refining only the promising boxes would recover a genuine spatial
   branch-and-bound, at the cost of a master problem that grows during the run.
3. **Choice of $m_i$.** No obvious a priori rule; it should probably be driven
   by a curvature estimate, which is already needed for the convexification.

## Benchmarking

The claim to establish is that the method reaches the global optimum after
solving **far fewer than $\prod_i m_i$ sub-problems**. The baseline to beat is
therefore *multistart local NLP, one start per box*, which is embarrassingly
parallel and needs no cuts at all.

`gemseo-benchmark` is the harness for this: performance histories, Moré–Wild
data profiles and reports, with the number of sub-problem solves as the budget
unit. It is a library rather than an algorithm plugin, and is declared in the
`benchmark` dependency group.

## Parallelism

The outer-approximation loop is sequential (master, then sub-problem, then cut).
The natural parallel variant is **multi-cut**: extract the $K$ best boxes from
the master at each iteration (via a solution pool or iterative no-good cuts),
solve the $K$ sub-problems concurrently, and add $K$ cuts at once.

## Upstream

The bounds limitation is worth reporting to
`gemseo-bilevel-outer-approximation`: a sub-problem design space that may depend
on the categorical variables, with the corresponding post-optimal sensitivity
routed through the bound-constraint multipliers that `MDOScenarioAdapter`
already computes.
