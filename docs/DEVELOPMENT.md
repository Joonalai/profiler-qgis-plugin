# Development instructions

The code for the plugin is in the [src](../src) folder. Make sure you have
required tools, such as
Qt with Qt Editor and Qt Linquist installed by following this
[tutorial](https://www.qgistutorials.com/en/docs/3/building_a_python_plugin.html#get-the-tools).

## Setting up development environment

This project uses [uv](https://docs.astral.sh/uv/getting-started/installation/)
to manage python packages. Make sure to have it installed first.

- Create a venv that is aware of system QGIS libraries: `uv venv --system-site-packages`
  - On Windows OSGeo4W v2 installs use `<osgeo>/apps/PythonXX/python.exe`
      with [necessary patches](https://trac.osgeo.org/osgeo4w/ticket/692)
- Activate the venv
- Install the dependencies:
- `uv sync`
- Install pre-commit: `pre-commit install`
- Create a `.env` from `.env.example`, and configure
   at least the QGIS executable path
- Launch development QGIS: `qpdt s`

## Requirements changes

To update requirements, do `uv lock --upgrade-package <package>`.

## Commit message style

Commit messages should follow [Conventional Commits notation](https://www.conventionalcommits.org/en/v1.0.0/#summary).

## Testing

Install python packages listed in [requirements.txt](../requirements.txt) to
the virtual environment and run tests with:

```shell script
pytest
```

## Release steps

When the branch is in a releasable state, trigger the Create draft
release workflow from GitHub Actions. Pass the to-be-released
version number as an input to the workflow.

Workflow creates two commits in the target branch, one with the
release state and one with the post-release state. It also
creates a draft release from the release state commit
with auto-generated release notes. Check the draft release
notes and modify those if needed. After the release is
published, the tag will be created, release workflow will
be triggered, and it publishes a new version to PyPI.

Note: if you created the release commits to a non-main branch
(i.e. to a branch with an open pull request), only publish the
release after the pull request has been merged to main branch.
Change the commit hash on the draft release to point to the actual
rebased commit on the main branch, instead of the now obsolete
commit on the original branch. If the GUI dropdown selection
won't show the new main branch commits, the release may need to
be re-created manually to allow selecting the rebased commit hash.
