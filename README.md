# QGIS profiler plugin

**UNDER ACTIVE DEVELOPMENT!**

The QGIS Profiler Plugin is a plugin ment to extend QGIS development tools
dock widget with two main functionalities:

* **Profiling** - makes the QGIS profiling more useful
  * ![profiling.gif](docs/profiling.gif?raw=True "Profiling")
* **Macros** - allow user to record simple macros
  * ![macro.gif](docs/macro.gif?raw=True "Profiling")

## Features

* A simpler python api for profiling
* Record profiling events (more info coming soon)
* Record and playback macros, ie. user mouse and keyboard events

## Installation

1. Clone the repository from GitHub.
2. Install requirements (in a venv): `pip install -r requirements.txt`
3. Install the repo (not editable): `pip install .`
4. Build a package: `qpdt b`
5. Open QGIS and navigate to `Plugins > Manage and Install Plugins`.
6. Click the `Install from ZIP` option and install the packaged plugin zip.

## Usage

Open QGIS development tools and interact with profiling and macro panel.

## Requirements

* QGIS version **3.22** or higher.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.
Development instructions coming soon.

## Inspirations

These awesome plugins are used as an inspiration for the plugin structure:

* <https://github.com/nlsfi/pickLayer>
* <https://github.com/nlsfi/segment-reshape-qgis-plugin>

## License

This plugin is released under the GNU General Public License (GPL) version 3. See
the [LICENSE](LICENSE) file for more details.
