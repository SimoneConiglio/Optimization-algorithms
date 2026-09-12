<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# The algorithm

The **box-subdivision outer approximation** is a bi-level method for multimodal
non-linear problems. A Cartesian subdivision of the design space defines a
finite set of boxes; a MILP master decides which box to look into, and a local
NLP solves the original problem inside it. Exploration and exploitation stay in
two distinct levels.

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Methodology
:link: methodology
:link-type: doc

The motivation, the bi-level formulation and its equations, the two
formulations, and what the convexification really does.
:::

:::{grid-item-card} Implementation
:link: implementation
:link-type: doc

The building blocks contributed to GEMSEO, the one-hot layout they share, and
the two pitfalls that fail silently.
:::

:::{grid-item-card} Usage
:link: usage
:link-type: doc

Building a GEMSEO scenario with either formulation, and the settings that
matter.
:::

:::{grid-item-card} Benchmark
:link: benchmark
:link-type: doc

Measured against the exhaustive enumeration of the boxes, and the tuning of the
convexification.
:::

::::

```{toctree}
:hidden:

methodology
implementation
usage
benchmark
```
