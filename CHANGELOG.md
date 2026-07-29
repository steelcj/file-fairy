# Changelog

All notable changes to file-fairy are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions track the `VERSION` file and the git tags. Dates are ISO 8601.

## [Unreleased]

### Added

- Initial implementation: `plan`, `apply`, and `status` commands over a YAML manifest, with checksum-based drift tracking distinguishing upstream source changes from local target edits. Applying a conflicted item requires `--force`. No path-containment guard on `dest`, the manifest is trusted, operator-authored config, not adversarial input; checksums exist for drift detection, not for safety.
