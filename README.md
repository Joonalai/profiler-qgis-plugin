# QGIS profiler plugin

![tests](https://github.com/Joonalai/profiler-qgis-plugin/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/Joonalai/profiler-qgis-plugin/branch/main/graph/badge.svg?token=D1RUB69MUM)](https://codecov.io/gh/Joonalai/profiler-qgis-plugin)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

The QGIS Profiler Plugin aims to extend QGIS Profiler development tool
to be able to profile plugins and QGIS itself easily.

![profiling.gif](docs/profiling.gif?raw=True "Profiling")

## Features

* Broader python api for profiling
  * Proper API documentation is coming soon
* Ability to filter and search profile events
* A feature to record profiler events and various meters
* A feature to record any python code with [cProfile](https://docs.python.org/3/library/profile.html#module-cProfile)
  (if installed in the system)
  * To get started, hit the python button inside
   the panel or use `cprofile_plugin` [decorator](src/qgis_profiler/decorators.py)
   with your plugin
* Ability to save the profile results into a stats file, that can then be further
  analysed for example with tools like [gprof2dot](https://github.com/jrfonseca/gprof2dot)
  and [snakeviz](https://jiffyclub.github.io/snakeviz/#snakeviz)
* Settings to control the behavior

## Installation

Install the plugin from the QGIS plugin repository
or download the zip from the repository releases.

## Usage

Open QGIS development tools and interact with the profiling panel.

## Requirements

* QGIS version **3.34** or higher.
* Qt version **5.13.1** or higher.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

See [development readme](docs/DEVELOPMENT.md) for details.

## Inspirations

These awesome plugins are used as inspiration for the plugin structure:

* <https://github.com/nlsfi/pickLayer>
* <https://github.com/nlsfi/segment-reshape-qgis-plugin>
* <https://github.com/GispoCoding/pytest-qgis>

## License & copyright

Licensed under GNU GPL v3.0.

Copyright (C) 2025 profiler-qgis-plugin contributors.
