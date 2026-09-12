<!--
Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
International License. To view a copy of this license, visit
http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

<!--
Changelog titles are:
- Added: for new features.
- Changed: for changes in existing functionality.
- Deprecated: for soon-to-be removed features.
- Removed: for now removed features.
- Fixed: for any bug fixes.
- Security: in case of vulnerabilities.
-->

# Changelog

All notable changes of this project will be documented here.

The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0)
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Fixed

- The benchmarks no longer have their report stripped by the `T20` rule of
  ruff, whose unsafe fixes silently replaced the `print` calls by `pass`.

### Changed

- The documentation is built with Sphinx instead of MkDocs, and published on
  GitHub Pages by a dedicated workflow.

### Added

- Initial packaging of the project as a GEMSEO plugin, generated from the
  [GEMSEO copier template](https://gitlab.com/gemseo/dev/copier-gemseo).
- Dependency on `gemseo-bilevel-outer-approximation`.
- `benchmark` dependency group with `gemseo-benchmark`, and the matching
  `tox -e benchmark` environment.
- Design note for the box-subdivision outer approximation algorithm.
- `BoxSubdivision`, a Cartesian subdivision of a design space.
- `BoxConstraint`, the discipline expressing the selected box as a
  vector-valued constraint, with its analytic Jacobian.
- `create_box_design_space`, building the design space of both levels.
- `BoxSubdivision.locate` and `BoxSubdivision.get_one_hot_names`.
- `create_box_start_adapter_class`, a `Benders` scenario adapter starting
  each sub-problem at the center of its box.
- `create_box_samples`, the one-hot vectors of every box, to solve them all
  with the `CustomDOE` driver.
- Benchmark comparing the outer approximation with that enumeration.
- `BoxMapping` and `create_normalized_box_design_space`, an alternative
  formulation solving the sub-problem in the normalized variables of the box.
- `BoxSubdivision.compute_bounds` and `BoxSubdivision.get_normalized_names`.
- `benchmarks/tune_convexification.py`, sweeping the convexification of both
  formulations, and the convexification tuned for each of them.
