---
dcterms:title: "Analysis: Ansible Builtin Modules as file-fairy Feature Candidates"
dcterms:version: "0.1.0"
dcterms:creator: "Christopher Steel"
dcterms:contributor: "Claude (Anthropic) — drafting assistance"
dcterms:description: "Surveys the ansible.builtin module collection, extracts every capability relevant to file-fairy's domain of repo-to-repo file distribution, and classifies each as adopt, adapt, defer, or out-of-scope, organized by the four-axes meta-model of a managed path. Produces the candidate feature list from which manifest organization will be designed in a subsequent step."
dcterms:created: "2026-08-02"
dcterms:modified: "2026-08-02"
dcterms:format: "text/markdown"
dcterms:language: "en"
sat:language_bcp47: "en"
dcterms:identifier: "analysis--ansible-builtin-modules-as-file-fairy-feature-candidates"
dcterms:rightsHolder: "Christopher Steel"
dcterms:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:repository: "file-fairy"
sat:path: "en/docs/design/"
sat:version_at_creation: "0.1.0"
sat:migration_status: pre-sat
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-02"
    author: "Christopher Steel"
    notes: "Initial draft: full ansible.builtin survey, candidate list classified adopt/adapt/defer/out-of-scope across the four axes."
---

# Analysis: Ansible Builtin Modules as file-fairy Feature Candidates

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## Purpose and scope

This is step one of a three-step sequence: (1) survey Ansible's builtin
modules and assemble a candidate feature list for file-fairy, (2) decide
which candidates are in, (3) design how the accepted features are
organized in the manifest so manifests stay clear, concise, and logical.
This document performs step one only. It proposes no manifest syntax; the
`sync_mode` names from `decision--file-fairy-manifest-declared-sync-policy`
are used as placeholders for semantics already decided there.

## The lens: what file-fairy is and is not

Every classification below follows from one distinction. Ansible is
configuration management: it owns a live filesystem on a possibly remote
host and converges it, attributes and all, toward a desired state,
overwriting drift by default. file-fairy is convention distribution: its
targets are git working trees on the operator's own machine, its content
travels onward through commits and checkouts to other people's platforms,
and its defining feature is that drift in a target can be *legitimate*
(a local hand-edit, protected by default) rather than an error to
converge away.

Three consequences of "the target is a git repo" recur throughout:

1. git preserves content and the executable bit; it does not preserve
   owner, group, general modes, timestamps, SELinux context, or extended
   attributes. Distributing what git will not carry is distributing
   nothing.
2. Committed symlinks and hard links behave badly or not at all on
   Windows checkouts, the same cross-platform concern recorded in
   `decision--gh-cli-for-release-asset-publishing`.
3. Remote-host machinery (connections, fetch/slurp, remote_src) has no
   meaning when source and target are directories on one disk.

## Survey coverage

The full `ansible.builtin` collection was reviewed. Modules outside the
file/content domain entirely — package management (`apt`, `dnf`, `pip`,
…), services (`service`, `systemd_service`), users (`user`, `group`),
execution (`command`, `shell`, `script`), networking (`uri`, `get_url`,
`git`), inventory, facts, and playbook control flow — are excluded
without further discussion. The relevant survivors: `file`, `copy`,
`template`, `stat`, `find`, `tempfile`, `lineinfile`, `blockinfile`,
`replace`, `assemble`, `slurp`, `fetch`, `unarchive`.

## Candidate features by axis

Classifications: **adopt** (take the semantic, near-term), **adapt**
(take the idea, reshape it for the fairy's domain), **defer** (real
candidate, not yet — recorded so it is a decision, not an accident),
**out** (contradicts the lens; scoped out deliberately).

### Axis 1 — Type and existence

| Candidate | From | Class | Rationale |
| --- | --- | --- | --- |
| Ensure directory exists (`state: directory`) | `file` | **adopt** | The fairy already `mkdir -p`s parents as a side effect of copying; making an empty directory declarable (e.g. a required `egress/` or `staging/` skeleton) is nearly free and completes the picture. |
| Delete a path (`state: absent`) | `file` | **adopt** | The missing verb. Today the fairy can only add or update across targets; retraction of a deprecated script or doc must be done by hand in every sibling. Distribution-wide removal is the natural per-item complement of directory prune, and per the sync-policy decision it is manifest-declared, never a CLI flag. |
| Create empty file (`state: touch`) | `file` | **adopt** | Trivial once `seed_if_missing` exists: it is `seed_if_missing` with no source. Covers "every project must have a CHANGELOG.md, even if empty." Ansible's timestamp-bumping half of `touch` is dropped (see Axis 4). |
| Symbolic links (`state: link`) | `file` | **defer** | Legitimate on the operator's own machine, but a committed symlink is a cross-platform hazard in a git repo. Defer until a concrete need appears; if adopted, flag it clearly as "does not travel well." |
| Hard links (`state: hard`) | `file` | **out** | Git cannot represent them; they silently become independent copies on clone. Nothing the fairy distributes can rely on them. |
| The `file`/`present` distinction | `file` | *(informational)* | Ansible's `state: file` does not create missing files; creation lives in `copy`/`touch`. The fairy's equivalent split is already decided: existence-keyed `seed_if_missing` vs content-keyed `mirror`/`overwrite`. |

