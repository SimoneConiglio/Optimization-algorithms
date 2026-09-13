<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Tuning the master

The [results](benchmark.md) are what the method achieves once its settings are
right. This page is how they were found, and what each setting does: the two
mechanisms that keep the cuts valid, the trust region that decides how far the
master may look, the two caps that end a run, and how both depend on the size of
the boxes.

Everything here is measured on the problems of
[the appendix](problems.md), from eight starting points in two dimensions and
three in five, so it is evidence about these landscapes rather than a rule.


## The master has two mechanisms, and they must not be combined

Outer-approximation cuts are supporting hyperplanes only if the value function is
convex. On a multimodal problem it is not, and the master offers **two distinct
mechanisms** for keeping its cuts usable. They rest on different arguments, and
measuring them together measures neither.

```{image} ../_static/figures/cuts.svg
:class: only-light
:alt: A cut that over-predicts the value at the next box
```

```{image} ../_static/figures/cuts-dark.svg
:class: only-dark
:alt: A cut that over-predicts the value at the next box
```


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

```{image} ../_static/figures/trust_region.svg
:class: only-light
:alt: What each radius of the trust region reaches
```

```{image} ../_static/figures/trust_region-dark.svg
:class: only-dark
:alt: What each radius of the trust region reaches
```


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
Measured over the whole comparison of the formulations, it is the same story,
the same reliability for up to twice the worst-case cost: the normalized
formulation goes from $20$–$36$ boxes to $24$–$56$, still 8/8, and the constraint
one from $24$–$28$ to $20$–$64$, still 7/8.
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

## At five variables, which knob to turn

The two-dimensional benchmark is where the mechanisms were tuned, and what works
there does not carry over unchanged. Two questions are open at five variables:
which of the two mechanisms to use, and whether to subdivide every variable
coarsely or a few of them finely.

### The constant is the better buy at the coarse subdivision

Two subdivisions per variable, equal budget, three starting points:

| problem | adaptive | pure convexification |
|---------|----------|----------------------|
| Rastrigin | $4.98$ · 899 · 0/3 | $4.98$ · **606** · 0/3 |
| Ackley | $9.71$ · 1429 · 0/3 | $14.43$ · 598 · 0/3 |
| Styblinski-Tang | $0.00$ · 466 · 3/3 | $0.00$ · **458** · 3/3 |
| Griewank | $0.06$ · 1644 · 0/3 | $0.06$ · **1277** · 0/3 |

Same answer on three problems out of four for a quarter to a third less, the
exception being Ackley. Sweeping each mechanism's constant per problem, at that
same subdivision:

| problem | constant | $1$ | $10$ | $100$ | $1000$ |
|---------|----------|-----|------|-------|--------|
| Rastrigin | convexification | $28.85$ | $8.57$ | **$4.98$** | $8.57$ |
| Rastrigin | margin | $8.57$ | $8.57$ | **$4.98$** | $4.98$ |
| Ackley | convexification | $14.43$ | $14.43$ | $14.43$ | $14.43$ |
| Ackley | margin | $14.43$ | $14.43$ | **$9.71$** | $9.71$ |
| Styblinski-Tang | convexification | $28.27$ | $28.27$ | **$0.00$** | $0.00$ |
| Styblinski-Tang | margin | $0.00$ | **$0.00$ (230)** | $0.00$ | $0.00$ |
| Griewank | convexification | $0.08$ | $0.06$ | $0.06$ | $0.06$ |
| Griewank | margin | **$0.06$ (422)** | $0.06$ | $0.06$ | $0.06$ |

The constant is **not** to be scaled down with the range of the objective as
simply as the two-dimensional case suggested: Griewank spans about two and is
served as well by any value, while Styblinski-Tang spans hundreds and the
convexification needs a hundred exactly. Where a smaller constant suffices it is
also cheaper, Styblinski-Tang being solved for $230$ evaluations at a margin of
ten instead of $466$ at a hundred, so the constant is worth sweeping downwards
once a configuration works. And Ackley is insensitive to every value of either
mechanism, which says the master is not what fails there.

### At the fine subdivision, the margin goes up, not down

