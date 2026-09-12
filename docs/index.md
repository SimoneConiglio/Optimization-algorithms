<!--
 Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# gemseo-algos-lab

A laboratory for exploring optimization algorithms built on
[GEMSEO](https://gemseo.org).

The package is a **GEMSEO plugin**: the algorithms it defines register
themselves in the GEMSEO factories and can be used wherever a GEMSEO algorithm
name is expected, without importing the package explicitly.

It currently implements the **box-subdivision outer approximation**, a bi-level
method for multimodal non-linear problems that keeps the exploration of the
design space and the local exploitation of a region in two distinct levels.

```{toctree}
:maxdepth: 2
:caption: Contents

installation
algorithm/index
api
changelog
```

## At a glance

On the Rastrigin function in two dimensions, subdivided into 100 boxes, the
method reaches the global optimum after solving about 20 boxes, roughly five
times cheaper than solving all of them.

```{warning}
The convexification constant defaults to `0.0` in GEMSEO, which makes the
outer-approximation cuts invalid on a multimodal problem: the master converges
after two or three sub-problems and reports success far from the optimum. Read
[Convexification](algorithm/methodology.md#convexification) before using the
method.
```

## Indices

- {ref}`genindex`
- {ref}`modindex`
