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
r"""The settings of a box-subdivision run, in the units the method measures.

The master of the outer approximation takes a dozen settings, several of which
are coupled: two mechanisms that must not be combined, a trust-region radius
whose unit is not obvious, and a convexity margin in the units of the objective.
This module names them in the terms the methodology uses and rejects the
combinations that measure nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Any
from typing import ClassVar

if TYPE_CHECKING:
    from collections.abc import Mapping

TRUST_REGION_RADIUS: int = 2
"""The default radius of the trust region, in components changed.

A radius of two is what the measurements support, and it is far from the radius
at which the region stops constraining. Letting the master change every component
at once is markedly worse, and removing the region is worse still.
"""

CONVEXITY_MARGIN: float = 100.0
"""The default convexity margin of the adaptive repair.

This is an **absolute** quantity in the units of the objective, so the default
only suits an objective of the scale of the benchmark. It has to be set to the
order of the variation of the objective over the design space.
"""


@dataclass
class BoxSubdivisionSettings:
    r"""The settings of a box-subdivision run.

    The defaults are the configuration the benchmark supports: the adaptive
    repair of the cut slopes, four probe points, and a trust region of two
    components.

    Two of these settings decide whether a run works at all, and neither has a
    default that transfers between problems:

    ``convexity_margin``
        subtracted from an objective difference, so it is absolute and in the
        units of *your* objective. Start from the variation of the objective
        over the design space. It crosses a threshold and then saturates, so
        erring high costs sub-problems rather than quality.

    ``trust_region_radius``
        the number of components a candidate box may change. Keep it small.
    """

    MECHANISMS: ClassVar[tuple[str, ...]] = ("adaptive", "convexification")
    """The two mechanisms keeping the cuts usable on a non-convex problem."""

    mechanism: str = "adaptive"
    r"""How the master keeps its cuts usable, ``"adaptive"`` or
    ``"convexification"``.

    They rest on different arguments and are **not** combined: the adaptive
    repair fixes the slope of each cut against the boxes already solved, while
    the convexification adds a convex term whose constant, once it dominates the
    concavity of the relaxation, makes the outer approximation convergent.
    Measuring the two together measures neither.
    """

    convexity_margin: float = CONVEXITY_MARGIN
    """The convexity margin of the adaptive repair, in the units of the objective."""

    convexification_constant: float = CONVEXITY_MARGIN
    """The constant of the convexification, in the units of the objective."""

    trust_region_radius: int = TRUST_REGION_RADIUS
    """The radius of the trust region of the master, in components changed."""

    n_parallel_points: int = 4
    """The number of trust-region radii the master probes per iteration."""

    max_iter: int = 80
    """The number of iterations of the master, not of the sub-problems."""

    sub_problem_max_iter: int = 40
    """The number of iterations of each sub-problem."""

    tolerance: float = 1e-4
    """The tolerance on the upper bound of the master."""

    options: Mapping[str, Any] = field(default_factory=dict)
    """Any other setting of the master, passed through unchanged."""

    def __post_init__(self) -> None:
        """Check the settings.

        Raises:
            ValueError: When the mechanism is unknown, or a count is not
                positive.
        """
        if self.mechanism not in self.MECHANISMS:
            msg = (
                f"The mechanism must be one of {list(self.MECHANISMS)}; "
                f"got {self.mechanism!r}."
            )
            raise ValueError(msg)

        for name in ("trust_region_radius", "n_parallel_points", "max_iter"):
            if getattr(self, name) < 1:
                msg = f"{name} must be positive; got {getattr(self, name)}."
                raise ValueError(msg)

    def to_master_settings(self, radius: int | None = None) -> dict[str, Any]:
        """Return the settings of the master problem.

        The mechanism decides which of the two constants is passed and which is
        switched off, so that the two can never be active at once.

        Args:
            radius: The radius of the trust region, overriding
                :attr:`.trust_region_radius`. Used by the encodings whose
                distance counts something other than design variables.

        Returns:
            The settings of the master problem.
        """
        adaptive = self.mechanism == "adaptive"
        settings = {
            "max_iter": self.max_iter,
            "ub_tol": self.tolerance,
            "adapt": adaptive,
            "min_dfk": self.convexity_margin if adaptive else 0.0,
            "convexification_constant": (
                0.0 if adaptive else self.convexification_constant
            ),
            "number_of_parallel_points": self.n_parallel_points if adaptive else 1,
            "max_step": self.trust_region_radius if radius is None else radius,
        }
        settings.update(self.options)
        return settings