### Axis 2 — Content provenance

| Candidate | From | Class | Rationale |
| --- | --- | --- | --- |
| Copy from source path | `copy` (src) | *(exists)* | This is file-fairy 0.1.0. |
| Inline content in the manifest (`content:`) | `copy` (content) | **adopt** | Small but excellent fit: a `VERSION` seeded as `0.1.0`, a one-line `.gitattributes`, a stub README. Removes the need for a source file whose only job is to hold three bytes, and makes `touch`-with-content free. |
| Managed block inside a target-owned file | `blockinfile` | **adapt — highest-value candidate** | Marker-delimited begin/end lines make a *region* of a file the unit of sync instead of the whole file. This dissolves the fairy's hardest standing problem: a license block, header, or "see also" section that sat-doc-automa owns, inside a README the target owns. Whole-file modes cannot express that; a managed block can, idempotently — replace between markers if present, insert (at EOF/BOF/anchor) if absent, and local edits *outside* the markers are never touched. Directly serves the existing `license-block--*.md` artifacts in sat-doc-automa. Drift detection generalizes cleanly: checksum the region between markers instead of the file. |
| Placeholder substitution at sync time | `template` | **adapt** | The idea (source as template, values filled per target) is right; the implementation (full Jinja2) is wrong for a PyYAML-only tool. Adapt as trivial `${var}`/`str.format` substitution from a per-target `vars:` mapping — enough for `${project_name}`, `${year}`, `${rights_holder}` in license blocks and stub docs, without a template-language dependency or debugging surface. Full Jinja2: **out**. |
| A "distributed by file-fairy" banner | `template` (`ansible_managed`) | **adopt** | Ansible stamps managed files with an `ansible_managed` comment. The fairy equivalent — "this file is distributed from sat-doc-automa by file-fairy; edit there, not here" — is cheap, composes with managed blocks and templating, and directly enforces the canonical-source charter at the point where a human is about to hand-edit the wrong copy. Opt-in per group (a comment line is not welcome in every file type). |
| Single-line edits by regex | `lineinfile` | **defer** | Powerful and dangerous: idempotence burden falls on the operator's regex, failure mode is silent duplication or wrong-line replacement. Nearly every fairy use case is better served by a managed block. Revisit only if a concrete need survives contact with `blockinfile`. |
| Regex find-and-replace across a file | `replace` | **defer** | Same posture as `lineinfile`, same reason. Useful someday for mechanical migrations ("rename this term across all targets"), but that is a migration tool, not a sync policy; a one-off script serves better today. |
| Assemble file from fragment directory | `assemble` | **defer** | Attractive for composing docs from license block + body + changelog, but it inverts the current model (many sources → one dest) and overlaps with SAT's own content pipeline (ingress/egress/transmog), which is the more likely owner of composition. Record and stand aside. |
| Archive extraction | `unarchive` | **out** | Release/install tooling territory, already owned by the self-update-via-release-archive decision in the tool repos. |

### Axis 3 — Reconciliation and safety

