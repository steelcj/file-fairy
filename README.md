# file-fairy

Version: 0.1.0
Status: Draft

A config-driven CLI that copies named groups of files from a source project to a target project on local disk, driven by a YAML manifest, with `plan`, `apply`, and `status` verbs and checksum-based drift tracking.

Originally scoped as the radar entry `fairy--file-sync-cli` in `sat-doc-automa`; renamed from Fairy to file-fairy on discovering that `fairy` is an existing, unrelated PyPI package.

## Description

Several projects sharing standing conventions, house style rules, license blocks, devops scripts, need a way to keep those shared files current without hand-copying them. file-fairy is not tied to git hosting or CI; source and target are local paths on the same machine, and the tool computes a plan, applies it, or reports drift between what a target holds and what the source currently has.

## Requirements

Python 3.8+ and PyYAML.

## Install

```bash
git clone https://github.com/steelcj/file-fairy.git
cd file-fairy
pip install .
/home/initial/.local/bin/python3.12 -m pip install .
```

venv option

```bash
git clone https://github.com/steelcj/file-fairy.git
cd file-fairy
VERSION=$(cat VERSION)
/home/initial/.local/bin/python3.12 -m venv --prompt "file-fairy-${VERSION}" ".venv-file-fairy-${VERSION}"
source ".venv-file-fairy-${VERSION}/bin/activate"
pip install .
```

Output example:

```bash
Processing ./.
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... done
Collecting PyYAML>=6.0 (from file-fairy==0.1.0)
  Using cached pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Using cached pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (807 kB)
Building wheels for collected packages: file-fairy
  Building wheel for file-fairy (pyproject.toml) ... done
  Created wheel for file-fairy: filename=file_fairy-0.1.0-py3-none-any.whl size=6756 sha256=7433e2dc74e700f06f0d5c6063302d04777fa396b8fad948eaf514f46900a23a
  Stored in directory: /home/initial/.cache/pip/wheels/26/96/69/5907a7ce2480b9d5336eba7f9e5856a38fbb30026162da2ebf
Successfully built file-fairy
Installing collected packages: PyYAML, file-fairy
Successfully installed PyYAML-6.0.3 file-fairy-0.1.0
```

and if required:

```bash
pip install --upgrade pip
```

Output example:

```bash
Requirement already satisfied: pip in ./.venv-file-fairy-0.1.0/lib/python3.12/site-packages (25.0.1)
Collecting pip
  Using cached pip-26.1.2-py3-none-any.whl.metadata (4.6 kB)
Using cached pip-26.1.2-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 25.0.1
    Uninstalling pip-25.0.1:
      Successfully uninstalled pip-25.0.1
Successfully installed pip-26.1.2
```

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
