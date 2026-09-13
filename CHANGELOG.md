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
  tuning rather than the formulations, and the reported collapse of the method
  when the number of boxes grows is a property of the fixed constant rather than
  of the method: with the adaptive repair, Styblinski-Tang in five dimensions is
  solved from every starting point over a hundred thousand boxes as well as over
  thirty-two.
- The benchmarks no longer have their report stripped by the `T20` rule of
  ruff, whose unsafe fixes silently replaced the `print` calls by `pass`.
- The equations of the documentation are rendered: MathJax is served by the
  documentation itself instead of a CDN, which a network blocking third-party
  CDNs, or a local build, left unreachable.

### Changed

- The documentation is illustrated, `docs/figures.py` drawing every figure for
  the light and the dark theme, and it is split so that the results are readable
  on their own: the benchmark page reports what the method achieves, a page of
  its own covers the tuning of the master, and two appendices describe and cite
  the benchmark problems and the baselines.
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
  `adaptive`, the default, and `pure_convexification`, whose constant is the
  order of the variation of the objective rather than an arbitrarily large
  number, and which the benchmarks now sweep over the range where it is worth
  using, reporting the cost as a fraction of the enumeration it replaces.
- `benchmarks/configurations.py` sizes the trust region of the master to the
  design space for every configuration. The master's default radius of ten is
  unrelated to that space, whose diameter is the sum over the components of the
  number of subdivisions minus one, and starting below it confines the search:
  with five variables and ten subdivisions each, that is the difference between
  solving Rastrigin, which no baseline here does, and returning a gap of
  sixteen. The benchmark page reports the comparison with the radius sized, the
  density sweep it corrects, and the constants of both mechanisms at the fine
  subdivision, where the convexity margin goes up rather than down.
- `benchmarks/refine_some_variables.py`, comparing a coarse subdivision of every
  variable with a fine subdivision of some of them, and the `partly_multimodal`
  problem it needs, multimodal in two variables and convex in the others.
- `BoxSubdivision.max_step`, the largest trust-region step of the master in the
  distance induced by the weights of the boxes, to be passed as its `max_step`
  when a run stops early: the master's own default of ten is smaller than the
  design space as soon as the subdivision is not coarse, and the run then ends
  on an infeasible master instead of on its optimality test.
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
