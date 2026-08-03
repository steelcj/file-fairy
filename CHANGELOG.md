# Changelog

All notable changes to file-fairy are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions track the `VERSION` file and the git tags. Dates are ISO 8601.

## [Unreleased]

### Added

- Managed blocks, second feature under decision--manifest-organization-one-key-per-axis: a `block:` item owns one marker-delimited region inside a file the target owns. Region reconciled per sync_mode (mirror protects in-region edits as conflicts, first contact with a differing region included; overwrite reclaims; seed_if_missing leaves a present block alone), inserted at `anchor` (EOF default, BOF) when markers are absent, dest created holding only the block when missing, everything outside the markers untouched, malformed markers an error. Block state tracked as `dest::name`. Twelve new checks (32 total).

## [0.3.0] - 2026-08-03

### Added

- `state: absent`, the manifest-declared retraction, first feature under decision--manifest-organization-one-key-per-axis: declare a dest, the fairy deletes it from the target if present (plan section `RETRACT`, no-op status `retired` when already gone), no source needed, blind to sync_mode and the state file by ruling. Scheduled states (`directory`, `touch`) refuse by name; unknown states are manifest errors. Seven new checks in test_file_fairy.py (20 total).
- The manifest-organization decision record and its design document land in en/docs/.

## [0.2.0] - 2026-08-03

### Added

- Manifest-declared sync modes, per decision--file-fairy-manifest-declared-sync-policy: `mirror` (the default, the pre-existing three-way protective behaviour), `seed_if_missing` (existence-keyed: plant once, then the target owns it; never clobbers a pre-existing file, closing the first-run gap for these items), `overwrite` (the target never gets a vote, no conflict state), and `reference_only` now honoured at item level as well as group level. Declared at group level (inherited) or item level (overrides); an unknown mode is a manifest error. `--force` is demoted to a one-off interactive override for `mirror` conflicts; its standing form is `sync_mode: overwrite` in the manifest. New plan status `present` for seeded items the target owns.
- test_file_fairy.py, an offline suite (13 checks) covering every mode, group inheritance and item override, the conflict refusal and --force path, and the unknown-mode error.

### Added

- Initial implementation: `plan`, `apply`, and `status` commands over a YAML manifest, with checksum-based drift tracking distinguishing upstream source changes from local target edits. Applying a conflicted item requires `--force`. No path-containment guard on `dest`, the manifest is trusted, operator-authored config, not adversarial input; checksums exist for drift detection, not for safety.
