<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Methodology

## The problem

$$
\min_{x \in [L, U] \subset \mathbb{R}^n} f(x)
\quad \text{subject to} \quad g(x) \le 0
$$

with $f$ and/or $g$ non-convex, so that the problem has several local minima. A
local solver returns whichever minimum lies in the basin of its starting point,
and a global one pays for the exploration of the whole design space.

## Motivation: separating exploration from exploitation

The idea is to make the two concerns explicit rather than have a single
algorithm arbitrate between them:

- **exploration** decides *where* to look, over a finite set of regions;
- **exploitation** solves the original problem *inside* one region, with a local
  gradient-based algorithm, which is what such algorithms are good at.

The regions come from a **Cartesian subdivision** of the design space: each
component $x_j$ is split into $m_j$ contiguous subdivisions
$[l_{j,k}, u_{j,k}]$. Their Cartesian product defines $\prod_j m_j$ boxes.

```{image} ../_static/figures/subdivision.png
:class: only-light
:alt: A Cartesian subdivision of a two-dimensional design space
```

```{image} ../_static/figures/subdivision-dark.png
:class: only-dark
:alt: A Cartesian subdivision of a two-dimensional design space
```

Choosing a box is a categorical decision, solving inside it is a continuous one,
so the problem becomes a **mixed-integer non-linear program**, which is exactly
what a bi-level outer approximation solves.

## Encoding the choice of a box

One categorical variable per design variable component, one-hot encoded as
$\alpha_{j,k} \in \{0,1\}$ with $\sum_k \alpha_{j,k} = 1$.

:::{important}
The master problem carries $\sum_j m_j$ binaries, **linear** in the number of
components, while the number of boxes $\prod_j m_j$ is exponential in it. The
Cartesian product is never enumerated.
:::

The bounds of the selected box are **affine** in $\alpha$:

$$
\ell_j(\alpha) = \sum_k l_{j,k}\, \alpha_{j,k},
\qquad
u_j(\alpha) = \sum_k u_{j,k}\, \alpha_{j,k}.
$$

## What grows with the dimension

The boxes are the Cartesian product of the subdivisions, $\prod_j m_j$, which
explodes with the number of variables. The **master does not see them**: it sees
the one-hot binaries, $\sum_j m_j$, which grow linearly. Five variables with ten
subdivisions each is $100\,000$ boxes and $50$ binaries.

```{image} ../_static/figures/complexity.svg
:class: only-light
:alt: The boxes grow as a product, the binaries as a sum
```

```{image} ../_static/figures/complexity-dark.svg
:class: only-dark
:alt: The boxes grow as a product, the binaries as a sum
```

What a budget buys is neither of those, but the number of **sub-problems solved**,
a few dozen for a few thousand evaluations. So the quantity that decides whether
a subdivision is usable is the ratio between the coefficients of the cut model,
$\sum_j m_j$, and the cuts that can be afforded. A fine subdivision is not out of
reach because of its boxes; it is demanding because its model has more
coefficients to identify.

## The bi-level problem

$$
\min_\alpha\ u(\alpha)
\quad \text{where} \quad
u(\alpha) = \min_x \left\{ f(x) : g(x) \le 0,\ \ell(\alpha) \le x \le u(\alpha) \right\}
$$

| Level | Decides | Solved by | Role |
|-------|---------|-----------|------|
| Main | the box, $\alpha$ | MILP master, outer approximation | exploration |
| Sub | $x$ inside the box | NLP, local | exploitation |

