---
dcterms:title: "Design: Manifest Organization for the Accepted Features"
dcterms:version: "0.1.0"
dcterms:creator: "Christopher Steel"
dcterms:contributor: "Claude Fable 5 (Anthropic) — drafting assistance"
dcterms:description: "The manifest-organization step gating further file-fairy features: proposes that each axis of the four-axes meta-model becomes exactly one manifest key (state, source or content, sync_mode, and discovery via glob), shows one full worked manifest, records the alternatives, and lists the rulings needed before implementation."
dcterms:created: "2026-08-03"
dcterms:modified: "2026-08-03"
dcterms:format: "text/markdown"
dcterms:language: "en"
sat:language_bcp47: "en"
dcterms:relation: "decision--file-fairy-manifest-declared-sync-policy, analysis--ansible-builtin-modules-as-file-fairy-feature-candidates"
dcterms:identifier: "design--manifest-organization-for-accepted-features"
dcterms:rightsHolder: "Christopher Steel"
dcterms:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:repository: "file-fairy"
sat:path: "en/docs/design/"
sat:version_at_creation: "0.2.0"
sat:migration_status: pre-sat
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-03"
    author: "Christopher Steel"
    notes: "Initial draft of the manifest-organization step: one key per axis, worked example, alternatives, and the open rulings."
---

# Design: Manifest Organization for the Accepted Features

Version: 0.1.0
Status: Draft
Style Guide: style-guide--technical-documentation-for-technologists

## Purpose

The roadmap gates further feature implementation on this step: deciding how the accepted features from the ansible analysis are declared, so that manifests stay clear, concise, and logical as the vocabulary grows. This document proposes the organization, shows one full worked manifest, records the alternatives considered, and ends with the rulings needed before code.

## The proposal: one key per axis

The ansible analysis organized the feature candidates along a meta-model: type and existence, content provenance, reconciliation, attributes, and discovery. The proposal is that this meta-model *is* the manifest schema. Each axis becomes exactly one item-level key, each key answers exactly one question, and no key ever answers two:

| Key | Axis | Question it answers | Values |
| --- | --- | --- | --- |
| `state` | type and existence | what should this path be? | `file` (default), `directory`, `absent` |
| `source` / `content` | content provenance | where do its bytes come from? | a source path, inline text, or nothing (`state` alone) |
| `sync_mode` | reconciliation | when desired and actual disagree, who wins? | `mirror` (default), `seed_if_missing`, `overwrite`, `reference_only` |
| `glob` / `exclude` | discovery | which paths are items at all? | glob patterns expanding to items |

Attributes need no key: the one accepted attribute, the executable bit, is preserved from the source unconditionally, a behavior rather than a declaration, because a distributed script that arrives non-executable is simply wrong.

The rules that keep the schema honest:

- Keys compose orthogonally. `state: absent` ignores `source` and `content` (there is nothing to provide). `content` and `source` are mutually exclusive. `sync_mode` applies to whatever the other keys produce, so `state: directory` with `seed_if_missing` means "create the directory once, never police it."
- Defaults are the current behavior. An item with only `source` and `dest` is `state: file`, `sync_mode: mirror`, exactly the pre-existing semantics, so every existing manifest is a valid manifest of the new schema unchanged.
- Managed blocks are not a key on file items; they are their own item shape (below), because their unit is a region, not a path, and forcing them into the file vocabulary would overload every key's meaning.
- Everything remains group-inheritable where it makes sense: `sync_mode` already inherits, and `state` and glob roots do not, because existence and discovery are inherently per-item declarations.

## Worked example

One manifest exercising every accepted feature, annotated:

```yaml
version: "0.2.0"
remote_source_repo: "steelcj/sat-doc-automa"
remote_target_repo: "steelcj/example-target"
local_source_repo_path: "~/2-areas/development/sat-doc-automa"
local_target_repo_path: "~/2-areas/development/example-target"

vars:                                # per-target values for ${var} substitution
  project_name: "example-target"
  rights_holder: "Christopher Steel"

groups:

  devops-scripts:
    sync_mode: mirror                # protect local edits, flag them as conflicts
    items:
      - source: bump-version.py
        dest: bump-version.py
      - source: cut-release.py
        dest: cut-release.py
      # executable bit preserved from source, always, no declaration

  markdown-automa:
    sync_mode: mirror
    items:
      - glob: "en/docs/automa/markdown/defaults/*.md"   # discovery: expands to items
        exclude: "*--draft-*.md"
        dest_root: "en/docs/automa/markdown/defaults/"  # source == dest by construction

  scaffolding:
    sync_mode: seed_if_missing       # plant once, then the target owns them
    items:
      - content: "0.1.0\n"           # inline content, no source file needed
        dest: VERSION
      - source: CHANGELOG-template.md
        dest: CHANGELOG.md
        substitute: true             # ${project_name} etc. filled from vars at copy
      - state: directory             # existence alone, no content
        dest: en/docs/

  managed-blocks:
    items:
      - block: license               # a region, not a file: the block item shape
        source: en/docs/automa/licenses/license-block--agpl-3-0-or-later.md
        dest: README.md
        anchor: EOF                  # insert at EOF if the markers are absent
        substitute: true
        # markers: <!-- fairy:begin license --> ... <!-- fairy:end license -->
        # region between markers is fairy-owned, mirror semantics on the
        # region's checksum; everything outside the markers is the target's

  retired:
    items:
      - state: absent                # distribution-wide retraction, manifest-declared
        dest: en/docs/devops/commit-and-versioning-workflow-v0-2-0.md
        note: "Superseded at the guides/ move; retract the orphan everywhere."
```

## Alternatives considered

**Verb-shaped groups** (a `copies:`, `seeds:`, `deletions:` section per verb). Rejected: it scatters one path's declaration across sections, and a path's full story, what it is, where it comes from, who wins, should be readable in one item. The axis keys keep the story in one place.

**Mode bundles** (named profiles like `profile: scaffold` expanding to state plus mode plus substitution). Rejected for now: it adds an indirection layer before there is repetition to compress. If manifests grow repetitive, profiles can be added later without breaking the axis keys they would expand into.

**Ansible-style `state` carrying reconciliation too** (`state: present` vs `state: latest` in package-manager tradition). Rejected: it is precisely the axis collapse the meta-model exists to prevent, and the sync-policy decision already separated existence from reconciliation.

**Blocks as a `region:` key on file items.** Rejected: a file item's keys describe the whole file; a block item's keys describe a region inside a file the target owns. Making blocks their own item shape keeps `sync_mode: mirror` on a file meaning the file, always.

## Rulings needed before implementation

1. The block marker syntax: HTML comments as shown (invisible in rendered markdown, visible in source) or a visible fenced convention. HTML comments recommended; they also survive GitHub rendering silently.
2. Whether `substitute: true` is per-item opt-in as shown (recommended, explicit and greppable) or automatic whenever `vars` exists (rejected by the author of this draft: invisible substitution is action at a distance).
3. Whether `absent` requires the path to have been fairy-synced at some point (state-file evidence) or applies to any declared dest. Recommended: any declared dest, with `plan` always showing retractions in their own section, because the orphan problem that motivates `absent` predates the state file by definition.
4. Glob change surfacing: recommended that `plan` reports items entering or leaving a glob's match set explicitly, so a widening glob is always visible before it applies.
5. Implementation order. Recommended: `absent` first (the fleet is paying the orphan tax today), then managed blocks (CLAUDE.md and license blocks are waiting), then content and substitution, then globs, then diff output.

## License

This document, *Design: Manifest Organization for the Accepted Features*, by **Christopher Steel**, with AI assistance from **Claude Fable 5 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).

## Changelog

| Version | Status | Notes |
|---------|--------|-------|
| 0.1.0 | Draft | Initial proposal: one key per axis (state, source or content, sync_mode, glob), managed blocks as their own item shape, worked example, alternatives, five rulings listed. |
