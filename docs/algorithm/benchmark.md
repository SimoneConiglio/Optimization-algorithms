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

### The pure convexification, which saturates

Same problem and starting points, `adapt` off, one parallel point:

| constant | $0$ | $1$ | $10$ | $50$ | $100$ | $500$ | $2000$ | $10^4$ | $10^5$ |
|----------|-----|-----|------|------|-------|-------|--------|--------|--------|
| reached | 0/8 | 0/8 | 0/8 | 5/8 | **6/8** | 5/8 | **6/8** | 4/8 | 3/8 |
| boxes | 2 | 2 | 2 | 20 | 15 | 16 | 16 | 15 | 16 |

Raising the constant helps sharply up to about a hundred, then **stops helping
and eventually hurts**, while the number of boxes explored saturates near
fifteen to twenty out of a hundred. That is not what the theory predicts, and the
reason is in the implementation rather than in the argument.

### Why raising the constant stops buying exploration

Instrumenting the master problem shows two coupled effects.

**The constant destroys the lower bound.** The optimum $\eta$ of the master comes
back at $-996$ for a constant of $1000$, and at $-9991$ for $10^4$: that is
$\eta \approx -\kappa$. The convexification tilts every cut by
$\pm\kappa / n_{\text{comp}}$ per component, and the relaxed master exploits that
tilt. The gap $\mathrm{ub} - \mathrm{lb} \approx \mathrm{ub} + \kappa$ therefore
never closes, and the convergence test on `ub_tol` can never fire. The guarantee
is not wrong; it is unreachable, the algorithm never obtaining the certificate
that would let it stop on optimality.

**Without a usable bound, the run can only die of an infeasible master.** The
trust region shrinks after three iterations without improvement, and the loop
ends on the first infeasible master problem:

```text
kappa = 1000 :  step 7.0 -> 4.9 -> 3.4, then infeasible -> stop   (13 boxes)
kappa = 10000:  step 5.9 -> 4.1 -> 2.9, then infeasible -> stop   (25 boxes)
```

So the number of boxes explored is set by the **schedule that shrinks the trust
region**, not by the constant, which is why it saturates and why it is not
monotone. Raising `max_step` from ten to a hundred changes nothing: it is the
shrinking that ends the run, not the ceiling.

Two things would follow from this, and neither is implemented here: restoring the
step towards `max_step` and retrying before giving up on an infeasible master,
and reporting the bound net of the convexification term, which vanishes at the
integer points and so leaves the gap meaningful.

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

The number of subdivisions per variable cannot be held fixed as the dimension
grows. In five dimensions with ten subdivisions, the Cartesian product is
$100\,000$ boxes, of which a run solves a score: the cut model, over $50$
binaries, cannot discriminate between them, and the master stops almost
immediately.

Sweeping the number of subdivisions in five dimensions, median distance to the
optimum over three starting points:

| problem | $m=2$ (32 boxes) | $m=3$ (243) | $m=4$ (1024) | $m=10$ ($10^5$) |
|---------|------------------|-------------|--------------|------------------|
| Styblinski-Tang | **$0.00$, 3/3** | $0.00$, 3/3 | $3.68$ | $35.07$ |
| Rastrigin | $4.98$ | $7.96$ | $6.70$ | $23.88$ |
| Ackley | $14.43$ | $16.85$ | $15.93$ | $18.82$ |

And the convexification is **not** the cause: raising its constant from $100$ to
$100\,000$ in five dimensions does not recover anything, Styblinski-Tang going
from $35$ to $73$, with the cost staying near a hundred evaluations, that is with
the master still stopping at once.

So two requirements pull against each other:

- the boxes must be **few enough** for the cut model, built from a handful of
  solved boxes, to tell them apart;
- each box must be **close enough to unimodal** for its local solve to return the
  box optimum, which is what the cuts assume.

Their conflict, rather than the dimension itself, is what bounds the method: the
subdivision has to **resolve the basins of the landscape**. Styblinski-Tang has
about $2^n$ basins and $m=2$ matches them exactly, hence the perfect score.
Rastrigin, whose minima are one unit apart over a range of ten, has about $10^n$
of them, out of reach of any tractable subdivision.

That is the honest answer to how the method scales: it scales with the **number
of basins**, not with the number of variables, and it suits a problem with a
moderate number of them. The default keeps the number of boxes bounded, which is
a stopgap; the number of subdivisions that suits a problem follows the spacing of
its basins, which the method does not know.

## What this does and does not establish

Established:

- against the exhaustive enumeration of the boxes, the outer approximation
  reaches the same optimum solving about a fifth of them, at about a fifth of the
  cost;
- the sub-problem starting point and the guard against non-convexity are both
  decisive, and both fail silently when wrong;
- the adaptive repair, with a convexity margin scaled to the objective and
  several boxes solved per master iteration, reaches the optimum from every
  starting point, where the fixed convexification constant saturates near
  six out of eight whatever its value;
- the two formulations behave alike under the same master settings, the
  normalized one being slightly ahead and cheaper to assemble;
- where the subdivision resolves the basins, the method reaches the optimum for
  three to five times fewer evaluations than multistart, CMA-ES or DIRECT;
- where it does not, the method is the worst of the four, and no setting of
  either mechanism recovers it.

Not established:

- **generalization.** The convexity margin and the number of subdivisions were
  tuned on the problems then reported, and the margin is in the units of the
  objective, so it does not even transfer between them unchanged. A claim about the method needs a held-out
  set or a protocol fixed in advance.
- **a rule for the number of subdivisions.** It has to follow the spacing of the
  basins, which is not known a priori. Estimating it, from the curvature or from
  a first sampling, is the most valuable next step.
- **behaviour with constraints.** Every problem here is bound-constrained only.
- **the industrial case.** The method earns its complexity when a sub-problem
  costs minutes, which is the regime none of these analytic problems is in, and
  the one where the baselines that need an algebraic form cannot compete.
