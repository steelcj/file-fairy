---
dcterms:title: "Decision: Manifest-Declared Sync Policy for file-fairy"
dcterms:version: "0.1.0"
dcterms:creator: "Christopher Steel"
dcterms:contributor: "Claude (Anthropic) — drafting assistance"
dcterms:description: "Records the decision to move file-fairy's per-file sync intent (create-if-missing, mirror, always-overwrite, reference-only) out of the global --force CLI flag and into a per-group/per-item sync_mode vocabulary in the manifest, and to keep destructive directory operations declaration-only."
dcterms:created: "2026-08-02"
dcterms:modified: "2026-08-02"
dcterms:format: "text/markdown"
dcterms:language: "en"
sat:language_bcp47: "en"
dcterms:identifier: "decision--file-fairy-manifest-declared-sync-policy"
dcterms:rightsHolder: "Christopher Steel"
dcterms:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:repository: "file-fairy"
sat:path: "en/docs/decisions/sync/"
sat:version_at_creation: "0.1.0"
sat:migration_status: pre-sat
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-02"
    author: "Christopher Steel"
    notes: "Initial draft, recording the decision reached in design discussion on moving sync intent from the global --force flag into a manifest-declared sync_mode vocabulary."
---

# Decision: Manifest-Declared Sync Policy for file-fairy

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## Context

file-fairy 0.1.0 copies named groups of files from a source project to a
target project, driven by a YAML manifest, and classifies each item as
`new`, `update`, `unchanged`, `conflict`, or `missing-source` before
applying. It exposes exactly one way to override the default protective
behaviour, the global `--force` flag on `apply`, and exactly one way to
declare per-target intent in the manifest, the hardcoded `sync_mode:
reference_only` group knob (plus `source: null` items, which are
informational and never written).

Two limitations surface from this shape.

First, `--force` is stateless about intent. Its meaning is "for this whole
run, also overwrite every item in conflict," where a conflict is a target
file edited locally since the last sync. But intent is almost never
uniform across a run. A maintainer typically means "the house-style files
are mine to push and the target does not get a vote," while at the same
time "each target owns its own VERSION, never stamp mine over it," and
"the shared docs should update but a local hand-edit must be protected." A
single global flag cannot express three different intents in one apply; it
can only turn protection off for all of them at once. That is precisely
the situation where `--force` clobbers something the operator did not mean
to clobber.

Second, the "ensure this file exists, and otherwise leave it alone"
semantic does not exist at all. A missing target is created (status
`new`), but there is no mode that keys on *existence* rather than on the
state checksum. Two consequences follow. A file that should be planted
once and then owned by the target, VERSION being the canonical example,
is instead overwritten whenever the source changes (status `update`). And
on the first-ever apply, when there is no state record for a dest,
`build_plan` marks the item `new` without checking whether the file
already exists on disk, so a first run silently overwrites a pre-existing,
untracked target file rather than leaving it in place.

The manifest is the artifact that already knows which file is which. The
`--force` flag does not. Intent therefore belongs in the manifest, at the
granularity of the file, not in the invocation, at the granularity of the
run.

## Decision

Sync intent for common file operations is declared in the manifest via a
`sync_mode` vocabulary, settable at group level (inherited by the group's
items) and overridable per item. When `sync_mode` is absent the behaviour
is `mirror`, which is exactly file-fairy 0.1.0's current behaviour, so
existing manifests are unaffected. The existing `reference_only` group
value becomes one member of the vocabulary rather than a special case.

| `sync_mode` | Dest missing | Dest present, source changed | Dest present, locally edited (drift) |
| --- | --- | --- | --- |
| `mirror` *(default; current behaviour)* | create | overwrite | protect (skip) |
| `seed_if_missing` | create | do nothing | do nothing |
| `overwrite` | create | overwrite | overwrite |
| `reference_only` *(existing)* | never touch | never touch | never touch |

`seed_if_missing` decides purely on whether the dest path exists, not on
the state checksum. This is what makes it correct for VERSION and similar
target-owned files: planted once when absent, never touched thereafter. It
also removes the first-run surprise for items declared this way, since
existence, not "do I hold a state record," becomes the decision.

