# Copyright 2026 Simone Coniglio
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
r"""Hierarchies of subdivisions: refining a box instead of subdividing it finely.

A box of a subdivision is an ordinary design space, so refining it is running the
method again inside its bounds. Which box to refine is the whole question, and
these are the rules that answer it and the three shapes of search built on them.

Each shape is a **loop around the method** rather than a change to it, so it is
driven by a callable that solves one level and reports the boxes it solved. The
caller keeps the construction of its own scenario, and its own accounting of the
budget, and signals exhaustion by returning no solved box.

The trade a hierarchy makes is set out in the documentation: writing :math:`c`
for the sub-problems a budget affords, a flat run puts all :math:`c` cuts into
one model, while a hierarchy of :math:`N` nodes puts :math:`c/N` into each of
:math:`N` models, and the cuts of a parent have no meaning in the subdivision of
a child. Reach for one when the flat method has no answer at all, a basin too
broad for any affordable density, rather than to improve a run that works.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass
from heapq import heappop
from heapq import heappush
from typing import TYPE_CHECKING

from numpy import argsort
from numpy import asarray
from numpy import ndarray  # noqa: TC002

from gemseo_box_subdivision.design_spaces import create_box_samples

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

    from gemseo_box_subdivision.subdivisions.box import BoxSubdivision


@dataclass(frozen=True)
class SolvedBox:
    """A box whose sub-problem was solved, and what the master learned from it."""

    one_hot: ndarray
    """The one-hot vector selecting the box."""

    value: float
    """The optimum of the sub-problem inside the box."""

    sensitivity: ndarray
    """The post-optimal sensitivity of that optimum to the one-hot vector."""


SolveLevel = (
    "Callable[[ndarray, ndarray, int], tuple[BoxSubdivision, Sequence[SolvedBox]]]"  # noqa: E501
)
"""The signature of the callable solving one level.

