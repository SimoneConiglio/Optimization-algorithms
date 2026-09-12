<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Installation

```shell
pip install gemseo-algos-lab
```

This installs [GEMSEO](https://gemseo.org) and
[gemseo-bilevel-outer-approximation](https://pypi.org/project/gemseo-bilevel-outer-approximation/),
whose `Benders` formulation and outer-approximation master the package builds on.

Python 3.10 to 3.13 are supported.

## Checking the installation

The plugin registers itself through the `gemseo_plugins` entry point, so its
algorithms appear in the GEMSEO factories:

```python
from gemseo.algos.opt.factory import OptimizationLibraryFactory

print(OptimizationLibraryFactory().algorithms)
```

## From the sources

```shell
git clone https://github.com/SimoneConiglio/Optimization-algorithms.git
cd Optimization-algorithms
python -m pip install tox tox-uv
```

| Command | Purpose |
|---------|---------|
| `tox -e py3.12` | run the tests |
| `tox -e py3.12-coverage` | run the tests with coverage |
| `tox -e check` | run the pre-commit hooks |
| `tox -e doc` | build this documentation |
| `tox -e benchmark` | run the algorithm benchmarks |
| `tox -e dist` | build and check the distribution |
