<!--
Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Contributing

## Setting up

```shell
python -m pip install tox tox-uv
tox -e check           # installs and runs the pre-commit hooks
tox -e py3.12          # runs the test suite
```

The pre-commit hooks format the code with [ruff](https://docs.astral.sh/ruff/),
insert the license headers and check the commit messages with
[commitizen](https://commitizen-tools.github.io/commitizen/), which expects
[conventional commits](https://www.conventionalcommits.org).

## Layout

```text
src/gemseo_algos_lab/
└── algos/
    └── opt/            # the optimization libraries contributed to GEMSEO
tests/                  # mirrors the layout of src
docs/                   # the Sphinx documentation
benchmarks/             # the algorithm benchmarks
```

## Adding an optimization algorithm

Create `src/gemseo_algos_lab/algos/opt/<algo_name>/` containing:

1. `<algo_name>_settings.py`, with a settings model deriving from
   `BaseOptimizerSettings` (or a more specific base such as `BaseMILPSettings`)
   and whose `_TARGET_CLASS_NAME` class variable is the name of the library
   class;
2. `<algo_name>.py`, with a class deriving from `BaseOptimizationLibrary`,
   declaring its algorithms in `ALGORITHM_INFOS` and implementing `_run`;
3. an `__init__.py` in each new directory.

Then add the settings class to the `runtime-evaluated-base-classes` list of
`.ruff.toml` if other settings models derive from it, and add the tests under
`tests/algos/opt/`.

GEMSEO discovers these classes by importing every module of the package, so a
module that raises at import time silently removes its algorithms from the
factories. The test `tests/test_plugin.py::test_all_modules_are_importable`
guards against this.

## Dependency pinning

Unlike the upstream GEMSEO copier template, this project does not pin the test
dependencies in `requirements/test-python*.txt`; the `dev` dependency group of
`pyproject.toml` is used directly, so a fresh clone can run `tox` without a
locking step. Only `requirements/check.in` remains, for the pre-commit tooling.

## Releasing

The version is derived from the git tags by
[setuptools_scm](https://setuptools-scm.readthedocs.io). Update `CHANGELOG.md`,
tag the commit, and push the tag: the `Release` workflow builds the
distribution and publishes it to PyPI through trusted publishing.
