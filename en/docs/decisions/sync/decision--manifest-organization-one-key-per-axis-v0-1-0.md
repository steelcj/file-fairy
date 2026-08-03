---
dcterms:title: "Decision: Manifest Organization, One Key per Axis"
dcterms:version: "0.1.0"
dcterms:creator: "Christopher Steel"
dcterms:contributor: "Claude Fable 5 (Anthropic) — drafting assistance"
dcterms:description: "Ratifies the manifest-organization design: each axis of the four-axes meta-model is exactly one manifest key (state; source or content; sync_mode; glob and exclude), managed blocks are their own item shape, and the five open rulings are decided, including absent-first implementation order."
dcterms:created: "2026-08-03"
dcterms:modified: "2026-08-03"
dcterms:format: "text/markdown"
dcterms:language: "en"
sat:language_bcp47: "en"
dcterms:relation: "design--manifest-organization-for-accepted-features, decision--file-fairy-manifest-declared-sync-policy"
dcterms:identifier: "decision--manifest-organization-one-key-per-axis"
dcterms:rightsHolder: "Christopher Steel"
dcterms:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:repository: "file-fairy"
sat:path: "en/docs/decisions/sync/"
sat:version_at_creation: "0.2.0"
sat:migration_status: pre-sat
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-03"
    author: "Christopher Steel"
    notes: "Initial record. Ratifies the design document's proposal and its five recommendations without amendment."
---

# Decision: Manifest Organization, One Key per Axis

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## Context

The roadmap gates feature implementation on the manifest-organization step. The design document `design--manifest-organization-for-accepted-features` (en/docs/design/) proposed the organization, showed a full worked manifest, and listed five open rulings. This record ratifies it.

## Decision

The four-axes meta-model is the manifest schema. Each axis is exactly one item-level key, and no key answers two questions: `state` for type and existence (`file` default, `directory`, `absent`); `source` or inline `content` for provenance, mutually exclusive; `sync_mode` for reconciliation, unchanged from the sync-policy decision; `glob` with `exclude` for discovery. The executable bit is preserved from source unconditionally, a behavior, not a declaration. Managed blocks are their own item shape, a region is not a file. Defaults are the pre-existing semantics, so every existing manifest remains valid unchanged.

The five rulings, each decided as the design recommended:

1. Block markers are HTML comments (`<!-- fairy:begin NAME -->` / `<!-- fairy:end NAME -->`), invisible in rendered markdown, visible in source.
2. `substitute: true` is explicit per-item opt-in. Automatic substitution wherever `vars` exists is rejected as action at a distance.
3. `state: absent` applies to any declared dest, whether or not the fairy ever synced it; the orphan problem predates the state file by definition. Retractions always appear in their own plan section.
4. `plan` reports items entering or leaving a glob's match set explicitly; a widening glob is never silent.
5. Implementation order: `absent`, then managed blocks, then `content` and substitution, then globs, then diff output.

## Consequences

- `absent` is implemented first, against this record; the fleet is paying the orphan tax today.
- Manifest schema documentation lives in the tool's docstring and README as each feature lands; the design document remains the full worked reference.
- Alternatives (verb-shaped groups, mode bundles, reconciliation folded into `state`, blocks as a key on file items) are recorded in the design document with the reasons they lost, and are not reopened by implementation details.

## Changelog

| Version | Status | Notes |
|---------|--------|-------|
| 0.1.0 | Draft | Ratifies the design and its five recommendations; absent-first order confirmed. |
