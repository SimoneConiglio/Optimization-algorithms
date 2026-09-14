<!--
 Copyright 2026 Simone Coniglio

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Annex C: tuning the master

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

Rastrigin, ten subdivisions per variable, no convexification constant. Two
variables, eight starting points, a budget of $1000$; each cell is the number of
them from which the optimum was reached, and the median cost:

| parallel points | `min_dfk` = 1 | 10 | 30 | **100** | 300 |
|-----------------|---------------|----|----|---------|-----|
| 1 | 0/8 | 0/8 | 2/8 | 6/8 (294) | 5/8 (294) |
| **4** | 1/8 | 5/8 | 7/8 | **8/8 (543)** | **8/8 (550)** |
| 8 | 1/8 | 1/8 | 8/8 (907) | 8/8 (1000) | 7/8 (1000) |

Two settings matter, and one of them for a different reason than an earlier
version of this page gave.

**Several parallel points.** The master probes one trust-region radius per
point, over `geomspace(step / 2, step)`, so that a feasible master problem stays
available. Four points reach the optimum every time; a single point reaches it
from six starting points out of eight, and eight points also reach it every time
but for nearly twice the cost, spending the budget on probes rather than on
boxes. Four is therefore a cost trade, not a matter of feasibility. With the
trust region charging the catalogue values, a single point used to stop a run
after two or three boxes; that collapse was the metric, not the probing.

**A margin on the scale of the objective.** `min_dfk` is subtracted from an
objective difference, so it is an absolute quantity in the units of the
objective, not a ratio. What it does is **cross a threshold and then saturate**,
rather than pass through a window: over an objective spanning about eighty, the
margin reaches the optimum from one starting point at $1$, five at $10$, seven
at $30$, and all eight at $100$ and at $300$. Five variables agree, from none at
$10$, two out of three at $30$, and all three at $100$ and at $300$:

| `min_dfk` | 1 | 10 | 30 | **100** | 300 |
|-----------|---|----|----|---------|-----|
| Rastrigin, $n=5$ | $17.91$ · 0/3 | $5.11$ · 0/3 | $0.00$ · 2/3 | **$0.00$ · 3/3** | $0.00$ · 3/3 |
| Ackley, $n=5$ | $8.99$ · 0/3 | $4.95$ · 1/3 | $4.95$ · 0/3 | $6.30$ · 0/3 | $7.23$ · 1/3 |

An over-large margin costs sub-problems rather than quality, so the default sits
at the first value that saturates. Ackley is the reminder that the margin is in
the units of *its* objective, which spans about twenty-two rather than eighty:
there the useful margin is the smallest one tried.

### The pure convexification, and the range where it is worth using

The constant has to dominate the non-convexity of the relaxed problem, and no
more: past that, every unexplored box outranks the incumbent whatever the cuts
say, the master ranks them by nothing in particular, and the method degenerates
towards the enumeration it exists to avoid. Unlike the convexity margin above,
it therefore passes through a genuine **window**, with a floor and a ceiling.

Rastrigin, same protocol, `adapt` off, one parallel point:

| constant | 10 | **30** | **50** | **100** | 200 |
|----------|----|--------|--------|---------|-----|
| $n=2$, budget $1000$ | $6.97$ · 0/8 | **$0.00$ · 6/8 (456)** | $0.00$ · 5/8 | **$0.00$ · 6/8 (466)** | $0.50$ · 4/8 |
| $n=5$, budget $2500$ | $33.41$ · 0/3 | $30.84$ · 0/3 | **$0.00$ · 2/3** | $1.92$ · 0/3 | $9.09$ · 0/3 |

The window **narrows as the dimension grows**. At two variables a factor of
three in the constant makes little difference and the mechanism reaches the
optimum from five or six starting points out of eight. At five variables only
one of the constants tried, $50$, reaches it at all, the two below it leaving
the cuts invalid and the two above it ranking the boxes by nothing. Ackley says
the same with its own scale, best at $100$ and much worse at $200$.

Against the adaptive repair, which reaches the same optima from eight starting
points out of eight at two variables and three out of three at five, the pure
convexification is **dominated on this benchmark**. It is kept because its
argument is the one the outer approximation actually rests on, and because it
needs no observed pairs to work from; it is not the default.

It is no accident that the useful constants are the order of magnitude of the
variation of the objective over the design space, which is also the order of the
convexity margin the adaptive repair needs: both mechanisms are calibrated
against the same quantity, the non-convexity they have to dominate, and neither
is dimensionless.

What does *not* happen is the cost growing with the constant: an exaggerated
constant buys nothing and costs about the same, because the run ends on the two
caps described next rather than on its optimality test. It is not a safe default
to be conservative with.

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

### A hierarchy of subdivisions, and the rule that refines it