This is the `Benders` formulation of
[gemseo-bilevel-outer-approximation](https://gitlab.com/gemseo/dev/gemseo-bilevel-outer-approximation),
with the box-selection variables as the categorical variables of the main
problem.

```{image} ../_static/figures/bilevel.svg
:class: only-light
:alt: The exchange between the master and the sub-problem
```

```{image} ../_static/figures/bilevel-dark.svg
:class: only-dark
:alt: The exchange between the master and the sub-problem
```

## Outer approximation and its sensitivity

The master builds a piecewise-linear underestimator of $u$ from the
sub-problems solved so far, one cut per visited $\alpha^{(i)}$:

$$
\eta \ \ge\ u(\alpha^{(i)}) + s^{(i)\top} (\alpha - \alpha^{(i)}),
\qquad
s^{(i)} = \left.\frac{\mathrm{d}u}{\mathrm{d}\alpha}\right|_{\alpha^{(i)}},
$$

and minimizes $\eta$ over the one-hot polytope. The cuts are what make the
exploration informed rather than exhaustive, so the **slope $s^{(i)}$ is the
heart of the method**.

GEMSEO obtains it by post-optimal analysis of the sub-problem:

$$
\frac{\mathrm{d} f(x^\ast(p), p)}{\mathrm{d} p}
= \frac{\partial f}{\partial p}
+ \lambda_g^\top \frac{\partial g}{\partial p}
+ \lambda_h^\top \frac{\partial h}{\partial p} .
$$

The bounds $\ell \le x \le u$ appear in the sub-problem but **not** in this
formula: it assumes them constant with respect to the parameter $p$. This single
fact drives the whole implementation, and the two formulations below are the two
ways of living with it.

(formulations)=
## The trust region of the master

The master does not choose among all the boxes at every iteration: it restricts
the mixed-integer problem to a neighbourhood of the incumbent box $\alpha$,

$$
\sum_{j \,:\, \alpha'_j = \alpha_j} w_j(\alpha)
\ \ge\ \sum_j w_j(\alpha) - \texttt{max\_step},
$$

whose radius shrinks when the upper bound stops improving. The distance is not
the number of boxes apart: the cost of moving is the sum of the **catalogue
weights the incumbent selects** over the components the candidate changes, and
the catalogue of a subdivided variable being the range of its subdivision
indexes, leaving the first subdivision of a component is free and leaving the
last one costs $m_j - 1$.

```{image} ../_static/figures/trust_region.svg
:class: only-light
:alt: What each radius of the trust region reaches
```

```{image} ../_static/figures/trust_region-dark.svg
:class: only-dark
:alt: What each radius of the trust region reaches
```

The diameter of the design space in that distance is therefore
$\sum_j (m_j - 1)$, which
{py:attr}`~gemseo_box_subdivision.algos.design_space.box_subdivision.BoxSubdivision.max_step`
returns. Starting from it and letting the master shrink it is what the outer
approximation assumes; starting below it confines the search from the first
iteration, and the master's own default radius has nothing to do with the design
space. This is the setting that decides whether a fine subdivision is usable at
all, see [the benchmark](benchmark.md#the-density-of-the-subdivision-decides).

## Two formulations

### Box as a constraint

Keep $x$ as the sub-problem variable and move the box into the constraints, as
one vector-valued function of dimension $2n$:

$$
g_{\text{box}}(x, \alpha) =
\begin{bmatrix} x - u(\alpha) \\ \ell(\alpha) - x \end{bmatrix} \le 0 .
$$

The dependency on $\alpha$ now travels through $\lambda_g^\top \partial g/\partial \alpha$,
and the slope is exact and analytic:

$$
\frac{\mathrm{d} u}{\mathrm{d} \alpha_{j,k}}
= -\lambda^{u}_j\, u_{j,k} + \lambda^{\ell}_j\, l_{j,k},
$$

where $\lambda^{u}_j, \lambda^{\ell}_j \ge 0$ are the multipliers of the upper
and lower faces of the box, that is the shadow price of moving a face.

$g_{\text{box}}$ is linear in $x$ and affine in $\alpha$, hence **jointly
convex**: all the non-convexity stays in the original $f$ and $g$.

### Box as normalized variables

Solve instead for $\xi \in [0,1]^n$, with

$$
x(\xi, \alpha) = \ell(\alpha) + \xi \odot (u(\alpha) - \ell(\alpha)).
$$

The box is then the *bounds* of the sub-problem, and those bounds are the unit
interval **whatever the box**, so the assumption made by the post-optimal
analysis holds instead of being worked around. The slope comes from the partial
derivative rather than from multipliers:

$$
\frac{\mathrm{d}u}{\mathrm{d}\alpha_{j,k}}
= \nabla_x f \cdot \frac{\partial x}{\partial \alpha_{j,k}},
\qquad
\frac{\partial x_j}{\partial \alpha_{j,k}}
= (1-\xi_j)\, l_{j,k} + \xi_j\, u_{j,k},
$$

correct at an interior optimum, where $\nabla_x f$ vanishes, and on a face,
where $\xi_j$ is pinned to a bound so the partial derivative is the total one.

The counterpart is that $x$ is **bilinear** in $(\xi, \alpha)$: the choice of the
box enters the non-linearity of the objective instead of staying in a jointly
convex constraint. As shown in [the benchmark](benchmark.md), this costs nothing
in quality: under the same master settings the normalized formulation reaches the
optimum from every starting point and the constraint one from all but one.

(convexification)=
## Convexification

Outer-approximation cuts are supporting hyperplanes **only if $u$ is convex**. On
a multimodal problem $u$ is not, so a cut built at one box can lie *above* $u$
elsewhere and cut the global optimum off. The master then converges quickly, and
reports a wrong answer without any error.

:::{warning}
Guarding against this is the single most important setting of the method, and
both guards are off by default: `convexification_constant=0.0` and
`adapt=False`. On the benchmark below, that default reaches the global optimum
from **none** of the starting points while reporting success.
:::

The master offers two mechanisms for it, described below. They act differently
and are **not meant to be combined**: use the fixed constant $\kappa$, which
carries the convergence guarantee, or the adaptive repair with its convexity
margin, which reaches the optimum more often, and leave the other at zero.

### What the convexification actually is

`gemseo-bilevel-outer-approximation` adds to the objective a term that is
**convex in the relaxed one-hot variables and vanishes at every integer point**:

$$
\tilde u(\alpha) = u(\alpha) + \kappa\, C(\alpha),
\qquad
C(\alpha) = \frac{1}{n_{\text{comp}}}
\sum_{j}\sum_{k} \alpha_{j,k}\left(\alpha_{j,k} - 1\right).
$$

```{image} ../_static/figures/convexification.svg
:class: only-light
:alt: The convexification term over a relaxed box choice
```

```{image} ../_static/figures/convexification-dark.svg
:class: only-dark
:alt: The convexification term over a relaxed box choice
```

Each term $\alpha(\alpha-1)$ is convex, equals $0$ at $\alpha \in \{0,1\}$ and
reaches $-1/4$ at $\alpha = 1/2$. Two consequences:

- **the discrete problem is unchanged**: at any feasible one-hot $\alpha$,
  $C(\alpha) = 0$, so $\tilde u = u$ and the optimum is exactly the optimum of
  the original problem;
- **the relaxation is lowered between the vertices**, which is what restores the
  validity of the cuts. Large enough $\kappa$ dominates the non-convexity of $u$
  over the relaxed polytope.

In practice the term is never evaluated: only the **slope** of each cut is
corrected, by $\nabla(\kappa C)$,

$$
s^{(i)} \leftarrow s^{(i)} + \frac{\kappa}{n_{\text{comp}}}\left(2\alpha^{(i)} - 1\right),
$$

which at an integer $\alpha^{(i)}$ tilts the hyperplane by $\pm\kappa/n_{\text{comp}}$
per component while leaving its value at $\alpha^{(i)}$ untouched.

:::{note}
This is a convexification **in the space of the box selection $\alpha$**, not an
$\alpha$BB-style underestimator of $f$ in the space of the design variables $x$.
It is not built from bounds on the Hessian of $f$, and it does **not** become
tighter as the boxes get smaller. Subdividing more finely still helps, but for a
different reason: each box becomes closer to unimodal, so the local sub-problem
solve is more likely to return the box optimum, which is what the cuts assume.
:::

### Adaptive convexification

With `adapt=True`, instead of relying on $\kappa$ alone, the master repairs the
slopes against the data it has already gathered. For every pair of visited
points, the cut at $\alpha^{(i)}$ must not over-predict the observed value at
$\alpha^{(j)}$:

$$
u(\alpha^{(i)}) + s^{(i)\top}\left(\alpha^{(j)} - \alpha^{(i)}\right)
\ \le\ u(\alpha^{(j)}) - \delta ,
$$

with $\delta$ a convexity margin (`min_dfk`). The violations are collected and a
least-squares correction is applied to each slope so that the cuts become
consistent with the whole history. It is a data-driven repair of cut validity,
and it **replaces** $\kappa$ rather than composing with it: the margin $\delta$
enforces the convexity the constant would otherwise impose, from the observed
values rather than from a worst case, so setting both applies the correction
twice over. Being a margin on the objective, $\delta$ is an **absolute**
quantity in the units of $f$ and has to be scaled to the problem, whereas
$\kappa$ scales with the relaxed polytope.

The two differ in what they guarantee. A large enough $\kappa$ dominates the
non-convexity of $u$ over the relaxed polytope and the cuts are then valid by
construction, which is the convergence argument; but it also lowers the master's
lower bound by nearly $\kappa$, so the bound never meets the incumbent and the
run ends on the trust region instead of on the tolerance, see
[the benchmark](tuning.md#the-two-caps-that-end-a-run).
The adaptive repair keeps the bound usable and, on the benchmark, reaches the
optimum from every starting point, but it enforces convexity only against the
boxes already visited, so it carries no guarantee.

## Subdividing some variables only

Nothing requires every variable to be subdivided. A variable left out stays an
ordinary variable of the sub-problem, which keeps the product of the
subdivisions small while resolving the variables that need it:

```python
subdivision = BoxSubdivision.from_design_space(design_space, 10, ["x_split"])
```

```{image} ../_static/figures/partial_refinement.png
:class: only-light
:alt: A subdivision of one variable only
```

```{image} ../_static/figures/partial_refinement-dark.png
:class: only-dark
:alt: A subdivision of one variable only
```

The exchange is only worth it when the objective is close to unimodal in the
variables left out: one of them keeps all of its basins inside every box, and the
local solve returns the basin it starts in. It therefore solves a problem whose
multimodality is concentrated in a few variables, and loses on one that is
multimodal in all of them.

## Hierarchies of subdivisions

A fine subdivision spends its budget over the whole space. A **hierarchy** spends
it where it seems to matter: subdivide coarsely, rank the boxes, refine the
promising ones with a subdivision of their own. The product of the subdivisions
is the resolution reached, so two levels of two and five resolve as finely as a
flat ten.

```{image} ../_static/figures/hierarchy.svg
:class: only-light
:alt: Three shapes of hierarchy over the boxes
```

```{image} ../_static/figures/hierarchy-dark.svg
:class: only-dark
:alt: Three shapes of hierarchy over the boxes
```

Three shapes were built and measured, and what separates them is the rule
deciding what to refine and whether a choice can be undone.

**Two levels** refine the best boxes of a coarse subdivision. The ranking may
use the value of the sub-problem solved inside a box, which exists only for the
boxes actually solved, or the **cut model** of the master,

$$
\hat u(\alpha) = \max_i \, u(\alpha^{(i)})
+ s^{(i)\top}\left(\alpha - \alpha^{(i)}\right),
$$

which is defined at every box, those never solved included, and which is an
optimistic estimate, so it ranks boxes far from anything solved first.

**Deep and narrow** splits every variable in two at each of several levels,
reaching $2^{\text{depth}}$ subdivisions per variable while keeping $2n$
coefficients per level, which is the only shape that improves the ratio of the
previous section.

**A frontier** keeps the open boxes of every level in one queue and expands the
most promising, so a box passed over early can still be taken later. That is a
spatial branch-and-bound over the subdivision, and the only shape that can undo a
choice.

Their measured behaviour, and the reason none of them becomes the default, is in
[the results](benchmark.md#the-extensions-and-what-they-are-worth).

## Relation to spatial branch-and-bound

Seen as a whole, the method is a **spatial branch-and-bound whose branching tree
is fixed a priori and flattened into a single MILP master**, rather than refined
adaptively. That framing sets the expectations: a fixed subdivision is either too
coarse, and the lower bound is weak, or too fine, and the master grows. Refining
only the promising boxes would recover a genuine spatial branch-and-bound, at the
cost of a master problem that grows during the run.

## References

- Barjhoux, P.-J., Diouane, Y., Grihon, S., & Morlier, J. (2022). *An outer
  approximation bi-level framework for mixed categorical structural optimization
  problems.* Structural and Multidisciplinary Optimization, 65(8), 214.
- Barjhoux, P.-J., Diouane, Y., Grihon, S., Bettebghor, D., & Morlier, J. (2020).
  *A bi-level methodology for solving large-scale mixed categorical structural
  optimization.* Structural and Multidisciplinary Optimization, 62(1), 337-351.
- Duran, M. A., & Grossmann, I. E. (1986). *An outer-approximation algorithm for
  a class of mixed-integer nonlinear programs.* Mathematical Programming, 36(3),
  307-339.