It receives the lower bounds, the upper bounds and the number of subdivisions per
variable of the level, and returns the subdivision it built and the boxes it
solved. Returning no solved box ends the search, which is how a caller reports
that its budget is spent or that the master became infeasible.
"""


def read_solved_boxes(problem, objective_name: str = "") -> list[SolvedBox]:  # noqa: ANN001
    """Return the boxes a master solved, from the database of its problem.

    Args:
        problem: The optimization problem of the master.
        objective_name: The name of the objective. If empty, take the name of the
            objective of the problem.

    Returns:
        The solved boxes, in the order the master visited them.
    """
    name = objective_name or problem.objective.name
    solved = []
    for key, values in problem.database.items():
        value = values.get(name)
        sensitivity = values.get(f"@{name}")
        if value is not None and sensitivity is not None:
            solved.append(
                SolvedBox(
                    asarray(key.unwrap()).ravel(),
                    float(value),
                    asarray(sensitivity).ravel(),
                )
            )

    return solved


def compute_cut_model(
    solved: Sequence[SolvedBox], subdivision: BoxSubdivision
) -> tuple[ndarray, ndarray]:
    r"""Return every box of a subdivision and what the cuts estimate there.

    The cuts gathered by a master define a lower estimate of the value of the
    problem over the whole subdivision,

    .. math::

        \hat u(\alpha) = \max_i \, u(\alpha^{(i)})
            + s^{(i)\top}(\alpha - \alpha^{(i)}),

    which is defined at the boxes the master never solved as well as at those it
    did. That is what makes it usable as a score: it proposes boxes that were
    never visited, where the value can only rank the few dozen that were.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vector of every box, and the value the cuts estimate there.
    """
    boxes = create_box_samples(subdivision)
    values = asarray([box.value for box in solved])
    alphas = asarray([box.one_hot for box in solved])
    slopes = asarray([box.sensitivity for box in solved])
    # One row per box, one column per cut.
    model = (
        values[None, :] + boxes @ slopes.T - (alphas * slopes).sum(axis=1)[None, :]
    ).max(axis=1)
    return boxes, model


def rank_by_value(
    solved: Sequence[SolvedBox], subdivision: BoxSubdivision
) -> list[ndarray]:
    """Rank the boxes by the value of the sub-problem solved inside them.

    Only the boxes whose sub-problem was solved can be ranked, so this compares
    measurements rather than extrapolations, over at most a few dozen boxes.

    Args:
        solved: The solved boxes.
        subdivision: Unused, the values being attached to the boxes.

    Returns:
        The one-hot vectors, from the most promising.
    """
    del subdivision
    return [solved[rank].one_hot for rank in argsort([box.value for box in solved])]


def rank_by_cuts(
    solved: Sequence[SolvedBox], subdivision: BoxSubdivision
) -> list[ndarray]:
    """Rank **every** box of the subdivision by the cut model of the master.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vectors, from the most promising.
    """
    boxes, model = compute_cut_model(solved, subdivision)
    return [boxes[rank] for rank in argsort(model)]


def rank_mixed(
    solved: Sequence[SolvedBox], subdivision: BoxSubdivision
) -> list[ndarray]:
    """Alternate the two rules, taking the first box of each in turn.

    The two fail on opposite landscapes: the value is noise where a coarse box
    holds many basins, and the cut model, being optimistic, extrapolates towards
    boxes far from anything solved, which is exploration where the value ranking
    already points at the right region.

    Args:
        solved: The solved boxes.
        subdivision: The subdivision of the level.

    Returns:
        The one-hot vectors, from the most promising.
    """
    mixed: list[ndarray] = []
    for value_box, cut_box in zip(
        rank_by_value(solved, subdivision),
        rank_by_cuts(solved, subdivision),
        strict=False,
    ):
        for box in (value_box, cut_box):
            if not any((box == other).all() for other in mixed):
                mixed.append(box)

    return mixed


RANKINGS: dict[str, Callable[..., list[ndarray]]] = {
    "value": rank_by_value,
    "cuts": rank_by_cuts,
    "mixed": rank_mixed,
}
"""The rules deciding which boxes to refine, by name."""


def refine_deep(
    solve: Callable,
    lower_bound: ndarray,
    upper_bound: ndarray,
    variable_name: str = "x",
    branching: int = 2,
    depth: int = 4,
    ranking: str = "value",
) -> list[tuple[ndarray, ndarray]]:
    r"""Refine the most promising box again and again, to a fixed depth.

    Every level splits each variable in :math:`m` and descends into one box, so a
    level carries :math:`n m` coefficients against the boxes it can afford to
    solve, and the resolution reached is :math:`m^{\text{depth}}` per variable
    without any level ever being large. This is the shape that answers a basin
    too broad for any affordable density.

    It cannot undo a choice: the box refined at one level is the only space the
    next level sees. Use :func:`.refine_frontier` when that matters.

    Args:
        solve: The callable solving one level, see :data:`.SolveLevel`.
        lower_bound: The lower bounds of the design space.
        upper_bound: The upper bounds of the design space.
        variable_name: The name of the subdivided variable.
        branching: The number of subdivisions per variable at every level.
        depth: The number of levels.
        ranking: The rule deciding which box to refine, a key of
            :data:`.RANKINGS`.

    Returns:
        The bounds of every region visited, coarsest first.
    """
    visited = [(lower_bound, upper_bound)]
    for _ in range(depth):
        subdivision, solved = solve(lower_bound, upper_bound, branching)
        if not solved:
            break

        one_hot = RANKINGS[ranking](solved, subdivision)[0]
        lower_bound, upper_bound = subdivision.compute_bounds(variable_name, one_hot)
        visited.append((lower_bound, upper_bound))

    return visited


def refine_two_levels(
    solve: Callable,
    lower_bound: ndarray,
    upper_bound: ndarray,
    variable_name: str = "x",
    coarse: int = 2,
    fine: int = 5,
    n_refined: int = 1,
    ranking: str = "value",
) -> list[tuple[ndarray, ndarray]]:
    """Solve a coarse level, then refine its most promising boxes.

    Args:
        solve: The callable solving one level, see :data:`.SolveLevel`.
        lower_bound: The lower bounds of the design space.
        upper_bound: The upper bounds of the design space.
        variable_name: The name of the subdivided variable.
        coarse: The number of subdivisions per variable of the coarse level.
        fine: The number of subdivisions per variable inside a refined box.
        n_refined: The number of boxes refined, the most promising first.
        ranking: The rule deciding which boxes to refine, a key of
            :data:`.RANKINGS`.

    Returns:
        The bounds of every region visited, the coarse one first.
    """
    visited = [(lower_bound, upper_bound)]
    subdivision, solved = solve(lower_bound, upper_bound, coarse)
    if not solved:
        return visited

    for one_hot in RANKINGS[ranking](solved, subdivision)[:n_refined]:
        bounds = subdivision.compute_bounds(variable_name, one_hot)
        visited.append(bounds)
        solve(bounds[0], bounds[1], fine)

    return visited


def refine_frontier(
    solve: Callable,
    lower_bound: ndarray,
    upper_bound: ndarray,
    variable_name: str = "x",
    branching: int = 2,
    expansions: int = 10,
    score: str = "optimistic",
    max_depth: int = 8,
    n_children: int = 4,
) -> list[tuple[ndarray, ndarray]]:
    """Search the boxes of every level best first, so that a run can backtrack.

    The descending shapes above never revisit a box they passed over. This one
    keeps a **frontier** of open boxes from every level at once, repeatedly
    taking the most promising, subdividing it, and putting its children back with
    their own scores, which makes it a spatial branch-and-bound over the
    subdivision.

    A box is scored by one of:

    ``"optimistic"``
        what the cuts of its parent estimate there, as a branch-and-bound would,
        the lowest bound being the box that may still hold the optimum.

    ``"greedy"``
        the value where the sub-problem was solved, and the estimate otherwise.

    ``"solved"``
        the value, only the solved boxes going on the frontier, so that the
        frontier compares measurements rather than extrapolations.

    Note:
        Every node restarts a master and discards its parent's cuts, and this
        shape creates the most nodes of the three, so it spreads a budget
        thinnest. It was the worst of the family wherever it was measured.

    Args:
        solve: The callable solving one level, see :data:`.SolveLevel`.
        lower_bound: The lower bounds of the design space.
        upper_bound: The upper bounds of the design space.
        variable_name: The name of the subdivided variable.
        branching: The number of subdivisions per variable of an expansion.
        expansions: The number of boxes expanded.
        score: The rule scoring a box.
        max_depth: The number of levels below which a box is not subdivided.
        n_children: The number of children of an expansion put on the frontier,
            the most promising first.

    Returns:
        The bounds of every region expanded, in the order they were expanded.
    """
    # The heap holds (score, tie breaker, depth, lower bounds, upper bounds).
    frontier: list[tuple[float, int, int, ndarray, ndarray]] = [
        (0.0, 0, 0, lower_bound, upper_bound)
    ]
    visited: list[tuple[ndarray, ndarray]] = []
    tie = 1
    for _ in range(expansions):
        if not frontier:
            break

        _, _, depth, lower, upper = heappop(frontier)
        if depth >= max_depth:
            continue

        subdivision, solved = solve(lower, upper, branching)
        visited.append((lower, upper))
        if not solved:
            continue

        observed = {tuple(box.one_hot): box.value for box in solved}
        boxes, model = compute_cut_model(solved, subdivision)
        children = []
        for one_hot, estimate in zip(boxes, model, strict=True):
            known = observed.get(tuple(one_hot))
            if score == "solved":
                if known is None:
                    continue

                children.append((known, one_hot))
            elif score == "greedy":
                children.append((estimate if known is None else known, one_hot))
            else:
                children.append((estimate, one_hot))

        # Push the most promising children only, a whole level of a fine
        # subdivision flooding the frontier with extrapolated estimates.
        children.sort(key=operator.itemgetter(0))
        for child, one_hot in children[:n_children]:
            child_bounds = subdivision.compute_bounds(variable_name, one_hot)
            heappush(frontier, (float(child), tie, depth + 1, *child_bounds))
            tie += 1

    return visited


SHAPES: dict[str, Callable[..., list[tuple[ndarray, ndarray]]]] = {
    "deep": refine_deep,
    "two_levels": refine_two_levels,
    "frontier": refine_frontier,
}
"""The shapes of hierarchy, by name."""
