# QGIS profiler plugin

![tests](https://github.com/Joonalai/profiler-qgis-plugin/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/Joonalai/profiler-qgis-plugin/branch/main/graph/badge.svg?token=D1RUB69MUM)](https://codecov.io/gh/Joonalai/profiler-qgis-plugin)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

**UNDER ACTIVE DEVELOPMENT!**

The QGIS Profiler Plugin aims to extend QGIS Profiler development tool
to be able to profile plugins and QGIS itself easily.

![profiling.gif](docs/profiling.gif?raw=True "Profiling")

## Features

* A simpler python api for profiling
* Record profiling events (more info coming soon)

## Installation

1. Clone the repository from GitHub.
2. Install requirements (in a venv created with --system-site-packages): `[uv] sync`
3. Build a package: `qpdt b`
4. Open QGIS and navigate to `Plugins > Manage and Install Plugins`.
5. Click the `Install from ZIP` option and install the packaged plugin zip.

## Usage

Open QGIS development tools and interact with profiling panel.

## Requirements

* QGIS version **3.34** or higher.
* Qt version **5.13.1** or higher.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

See [development readme](docs/DEVELOPMENT.md) for details.

## Inspirations

These awesome plugins are used as an inspiration for the plugin structure:

* <https://github.com/nlsfi/pickLayer>
* <https://github.com/nlsfi/segment-reshape-qgis-plugin>
* <https://github.com/GispoCoding/pytest-qgis>

## License & copyright

Licensed under GNU GPL v3.0.

Copyright (C) 2025 profiler-qgis-plugin contributors.

[uv](https://docs.astral.sh/uv/getting-started/installation/)
[cProfile](https://docs.python.org/3/library/profile.html#module-cProfile)