Rather than one fine subdivision of the whole space, a **hierarchy** subdivides
coarsely, ranks the boxes, and refines the most promising ones, the same method
running again inside the bounds of one box. The product of the subdivisions is
the resolution reached, so two levels of two and five resolve as finely as a
flat ten, and the budget is spent where it seems to matter instead of being
spread over $10^5$ boxes.

Everything then depends on the **rule deciding what to refine**, and three were
measured, in `benchmarks/hierarchy.py`:

`value`
: refine the boxes whose sub-problem returned the best value. It can only
  propose boxes already solved, a few dozen of them, and their score is one
  local solve started at a box centre.

`cuts`
: refine the boxes the **cut model of the master** scores lowest,
  $\hat u(\alpha) = \max_i u(\alpha^{(i)}) + s^{(i)\top}(\alpha - \alpha^{(i)})$,
  which is defined at every box, those never solved included. Being an
  optimistic estimate, it extrapolates downwards far from anything solved, so it
  ranks distant unexplored boxes first.

`mixed`
: one box from each ranking in turn.

Five variables, one budget of $2500$ shared by the levels, six starting points,
median distance to the optimum and the number of runs reaching it:

| method | Rastrigin | Ackley | Styblinski-Tang |
|--------|-----------|--------|-----------------|
| flat $m=2$ | $4.98$ | $9.71$ | **$0.00$, 6/6, 468** |
| flat $m=10$ | **$1.00$, 2/6** | $10.15$ | $0.00$, 2/6 |
| 2 then 5, `value` | $4.98$ | $6.77$ | $0.00$, 6/6, 1303 |
| 2 then 5, `cuts` | $2.99$ | $15.61$ | $0.00$, 6/6, 1540 |
| 2 then 5, `mixed` | $4.98$ | $9.90$ | $0.00$, 6/6, 2290 |
| deep, 4 levels of 2, `value` | $4.98$ | $7.88$, **3/6** | $0.00$, 6/6, 1934 |
| deep, 4 levels of 2, `cuts` | $4.98$ | $14.76$ | $0.00$, 6/6, 1508 |
| deep, 6 levels of 2, `value` | $4.98$ | $14.96$, 2/6 | $0.00$, 5/6 |
| frontier, 10 expansions, optimistic | $6.70$ | $9.71$ | $0.00$, 6/6, 2500 |
| frontier, 10 expansions, greedy | $10.15$ | $9.71$ | $0.00$, 6/6, 2500 |
| frontier, 20 expansions, optimistic | $8.43$ | $9.71$ | $0.00$, 6/6, 2500 |

**One variant does something no other configuration in this documentation
does.** The deep hierarchy, splitting every variable in two at each of four
levels and refining the best box by its value, reaches the optimum of Ackley in
five dimensions from **three starting points out of six**, where every flat
subdivision and every two-level hierarchy reaches it from none. Its median is
worse than the best two-level median, $7.88$ against $6.77$, because the outcome
is bimodal: it either descends into the central basin and solves the problem, or
commits to the wrong subdomain and stays there.

That bimodality is the whole story of the family. **A hierarchy cannot
backtrack**: the box it refines at one level is the only space the next level
sees, so an unreliable score compounds instead of averaging out. It follows that

- `cuts` helps where the observed values are noise, Rastrigin, $4.98$ to $2.99$,
  and ruins the case where they are informative, Ackley, $6.77$ to $15.61$: an
  optimistic model explores, and exploration is wrong when the ranking already
  points at the right region;
- `mixed` inherits the worse of the two rather than hedging, halving the budget
  of each refinement, depth mattering more than coverage here;
- deeper is not better in itself, six levels being worse than four, each level
  being one more irreversible commitment;
- the frontier, which alone can return to a box it passed over, is the worst of
  the family on Rastrigin, $6.70$ optimistic and $10.15$ greedy, and more
  expansions make it worse, $8.43$ at twenty: backtracking does not pay for the
  model it destroys, each node restarting a master with a handful of cuts.

None of the three beats the flat fine subdivision on Rastrigin or the flat
coarse one on Styblinski-Tang, so the hierarchy is not a default. What it is, is
the only construction here that reaches Ackley at five variables, and the
measured reason the others do not is a missing ingredient rather than a wrong
idea: a **best-first frontier** over the boxes of every level, scored by the cut
model that produced them, which would let a run return to a subdomain it passed
over. That is a spatial branch-and-bound over the subdivision, and it subsumes
the three rules above.

:::{note}
The two-level hierarchy was justified by the statistics of the cut model, and it
does not improve them: its fine level carries $n \times m$ coefficients against
the twenty or so cuts a budget affords, which is the flat situation. Only the
deep hierarchy improves that ratio, $2n$ coefficients per level, and it is the
one that produces the result above.
:::

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
