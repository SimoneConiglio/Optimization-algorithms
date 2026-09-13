<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Results

What the method achieves, against the exhaustive enumeration of the boxes and
against the three baselines of the problem class. The problems are described in
[one appendix](problems.md) and the baselines in [the other](baselines.md); how
the settings were arrived at is [annex C](tuning.md).

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

Refining further stops paying, and the point where it turns over is the ratio of
the methodology: the cut model has $\sum_j m_j$ coefficients, and a budget buys a
few dozen cuts to identify them. Sweeping past the density above, with the radius
sized to the diameter each time:

| problem | budget | $m=10$ (50 binaries) | $m=16$ (80) | $m=24$ (120) |
|---------|--------|----------------------|-------------|--------------|
| Rastrigin | $2500$ | **$1.00$, 2/6** | $4.38$ | $6.96$ |
| Rastrigin | $5000$ | **$0.50$, 3/6** | $3.39$ | $6.83$ |
| Ackley | $2500$ | **$10.15$** | $16.61$ | $14.42$ |
| Ackley | $5000$ | **$8.11$, 1/6** | $9.63$ | $11.66$ |

Ten subdivisions per variable is a sweet spot rather than a floor: at sixteen the
model carries eighty coefficients against the fifty or so cuts the budget
affords, and the quality collapses whatever the number of boxes it could
represent. So a subdivision is usable while its **binaries stay below the
sub-problems a budget can pay for**, which is the rule the number of boxes never
gave.

So the subdivision has to **resolve the basins** of the landscape, and it can
afford to, up to that ratio; refining past the basins spends sub-problems on
boxes that were already unimodal. Two settings decide whether that is reachable, the radius of the trust
region and the convexity margin, both in [annex C](tuning.md).

:::{note}
An earlier version of this page reported this density as a failure and concluded
that densely multimodal landscapes were out of reach. That measurement was made
with the trust region of the master four times smaller than the design space,
which is its default and is unrelated to the problem.
:::

## The extensions, and what they are worth

Three extensions were built on top of the method and measured at equal budget,
five variables, six starting points, $2500$ equivalent evaluations. None of them
becomes a default, and each says something about where the method's difficulty
lies. The sweeps behind these numbers are in [annex C](tuning.md).

**Subdividing some variables only** wins where the multimodality is concentrated
and loses where it is not, which is the requirement of the method restated: a
variable left out keeps all of its basins inside every box.

| subdivision of `partly_multimodal` | boxes | gap | reached |
|------------------------------------|-------|-----|---------|
| all 5 variables, $m=2$ | 32 | $1.99$ | 0/3 |
| 2 variables, $m=10$ | 100 | **$0.00$** | **3/3** |
| 2 variables, $m=5$ | 25 | $1.99$ | 0/3 |

**A hierarchy** was built in three shapes. The deep one reaches the optimum of
Ackley from half of the starting points, which nothing else here does; none of
them beats the flat subdivision elsewhere.

| method | Rastrigin | Ackley | Styblinski-Tang |
|--------|-----------|--------|-----------------|
| flat $m=2$ | $4.98$ | $9.71$ | **$0.00$, 6/6, 468** |
| flat $m=10$ | **$1.00$, 2/6** | $10.15$ | $0.00$, 2/6, 1044 |
| two levels, by value | $4.98$ | $6.77$ | $0.00$, 6/6, 1303 |
| two levels, by cuts | $2.99$ | $15.61$ | $0.00$, 6/6, 1540 |
| deep, 4 levels of 2 | $4.98$ | $7.88$, **3/6** | $0.00$, 6/6, 1934 |
| frontier, best first | $6.70$ | $9.71$ | $0.00$, 6/6, 2500 |

```{image} ../_static/figures/extensions.svg
:class: only-light
:alt: The hierarchies against the flat subdivisions
```

```{image} ../_static/figures/extensions-dark.svg
:class: only-dark
:alt: The hierarchies against the flat subdivisions
```

Two readings the medians alone hide. The deep hierarchy is the only
configuration here that **reaches** the optimum of Ackley, from three starting
points out of six, and its median is worse than the two-level one precisely
because the outcome is bimodal, a run either descending into the central basin
or committing to the wrong subdomain. And on Styblinski-Tang every
configuration solves the problem, so the panel is about cost alone, where the
flat coarse subdivision wins outright, $468$ evaluations against $1300$ to
$2500$ for the hierarchies.

**The frontier**, which is the only shape able to undo a choice, is the worst of
the family on Rastrigin, $6.70$ against $4.98$ for doing nothing at all, and the
reason is not the backtracking it adds but what it costs: every node restarts a master and throws its cuts away, so the same budget
that fills one model with fifty cuts fills ten models with five each, none of
them determined enough to rank its own children. What the flat method does
instead is keep one model over the whole subdivision and localize with its trust
region, which can also widen again.

What all of this establishes, and where it can go, is [the conclusion](conclusion.md).
