<!--
Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# gemseo-algos-lab

[![PyPI](https://img.shields.io/pypi/v/gemseo-algos-lab)](https://pypi.org/project/gemseo-algos-lab/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gemseo-algos-lab)](https://pypi.org/project/gemseo-algos-lab/)
[![PyPI - License](https://img.shields.io/pypi/l/gemseo-algos-lab)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
[![CI](https://github.com/SimoneConiglio/Optimization-algorithms/actions/workflows/ci.yml/badge.svg)](https://github.com/SimoneConiglio/Optimization-algorithms/actions/workflows/ci.yml)
[![Documentation](https://github.com/SimoneConiglio/Optimization-algorithms/actions/workflows/docs.yml/badge.svg)](https://simoneconiglio.github.io/Optimization-algorithms/)

A laboratory for exploring optimization algorithms built on
[GEMSEO](https://gemseo.org).

## Installation

```shell
pip install gemseo-algos-lab
```

Python 3.10 to 3.13. This also installs GEMSEO and
[gemseo-bilevel-outer-approximation](https://pypi.org/project/gemseo-bilevel-outer-approximation/).

## Documentation

**<https://simoneconiglio.github.io/Optimization-algorithms/>**

| Page | Contents |
|------|----------|
| [Methodology](https://simoneconiglio.github.io/Optimization-algorithms/algorithm/methodology.html) | motivation, equations, convexification |
| [Implementation](https://simoneconiglio.github.io/Optimization-algorithms/algorithm/implementation.html) | the building blocks and their pitfalls |
| [Usage](https://simoneconiglio.github.io/Optimization-algorithms/algorithm/usage.html) | how to build a GEMSEO scenario |
| [Benchmark](https://simoneconiglio.github.io/Optimization-algorithms/algorithm/benchmark.html) | measured results against enumeration |

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
solving all of them.

> [!WARNING]
> The convexification constant defaults to `0.0` in GEMSEO, which makes the
> outer-approximation cuts invalid on a multimodal problem: the master converges
> after two or three sub-problems and reports success far from the optimum. See
> [Convexification](https://simoneconiglio.github.io/Optimization-algorithms/algorithm/methodology.html#convexification).

## Development

```shell
git clone https://github.com/SimoneConiglio/Optimization-algorithms.git
cd Optimization-algorithms
python -m pip install tox tox-uv
tox -e py3.12       # tests
tox -e check        # pre-commit hooks
tox -e doc          # documentation, into docs/_build/html
tox -e benchmark    # algorithm benchmarks
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Bugs and questions

Please use the
[GitHub issue tracker](https://github.com/SimoneConiglio/Optimization-algorithms/issues).

## Contributors

- Simone Coniglio
