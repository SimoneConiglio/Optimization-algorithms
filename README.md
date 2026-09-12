<!--
Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# gemseo-box-subdivision

[![PyPI](https://img.shields.io/pypi/v/gemseo-box-subdivision)](https://pypi.org/project/gemseo-box-subdivision/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gemseo-box-subdivision)](https://pypi.org/project/gemseo-box-subdivision/)
[![PyPI - License](https://img.shields.io/pypi/l/gemseo-box-subdivision)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
[![CI](https://github.com/SimoneConiglio/gemseo-box-subdivision/actions/workflows/ci.yml/badge.svg)](https://github.com/SimoneConiglio/gemseo-box-subdivision/actions/workflows/ci.yml)
[![Documentation](https://github.com/SimoneConiglio/gemseo-box-subdivision/actions/workflows/docs.yml/badge.svg)](https://simoneconiglio.github.io/gemseo-box-subdivision/)

A laboratory for exploring optimization algorithms built on
[GEMSEO](https://gemseo.org).

## Installation

```shell
pip install gemseo-box-subdivision
```

Python 3.10 to 3.13. This also installs GEMSEO and
[gemseo-bilevel-outer-approximation](https://pypi.org/project/gemseo-bilevel-outer-approximation/).

## Documentation

**<https://simoneconiglio.github.io/gemseo-box-subdivision/>**

| Page | Contents |
|------|----------|
| [Methodology](https://simoneconiglio.github.io/gemseo-box-subdivision/algorithm/methodology.html) | motivation, equations, convexification |
| [Implementation](https://simoneconiglio.github.io/gemseo-box-subdivision/algorithm/implementation.html) | the building blocks and their pitfalls |
| [Usage](https://simoneconiglio.github.io/gemseo-box-subdivision/algorithm/usage.html) | how to build a GEMSEO scenario |
| [Benchmark](https://simoneconiglio.github.io/gemseo-box-subdivision/algorithm/benchmark.html) | measured results against enumeration |

## What it does

The package is a **GEMSEO plugin**: its algorithms register themselves in the
GEMSEO factories and are usable wherever a GEMSEO algorithm name is expected.

It implements the **box-subdivision outer approximation**, a bi-level method for
multimodal non-linear problems. Each design variable is split into subdivisions,
whose Cartesian product defines boxes. A MILP master decides which box to look
into, and a local NLP solves the original problem inside it, so the exploration
of the design space and its local exploitation stay in two distinct levels.

On the Rastrigin function in two dimensions subdivided into 100 boxes, it reaches
the global optimum after solving about 20 boxes, roughly five times cheaper than
solving all of them, and on Styblinski-Tang in five dimensions it does so for
three to five times fewer evaluations than multistart, CMA-ES or DIRECT.

The method suits a landscape with a **moderate number of basins**, the
subdivision having to resolve them; on a densely multimodal one an evolution
strategy does better. The
[benchmark](https://simoneconiglio.github.io/gemseo-box-subdivision/algorithm/benchmark.html)
reports both sides.

**Warning.** The master's two guards against non-convexity are both off by
default in GEMSEO, which makes the outer-approximation cuts invalid on a
multimodal problem: the master converges after two or three sub-problems and
reports success far from the optimum. Set one of them, `adapt=True` with a
convexity margin `min_dfk` scaled to the objective, or a
`convexification_constant` alone, never both. See
[Convexification](https://simoneconiglio.github.io/gemseo-box-subdivision/algorithm/methodology.html#convexification).

## Development

```shell
git clone https://github.com/SimoneConiglio/gemseo-box-subdivision.git
cd gemseo-box-subdivision
python -m pip install tox tox-uv
tox -e py3.12       # tests
tox -e check        # pre-commit hooks
tox -e doc          # documentation, into docs/_build/html
tox -e benchmark    # algorithm benchmarks
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Bugs and questions

Please use the
[GitHub issue tracker](https://github.com/SimoneConiglio/gemseo-box-subdivision/issues).

## Contributors

- Simone Coniglio
