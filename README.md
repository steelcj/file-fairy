# file-fairy

> **Archived on 2026-10-11.** file-fairy is no longer developed. Its last release is [v0.7.0](https://github.com/steelcj/file-fairy/releases/tag/v0.7.0).
>
> Its engine continues as **[uc-portage](https://github.com/steelcj/uc-portage)**, a generic file reconciler with the same sync modes (`mirror`, `seed_if_missing`, `overwrite`, `reference_only`), managed blocks and `state: absent` retraction, plus line-ending-blind checksums, a case-collision check and `harvest`. Shared files are now published as offerings by **[uc-automa](https://github.com/steelcj/uc-automa)**, and each repository subscribes to them in its own `.uc-automa.yaml`, instead of manifests with local source and target paths.
>
> This repository stays readable, and every link and clone keeps working. Its code and documents remain under AGPL-3.0-or-later; uc-portage and uc-automa are MIT for code and CC BY 4.0 for documentation.

## Moving from file-fairy

- **Manifests are not migrated.** A repository that received files through an `ff-manifest-*.yaml` runs `uc-automa init` and `uc-automa offerings apply` instead; see uc-automa's README.
- **Managed blocks are renamed.** Blocks marked `<!-- fairy:begin NAME -->` and `<!-- fairy:end NAME -->` are written `<!-- uc-portage:begin NAME -->` and `<!-- uc-portage:end NAME -->` by uc-portage. Rename existing markers before the first apply, or uc-portage adds a second block.
- **The state file starts afresh.** `.file-fairy-state.yaml` is not read; uc-portage keeps `.uc-portage-state.yaml`. On the first apply, a file identical to the offering is adopted, and a differing one under `mirror` is reported as a conflict to review, never overwritten.
- **The command is `uc-portage`.** There is no `ff` alias and no bare form that means apply.
- **The decisions carried over.** The sync-policy and one-key-per-axis decisions are uc-portage's decision records 0001 and 0002, revised to offerings, each naming its file-fairy original in `dc:source`.
- **Removing file-fairy.** Once nothing uses it, delete its install root, `~/.local/share/file-fairy/` (`%LOCALAPPDATA%\file-fairy\` on Windows), and the `ff` and `file-fairy` wrappers it wrote in `~/.local/bin/` (`%LOCALAPPDATA%\Programs\` on Windows).

A config-driven CLI that copies named groups of files from a source project to a target project on local disk, driven by a YAML manifest, with `plan`, `apply`, and `status` verbs and checksum-based drift tracking.

Originally scoped as the radar entry `fairy--file-sync-cli` in `sat-doc-automa`; renamed from Fairy to file-fairy on discovering that `fairy` is an existing, unrelated PyPI package.

## Description

Several projects sharing standing conventions, house style rules, license blocks, devops scripts, need a way to keep those shared files current without hand-copying them. file-fairy is not tied to git hosting or CI; source and target are local paths on the same machine, and the tool computes a plan, applies it, or reports drift between what a target holds and what the source currently has.

## Requirements

Python 3.8+ and PyYAML.

## Install

`install-ff.py` installs file-fairy into user-space, following the same layout as the other OSAT managers (osat-fluent-python-tool, osat-manager-slugify). No root or Administrator privilege is needed, and the manager refuses to run with it. It needs Python 3.8 or later with working `venv` and `pip`, and builds the venv from whichever interpreter runs it, so use your python-tool install if you have one.

```bash
cd ~/2-areas/development/file-fairy
python3.12 install-ff.py --install
```

That installs the checkout's `VERSION` under `~/.local/share/file-fairy/<version>/` and renders `ff` and `file-fairy` wrappers into `~/.local/bin`. On Windows the same pieces go to `%LOCALAPPDATA%\file-fairy\<version>\` and `%LOCALAPPDATA%\Programs\`, which is not on `PATH` by default.

The install is a snapshot of the checkout. Pulling or editing changes nothing until you run `--install` again, so a fairy you are developing is exercised with `python3 file_fairy.py` from the checkout, or reinstalled with `--install --force`.

```
install-ff.py --install          Install this checkout's version and activate it
install-ff.py --switch VERSION   Point the wrappers at another installed version
install-ff.py --status           Show installed and active versions
install-ff.py --remove VERSION   Remove an installed, inactive version
install-ff.py --version          Show the manager's version
```

The package version now comes from `VERSION` through `pyproject.toml`, so `pip show file-fairy` agrees with the release tags.

## Manifest format

```yaml
local_source_repo_path: "~/path/to/source"
local_target_repo_path: "~/path/to/target"
groups:
  <group-name>:
    sync_mode: reference_only   # optional; skips the whole group
    items:
      - source: relative/path/in/source.md
        dest: relative/path/in/target.md
      - source: null             # informational only; never synced
        dest: SOME/FILE.md
```

See `osat-fluent-sync-manifest.yaml` in `sat-doc-automa` for a worked example.

## Usage

```bash
file-fairy plan manifest.yaml  # show changes, no writes
file-fairy status manifest.yaml # alias for plan
file-fairy apply  manifest.yaml # copy new/updated items
file-fairy apply  manifest.yaml --yes # skip confirmation
file-fairy apply  manifest.yaml --force # one-off override for mirror conflicts
```

Output example for 

```bash
file-fairy apply  manifest.yaml 
```

is something like:

```bash
NEW  (not yet synced)
  [devops-scripts] bump-version.py -> bump-version.py
  [devops-scripts] cut-release.py -> cut-release.py
  [devops-scripts] check-conformance.py -> check-conformance.py
  [devops-docs] en/docs/devops/commit-and-versioning-workflow-v0-2-0.md -> en/docs/devops/commit-and-versioning-workflow-v0-2-0.md

[file-fairy] 4 item(s) would be synced, 0 conflict(s), 0 missing source(s)

Apply the above? [y/N] y
  synced: bump-version.py -> bump-version.py
  synced: cut-release.py -> cut-release.py
  synced: check-conformance.py -> check-conformance.py
  synced: en/docs/devops/commit-and-versioning-workflow-v0-2-0.md -> en/docs/devops/commit-and-versioning-workflow-v0-2-0.md

```

Each item is classified as `new`, `update` (source changed upstream), `unchanged`, `present` (a `seed_if_missing` item the target now owns), `conflict` (a `mirror` item the target changed locally since the last sync), or `missing-source`. `apply` skips conflicts unless `--force` is given, so a local hand-edit is never silently overwritten.

## Sync modes

Sync intent is declared in the manifest, per *Decision: Manifest-Declared Sync Policy* (`en/docs/decisions/sync/`), at group level (inherited by the group's items) or item level (overrides the group). Absent means `mirror`, which is exactly the pre-0.2.0 behaviour, so existing manifests are unaffected.

| `sync_mode` | Dest missing | Dest present, source changed | Dest present, locally edited |
| --- | --- | --- | --- |
| `mirror` (default) | create | overwrite | protect (conflict, skip) |
| `seed_if_missing` | create | do nothing | do nothing |
| `overwrite` | create | overwrite | overwrite |
| `reference_only` | never touch | never touch | never touch |

`seed_if_missing` decides purely on whether the dest path exists, never on content or sync state, which makes it right for files each target should own after birth, a `VERSION` being the canonical example. `overwrite` is the standing form of "the target never gets a vote"; `--force` remains only as a one-off interactive override for `mirror` conflicts. `reference_only` now also works per item.

Example:

```yaml
groups:
  house-style:
    sync_mode: overwrite        # the project doesn't get a vote on these
    items:
      - source: .editorconfig
        dest: .editorconfig
  scaffolding:
    sync_mode: seed_if_missing  # plant it once, then it's theirs
    items:
      - source: VERSION
        dest: VERSION
  shared-docs:                  # no sync_mode, so mirror, the safe default
    items:
      - source: en/docs/guides/devops/commit-and-versioning-workflow-v0-3-0.md
        dest: en/docs/guides/devops/commit-and-versioning-workflow-v0-3-0.md
```

## Retraction

`state: absent` is the manifest-declared retraction, per *Decision: Manifest Organization, One Key per Axis* (`en/docs/decisions/sync/`): declare a dest and the fairy deletes it from the target if present, shown first in the plan under its own `RETRACT` section. No source is needed, no CLI flag exists for it, and it applies to any declared dest whether or not the fairy ever synced it, because the orphan problem predates the state file. An already-absent dest reports as `retired`, a no-op.

```yaml
  retired:
    items:
      - state: absent
        dest: en/docs/devops/commit-and-versioning-workflow-v0-2-0.md
```

## Managed blocks

A block item makes a *region* the unit of sync instead of a file: the fairy owns the text between HTML comment markers inside a file the target otherwise owns, per *Decision: Manifest Organization, One Key per Axis*. If the markers exist, the region is reconciled under the item's `sync_mode` with the region as the unit, a local edit inside the markers is a `mirror` conflict, everything outside the markers is never touched. If the markers are absent the block is inserted at `anchor` (`EOF` default, or `BOF`); if the dest file is absent it is created holding only the block. First contact with an existing, differing region is a conflict, not a clobber. Malformed markers are an error, never a guess.

```yaml
  managed-blocks:
    items:
      - block: license
        source: en/docs/automa/licenses/license-block--agpl-3-0-or-later.md
        dest: README.md
        anchor: EOF
```

renders in the target as:

```markdown
<!-- fairy:begin license -->
...the source file's content...
<!-- fairy:end license -->
```

Run the test suite with `python3 test_file_fairy.py`.

## State

A per-target state file, `<local_target_repo_path>/.file-fairy-state.yaml`, records the source and dest checksum for every synced item as of the last successful apply. This is what makes `plan` cheap and lets it tell "source changed upstream" apart from "target changed locally."

## Design notes

No path-containment guard exists on `dest`. The manifest is a config file the operator authors themselves, not adversarial input, so it is trusted and executed as written. Checksums exist to detect drift, not to guard against a malicious config.

## See also

- `sat-doc-automa/en/docs/radar/assess/sync/fairy--file-sync-cli.md`, the original radar entry.
- `sat-doc-automa/en/docs/devops/decision--gh-cli-for-release-asset-publishing-v0-1-0.md` and `osat-fluent-restic-tool/docs/en/guides/development/decision--self-update-via-github-release-archive-v0-1-0.md`, for the surrounding decision-record conventions this README follows loosely.

## License

This document, *file-faiexiexry*, by **Christopher Steel**, with AI assistance from **Claude Sonnet 5 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).

## Changelog

| Version | Status | Notes |
|---------|--------|-------|
| 0.1.0 | Draft | Initial implementation: plan/apply/status, checksum-based drift tracking, --force for conflicts |
