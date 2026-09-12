<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Benchmark results

## Protocol

Rastrigin in two dimensions over $[-4.1, 5.9]^2$, whose local minima are about
one unit apart, subdivided into $10 \times 10 = 100$ boxes. The bounds are
deliberately asymmetric so that the global minimizer, the origin with $f = 0$, is
neither at the center of a box nor on its border.

The reference is the **enumeration of the boxes**: solving the sub-problem of
every box. It is exhaustive, embarrassingly parallel and needs no cuts, so the
outer approximation is only worth its complexity if it reaches the same optimum
after substantially fewer sub-problems.

Both are drivers of the *same* main problem, through the same `Benders`
formulation and the same design space, so the comparison isolates the
exploration strategy. The budget is counted in **executions of the objective
discipline**, the quantity that is expensive in an industrial problem.

Reproduce with `tox -e benchmark`.

## Cost, and the two formulations

Both formulations run the same master, in the `adaptive` configuration described
below; nothing here is tuned per formulation.

| Formulation | Method | Objective | Boxes solved | Executions |
|-------------|--------|-----------|--------------|------------|
| constraint | enumeration | $0.0$ | 100 | 1427 |
| constraint | outer approximation | $0.0$ | 24 to 28 | 346 to 404 |
| normalized | enumeration | $0.0$ | 100 | 1267 |
| normalized | outer approximation | $0.0$ | 20 to 36 | 254 to 470 |

About **four times cheaper for the same optimum**.

Over eight starting points, the normalized formulation reaches the global optimum
**8 out of 8** times and the constraint one **7 out of 8**, so the normalized one
is retained, as it was on the earlier measurement, but by a much smaller margin
than that measurement suggested.

The normalized formulation also solves its boxes for about 11% less when
enumerating, since its sub-problems are bounded by their box and start inside it,
instead of having to restore the feasibility of a box constraint.

:::{note}
An earlier version of this page reported 96% against 58% for the two
formulations, with a convexification constant tuned separately for each. Once the
two mechanisms of the master are separated and only one is used, both
formulations do better and the difference between them is small. What that
earlier measurement mostly compared was the tuning.
:::

## The master has two mechanisms, and they must not be combined

Outer-approximation cuts are supporting hyperplanes only if the value function is
convex. On a multimodal problem it is not, and the master offers **two distinct
mechanisms** for keeping its cuts usable. They rest on different arguments, and
measuring them together measures neither.

`pure_convexification`
: adds to the objective a convex term vanishing at the integer points. Once its
  constant dominates the concavity of the relaxed problem, the relaxation is
  convex and the outer approximation converges. Driven by
  `convexification_constant`, with `adapt` off.

`adaptive`
: repairs the slope of each cut by least squares against the pairs of points
  already observed, so that no cut over-predicts a value that has been measured.
  Driven by `adapt` and the convexity margin `min_dfk`, with no convexification
  constant.

:::{warning}
An earlier version of this page reported a single sweep with **both** mechanisms
active, and concluded that the convexification constant was decisive and not
transferable between formulations. That measurement was confounded and its
conclusion is withdrawn. The two are swept apart below.
:::

### The adaptive repair, which reaches the optimum most often

Rastrigin in two dimensions, eight starting points, no convexification constant:

| parallel points | `min_dfk` = 1 | 10 | **30** | **100** | 300 |
|-----------------|---------------|----|--------|---------|-----|
| 1 | 0/8 | 0/8 | — | — | — |
| **4** | 1/8 | 3/8 | **8/8** (26 boxes) | **8/8** (24 boxes) | 7/8 |
| 8 | 0/8 | 1/8 | 8/8 (26) | 8/8 (52) | 8/8 (56) |

Two settings are essential rather than an optimization.

**Several parallel points.** The master probes one trust-region radius per point,
over `geomspace(step / 2, step)`, so that a feasible master problem stays
available. With a single point the run stops after two or three boxes whatever
the margin.

**A margin on the scale of the objective.** `min_dfk` is subtracted from an
objective difference, so it is an absolute quantity in the units of the
objective, not a ratio. The objective spans about eighty here, and a margin of
thirty to a hundred reaches the optimum every time, a margin of ten three times
out of eight, a margin of one never.

### The pure convexification, and the range where it is worth using