| Candidate | From | Class | Rationale |
| --- | --- | --- | --- |
| `mirror` / `seed_if_missing` / `overwrite` / `reference_only` | *(fairy's own)* | *(decided)* | Per the sync-policy decision record. Notably, Ansible's `copy` with `force: false` — "transfer only if destination doesn't exist" — is exactly `seed_if_missing`: independent precedent that the vocabulary carves reality at a real joint. The fairy's `mirror` (protect local drift) is the one mode Ansible *lacks*, and remains its distinctive value. |
| Backup before overwrite | `copy`/`template` (backup) | **adopt** | Timestamped `dest.~fairy-backup~` (name TBD in step three) before any `overwrite` or `--force` write. Cheap insurance that makes the aggressive modes much easier to trust. Arguably git already provides this — but only for committed state; the backup covers the uncommitted-local-edit case, which is precisely the case `--force` clobbers. |
| Validate hook before finalizing | `copy`/`template` (validate) | **adopt (small)** | Write to a temp file, run a declared command with `%s`, only move into place on exit 0 — e.g. `python -m py_compile %s` for distributed scripts, a YAML parse for manifests. Atomic-replace via tempfile-and-rename (Ansible's underlying mechanism, cf. `tempfile`) comes along naturally and is worth having regardless. |
| Plan/check and diff mode | Ansible `--check --diff` | *(exists / adopt diff)* | `plan` already is check mode. The missing half is **diff**: show the actual content difference for `update`/`conflict` items, not just the status word. High value for deciding whether a conflict deserves `--force`. |
| Checksum verification of the copy | `copy` (checksum) | *(exists)* | The state file's post-copy sha256 already serves this. |
| Prune (delete dest files absent from source) | `copy`/`synchronize`-adjacent | *(decided)* | Manifest-declared only, per the sync-policy decision. Listed for completeness. |

### Axis 4 — Attributes

| Candidate | From | Class | Rationale |
| --- | --- | --- | --- |
| Executable bit | `file`/`copy` (mode) | **adopt — the one survivor** | The single permission git actually tracks, and the fairy distributes scripts (`bump-version.py`, `cut-release.py`) that must arrive executable. `mode: preserve` semantics — carry the source's executable bit — is likely the whole feature. |
| General modes (0644 etc.) | `file` (mode) | **out** | Not carried by git; umask on checkout decides. Distributing it is a false promise. |
| Owner / group | `file` (owner, group) | **out** | Single-operator machine; git does not track; meaningless downstream. |
| Timestamps | `file` (access/modification_time) | **out** | Not stable across clone/checkout; nothing in the SAT toolchain keys on mtime. |
| SELinux context, chattr attributes, unsafe_writes | `file`/`copy` | **out** | Config-management concerns for live systems; no expression in a git repo. |

### Axis 5 (new) — Discovery and inspection

The survey surfaced a fifth axis the four-axes model lacked: how items
*enter* the plan at all. Today every item is enumerated by hand.

| Candidate | From | Class | Rationale |
| --- | --- | --- | --- |
| Glob/pattern item sets | `find` (paths, patterns, excludes, recurse) | **adapt** | `source_glob: "en/docs/automa/licenses/*.md"` with excludes turns N hand-maintained items into one declaration and is the enabler for directory-level sync and prune (the pruning set is "what the glob matched last time vs now"). The main step-three question it raises: matched-set changes must surface in `plan` so a glob never silently widens. |
| Rich status inspection | `stat` | **adapt (into status output)** | Not a feature, an ingredient: `status` output enriched per item with exists/size/checksum-short/region-drift, in service of the diff feature above. |
| Read file into memory | `slurp`/`fetch` | **out** | Remote-host machinery; the fairy reads files directly. |

## Summary of proposed classifications

**Adopt:** `absent` (retraction), `directory`, `touch`, inline
`content:`, managed-source banner, backup-before-overwrite, validate
hook with atomic replace, diff in plan/status, executable-bit
preservation.

**Adapt:** managed blocks (`blockinfile` semantics — the standout),
lightweight `${var}` substitution (not Jinja2), glob item sets with
excludes, stat-enriched status.

**Defer (recorded, not accidental):** symlinks, `lineinfile`, `replace`,
`assemble`.

**Out (deliberate):** hard links, full Jinja2, general modes,
owner/group, timestamps, SELinux/chattr/unsafe_writes, remote-anything
(`remote_src`, `fetch`, `slurp`), `unarchive`.

## What this analysis does not do

It does not design manifest syntax, key names, or grouping — that is
step three, taken after the adopt/adapt list above is confirmed or
amended. It also does not sequence implementation; a plausible ordering
(managed blocks and `absent` first, discovery last) is visible in the
rationale but is not decided here.

## See also

- `decision--file-fairy-manifest-declared-sync-policy-v0-1-0.md`, the
  reconciliation-axis decision this analysis builds on.
- `sat-doc-automa/en/docs/decisions/devops/decision--gh-cli-for-release-asset-publishing-v0-1-0.md`,
  for the cross-platform concern pattern reused here.
- `sat-doc-automa/en/docs/automa/licenses/license-block--*.md`, the
  artifacts the managed-block candidate directly serves.
- Ansible module references: `ansible.builtin.file`, `copy`, `template`,
  `lineinfile`, `blockinfile`, `replace`, `assemble`, `find`, `stat`
  (docs.ansible.com, retrieved 2026-08-02).

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Draft | Initial survey and classification: 9 adopt, 4 adapt, 4 defer, and a deliberate out-of-scope list, organized across four axes plus a newly identified discovery axis. |
