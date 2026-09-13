<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Conclusion

The box-subdivision outer approximation separates the exploration of a design
space from its local exploitation: a Cartesian subdivision turns the choice of a
region into a categorical variable, a mixed-integer master decides which box to
look into from the cuts of the boxes already solved, and a local solver does the
rest inside it.

## What the method is, once measured

**It is a method for a landscape of few, well-separated basins.** Where the
subdivision resolves them, it reaches the optimum for three to five times fewer
evaluations than multistart, CMA-ES or DIRECT, and for about a quarter of the
cost of enumerating the boxes it replaces. Where it does not, it is the worst of
the four, and no setting recovers it.

**Its size is set by the binaries, not by the boxes.** The master grows as
$\sum_j m_j$ while the boxes grow as $\prod_j m_j$, so a hundred thousand boxes
over five variables is a master of fifty binaries, and that density solves
Rastrigin in five dimensions, which none of the baselines does. The limit is the
ratio between those binaries and the sub-problems a budget can pay for: past
some fifty coefficients for fifty cuts, the cut model is underdetermined and the
quality collapses.

**Two settings decide whether a run works at all**, and both fail silently when
wrong: the guard against non-convexity, the adaptive repair of the cut slopes or
the convexification constant, never both; and the radius of the trust region,
which has to start at the diameter of the design space rather than at the
master's own default.

## What is established, and what is not

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

## Where this can go

Four directions follow from the measurements above, in the order in which they
would pay.

**A subdivision that follows the basins.** Everything on this page turns on the
subdivision resolving the basins of the landscape, and the method has no way of
knowing their spacing. Estimating it, from the curvature at a first sampling or
from the failures of the local solves themselves, would replace the one setting
that is tuned by hand and would say, at the same time, which variables deserve
subdividing at all.

**A master that keeps its cuts while the boxes change.** The hierarchies all
restart a master per node, which is what makes them lose. A master over a
**growing set of leaves**, adding binaries as a box is split and keeping every
cut, would be the genuine lazy branch-and-bound: the frontier without its cost.
It cannot be built on a catalogue design space fixed at construction, so it means
writing the master problem rather than calling it.

**A bound worth the name.** A run ends on its trust region or on its stall
counter, never on its optimality test, because the convexification degrades the
lower bound by its own constant. Reporting the bound net of a term that vanishes
at every integer point would make the gap meaningful, and a meaningful gap is
what turns the method into one that can stop on a proof rather than on a budget.

**The regime the method is for.** Every problem here is analytic and
bound-constrained, where a sub-problem costs microseconds. The method is built
for a sub-problem that costs minutes and comes with an adjoint, and for
constraints that make a box infeasible rather than merely expensive. A case of
that kind, against Bayesian optimization as well as against the baselines used
here, is what would establish it.
