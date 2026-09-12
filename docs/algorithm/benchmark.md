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

## What this does and does not establish

Established, on this problem:

- the outer approximation reaches the global optimum solving about a fifth of the
  boxes, at about a fifth of the cost of enumerating them;
- the sub-problem starting point and the convexification are both decisive, and
  both fail silently when wrong;
- the normalized formulation dominates, once each is tuned.

Not established:

- **generalization.** One problem family, two dimensions, 100 boxes. Nothing here
  says how the method scales with dimension, nor how it behaves with constraints
  on the original problem.
- **a rule for the constant.** It was tuned by sweeping. A curvature-based
  estimate would be the principled replacement, and is the most valuable next
  step.
- **the guarantee.** Enumeration is exhaustive over the boxes and always returns
  the best box; the outer approximation reaches it from 96% of the starting
  points. The trade is five times fewer executions against that guarantee.
