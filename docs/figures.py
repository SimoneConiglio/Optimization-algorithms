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
"""Draw the figures of the documentation.

Each figure is written twice, once for the light theme and once for the dark one,
the pages including both and the theme showing the right one. The files are
committed, so that building the documentation needs no plotting:

```shell
python docs/figures.py
```
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
from numpy import arange
from numpy import array
from numpy import cos
from numpy import e
from numpy import exp
from numpy import linspace
from numpy import log1p
from numpy import meshgrid
from numpy import pi
from numpy import sqrt

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

DIRECTORY = Path(__file__).parent / "_static" / "figures"
"""The directory of the figures."""

LIGHT = "#24292f"
"""The foreground of the light theme."""

DARK = "#c9d1d9"
"""The foreground of the dark theme."""

ACCENT = "#e8590c"
"""The colour marking what the figure is about."""

SECOND = "#1c7ed6"
"""The colour of the second series of a figure."""

THIRD = "#2f9e44"
"""The colour of the third series of a figure."""


def rastrigin(x, y):
    """Return the Rastrigin function of two variables."""
    return 20.0 + x**2 - 10.0 * cos(2 * pi * x) + y**2 - 10.0 * cos(2 * pi * y)


def ackley(x, y):
    """Return the Ackley function of two variables."""
    return (
        -20.0 * exp(-0.2 * sqrt(0.5 * (x**2 + y**2)))
        - exp(0.5 * (cos(2 * pi * x) + cos(2 * pi * y)))
        + e
        + 20.0
    )


def styblinski_tang(x, y):
    """Return the Styblinski-Tang function of two variables."""
    return 0.5 * (x**4 - 16 * x**2 + 5 * x + y**4 - 16 * y**2 + 5 * y)


def griewank(x, y):
    """Return the Griewank function of two variables."""
    return 1.0 + (x**2 + y**2) / 4000.0 - cos(x) * cos(y / sqrt(2.0))


def partly_multimodal(x, y):
    """Return the partly multimodal function, Rastrigin against a parabola."""
    return 10.0 + x**2 - 10.0 * cos(2 * pi * x) + y**2


def _style(foreground: str) -> dict[str, object]:
    """Return the style of a theme.

    Args:
        foreground: The colour of the text and of the axes.

    Returns:
        The matplotlib settings.
    """
    return {
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.facecolor": "none",
        "savefig.transparent": True,
        "text.color": foreground,
        "axes.labelcolor": foreground,
        "axes.edgecolor": foreground,
        "xtick.color": foreground,
        "ytick.color": foreground,
        "axes.titlecolor": foreground,
        "font.size": 9,
        "axes.titlesize": 10,
        "legend.frameon": False,
        "legend.labelcolor": foreground,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
    }


def save(name: str, draw, extension: str = "svg") -> None:
    """Draw a figure for both themes and write it.

    Args:
        name: The name of the figure, without its extension.
        draw: The function drawing the figure, taking the foreground colour.
        extension: The format, ``"png"`` for the figures holding a filled
            contour, whose vector form weighs tens of megabytes.
    """
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for suffix, foreground in (("", LIGHT), ("-dark", DARK)):
        with plt.rc_context(_style(foreground)):
            figure = draw(foreground)
            figure.savefig(
                DIRECTORY / f"{name}{suffix}.{extension}",
                bbox_inches="tight",
                format=extension,
                dpi=160,
            )
            plt.close(figure)


def draw_subdivision(foreground: str):
    """Draw the Cartesian subdivision of a design space."""
    figure, axes = plt.subplots(figsize=(5.2, 4.4))
    x = linspace(-4.1, 5.9, 400)
    grid_x, grid_y = meshgrid(x, x)
    axes.contourf(grid_x, grid_y, rastrigin(grid_x, grid_y), 40, cmap="Greys_r")
    breakpoints = linspace(-4.1, 5.9, 11)
    for position in breakpoints:
        axes.axvline(position, color=foreground, linewidth=0.5, alpha=0.5)
        axes.axhline(position, color=foreground, linewidth=0.5, alpha=0.5)

    axes.add_patch(
        plt.Rectangle(
            (breakpoints[4], breakpoints[4]),
            breakpoints[5] - breakpoints[4],
            breakpoints[5] - breakpoints[4],
            facecolor="none",
            edgecolor=ACCENT,
            linewidth=2.5,
        )
    )
    axes.plot([0.0], [0.0], marker="*", color=ACCENT, markersize=14, linestyle="none")
    axes.set_xlabel("$x_1$")
    axes.set_ylabel("$x_2$")
    axes.set_title(
        "One box per cell, one sub-problem per box\n"
        r"$\alpha$ selects the box, the sub-problem solves inside it"
    )
    return figure


def draw_bilevel(foreground: str):
    """Draw the exchange between the master and the sub-problem."""
    figure, axes = plt.subplots(figsize=(6.0, 2.9))
    axes.set_axis_off()
    boxes = (
        (0.02, "Master, a MILP\nover the one-hot $\\alpha$\n(which box)", SECOND),
        (0.56, "Sub-problem, an NLP\nover $x$ inside the box\n(where in it)", THIRD),
    )
    for left, label, colour in boxes:
        axes.add_patch(
            plt.Rectangle(
                (left, 0.28),
                0.42,
                0.52,
                transform=axes.transAxes,
                facecolor="none",
                edgecolor=colour,
                linewidth=2.0,
            )
        )
        axes.text(
            left + 0.21,
            0.54,
            label,
            transform=axes.transAxes,
            ha="center",
            va="center",
            color=foreground,
        )

    axes.annotate(
        "",
        xy=(0.56, 0.66),
        xytext=(0.44, 0.66),
        xycoords=axes.transAxes,
        arrowprops={"arrowstyle": "-|>", "color": foreground, "linewidth": 1.4},
    )
    axes.text(
        0.5, 0.72, r"box $\alpha^{(i)}$", ha="center", color=foreground, fontsize=8.5
    )
    axes.annotate(
        "",
        xy=(0.44, 0.42),
        xytext=(0.56, 0.42),
        xycoords=axes.transAxes,
        arrowprops={"arrowstyle": "-|>", "color": foreground, "linewidth": 1.4},
    )
    axes.text(
        0.5,
        0.3,
        "value and post-optimal\nsensitivity, one cut",
        ha="center",
        va="center",
        color=foreground,
        fontsize=8.5,
    )
    axes.text(
        0.5,
        0.06,
        "the master keeps every cut, so each solved box narrows the choice of the next",
        ha="center",
        color=foreground,
        fontsize=8.5,
        alpha=0.85,
    )
    return figure


def draw_cuts(foreground: str):
    """Draw why a cut needs the convexification."""
    figure, (left, right) = plt.subplots(1, 2, figsize=(7.4, 3.0), sharey=True)
    alpha = linspace(0.0, 1.0, 300)
    value = 3.0 - 6.0 * alpha + 8.0 * alpha * (1.0 - alpha)

    for axes, corrected in ((left, False), (right, True)):
        axes.plot(alpha, value, color=foreground, linewidth=1.8, label="$u(\\alpha)$")
        slope = -6.0 + 8.0 - 16.0 * 0.0
        if corrected:
            slope -= 9.0
        axes.plot(
            alpha,
            value[0] + slope * alpha,
            color=ACCENT,
            linewidth=1.8,
            linestyle="--",
            label="cut at $\\alpha = 0$",
        )
        axes.plot([0.0, 1.0], [value[0], value[-1]], "o", color=SECOND, markersize=6)
        axes.set_xlabel(r"$\alpha$, relaxed between two boxes")
        axes.set_title(
            "without the convexification,\nthe cut cuts the optimum off"
            if not corrected
            else "with it, the cut stays below\nthe value at both boxes"
        )
        axes.legend(loc="upper right", fontsize=8)

    left.set_ylabel("value of the sub-problem")
    return figure


def draw_convexification(foreground: str):
    """Draw the convexification term and its effect on a cut slope."""
    figure, axes = plt.subplots(figsize=(4.8, 3.0))
    alpha = linspace(0.0, 1.0, 300)
    axes.plot(
        alpha,
        alpha * (alpha - 1.0),
        color=ACCENT,
        linewidth=2.0,
        label=r"$\alpha(\alpha-1)$",
    )
    axes.axhline(0.0, color=foreground, linewidth=0.8, alpha=0.6)
    axes.plot([0.0, 1.0], [0.0, 0.0], "o", color=SECOND, markersize=7)
    axes.annotate(
        "zero at every box,\nso the discrete problem is unchanged",
        xy=(1.0, 0.0),
        xytext=(0.30, 0.06),
        color=foreground,
        fontsize=8.5,
        arrowprops={"arrowstyle": "-", "color": foreground, "alpha": 0.6},
    )
    axes.annotate(
        r"lowered by $\kappa/4$ between them",
        xy=(0.5, -0.25),
        xytext=(0.16, -0.20),
        color=foreground,
        fontsize=8.5,
        arrowprops={"arrowstyle": "-", "color": foreground, "alpha": 0.6},
    )
    axes.set_xlabel(r"$\alpha$, relaxed")
    axes.set_title("The convexification acts in the space of the box choice")
    axes.legend(loc="lower right", fontsize=8)
    return figure


def draw_trust_region(foreground: str):
    """Draw what the radius of the trust region reaches, under either metric."""
    figure, axes_triple = plt.subplots(1, 3, figsize=(8.6, 3.3), sharey=True)
    indexes = arange(10)
    incumbent = (7, 6)
    panels = (
        ("catalogue values, radius 10", "indexes", 10),
        ("components changed, radius 1", "unit", 1),
        ("components changed, radius 2", "unit", 2),
    )
    for axes, (title, metric, radius) in zip(axes_triple, panels, strict=True):
        for i in indexes:
            for j in indexes:
                if metric == "unit":
                    # Every subdivision weighs one, so the cost of a candidate
                    # is the number of components it changes.
                    cost = (i != incumbent[0]) + (j != incumbent[1])
                else:
                    # The weight charged is the index the *incumbent* holds, so
                    # leaving the first subdivision is free and leaving the last
                    # one costs nine, wherever the candidate goes.
                    cost = (i != incumbent[0]) * incumbent[0] + (
                        j != incumbent[1]
                    ) * incumbent[1]

                axes.add_patch(
                    plt.Rectangle(
                        (i - 0.5, j - 0.5),
                        1.0,
                        1.0,
                        facecolor=SECOND if cost <= radius else "none",
                        alpha=0.35 if cost <= radius else 1.0,
                        edgecolor=foreground,
                        linewidth=0.4,
                    )
                )

        axes.plot(
            [incumbent[0]], [incumbent[1]], marker="s", color=ACCENT, markersize=8
        )
        axes.set_xlim(-0.6, 9.6)
        axes.set_ylim(-0.6, 9.6)
        axes.set_aspect("equal")
        axes.set_xlabel("box index of $x_1$")
        axes.set_title(title, fontsize=9)

    axes_triple[0].set_ylabel("box index of $x_2$")
    figure.suptitle(
        "The catalogue values charge where the incumbent sits, not how far "
        "the candidate moves",
        fontsize=9.5,
        y=1.02,
    )
    return figure


def draw_complexity(foreground: str):  # noqa: ARG001
    """Draw what grows with the dimension, the boxes or the master."""
    figure, axes = plt.subplots(figsize=(5.6, 3.2))
    dimensions = arange(1, 11)
    for subdivisions, colour in ((10, ACCENT), (2, SECOND)):
        axes.semilogy(
            dimensions,
            subdivisions**dimensions,
            color=colour,
            linewidth=1.8,
            label=f"boxes, $m={subdivisions}$",
        )
        axes.semilogy(
            dimensions,
            subdivisions * dimensions,
            color=colour,
            linewidth=1.8,
            linestyle="--",
            label=f"binaries, $m={subdivisions}$",
        )

    axes.set_xlabel("number of design variables")
    axes.set_ylabel("count")
    axes.set_title("The master grows with the binaries, not with the boxes")
    axes.legend(fontsize=8, ncols=2)
    return figure


def draw_hierarchy(foreground: str):
    """Draw the shapes of hierarchy, and the frontier that backtracks."""
    figure, axes_row = plt.subplots(1, 3, figsize=(11.0, 3.4))
    for axes in axes_row:
        axes.set_xticks([])
        axes.set_yticks([])
        axes.set_aspect("equal")
        axes.set_xlim(0, 1)
        axes.set_ylim(0, 1)

    def grid(axes, count, origin=(0.0, 0.0), size=1.0, colour=None, width=0.6):
        """Draw a grid of boxes."""
        step = size / count
        for i in range(count):
            for j in range(count):
                axes.add_patch(
                    plt.Rectangle(
                        (origin[0] + i * step, origin[1] + j * step),
                        step,
                        step,
                        facecolor="none",
                        edgecolor=colour or foreground,
                        linewidth=width,
                    )
                )

    # Two levels: a coarse grid, one box refined.
    grid(axes_row[0], 2)
    grid(axes_row[0], 5, origin=(0.5, 0.0), size=0.5, colour=ACCENT, width=0.9)
    axes_row[0].add_patch(
        plt.Rectangle(
            (0.5, 0.0), 0.5, 0.5, facecolor="none", edgecolor=ACCENT, linewidth=2.4
        )
    )
    axes_row[0].set_title("two levels\ncoarse, then one box refined")

    # Deep: the same box split again and again.
    origin, size = (0.0, 0.0), 1.0
    for depth in range(4):
        grid(
            axes_row[1],
            2,
            origin=origin,
            size=size,
            colour=ACCENT if depth == 3 else foreground,
            width=0.9 if depth == 3 else 0.6,
        )
        size /= 2.0
        origin = (origin[0] + size, origin[1])

    axes_row[1].set_title("deep and narrow\neach level splits in two")

    # Frontier: open boxes at several levels, the next one taken marked.
    grid(axes_row[2], 2)
    grid(axes_row[2], 2, origin=(0.5, 0.5), size=0.5, colour=SECOND, width=0.9)
    grid(axes_row[2], 2, origin=(0.0, 0.0), size=0.5, colour=SECOND, width=0.9)
    axes_row[2].add_patch(
        plt.Rectangle(
            (0.25, 0.0), 0.25, 0.25, facecolor=ACCENT, alpha=0.35, edgecolor=ACCENT
        )
    )
    axes_row[2].add_patch(
        plt.Rectangle(
            (0.5, 0.75), 0.25, 0.25, facecolor=ACCENT, alpha=0.35, edgecolor=ACCENT
        )
    )
    axes_row[2].set_title("frontier\nopen boxes of every level compete")
    return figure


def draw_partial_refinement(foreground: str):
    """Draw a subdivision of some of the variables only."""
    figure, axes = plt.subplots(figsize=(5.0, 4.2))
    x = linspace(-4.1, 5.9, 300)
    grid_x, grid_y = meshgrid(x, x)
    axes.contourf(grid_x, grid_y, partly_multimodal(grid_x, grid_y), 40, cmap="Greys_r")
    for position in linspace(-4.1, 5.9, 11):
        axes.axvline(position, color=ACCENT, linewidth=0.9)

    axes.plot([0.0], [0.0], marker="*", color="#ffd43b", markersize=14)
    axes.set_xlabel("$x_1$, subdivided, the objective is multimodal in it")
    axes.set_ylabel("$x_2$, left to the sub-problem")
    axes.set_title("Subdividing the variables that need it, and only those")
    return figure


def draw_problems(foreground: str):
    """Draw the benchmark problems in two dimensions."""
    problems = (
        ("Rastrigin", rastrigin, -4.1, 5.9, (0.0, 0.0)),
        ("Ackley", ackley, -28.7, 34.9, (0.0, 0.0)),
        ("Styblinski-Tang", styblinski_tang, -4.9, 5.1, (-2.903534, -2.903534)),
        ("Griewank", griewank, -58.1, 61.9, (0.0, 0.0)),
        ("Partly multimodal", partly_multimodal, -4.1, 5.9, (0.0, 0.0)),
    )
    figure, axes_grid = plt.subplots(2, 3, figsize=(8.4, 5.8))
    axes_row = axes_grid.ravel()
    axes_row[-1].set_axis_off()
    for axes, (name, function, lower, upper, optimum) in zip(
        axes_row, problems, strict=False
    ):
        x = linspace(lower, upper, 400)
        grid_x, grid_y = meshgrid(x, x)
        values = function(grid_x, grid_y)
        # A logarithmic scale, the linear one hiding the basins of the flat
        # problems behind the growth of their envelope.
        axes.contourf(grid_x, grid_y, log1p(values - values.min()), 60, cmap="viridis")
        axes.plot(
            [optimum[0]],
            [optimum[1]],
            marker="*",
            color="#ffd43b",
            markersize=13,
            markeredgecolor=LIGHT,
            markeredgewidth=0.6,
            linestyle="none",
        )
        axes.set_title(name)
        axes.set_xticks([])
        axes.set_yticks([])
        axes.set_aspect("equal")

    figure.supxlabel(
        "logarithmic colour scale, the star marking the global optimum",
        color=foreground,
        fontsize=8.5,
    )
    return figure


def draw_landscape_slice(foreground: str):
    """Draw a one-dimensional slice of each problem, on a common scale."""
    figure, axes = plt.subplots(figsize=(6.4, 3.0))
    for name, function, lower, upper, colour in (
        ("Rastrigin", rastrigin, -4.1, 5.9, ACCENT),
        ("Ackley", ackley, -28.7, 34.9, SECOND),
        ("Griewank", griewank, -58.1, 61.9, THIRD),
    ):
        x = linspace(lower, upper, 800)
        values = function(x, 0.0 * x)
        axes.plot(
            (x - lower) / (upper - lower),
            (values - values.min()) / (values.max() - values.min()),
            color=colour,
            linewidth=1.4,
            label=name,
        )

    axes.set_xlabel("position in the range of the variable")
    axes.set_ylabel("objective, normalized")
    axes.set_title("How far apart the basins are, at the same scale")
    axes.legend(fontsize=8)
    return figure


def _sample(method: str, budget: int = 400):
    """Return the points a method evaluates on Rastrigin in two dimensions.

    Args:
        method: The name of the method.
        budget: The budget in equivalent objective evaluations.

    Returns:
        The evaluated points.
    """
    import logging
    import sys

    # The benchmarks live at the root of the repository, not on the path of a
    # script run from the documentation directory.
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from benchmarks import baselines
    from benchmarks.problems import PROBLEMS

    logging.disable(logging.CRITICAL)
    points = []

    def recording(base):
        """Return a counter class recording where the objective is evaluated."""

        class Recorder(base):
            """A counter recording where the objective is evaluated."""

            def objective(self, x):  # noqa: ANN001, ANN202, D102
                points.append(x.copy())
                return super().objective(x)

        return Recorder

    # The methods using no gradient count with the plain counter, the others
    # with the budgeted one, so both have to be recorded.
    originals = (baselines.BudgetedCounter, baselines.Counter)
    baselines.BudgetedCounter = recording(originals[0])
    baselines.Counter = recording(originals[1])
    try:
        baselines.run(method, PROBLEMS["rastrigin"], 2, 11, budget)
    finally:
        baselines.BudgetedCounter, baselines.Counter = originals

    return array(points)


def draw_sampling(foreground: str):
    """Draw where each method evaluates the objective."""
    figure, axes_row = plt.subplots(1, 4, figsize=(12.0, 3.3))
    x = linspace(-4.1, 5.9, 300)
    grid_x, grid_y = meshgrid(x, x)
    values = rastrigin(grid_x, grid_y)
    titles = {
        "box_subdivision": "box subdivision",
        "multistart": "multistart of SLSQP",
        "cmaes": "CMA-ES",
        "direct": "DIRECT",
    }
    for axes, (method, title) in zip(axes_row, titles.items(), strict=True):
        axes.contourf(grid_x, grid_y, values, 30, cmap="Greys_r")
        sampled = _sample(method)
        axes.plot(
            sampled[:, 0],
            sampled[:, 1],
            marker="o",
            markersize=2.0,
            linestyle="none",
            color=ACCENT,
            alpha=0.75,
        )
        axes.plot(
            [0.0], [0.0], marker="*", color="#ffd43b", markersize=12, linestyle="none"
        )
        axes.set_title(f"{title}\n{len(sampled)} evaluations")
        axes.set_xticks([])
        axes.set_yticks([])
        axes.set_aspect("equal")

    figure.supxlabel(
        "the same budget on Rastrigin, the star marking the global optimum",
        color=foreground,
        fontsize=8.5,
    )
    return figure


def draw_results(foreground: str):
    """Draw the cost of each method, per problem and dimension."""
    labels = (
        "Rastrigin 2",
        "Rastrigin 5",
        "Ackley 2",
        "Ackley 5",
        "Styblinski 2",
        "Styblinski 5",
        "Griewank 2",
        "Griewank 5",
    )
    costs = {
        "box subdivision": (786, 899, 422, 1388, 240, 466, 1000, 1644),
        "multistart": (1000, 2500, 1000, 2500, 1000, 2340, 1000, 2500),
        "CMA-ES": (631, 1945, 745, 2009, 535, 1457, 643, 1769),
        "DIRECT": (649, 461, 417, 353, 1011, 2505, 1011, 397),
    }
    reached = {
        "box subdivision": (3, 0, 2, 0, 3, 3, 0, 0),
        "multistart": (2, 0, 3, 0, 3, 3, 0, 0),
        "CMA-ES": (0, 0, 3, 3, 2, 2, 0, 0),
        "DIRECT": (3, 0, 3, 0, 3, 3, 0, 0),
    }
    colours = (ACCENT, SECOND, THIRD, "#868e96")
    figure, axes = plt.subplots(figsize=(8.6, 3.4))
    positions = arange(len(labels))
    width = 0.2
    for index, (name, values) in enumerate(costs.items()):
        offset = (index - 1.5) * width
        bars = axes.bar(
            positions + offset, values, width, color=colours[index], label=name
        )
        for bar, count in zip(bars, reached[name], strict=True):
            if count:
                axes.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 40,
                    "✓" * count,
                    ha="center",
                    fontsize=6.5,
                    color=colours[index],
                )

    axes.set_xticks(positions)
    axes.set_xticklabels(labels, rotation=20, ha="right")
    axes.set_ylabel("equivalent evaluations")
    axes.set_title(
        "Cost at equal budget, a tick per starting point reaching the optimum",
        pad=26,
    )
    axes.legend(ncols=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.10))
    return figure


EXTENSIONS = {
    "Rastrigin": {
        "flat $m=2$": (4.975, 900, 0),
        "flat $m=10$": (0.995, 2500, 2),
        "2 then 5, value": (4.975, 2500, 0),
        "2 then 5, cuts": (2.985, 2499, 0),
        "deep, 4 of 2": (4.975, 2140, 0),
        "frontier": (6.700, 2500, 0),
    },
    "Ackley": {
        "flat $m=2$": (9.714, 1226, 0),
        "flat $m=10$": (10.149, 2500, 0),
        "2 then 5, value": (6.765, 2500, 0),
        "2 then 5, cuts": (15.605, 2500, 0),
        "deep, 4 of 2": (7.880, 2500, 3),
        "frontier": (9.714, 2500, 0),
    },
    "Styblinski-Tang": {
        "flat $m=2$": (0.0, 468, 6),
        "flat $m=10$": (0.0, 1044, 2),
        "2 then 5, value": (0.0, 1303, 6),
        "2 then 5, cuts": (0.0, 1540, 6),
        "deep, 4 of 2": (0.0, 1934, 6),
        "frontier": (0.0, 2500, 6),
    },
}
"""The extensions against the flat subdivisions, at five variables.