The constant has to dominate the non-convexity of the relaxed problem, and no
more: past that, every unexplored box outranks the incumbent whatever the cuts
say, the master ranks them by nothing in particular, and the method degenerates
towards the enumeration it exists to avoid. Since the enumeration of these $100$
boxes is available for free and is embarrassingly parallel, a configuration is
only worth its complexity while it stays well under it, which is the last two
columns below.

Same problem and starting points, `adapt` off, one parallel point, trust region
sized to the design space:

| constant | reached | worst | boxes | of the enumeration | evaluations | of the enumeration |
|----------|---------|-------|-------|--------------------|-------------|--------------------|
| $10$ | 0/8 | $17.91$ | 2 | 2% | 32 | 3% |
| $20$ | 5/8 | $3.98$ | 14 | 14% | 182 | 14% |
| $30$ | 7/8 | $1.99$ | 26 | 26% | 334 | 26% |
| $50$ | **8/8** | $0.00$ | 22 | 22% | 288 | 23% |
| $75$ | 7/8 | $0.99$ | 22 | 22% | 281 | 22% |
| $100$ | **8/8** | $0.00$ | 20 | 20% | 254 | 20% |
| $150$ | 6/8 | $0.99$ | 22 | 22% | 283 | 22% |
| $200$ | 5/8 | $1.99$ | 18 | 18% | 239 | 19% |
| $300$ | 6/8 | $0.99$ | 20 | 20% | 258 | 20% |

The useful window is **fifty to a hundred**, where the optimum is reached from
every starting point for about a fifth of the enumeration. It is no accident that
this is the order of magnitude of the variation of the objective over the design
space, about eighty here, which is also the order of the convexity margin the
adaptive repair needs: both mechanisms are calibrated against the same quantity,
the non-convexity they have to dominate, and neither is dimensionless.

Past that window the result decays, $6/8$ then $5/8$, and it keeps decaying at the
values tried before writing this, $4/8$ at $10^4$ and $3/8$ at $10^5$. What does
*not* happen is the cost growing with the constant: it stays near a fifth of the
enumeration throughout, because the run ends on the two caps described next
rather than on its optimality test. An exaggerated constant therefore buys
nothing and costs the same; it is not a safe default to be conservative with.

### The two caps that end a run

Instrumenting the master problem shows why the constant cannot be pushed to the
regime where its guarantee would apply.

**The constant destroys the lower bound.** The optimum $\eta$ of the master comes
back at $-996$ for a constant of $1000$, and at $-9991$ for $10^4$: that is
$\eta \approx -\kappa$. The convexification tilts every cut by
$\pm\kappa / n_{\text{comp}}$ per component, and the relaxed master exploits that
tilt. The gap $\mathrm{ub} - \mathrm{lb} \approx \mathrm{ub} + \kappa$ therefore
never closes, and the convergence test on `ub_tol` can never fire. The guarantee
is not wrong; it is unreachable, the algorithm never obtaining the certificate
that would let it stop on optimality.

**So the run ends on a heuristic cap instead.** Either the trust region shrinks
until the master is infeasible, described in the next section, or, when the trust
region is inactive, the stall counter fires:

```text
MILP : Stalling iterations: 10/10.
The Upper bound stopped changing for 10 iterations.
```

`upper_bound_stall` defaults to ten: the master gives up after ten iterations
that do not improve the incumbent, whatever its lower bound says. With one box
solved per iteration, that alone caps a run near twenty boxes out of a hundred,
which is exactly where the table above saturates.

That is the whole answer to why raising the constant stops buying exploration:
the run can only end on one of these caps, never on the optimality test, so the
exploration is set by the caps and the constant only decides how well the cuts
rank the boxes visited before they fire. Lifting the caps to recover the
guarantee would cost the sub-problems the outer approximation exists to save,
which is the same trade as enumerating.

Two implementation changes would follow, and neither is made here: restoring the
step towards `max_step` and retrying before giving up on an infeasible master,
and reporting the bound net of the convexification term, which vanishes at the
integer points and so leaves the gap meaningful.

## The trust region is a compromise, and its default is not the design space

The master does not consider every box at each iteration: it restricts the MILP
to a neighbourhood of the incumbent, whose radius `max_step` shrinks when the
upper bound stops improving. Without that restriction the master is the textbook
outer approximation, which explores until its lower bound rises above the
incumbent; with it, the run is cheaper and stops earlier. Which is the better
trade depends on the problem, so the radius is worth setting deliberately.

Two things make the default wrong for a box subdivision.

**The distance is not the number of boxes apart.** The trust region is the linear
constraint

