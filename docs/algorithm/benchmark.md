<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Benchmark results

What the method achieves, against the exhaustive enumeration of the boxes and
against the three baselines of the problem class. The problems are described in
[one appendix](problems.md) and the baselines in [the other](baselines.md); how
the settings were arrived at is [a page of its own](tuning.md).

Reproduce with `tox -e benchmark`.

## Against the enumeration of the boxes

The reference is the **enumeration**: solving the sub-problem of every box. It is
exhaustive, embarrassingly parallel and needs no cuts, so the outer approximation
is only worth its complexity if it reaches the same optimum after substantially
fewer sub-problems. Both drive the same main problem through the same `Benders`
formulation, so the comparison isolates the exploration strategy.

Rastrigin in two dimensions, $10 \times 10 = 100$ boxes, eight starting points,
counted in **executions of the objective discipline**:

| formulation | method | objective | boxes solved | executions |
|-------------|--------|-----------|--------------|------------|
| constraint | enumeration | $0.0$ | 100 | 1427 |
| constraint | outer approximation | $0.0$ | 24 to 28 | 346 to 404 |
| normalized | enumeration | $0.0$ | 100 | 1267 |
| normalized | outer approximation | $0.0$ | 20 to 36 | 254 to 470 |

About **four times cheaper for the same optimum**. The normalized formulation
reaches it from all eight starting points and the constraint one from seven, and
it also enumerates for about 11% less, its sub-problems being bounded by their
box instead of having to restore the feasibility of a box constraint. It is
therefore the one to prefer, by a small margin.

## Against the baselines

Four problems, two dimensions, three starting points, a budget of $500$
equivalent evaluations per design variable under the adjoint convention. Each
cell is the **median distance to the optimum**, the **median cost**, and the
number of starting points from which the optimum was **reached**.

| problem | $n$ | box subdivision | multistart | CMA-ES | DIRECT |
|---------|-----|-----------------|------------|--------|--------|
| Rastrigin | 2 | $0.00$ · 786 · 3/3 | $0.00$ · 1000 · 2/3 | $1.00$ · 631 · 0/3 | $0.00$ · 649 · 3/3 |
| Rastrigin | 5 | $4.98$ · 899 · 0/3 | $3.98$ · 2500 · 0/3 | $8.96$ · 1945 · 0/3 | $4.98$ · 461 · 0/3 |
| Ackley | 2 | $0.00$ · 422 · 2/3 | $0.00$ · 1000 · 3/3 | $0.00$ · 745 · 3/3 | $0.00$ · 417 · 3/3 |
| Ackley | 5 | $9.71$ · 1388 · 0/3 | $9.55$ · 2500 · 0/3 | $0.00$ · 2009 · 3/3 | $0.11$ · 353 · 0/3 |
| Styblinski-Tang | 2 | $0.00$ · 240 · 3/3 | $0.00$ · 1000 · 3/3 | $0.00$ · 535 · 2/3 | $0.00$ · 1011 · 3/3 |
| Styblinski-Tang | 5 | $0.00$ · 466 · 3/3 | $0.00$ · 2340 · 3/3 | $0.00$ · 1457 · 2/3 | $0.00$ · 2505 · 3/3 |
| Griewank | 2 | $0.01$ · 1000 · 0/3 | $0.01$ · 1000 · 0/3 | $0.05$ · 643 · 0/3 | $0.01$ · 1011 · 0/3 |
| Griewank | 5 | $0.06$ · 1644 · 0/3 | $0.05$ · 2500 · 0/3 | $0.03$ · 1769 · 0/3 | $0.01$ · 397 · 0/3 |

```{image} ../_static/figures/results.svg
:class: only-light
:alt: Cost of each method on each problem, with the optima reached
```

```{image} ../_static/figures/results-dark.svg
:class: only-dark
:alt: Cost of each method on each problem, with the optima reached
```

**Where it works, it is the cheapest.** Styblinski-Tang in five dimensions is
solved from every starting point for $466$ evaluations, against $2340$ for
multistart, $1457$ for CMA-ES and $2505$ for DIRECT: the same answer, three to
five times cheaper.

**It is not the most reliable.** On Ackley in five dimensions CMA-ES reaches the
optimum every time and the method does not; on Griewank, DIRECT is closer. And
DIRECT is a serious baseline at low dimension, cheap and reliable, so any claim
for the method has to be made against it rather than against multistart alone.