The CLI `--force` flag is demoted, not removed. It remains only as a
one-off, interactive override that applies conflicts for `mirror` items in
a single run, "yes, I edited this locally, overwrite it just this once."
The *standing* declaration "this file is always taken from source" moves
into `sync_mode: overwrite` in the manifest, where it is visible in a
diff, reviewable, and scoped to named files rather than to the whole run.

Destructive directory operations follow the same philosophy and are
stricter about it. Pruning, deleting files in a target directory that the
source no longer contains, must be a declared per-group intent in the
manifest (for example `prune: true` on a directory-syncing group) and must
never be reachable through a CLI flag. No one should be able to delete
files in a target by typing a flag; they must write down, in the manifest,
that the directory is a mirror and that deletions are accepted. Whether
directory-level (glob or tree) syncing and `prune` land in the same change
as the `sync_mode` vocabulary or in a follow-on is an implementation
sequencing question, not a change to this decision.

## Alternatives considered

**Keep the global `--force` flag as the intent mechanism.** Rejected. The
flaw is structural, not cosmetic: a per-run flag cannot carry per-file
intent, so any manifest containing a mix of owned, seeded, and protected
files forces the operator to choose between under-forcing (and hand-fixing
the ones that should have been overwritten) or over-forcing (and clobbering
the ones that should have been protected). It is also unreviewable, the
decision to overwrite leaves no trace in the repository.

**Remove `--force` entirely and make the manifest the only voice.**
Rejected, though close. It is the cleaner end state, but it drops the
legitimate ad-hoc case, "I know I edited this `mirror` file locally and I
want to discard that edit this once," which does not warrant permanently
reclassifying the file as `overwrite` in the manifest. Demoting `--force`
to that narrow override keeps the escape hatch without letting it carry
standing policy.

**Add an `ensure`/`seed` subcommand instead of a manifest mode.**
Rejected for the same reason as keeping `--force`: a verb operates at the
granularity of the run, but the intent is a property of the file. A
`seed_if_missing` file wants that behaviour on every apply, not only when
someone remembers to invoke a special subcommand, and mixing seed and
mirror files in one manifest would again require multiple invocations to
apply one logical sync.

## Consequences

- The manifest schema gains an optional `sync_mode` key at both group and
  item level, with item overriding group. Absence means `mirror`, so every
  existing manifest keeps its current behaviour with no edit. `reference_only`
  continues to work unchanged, now as one value in a documented set.
- `build_plan` takes the effective `sync_mode` for each item into account
  when computing status, and `cmd_apply` acts on it. `seed_if_missing`
  requires an existence check that is independent of the state record, which
  also closes the first-run "overwrite a pre-existing untracked file"
  behaviour for items declared that way. Whether to change that first-run
  behaviour for `mirror` items as well is noted here as an open question,
  not decided by this record.
- `--force` documentation (README and `--help`) is reworded from "also
  overwrite items in conflict" to a one-off override for `mirror` conflicts,
  and the standing-overwrite use is pointed at `sync_mode: overwrite`.
- README and CHANGELOG are updated: the `sync_mode` table, a worked manifest
  example (an `overwrite` house-style group, a `seed_if_missing` scaffolding
  group with VERSION, a default-`mirror` docs group), and a changelog entry
  under Unreleased.
- Directory-level syncing and `prune` are recorded here as declaration-only
  by policy even if implemented later; the destructive path must never be a
  CLI flag. If they are deferred, they are deferred as a follow-on to this
  decision, not reopened as a question.
- This record is authored to be synced by file-fairy from sat-doc-automa as
  the canonical source, consistent with the project's charter of keeping
  sat-doc-automa canonical and distributing conventions outward via the
  fairy itself.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Draft | Initial draft: manifest-declared `sync_mode` vocabulary (`mirror`/`seed_if_missing`/`overwrite`/`reference_only`), `--force` demoted to a one-off `mirror`-conflict override, destructive directory `prune` declared manifest-only. |
