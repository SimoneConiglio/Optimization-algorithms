<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Appendix: the baselines

Enumerating the boxes measures the exploration of the master, but it is not what
a practitioner would otherwise use. The comparison therefore also runs the three
methods that actually address a multimodal non-linear program, each with the
settings below, in `benchmarks/baselines.py`.

## Multistart of a local solver

The reference of the class, and the ancestor of the frameworks that combine a
global sampling with local solves (Rinnooy Kan and Timmer, 1987). A design of
experiments draws starting points, a gradient-based solver runs from each, and
the best result is kept.

Run through GEMSEO's `MultiStart` with $50$ starting points and SLSQP (Kraft,
1988) as the local solver, which is the same solver the box-subdivision
sub-problems use, so the comparison isolates **how the starting regions are
chosen** rather than how they are exploited.

## CMA-ES

The covariance matrix adaptation evolution strategy (Hansen and Ostermeier,
2001), a stochastic method that adapts a full covariance to the landscape. It
uses **no gradient**, which makes it the natural baseline when none is available,
and it is the strongest of the three on a densely rippled landscape.

Run through the `cma` package, from the same starting point as the other methods,
with an initial standard deviation of a quarter of the range and its own
`maxfevals` enforcing the budget exactly.

## DIRECT

*DIviding RECTangles* (Jones, Perttunen and Stuckey, 1993), a deterministic
partitioning method: it splits the design space into hyperrectangles and samples
the ones that are potentially optimal for some balance of size and value. It is
the closest baseline in spirit to this package, subdividing the space as well,
but it **refines its partition adaptively** and samples points rather than
solving a sub-problem in each region.

Run through `scipy.optimize.direct`, which ignores the starting point, with its
own `maxfun` enforcing the budget.

:::{note}
Relaxation-based global solvers, BARON, SCIP, Couenne or Alpine, are deliberately
absent. They build convex relaxations from the **algebraic form** of the problem,
which the sub-problem of an industrial case does not have: it is a disciplinary
optimization or a multidisciplinary analysis. They are the right comparison for a
polynomial program, and no comparison at all for this one.
:::

## Counting a budget across methods that differ that much

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
equal number of iterations, which would mean nothing across methods that differ
this much.

The budget itself is $500$ equivalent evaluations per design variable, since a
fixed budget would favour the low-dimensional cases of whichever method converges
fastest there.

## References

- Rinnooy Kan, A. H. G., & Timmer, G. T. (1987). *Stochastic global optimization
  methods. Part II: Multi level methods.* Mathematical Programming, 39(1), 57-78.
- Kraft, D. (1988). *A software package for sequential quadratic programming.*
  DFVLR-FB 88-28, DLR German Aerospace Center.
- Hansen, N., & Ostermeier, A. (2001). *Completely derandomized self-adaptation in
  evolution strategies.* Evolutionary Computation, 9(2), 159-195.
- Jones, D. R., Perttunen, C. D., & Stuckey, B. E. (1993). *Lipschitzian
  optimization without the Lipschitz constant.* Journal of Optimization Theory
  and Applications, 79(1), 157-181.
- Virtanen, P., et al. (2020). *SciPy 1.0: fundamental algorithms for scientific
  computing in Python.* Nature Methods, 17, 261-272.
