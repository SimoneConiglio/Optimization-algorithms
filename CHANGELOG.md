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

- The benchmarks no longer mix the two mechanisms of the master, the adaptive
  repair of the cut slopes and the fixed convexification constant, which are
  different approaches. The configuration is now an explicit axis,
  `benchmarks/configurations.py`, and the settings and results reported by the
  documentation are measured with one mechanism at a time. The previously
  reported comparison of the two formulations, 96% against 58%, compared their
  tuning rather than the formulations.
- The benchmarks no longer have their report stripped by the `T20` rule of
  ruff, whose unsafe fixes silently replaced the `print` calls by `pass`.
- The equations of the documentation are rendered: MathJax is served by the
  documentation itself instead of a CDN, which a network blocking third-party
  CDNs, or a local build, left unreachable.

### Changed

- The project is named `gemseo-box-subdivision`, since it is about the
  box-subdivision outer approximation rather than a collection of
  algorithms. The package is `gemseo_box_subdivision`.
- The GEMSEO monogram is no longer used as the logo of the documentation,
  being the registered mark of GEMSEO.
- The documentation is built with Sphinx instead of MkDocs, and published on
  GitHub Pages by a dedicated workflow.
- The documentation uses the PyData theme, with a navigation bar, a section
  navigation, a page outline and cards on the landing pages.

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
- `benchmarks/configurations.py`, the two named configurations of the master,
  `adaptive`, the default, and `pure_convexification`.
- Benchmark comparing the method with the baselines of the problem class,
  multistart, CMA-ES and DIRECT, at equal budget of equivalent objective
  evaluations under both gradient-cost conventions.
- `benchmarks/run_baselines.py`, sweeping the baselines over the problems,
  the dimensions and the seeds.
- `BoxMapping` and `create_normalized_box_design_space`, an alternative
  formulation solving the sub-problem in the normalized variables of the box.
- `BoxSubdivision.compute_bounds` and `BoxSubdivision.get_normalized_names`.
- `benchmarks/tune_convexification.py`, sweeping the convexification of both
  formulations, and the convexification tuned for each of them.
