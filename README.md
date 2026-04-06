# QGIS profiler plugin

![tests](https://github.com/Joonalai/profiler-qgis-plugin/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/Joonalai/profiler-qgis-plugin/branch/main/graph/badge.svg?token=D1RUB69MUM)](https://codecov.io/gh/Joonalai/profiler-qgis-plugin)
[![docs](https://readthedocs.org/projects/profiler-qgis-plugin/badge/?version=latest)](https://profiler-qgis-plugin.readthedocs.io/en/latest/)
[![GPLv3 license](https://img.shields.io/badge/License-GPLv3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

The QGIS Profiler Plugin aims to extend QGIS Profiler development tool
to be able to profile plugins and QGIS itself easily.

![profiling.gif](docs/profiling.gif?raw=True "Profiling")

## Features

* Broader python api for profiling
  * See the [API documentation](https://profiler-qgis-plugin.readthedocs.io/en/latest/core/index.html)
* Ability to filter and search profile events
* A feature to record profiler events and various meters
* A feature to record any python code with [cProfile](https://docs.python.org/3/library/profile.html#module-cProfile)
  (if installed in the system)
* Ability to save the profile results into a stats file for further analysis
* Performance meters for detecting anomalies (recovery time, thread health, map rendering)
* Settings to control the behavior

## Installation

Install the plugin from the QGIS plugin repository
or download the zip from the repository releases.

## Usage

Open QGIS Development Tools and navigate to the Profiler tab. The plugin extends
the built-in profiler panel with additional controls.

### Recording Profile Events

Click the **Record** button in the profiler panel, then interact with QGIS normally
(pan, zoom, identify features, etc.). The profiler captures timing data for each
interaction. Stop recording to inspect the results in the profiler tree.

### Filtering and Searching Events

Use the **filter text field** to search for specific events by name. Adjust the
**time threshold spinner** to hide events below a certain duration, making it easy
to focus on bottlenecks and ignore noise.

### Saving and Exporting Results

Click the **Save** button to export profiling data as a `.prof` file. This format
is compatible with standard Python profiling tools such as
[gprof2dot](https://github.com/jrfonseca/gprof2dot) and
[snakeviz](https://jiffyclub.github.io/snakeviz/#snakeviz) for further analysis
and visualization.

### Python cProfile Integration

Toggle the **cProfile button** (Python icon) to record Python-level profiling data.
This captures detailed call stacks and timing for all Python code executed while
active. Results are logged to the console and can be saved to a stats file.

To profile an entire plugin lifecycle, use the `@cprofile_plugin` decorator:

```python
from qgis_profiler.decorators import cprofile_plugin


@cprofile_plugin()
class MyPlugin:
    def initGui(self):
        ...

    def unload(self):
        ...
```

### Profiling with Decorators

Use the `@profile` decorator to measure individual functions or `@profile_class`
to instrument all methods in a class:

```python
from qgis_profiler.decorators import profile, profile_class


@profile
def my_slow_function():
    ...


@profile_class(exclude=["_private_method"])
class MyProcessor:
    def process(self):
        ...
```

Results appear in the profiler tree under the configured group name.

### Performance Meters

The plugin includes three performance meters that can detect anomalies automatically:

* **Recovery Meter** -- measures how long QGIS takes to recover after a freeze
* **Thread Health Checker** -- monitors main thread responsiveness via pinging
* **Map Rendering Meter** -- tracks map canvas rendering time

Enable and calibrate meters in **Settings**. Use the **Calibrate** button to
auto-adjust thresholds to your system's baseline performance.

## Requirements

* QGIS version **3.40** or higher including QGIS 4.

## Documentation

Full documentation is available at
[profiler-qgis-plugin.readthedocs.io](https://profiler-qgis-plugin.readthedocs.io/en/latest/).

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

See [development readme](docs/DEVELOPMENT.md) for details.

## Inspirations

These awesome plugins are used as inspiration for the plugin structure:

* <https://github.com/nlsfi/pickLayer>
* <https://github.com/nlsfi/segment-reshape-qgis-plugin>
* <https://github.com/osgeosuomi/pytest-qgis>

## License & copyright

Licensed under GNU GPL v3.0.

Copyright (C) 2025-2026 profiler-qgis-plugin contributors.
