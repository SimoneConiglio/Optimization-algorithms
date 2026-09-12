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

## Cost

| Formulation | Method | Objective | Boxes solved | Executions |
|-------------|--------|-----------|--------------|------------|
| constraint | enumeration | $0.0$ | 100 | 1427 |
| constraint | outer approximation | $0.0$ | 18 to 22 | 253 to 316 |
| normalized | enumeration | $0.0$ | 100 | 1267 |
| normalized | outer approximation | $0.0$ | 15 to 22 | 195 to 281 |

About **five times cheaper for the same optimum**, each formulation using its own
tuned convexification.

The normalized formulation also solves its boxes for about 11% less when
enumerating, since its sub-problems are bounded by their box and start inside it,
instead of having to restore the feasibility of a box constraint.

## Convexification is decisive, and not transferable

Sweeping the convexification constant over 16 starting points, counting how often
the global optimum is reached (`benchmarks/tune_convexification.py`):

| Formulation | Constant | `adapt` | Reached | Median executions |
|-------------|----------|---------|---------|-------------------|
| constraint | $0$ to $5$ | yes | 0 / 16 | 30 to 90 |
| constraint | $10$ | yes | 8 / 16 | 234 |
| constraint | $50$ | yes | 9 / 16 | 254 |
| constraint | $500$ | yes | 9 / 16 | 280 |
| normalized | $10$ | yes | 6 / 16 | 188 |
| normalized | $50$ | yes | 15 / 16 | 230 |
| normalized | **$100$** | yes | **16 / 16** | 235 |
| normalized | $200$ | yes | 12 / 16 | 221 |

Three readings:

**Too small a constant fails silently.** Below $10$, the master converges after
two or three sub-problems on a point an order of magnitude from the optimum, and
reports success. The GEMSEO default of $0$ is in this regime.

**There is a genuine optimum.** Too large a constant loosens the relaxation and
the exploration degrades again: the normalized formulation drops from 16/16 at
$100$ to 12/16 at $200$. It cannot simply be set conservatively high.

**The constant is not transferable between formulations.** The normalized one
needs about ten times more, because the bilinearity of $x(\xi,\alpha)$ adds
curvature with respect to the box selection, which is precisely what the
convexification has to dominate.

## Reliability

The tuned settings, over three independent seeds of 16 starting points each:

| Configuration | seed 11 | seed 101 | seed 202 | Total | Median executions |
|---------------|---------|----------|----------|-------|-------------------|
| normalized, $\kappa=100$, adapt | 16/16 | 15/16 | 15/16 | **96%** | 231 |
| constraint, $\kappa=500$, adapt | 9/16 | 10/16 | 9/16 | 58% | 234 |
| constraint, $\kappa=25$, no adapt | 9/16 | 8/16 | 6/16 | 48% | 235 |

At equal cost, the normalized formulation reaches the global optimum from 96% of
the starting points against 58% for the best setting of the constraint one. The
constraint formulation never exceeded 9/16 anywhere between $10$ and $500$, with
or without adaptation, so this is not a tuning gap.

The adaptive convexification is worth 16/16 against 12/16 for the normalized
formulation at its best constant.

:::{note}
An earlier version of this page reported the opposite, that the constraint
formulation explored better. That measurement compared the two at a single
constant of $10$, which suits the constraint formulation and is far too small for
the normalized one. Comparing formulations at a shared constant measures the
constant, not the formulation.
:::

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
| Rastrigin | 2 | $0.00$ · 344 · 3/3 | $0.00$ · 1000 · 2/3 | $1.00$ · 631 · 0/3 | $0.00$ · 649 · 3/3 |
| Rastrigin | 5 | $4.98$ · 584 · 0/3 | $3.98$ · 2500 · 0/3 | $8.96$ · 1945 · 0/3 | $4.98$ · 461 · 0/3 |
| Ackley | 2 | $0.00$ · 353 · 2/3 | $0.00$ · 1000 · 3/3 | $0.00$ · 745 · 3/3 | $0.00$ · 417 · 3/3 |
| Ackley | 5 | $14.43$ · 599 · 0/3 | $9.55$ · 2500 · 0/3 | $0.00$ · 2009 · 3/3 | $0.11$ · 353 · 0/3 |
| Styblinski-Tang | 2 | $0.00$ · 105 · 2/3 | $0.00$ · 1000 · 3/3 | $0.00$ · 535 · 2/3 | $0.00$ · 1011 · 3/3 |
| Styblinski-Tang | 5 | $0.00$ · 502 · 3/3 | $0.00$ · 2340 · 3/3 | $0.00$ · 1457 · 2/3 | $0.00$ · 2505 · 3/3 |
| Griewank | 2 | $0.03$ · 336 · 0/3 | $0.01$ · 1000 · 0/3 | $0.05$ · 643 · 0/3 | $0.01$ · 1011 · 0/3 |
| Griewank | 5 | $0.08$ · 709 · 0/3 | $0.05$ · 2500 · 0/3 | $0.03$ · 1769 · 0/3 | $0.01$ · 397 · 0/3 |

:::{warning}
**These numbers are measurements, not a claim of generalization.** The
convexification constant was tuned on Rastrigin in two dimensions and then held
fixed, which penalises the other three problems, and the default number of
subdivisions was read off the sweep below, on these very problems. Tuning on the
problems one then reports is circular. A claim about the method, rather than
about its tuning, needs a held-out set of problems or a protocol fixed in
advance.
:::

Read with that caveat, the table says three things.

**Where it works, it is the cheapest.** Styblinski-Tang in five dimensions is
solved from every starting point for $502$ evaluations, against $2340$ for
multistart, $1457$ for CMA-ES and $2505$ for DIRECT. Same answer, three to five
times cheaper. Same in two dimensions, for $105$.

**It is not the most reliable.** On Ackley in five dimensions it is the worst of
the four, while CMA-ES reaches the optimum every time.

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
- the sub-problem starting point and the convexification are both decisive, and
  both fail silently when wrong;
- the normalized formulation dominates the constraint one, once each is tuned;
- where the subdivision resolves the basins, the method reaches the optimum for
  three to five times fewer evaluations than multistart, CMA-ES or DIRECT;
- where it does not, the method is the worst of the four, and no setting of the
  convexification recovers it.

Not established:

- **generalization.** The convexification and the number of subdivisions were
  tuned on the problems then reported. A claim about the method needs a held-out
  set or a protocol fixed in advance.
- **a rule for the number of subdivisions.** It has to follow the spacing of the
  basins, which is not known a priori. Estimating it, from the curvature or from
  a first sampling, is the most valuable next step.
- **behaviour with constraints.** Every problem here is bound-constrained only.
- **the industrial case.** The method earns its complexity when a sub-problem
  costs minutes, which is the regime none of these analytic problems is in, and
  the one where the baselines that need an algebraic form cannot compete.
