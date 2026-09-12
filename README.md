<!--
Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# gemseo-algos-lab

[![PyPI - License](https://img.shields.io/pypi/l/gemseo-algos-lab)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gemseo-algos-lab)](https://pypi.org/project/gemseo-algos-lab/)
[![PyPI](https://img.shields.io/pypi/v/gemseo-algos-lab)](https://pypi.org/project/gemseo-algos-lab/)
[![CI](https://github.com/SimoneConiglio/Optimization-algorithms/actions/workflows/ci.yml/badge.svg)](https://github.com/SimoneConiglio/Optimization-algorithms/actions/workflows/ci.yml)

## Overview

A laboratory for exploring optimization algorithms built on
[GEMSEO](https://gemseo.org).

This package is a GEMSEO plugin: the algorithms it defines are registered in the
GEMSEO factories and can be used wherever a GEMSEO algorithm name is expected,
without importing this package explicitly.

It also depends on
[gemseo-bilevel-outer-approximation](https://pypi.org/project/gemseo-bilevel-outer-approximation/),
so that its mixed-integer algorithms (`OUTER_APPROXIMATION`,
`BILEVEL_MASTER_OUTER_APPROXIMATION` and `ORTOOLS_MILP`) are available as
building blocks.

At this stage the package contains no algorithm yet, only the plugin scaffolding.

## Installation

Install the latest version with `pip install gemseo-algos-lab`.

See [pip](https://pip.pypa.io/en/stable/getting-started/) for more information.

## Usage

Once installed, the algorithms of this package are listed by GEMSEO:

```python
from gemseo.algos.opt.factory import OptimizationLibraryFactory

print(OptimizationLibraryFactory().algorithms)
```

## Adding an optimization algorithm

Algorithms live under `src/gemseo_algos_lab/algos/opt/<algo_name>/` and follow
the GEMSEO conventions:

- `<algo_name>_settings.py` defines a Pydantic settings model deriving from
  `gemseo.algos.opt.base_optimizer_settings.BaseOptimizerSettings`, whose
  `_TARGET_CLASS_NAME` is the name of the library class;
- `<algo_name>.py` defines a class deriving from
  `gemseo.algos.opt.base_optimization_library.BaseOptimizationLibrary`, which
  declares its algorithms in `ALGORITHM_INFOS` and implements `_run`.

Any such class placed in this package is discovered automatically through the
`gemseo_plugins` entry point declared in `pyproject.toml`.

## Development

The project uses [tox](https://tox.wiki):

```shell
tox -e py3.12          # run the tests
tox -e py3.12-coverage # run the tests with coverage
tox -e check           # run the pre-commit hooks
tox -e doc             # serve the documentation locally
tox -e dist            # build and check the distribution
```

## Bugs and questions

Please use the
[GitHub issue tracker](https://github.com/SimoneConiglio/Optimization-algorithms/issues)
to submit bugs or questions.

## Contributing

See [CONTRIBUTING.md](https://github.com/SimoneConiglio/Optimization-algorithms/blob/main/CONTRIBUTING.md).

## Contributors

- Simone Coniglio