Each entry is the median distance to the optimum, the median cost and the number
of starting points out of six from which the optimum was reached, for a budget of
$2500$ equivalent evaluations, as measured by ``benchmarks/hierarchy.py``.
"""


def draw_extensions(foreground: str):
    """Draw what the hierarchies are worth against the flat subdivisions."""
    methods = tuple(next(iter(EXTENSIONS.values())))
    colours = (SECOND, "#4dabf7", ACCENT, "#f08c00", THIRD, "#868e96")
    figure, axes_grid = plt.subplots(2, 3, figsize=(11.5, 5.4), sharex="col")
    positions = arange(len(methods))
    for column, (problem, methods_of) in enumerate(EXTENSIONS.items()):
        gaps = [methods_of[method][0] for method in methods]
        costs = [methods_of[method][1] for method in methods]
        reached = [methods_of[method][2] for method in methods]
        for row, (values, label) in enumerate((
            (gaps, "distance to the optimum"),
            (costs, "equivalent evaluations"),
        )):
            axes = axes_grid[row][column]
            drawn = [0.0 if value is None else value for value in values]
            bars = axes.bar(positions, drawn, 0.68, color=colours)
            for bar, value, count in zip(bars, values, reached, strict=True):
                if value is None:
                    axes.text(
                        bar.get_x() + bar.get_width() / 2,
                        0.0,
                        "not run",
                        ha="center",
                        va="bottom",
                        rotation=90,
                        fontsize=7,
                        color=foreground,
                        alpha=0.7,
                    )
                elif row == 0 and count:
                    axes.text(
                        bar.get_x() + bar.get_width() / 2,
                        max(drawn) * 0.02 + value,
                        "\u2713" * count,
                        ha="center",
                        fontsize=6.5,
                        color=colours[list(bars).index(bar)],
                    )

            if row == 0 and max(drawn) <= 1e-6:
                # Every run solved the problem: a bar chart of zeros says
                # nothing, so the panel says it in words.
                axes.set_ylim(0.0, 1.0)
                axes.text(
                    positions.mean(),
                    0.45,
                    "every configuration reaches the optimum,\nthey differ in cost",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=foreground,
                )
            elif row == 0:
                axes.set_ylim(0.0, max(drawn) * 1.25)

            if column == 0:
                axes.set_ylabel(label)

            if row == 0:
                axes.set_title(problem)
            else:
                axes.set_xticks(positions)
                axes.set_xticklabels(methods, rotation=35, ha="right", fontsize=8)

    figure.suptitle(
        "Five variables, one budget of 2500, median over six starting points, "
        "a tick per run reaching the optimum",
        fontsize=9.5,
    )
    figure.tight_layout()
    return figure


def draw_density(foreground: str):  # noqa: ARG001
    """Draw what the subdivision density does at five variables."""
    figure, axes = plt.subplots(figsize=(6.0, 3.2))
    labels = ("Rastrigin", "Ackley", "Styblinski-Tang", "Griewank")
    coarse = (4.98, 9.71, 0.0, 0.06)
    fine = (0.0, 7.08, 0.0, 0.11)
    positions = arange(len(labels))
    axes.bar(
        positions - 0.2, coarse, 0.4, color=SECOND, label="2 subdivisions (32 boxes)"
    )
    axes.bar(
        positions + 0.2, fine, 0.4, color=ACCENT, label=r"10 subdivisions ($10^5$)"
    )
    axes.set_xticks(positions)
    axes.set_xticklabels(labels, rotation=12, ha="right")
    axes.set_ylabel("distance to the optimum")
    axes.set_title("Five variables: refining pays only where the basins need it")
    axes.legend(fontsize=8)
    return figure


FIGURES = {
    "subdivision": (draw_subdivision, "png"),
    "bilevel": (draw_bilevel, "svg"),
    "cuts": (draw_cuts, "svg"),
    "convexification": (draw_convexification, "svg"),
    "trust_region": (draw_trust_region, "svg"),
    "complexity": (draw_complexity, "svg"),
    "hierarchy": (draw_hierarchy, "svg"),
    "partial_refinement": (draw_partial_refinement, "png"),
    "problems": (draw_problems, "png"),
    "landscape_slice": (draw_landscape_slice, "svg"),
    "sampling": (draw_sampling, "png"),
    "results": (draw_results, "svg"),
    "extensions": (draw_extensions, "svg"),
    "density": (draw_density, "svg"),
}
"""The figures, by name, with the format each is written in."""


def main() -> None:
    """Write every figure, for both themes."""
    for name, (draw, extension) in FIGURES.items():
        save(name, draw, extension)
        print(f"{name}.{extension}")  # noqa: T201


if __name__ == "__main__":
    main()
