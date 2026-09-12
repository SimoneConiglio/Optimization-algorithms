# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""The configurations of the master problem, which must not be mixed.

The master has **two distinct mechanisms** for keeping its cuts usable on a
non-convex value function. They rest on different arguments and are not meant to
be combined:

`pure_convexification`
: adds to the objective a convex term vanishing at the integer points, whose
  constant, once it dominates the concavity of the relaxed problem, makes the
  relaxation convex and the outer approximation convergent. It is driven by
  ``convexification_constant`` alone, with ``adapt`` off.

`adaptive`
: repairs the slope of each cut by least squares against the pairs of points
  already observed, so that no cut over-predicts a value that has been measured,
  with ``min_dfk`` as the convexity margin. It is driven by ``adapt`` and
  ``min_dfk``, with no convexification constant.

Measuring the two together, as an earlier version of these benchmarks did,
measures neither.
"""

from __future__ import annotations

from types import MappingProxyType

ADAPTIVE = MappingProxyType({
    "adapt": True,
    "min_dfk": 100.0,
    "convexification_constant": 0.0,
    "number_of_parallel_points": 4,
})
"""The adaptive repair of the cut slopes, which reaches the optimum most often.

Two of its settings are essential rather than an optimization.

Several **parallel points**: the master probes one trust-region radius per point,
over ``geomspace(step / 2, step)``, so that a feasible master problem stays
available. With a single point the run stops after two or three boxes, whatever
the convexity margin.

A convexity margin on the **scale of the objective**: ``min_dfk`` is subtracted
from an objective difference, so it is an absolute quantity in the units of the
objective, not a ratio. On the Rastrigin benchmark, whose objective spans about
eighty, a margin of thirty to a hundred reaches the optimum from every starting
point, while a margin of ten reaches it from three out of eight and a margin of
one from none. It has to be scaled to the problem.
"""

PURE_CONVEXIFICATION = MappingProxyType({
    "adapt": False,
    "min_dfk": 0.0,
    "convexification_constant": 100.0,
    "number_of_parallel_points": 1,
})
"""The convex term added to the objective.

The constant has to dominate the concavity of the relaxed problem and no more.
It is an absolute quantity, of the order of the variation of the objective over
the design space, about eighty on the Rastrigin benchmark, where the useful
window is fifty to a hundred: the optimum is then reached from every starting
point for about a fifth of the cost of enumerating the boxes.

Below that window the cuts stay invalid and the master converges on a wrong
point; above it, every unexplored box outranks the incumbent whatever the cuts
say, so the master ranks them by nothing in particular and the result decays,
six then five starting points out of eight, without the cost falling. An
exaggerated constant is not a conservative choice, and the regime where the
convergence argument would apply is out of reach anyway, the run ending on the
trust region or on the stall counter rather than on its optimality test.

This window was measured with the trust region sized to the design space, that
is with the master's ``max_step`` set to
:attr:`.BoxSubdivision.max_step`; with the master's own default of ten, the same
constants reach the optimum from five or six starting points out of eight.
See `tune_convexification.py`.
"""

CONFIGURATIONS = MappingProxyType({
    "adaptive": ADAPTIVE,
    "pure_convexification": PURE_CONVEXIFICATION,
})
"""The configurations of the master, by name."""

DEFAULT_CONFIGURATION = "adaptive"
"""The configuration reaching the optimum with the fewest boxes."""
