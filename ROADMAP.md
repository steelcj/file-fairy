---
dcterms:title: "file-fairy Roadmap"
dcterms:version: "0.1.0"
dcterms:creator: "Christopher Steel"
dcterms:contributor: "Claude Fable 5 (Anthropic) — drafting assistance"
dcterms:description: "Running record of decisions and open work for file-fairy, newest first: the usage guide's canonical home, the invocation and venv friction, and the accepted feature backlog carried by reference."
dcterms:created: "2026-08-03"
dcterms:modified: "2026-08-03"
dcterms:format: "text/markdown"
dcterms:language: "en"
sat:language_bcp47: "en"
dcterms:identifier: "file-fairy-roadmap"
dcterms:rightsHolder: "Christopher Steel"
dcterms:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:repository: "file-fairy"
sat:path: "./"
sat:version_at_creation: "0.2.0"
sat:migration_status: pre-sat
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-03"
    author: "Christopher Steel"
    notes: "Initial roadmap, created after the 0.2.0 release closed the fleet's first full receive-cut-publish loop. Records the usage-guide placement item, the invocation friction item, and the accepted feature backlog by reference. Also closes the standard-repository-layout drift finding that this repository lacked a ROADMAP.md."
---

# file-fairy Roadmap

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## Abstract

Running record of decisions and open work for file-fairy. Items are pending until resolved; resolutions name what was decided and where the record lives. The repository's feature law lives in `en/docs/decisions/sync/` and its feature backlog in `en/docs/design/`; this roadmap tracks what is scheduled, not what is decided.

## Pending

### A fairy usage guide, canonical in sat-doc-automa, distributed here

The fairy's operating workflow has no guide anywhere: plan and status reading, the receive-then-commit pattern observed in the 0.2.0 release loop (apply the manifest, commit the arrivals as their own commit, then cut), conflict resolution for `mirror` items, and when each `sync_mode` fits. The commit-and-versioning workflow deliberately excludes this, it is sync workflow, not release workflow.

Because file-fairy exists in large part to serve sat-doc-automa, the guide should be authored canonically in sat-doc-automa beside the fleet's other operating guides, `en/docs/guides/devops/` or a sibling, and distributed to this repository through the fairy's own manifest at `source == dest`, `mirror` mode, the same road the commit-and-versioning workflow already travels. The fairy carrying its own manual is the correct shape: one canonical source, and this repository holds a current copy because the tool it documents put it there.

### Invocation friction: the venv depends on the file-fairy checkout

Running `ff` today effectively requires the file-fairy project's own venv, because the documented venv creation names the environment from the checkout's `VERSION` file. Two symptoms are already observed: an operator working in a *target* repository must hop to the fairy checkout or hard-code its venv path, and the venv's name goes stale on every release, the 0.2.0 release was cut from a shell prompting `(file-fairy-0.1.0)`.

Candidates to investigate, not yet decided: a per-machine install (`pipx install`, or `pip install --user`) that puts `ff` on PATH once and removes the venv from the operator's day entirely, PyYAML being the sole dependency; decoupling the venv naming from `VERSION` so the environment survives releases; or an installer following the osat-fluent conventions if the acquisition problem ever grows to deserve one. The choice belongs in a decision record at `en/docs/decisions/` when made; the pipx-shaped option is the lightest and should be evaluated first.

### Accepted feature backlog, carried by reference

The adopt and adapt list, `absent` for distribution-wide retraction, managed blocks, inline `content:`, lightweight substitution, glob item sets, diff output in plan, backup-before-overwrite, the validate hook, executable-bit preservation, lives in `en/docs/design/analysis--ansible-builtin-modules-as-file-fairy-feature-candidates-v0-1-0.md` and is not restated here. Sequencing gate: the manifest-organization step, deciding how accepted features are declared so manifests stay clear, concise, and logical, comes before implementation of the next feature. `absent` carries extra weight: until it exists, every renamed document orphans a stale copy in every target, a cost paid by hand at the 0.2.0 receive.

## Resolved

### Manifest-declared sync modes

Resolved at 0.2.0. `mirror`, `seed_if_missing`, `overwrite`, and `reference_only`, group-level inherited and item-level overridable, `--force` demoted to a one-off `mirror`-conflict override. Recorded in `en/docs/decisions/sync/decision--file-fairy-manifest-declared-sync-policy-v0-1-0.md`; exercised by `test_file_fairy.py`.

## License

This document, *file-fairy Roadmap*, by **Christopher Steel**, with AI assistance from **Claude Fable 5 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).

## Changelog

| Version | Status | Notes |
|---------|--------|-------|
| 0.1.0 | Draft | Initial roadmap: usage-guide placement, invocation friction, feature backlog by reference, sync modes recorded as resolved. Closes the missing-ROADMAP drift finding. |