**The table understates the five-variable rows**, which use the default
subdivision of two per variable. At ten per variable Rastrigin is solved, as the
next section shows, and nothing else in this table does that.

:::{warning}
**These numbers are measurements, not a claim of generalization.** The convexity
margin and the number of subdivisions were tuned on these very problems, and the
margin is an absolute quantity in the units of the objective, so it does not even
transfer between them unchanged. A claim about the method needs a held-out set of
problems and a protocol fixed in advance.
:::

## The density of the subdivision decides

The number of boxes is the Cartesian product of the subdivisions, so it explodes
with the dimension, but the master does not see it: it sees the **one-hot
binaries**, $\sum_j m_j$, which grow linearly. Five variables with ten
subdivisions each is $100\,000$ boxes and only $50$ binaries.

Five variables, the `adaptive` configuration, the trust region sized to the
design space:

| problem | $m = 2$ (32 boxes) | $m = 10$ ($10^5$ boxes) |
|---------|--------------------|-------------------------|
| Rastrigin | $4.98$ · 899 · 0/3 | **$0.00$ · 3357 · 2/3** |
| Ackley | $9.71$ · 1429 · 0/3 | $7.08$ · 4665 · 0/3 |
| Styblinski-Tang | **$0.00$ · 466 · 3/3** | $0.00$ · 905 · 1/3 |
| Griewank | **$0.06$ · 1644 · 0/3** | $0.11$ · 4964 · 0/3 |

```{image} ../_static/figures/density.svg
:class: only-light
:alt: What the density of the subdivision does at five variables
```

```{image} ../_static/figures/density-dark.svg
:class: only-dark
:alt: What the density of the subdivision does at five variables
```

**Rastrigin in five dimensions is solved**, from two starting points out of
three, for about $3400$ evaluations, which no baseline achieves at any budget
tried here. Ackley improves for three times the cost. Styblinski-Tang and
Griewank, whose basins two subdivisions per variable already separate, only get
more expensive.

So the subdivision has to **resolve the basins** of the landscape, and it can
afford to; refining past them spends sub-problems on boxes that were already
unimodal. Two settings decide whether that is reachable, the radius of the trust
region and the convexity margin, both on [the tuning page](tuning.md).

:::{note}
An earlier version of this page reported this density as a failure and concluded
that densely multimodal landscapes were out of reach. That measurement was made
with the trust region of the master four times smaller than the design space,
which is its default and is unrelated to the problem.
:::

## What this does and does not establish

Established:

- against the exhaustive enumeration of the boxes, the outer approximation
  reaches the same optimum solving about a quarter of them, at about a quarter of
  the cost;
- the sub-problem starting point and the guard against non-convexity are both
  decisive, and both fail silently when wrong;
- where the subdivision resolves the basins, the method reaches the optimum for
  three to five times fewer evaluations than multistart, CMA-ES or DIRECT;
- a subdivision fine enough to resolve them stays tractable, the master growing
  with the binaries and not with the boxes: Rastrigin in five dimensions, out of
  reach of every baseline here, is solved over $100\,000$ boxes;
- subdividing only the variables the objective is multimodal in solves a problem
  that subdividing every variable coarsely does not, and loses when the
  multimodality is spread over all of them;
- the radius of the trust region has to start at the diameter of the design
  space, $\sum_j (m_j - 1)$, the master's default of ten being unrelated to it.

Not established:

- **generalization.** The constants and the number of subdivisions were tuned on
  the problems then reported. A claim about the method needs a held-out set or a
  protocol fixed in advance.
- **a rule for the number of subdivisions.** It has to follow the spacing of the
  basins rather than the dimension, and that spacing is not known a priori.
  Estimating it, from the curvature or from a first sampling, is the most
  valuable next step, and the same estimate would say which variables to
  subdivide at all.
- **the convergence guarantee of the convexification.** A run ends on the trust
  region or on the stall counter, never on the optimality test, so the guarantee
  is out of reach whatever the constant, and lifting both caps to recover it
  costs the sub-problems the method exists to save.
- **behaviour with constraints.** Every problem here is bound-constrained only.
- **the industrial case.** The method earns its complexity when a sub-problem
  costs minutes, which is the regime none of these analytic problems is in, and
  the one where the baselines that need an algebraic form cannot compete.
