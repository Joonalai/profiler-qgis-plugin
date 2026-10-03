# CHANGELOG

## Unreleased

- Updated dependencies and added bandit security checks
- Adopted qgis-plugin-copier-template
- Dropped support for QGS < 3.40
- Fixed duplicate meter contexts after reopening the settings dialog
- Profile filter now matches the typed text literally instead of as a regular expression
- Fixed the save notification showing the file path without the added `.prof` suffix
- Fixed the map rendering meter reporting the same slow render more than once
- Fixed the profiler extension missing from the profiler panel when QGIS starts with the plugin enabled
- Settings dialog is now scrollable and fits on smaller screens
- Fixed meter results not appearing in the profiler panel until the group was changed

## 0.1.0 (2026-04-07)

- Initial release of the profiler plugin and core library.