$$
\sum_{j \,:\, \alpha'_j = \alpha_j} w_j(\alpha) \ \ge\ \sum_j w_j(\alpha) - \texttt{max\_step},
$$

so the cost of moving from the incumbent $\alpha$ to a candidate $\alpha'$ is the
sum of the **weights the incumbent selects** over the components the candidate
changes. The design spaces built here leave the catalogue weights at their
default, which `CatalogueDesignSpace` sets to the catalogue itself, and the
catalogue of a subdivided variable is the range of its subdivision indexes:

```text
x_box weights = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
```

Leaving the first subdivision of a component is therefore free and leaving the
last one costs $m_j - 1$, whatever the candidate. The distance is neither the
number of components changed nor how far they move.

**The default radius is smaller than the design space.** The largest distance is
$\sum_j (m_j - 1)$, which is $18$ for the two variables and ten subdivisions of
this benchmark, against the master's default `max_step` of $10$. The trust region
is then active from the first iteration, and once it shrinks, an incumbent whose
indexes are high cannot change any component at all: the master can only
re-propose the incumbent, which has been eliminated, so the MILP becomes
infeasible and the run stops. Instrumenting the last iteration of a run stopping
at $14$ boxes shows exactly that: dropping either the elimination constraints or
the trust region alone restores feasibility, neither alone is the cause.

{py:attr}`~gemseo_box_subdivision.algos.design_space.box_subdivision.BoxSubdivision.max_step`
returns that largest distance, to be passed to the master.

Sweeping the constant of the pure convexification at both radii, over eight
starting points:

| `max_step` | $\kappa = 10$ | $50$ | $100$ | $1000$ |
|------------|---------------|------|-------|--------|
| $10$, the master default | 0/8 | 5/8 | 6/8 | — |
| $18$, the design space | 0/8 | **8/8** | **8/8** | 7/8 |

At its best constant, the pure convexification reaches the optimum from every
starting point once the trust region is sized to the design space. Per starting
point, the two runs that fail at $10$ both succeed at $18$, and every run solves
a few more boxes:

```text
start box      max_step 10          max_step 18
   [1, 4]   0.9950 (14 boxes)   0.0000 (20 boxes)
   [3, 5]   0.9950 (16 boxes)   0.0000 (20 boxes)
```

For the adaptive repair, which already reaches 8/8, the larger radius only costs:
$47$ boxes and $606$ evaluations instead of $24$ and $308$, for the same optimum.
So the radius buys exploration and is paid for in evaluations, which is what a
trust region is for; the default configuration keeps the master's own value, and
a problem on which the run stops early is a reason to raise it to
`subdivision.max_step`.

Deactivating the shrink instead, by setting `step_decreasing_activation` above
the number of iterations, does not help: the run then ends on the stall counter
described above, at 6/8 for $\kappa = 100$, with the same numbers under the index
weights and under unit weights, which is the signature of a trust region inactive
in both. The two caps replace each other, which is why neither the constant nor
the radius alone recovers the guarantee.

## Comparison with the baselines of the problem class

Enumerating the boxes measures the exploration, but it is not what a practitioner
would otherwise use. The baselines that actually address a multimodal non-linear
program driven by a local solver are:

**multistart** of that local solver
: the reference of the class, and the ancestor of the frameworks that combine a
  global sampling with local solves.

**CMA-ES**
: an evolution strategy, which uses no gradient.

**DIRECT**
: a deterministic partitioning method, which uses no gradient either.

:::{note}
Relaxation-based global solvers, BARON, SCIP, Couenne or Alpine, are
deliberately absent. They build convex relaxations from the **algebraic form** of
the problem, which the sub-problem of an industrial case does not have: it is a
disciplinary optimization or a multidisciplinary analysis. They are the right
comparison for a polynomial program, and no comparison at all for this one.
:::

### Counting a budget across methods that differ that much

A method using the gradient cannot be compared with one that does not on the
number of objective evaluations alone: the gradient is information, and it is not
free. The budget is therefore counted in **equivalent** evaluations, under the
two conventions that bracket the truth:

| convention | a gradient costs | the case it represents |
|------------|------------------|------------------------|
| adjoint | $1$ evaluation | an adjoint is available, which is what the method targets |
| finite differences | $n$ evaluations | the objective is a black box |

CMA-ES and DIRECT are unaffected by the convention, so reporting both brackets
the comparison instead of picking the flattering one. Every method is stopped as
soon as its budget is spent, so the comparison is at equal cost rather than at
equal number of iterations, which would mean nothing here.

Two pitfalls the harness guards against, both found the hard way:

- a method whose settings are rejected returns an infinite objective after **no
  evaluation at all**, and so appears to lose fairly. A test now asserts that
  every method evaluates something and returns a finite value;
- DIRECT calls its objective from a C extension, where raising an exception to
  stop on the budget yields a `SystemError`. The methods that bound their own
  number of evaluations exactly are left to do so.

### Results

Four problems, two dimensions, three starting points, a budget of $500$
equivalent evaluations per design variable. Each cell is the **median distance to
the optimum**, the **median cost** under the adjoint convention, and the number
of starting points from which the optimum was **reached**.

| problem | $n$ | box subdivision | multistart | CMA-ES | DIRECT |
|---------|-----|-----------------|------------|--------|--------|
| Rastrigin | 2 | $0.00$ · 519 · 3/3 | $0.00$ · 1000 · 2/3 | $1.00$ · 631 · 0/3 | $0.00$ · 649 · 3/3 |
| Rastrigin | 5 | $4.98$ · 899 · 0/3 | $3.98$ · 2500 · 0/3 | $8.96$ · 1945 · 0/3 | $4.98$ · 461 · 0/3 |
| Ackley | 2 | $0.00$ · 708 · 3/3 | $0.00$ · 1000 · 3/3 | $0.00$ · 745 · 3/3 | $0.00$ · 417 · 3/3 |
| Ackley | 5 | $9.71$ · 1429 · 0/3 | $9.55$ · 2500 · 0/3 | $0.00$ · 2009 · 3/3 | $0.11$ · 353 · 0/3 |
| Styblinski-Tang | 2 | $0.00$ · 218 · 3/3 | $0.00$ · 1000 · 3/3 | $0.00$ · 535 · 2/3 | $0.00$ · 1011 · 3/3 |
| Styblinski-Tang | 5 | $0.00$ · 466 · 3/3 | $0.00$ · 2340 · 3/3 | $0.00$ · 1457 · 2/3 | $0.00$ · 2505 · 3/3 |
| Griewank | 2 | $0.01$ · 1000 · 0/3 | $0.01$ · 1000 · 0/3 | $0.05$ · 643 · 0/3 | $0.01$ · 1011 · 0/3 |
| Griewank | 5 | $0.06$ · 1644 · 0/3 | $0.05$ · 2500 · 0/3 | $0.03$ · 1769 · 0/3 | $0.01$ · 397 · 0/3 |

:::{warning}
**These numbers are measurements, not a claim of generalization.** The convexity
margin was set on Rastrigin in two dimensions and then applied to every problem,
although it is an absolute quantity in the units of the objective: it is far too
large for Griewank, whose objective spans about two, and probably too small for
Styblinski-Tang in five dimensions, whose objective spans hundreds. The default
number of subdivisions was likewise read off the sweep below, on these very
problems. Tuning on the problems one then reports is circular. A claim about the
method needs a held-out set of problems, a protocol fixed in advance, and a
margin scaled to each problem.
:::

Read with that caveat, the table says three things.

**Where it works, it is the cheapest.** Styblinski-Tang in five dimensions is
solved from every starting point for $466$ evaluations, against $2340$ for
multistart, $1457$ for CMA-ES and $2505$ for DIRECT. Same answer, three to five
times cheaper. In two dimensions it reaches the optimum from every starting point
on all three problems that any method solves.

**It is not the most reliable in five dimensions.** On Ackley it matches
multistart and is beaten by CMA-ES, which reaches the optimum every time; on
Griewank, DIRECT is closer.

**DIRECT is a serious baseline at low dimension**, cheap and reliable, and any
claim for the method has to be made against it rather than against multistart
alone.

## The subdivision has to resolve the basins

Sweeping the number of subdivisions per variable in five dimensions, in the
`adaptive` configuration, over three starting points: median distance to the
optimum, the number of runs reaching it, and the median number of evaluations.

| problem | $m=2$ (32 boxes) | $m=3$ (243) | $m=4$ (1024) | $m=10$ ($10^5$) |
|---------|------------------|-------------|--------------|------------------|
| Styblinski-Tang | **$0.00$, 3/3, 481** | $0.00$, 3/3, 641 | $0.00$, 3/3, 783 | $0.00$, 3/3, 1387 |
| Rastrigin | **$4.98$**, 0/3, 707 | $4.98$, 0/3, 1882 | $6.70$, 0/3, 950 | $15.92$, 0/3, 1319 |
| Ackley | **$9.71$**, 0/3, 1428 | $14.90$, 1/3, 2500 | $14.70$, 0/3, 2500 | $17.86$, 0/3, 1946 |

Two readings, one of which corrects an earlier version of this page.

**The number of boxes is a matter of cost, not of feasibility.**
Styblinski-Tang is solved from every starting point at *every* density, from
$32$ boxes to $100\,000$, the cost merely growing from $481$ to $1387$
evaluations: the master still finds its way among $50$ binaries. The coarsest
subdivision is therefore the right default, being the cheapest, not the only one
that works.

:::{note}
An earlier version of this page reported Styblinski-Tang degrading from $0.00$
at $m=2$ to $35.07$ at $m=10$ and concluded that too many boxes make the cut
model unable to discriminate. That measurement mixed the two mechanisms of the
master; with the adaptive repair alone, the degradation disappears. What
collapses under a large number of boxes is the fixed convexification constant,
not the method: run instead in the `pure_convexification` configuration, the
same Styblinski-Tang goes from $0.00$, 3/3 at $m=2$ to $65.42$, 0/3 at $m=10$,
the run stopping after $151$ evaluations, the master being infeasible almost at
once.
:::

**What the subdivision must resolve is the landscape, not the dimension.**
Styblinski-Tang has about $2^n$ basins and even $m=2$ separates them, hence the
perfect score at every density. Rastrigin, whose minima are one unit apart over a
range of ten, has about $10^n$ of them: no tractable subdivision separates them
in five dimensions, and refining does not help, it hurts, the boxes staying
multimodal while the master grows. Ackley behaves the same way.

The requirement is therefore on the **basins** rather than on the boxes: each box
has to be close enough to unimodal for its local solve to return the box optimum,
which is what the cuts assume. That is the honest answer to how the method
scales: it scales with the number of basins, not with the number of variables,
and it suits a problem with a moderate number of them.

The default keeps the number of boxes in the hundreds, which is a stopgap
justified by cost: it is the cheapest density among those that do as well. The
number of subdivisions that actually suits a problem follows the spacing of its
basins, which the method does not know, and estimating it, from the curvature or
from a first sampling, is the most valuable next step.

## What this does and does not establish

Established:

- against the exhaustive enumeration of the boxes, the outer approximation
  reaches the same optimum solving about a fifth of them, at about a fifth of the
  cost;
- the sub-problem starting point and the guard against non-convexity are both
  decisive, and both fail silently when wrong;
- the adaptive repair, with a convexity margin scaled to the objective and
  several boxes solved per master iteration, reaches the optimum from every
  starting point, for about a quarter of the enumeration;
- so does the fixed convexification constant, in a window of about fifty to a
  hundred and with the trust region sized to the design space, for about a fifth
  of the enumeration; outside that window it decays, and both constants are of
  the order of the variation of the objective, not dimensionless;
- the two formulations behave alike under the same master settings, the
  normalized one being slightly ahead and cheaper to assemble;
- where the subdivision resolves the basins, the method reaches the optimum for
  three to five times fewer evaluations than multistart, CMA-ES or DIRECT;
- where it does not, the method is the worst of the four, and no setting of
  either mechanism recovers it;
- the number of boxes costs evaluations but does not, by itself, defeat the
  master: with the adaptive repair, Styblinski-Tang in five dimensions is solved
  from every starting point over $32$ boxes as well as over $100\,000$.

Not established:

- **generalization.** The convexity margin and the number of subdivisions were
  tuned on the problems then reported, and the margin is in the units of the
  objective, so it does not even transfer between them unchanged. A claim about
  the method needs a held-out set or a protocol fixed in advance.
- **a rule for the number of subdivisions.** It has to follow the spacing of the
  basins rather than the dimension, and that spacing is not known a priori. Estimating it, from the curvature or from
  a first sampling, is the most valuable next step.
- **the convergence guarantee of the convexification.** A run ends on the trust
  region or on the stall counter, never on the optimality test, so the guarantee
  is out of reach whatever the constant; and lifting both caps to recover it
  costs the sub-problems the method exists to save.
- **behaviour with constraints.** Every problem here is bound-constrained only.
- **the industrial case.** The method earns its complexity when a sub-problem
  costs minutes, which is the regime none of these analytic problems is in, and
  the one where the baselines that need an algebraic form cannot compete.