Ten subdivisions per variable, the radius sized to the diameter of the design
space, $45$, a budget of $5000$:

| problem | mechanism | $1$ | $10$ | $30$ | $100$ |
|---------|-----------|-----|------|------|-------|
| Rastrigin | margin | $17.91$ | $6.11$ | **$0.00$, 2/3 (2895)** | **$0.00$, 2/3 (3357)** |
| Rastrigin | convexification | $33.41$ | $33.41$ | $33.41$ | **$6.97$** |
| Ackley | margin | $8.12$ | $8.12$ | $8.12$ | **$7.08$** |
| Ackley | convexification | $19.42$ | $19.42$ | $18.58$ | **$16.52$**, 1/3 |

Finer boxes differ from each other by less, so a constant tuned on the coarse
subdivision might be expected to swamp their ranking. Measured with the radius
left at the master's default, that is what it looks like: a margin of ten then
beats a margin of a hundred at this density, $3.98$ against $15.92$. With the
radius sized, the ordering reverses and the large margin wins outright. The
apparent need for a smaller constant was the master being unable to move more
than a variable or two at a time, and a smaller margin making that confinement
less harmful.

One case does behave the other way, and it is the pure convexification rather
than the adaptive repair: Styblinski-Tang at ten subdivisions per variable, with
the radius already sized, is solved by a constant of **one** for $212$
evaluations, the cheapest configuration measured on any five-variable problem
here, and ruined by ten or a hundred, $46.82$ and $28.27$, while the same problem
at four subdivisions per variable needs a hundred. So the constant of the
convexification does depend on the size of the boxes; it is not a rule that
transfers from one problem to another.

### Refining some variables only, and when it pays

The number of boxes is the Cartesian product of the subdivisions, so subdividing
only the variables that need it keeps the master small, the others staying
ordinary variables of the sub-problem. The package does this already:

```python
subdivision = BoxSubdivision.from_design_space(design_space, 10, ["x_split"])
```

On the benchmark problems, which are multimodal in **every** variable, it loses:

| problem | 5 split, $m=2$ (32 boxes) | 3 split, $m=4$ (64) | 2 split, $m=10$ (100) | 1 split, $m=10$ (10) |
|---------|---------------------------|---------------------|-----------------------|----------------------|
| Rastrigin | **$4.98$** | $9.95$ | $9.95$ | $18.90$ |
| Ackley | $9.71$ | $13.64$ | **$9.53$** | $16.07$ |
| Styblinski-Tang | **$0.00$, 3/3** | $14.14$, 1/3 | $28.27$ | $28.27$ |

The reason is the one already established: a variable left unsubdivided keeps all
of its basins inside every box, and the local solve returns the one it starts in.
Styblinski-Tang has two basins per variable, so leaving three of the five out
leaves eight basins in every box, and the run that solved every starting point
with thirty-two boxes now solves none with a hundred.

On an objective whose multimodality is concentrated, `partly_multimodal`, which is
Rastrigin in two variables plus a paraboloid in the other three, it wins clearly:

| subdivision | boxes | gap | cost | reached |
|-------------|-------|-----|------|---------|
| 5 split, $m=2$ | 32 | $1.99$ | 708 | 0/3 |
| 3 split, $m=4$ | 64 | **$0.00$** | 1165 | **3/3** |
| 2 split, $m=10$ | 100 | **$0.00$** | 1329 | **3/3** |
| 2 split, $m=5$ | 25 | $1.99$ | 950 | 0/3 |
| 2 split, $m=3$ | 9 | $1.99$ | 381 | 0/3 |

Subdividing every variable coarsely fails from every starting point; subdividing
the two multimodal ones finely succeeds from every one. And the requirement is
the same as everywhere else, the subdivision resolving the basins: Rastrigin's
minima are a unit apart over a range of ten, so $m=10$ works on those two
variables and $m=5$ or $m=3$ does not, at a third of the cost and none of the
result.

So the rule is not about the number of variables but about **where the
multimodality is**: subdivide the variables the objective is multimodal in, as
finely as their basins require, and leave the others to the sub-problem. What the
method still cannot do is find out by itself which ones those are.
