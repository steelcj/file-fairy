#!/usr/bin/env python3
# file_fairy.py
"""
file-fairy — Config-driven file sync CLI.

Copies named groups of files from a source project to a target project on
local disk, driven by a YAML manifest, with plan/apply/status verbs and
checksum-based drift tracking.

Usage:
    file-fairy MANIFEST.yaml              apply (plan shown, confirm, sync)
    file-fairy apply  MANIFEST.yaml [--yes] [--force]
    file-fairy plan   MANIFEST.yaml       show what would change; no writes
    file-fairy status MANIFEST.yaml       alias for plan

Also installed as `ff`, so the common case is:

    ff osat-fluent-sync-manifest.yaml

Manifest shape (see osat-fluent-sync-manifest.yaml for a worked example):

    local_source_repo_path: "~/path/to/source"
    local_target_repo_path: "~/path/to/target"
    groups:
      <group-name>:
        sync_mode: mirror           # optional; group default, see below
        items:
          - source: relative/path/in/source.md
            dest: relative/path/in/target.md
          - source: relative/path/in/source_2.md
            dest: relative/path/in/target_2.md
            sync_mode: seed_if_missing   # optional; overrides the group
          - source: null            # items with no source are informational
            dest: SOME/FILE.md      # only; file-fairy never touches them
          - state: absent           # manifest-declared retraction: delete
            dest: old/path.md       # this path in the target if present

Sync modes, per decision--file-fairy-manifest-declared-sync-policy:
declared in the manifest at group level (inherited) or item level
(overrides the group). Absent means mirror.

    mirror          create if missing, overwrite when the source changed,
                    protect a local hand-edit (conflict, skipped unless
                    apply is run with --force)
    seed_if_missing create if the dest path is missing, otherwise leave
                    the target's copy alone regardless of content
    overwrite       the target never gets a vote; create or overwrite,
                    local edits included, no conflict state
    reference_only  declared but never touched (group or item level)

The state key, per decision--manifest-organization-one-key-per-axis:
state declares what a path should BE (file, the default, or absent).
state: absent needs no source; if the dest exists in the target it is
retracted (deleted) at apply, shown in the plan's own RETRACT section
first. Retraction is manifest-declared intent, never a CLI flag, per
the sync-policy decision. Other state values from the design (directory,
touch) are scheduled, not yet implemented, and are refused by name.

State file: a per-target-repo YAML file, default
<local_target_repo_path>/.file-fairy-state.yaml, recording, per dest path,
the source and dest checksums as of the last successful apply. This is
what makes plan/status cheap and lets file-fairy tell "source changed
upstream" apart from "target changed locally" (a mirror conflict). The
--force flag is a one-off interactive override for mirror conflicts only;
the standing declaration "always take source" belongs in the manifest as
sync_mode: overwrite, where it is reviewable in a diff.

Deliberately not implemented: any path-containment guard on dest. The
manifest is a config file the operator authors themselves, not adversarial
input, so it is trusted and executed as written, consistent with the
2026-07-29 design discussion. Checksums exist for drift detection, not
for safety.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

STATE_FILENAME = ".file-fairy-state.yaml"

SYNC_MODES = ("mirror", "seed_if_missing", "overwrite", "reference_only")

STATES = ("file", "absent")
SCHEDULED_STATES = ("directory", "touch")


# ── Small helpers ────────────────────────────────────────────────────────────

def log(message: str) -> None:
    print(f"[file-fairy] {message}")


def fail(message: str) -> None:
    print(f"[file-fairy ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def expand(path_str: str) -> Path:
    return Path(path_str).expanduser()


# ── Manifest and state ──────────────────────────────────────────────────────

def load_manifest(manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        fail(f"manifest not found: {manifest_path}")
    with manifest_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for required in ("local_source_repo_path", "local_target_repo_path", "groups"):
        if required not in data:
            fail(f"manifest is missing required key: {required}")
    return data


def load_state(state_path: Path) -> dict:
    if not state_path.is_file():
        return {"synced": {}}
    with state_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {"synced": {}}


def save_state(state_path: Path, state: dict) -> None:
    with state_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(state, f, sort_keys=False)


# ── Planning ─────────────────────────────────────────────────────────────────

def effective_mode(group: dict, item: dict, group_name: str) -> str:
    """The item's sync_mode, falling back to the group's, defaulting to
    mirror. An unknown value is a manifest error, not a silent default."""
    mode = item.get("sync_mode", group.get("sync_mode", "mirror"))
    if mode not in SYNC_MODES:
        fail(f"unknown sync_mode {mode!r} in group {group_name!r}; "
             f"valid modes: {', '.join(SYNC_MODES)}")
    return mode


def effective_state(item: dict, group_name: str) -> str:
    """The item's state, defaulting to file. Scheduled-but-unimplemented
    states are refused by name; unknown states are a manifest error."""
    state = item.get("state", "file")
    if state in SCHEDULED_STATES:
        fail(f"state {state!r} in group {group_name!r} is scheduled but "
             f"not yet implemented (see the manifest-organization "
             f"decision's implementation order)")
    if state not in STATES:
        fail(f"unknown state {state!r} in group {group_name!r}; "
             f"valid states: {', '.join(STATES)}")
    return state


def iter_syncable_items(manifest: dict):
    """Yield (group_name, item, mode, state) for every item the plan
    should consider: skips reference_only groups and items, and file
    items with no source (informational only). Absent items need no
    source; their declaration is the whole instruction."""
    for group_name, group in manifest["groups"].items():
        for item in group.get("items", []):
            mode = effective_mode(group, item, group_name)
            if mode == "reference_only":
                continue
            state = effective_state(item, group_name)
            if state == "file" and item.get("source") is None:
                continue
            yield group_name, item, mode, state


def build_plan(manifest: dict, state: dict) -> list[dict]:
    """Return a list of per-item plan entries with a computed status:
    new, update, unchanged, present, conflict, or missing-source. The
    status a path can reach depends on its sync_mode; only mirror items
    can be in conflict."""
    source_root = expand(manifest["local_source_repo_path"])
    target_root = expand(manifest["local_target_repo_path"])
    synced = state.get("synced", {})

    plan = []
    for group_name, item, mode, state in iter_syncable_items(manifest):
        dest_path = target_root / item["dest"]

        if state == "absent":
            # Manifest-declared retraction: existence-keyed, blind to
            # sync_mode and to the state file, per ruling 3 of the
            # manifest-organization decision.
            plan.append({
                "group": group_name,
                "source": item.get("source"),
                "dest": item["dest"],
                "dest_path": dest_path,
                "mode": mode,
                "status": "retract" if dest_path.is_file() else "retired",
            })
            continue

        source_path = source_root / item["source"]
        entry = {
            "group": group_name,
            "source": item["source"],
            "dest": item["dest"],
            "source_path": source_path,
            "dest_path": dest_path,
            "mode": mode,
        }

        if not source_path.is_file():
            entry["status"] = "missing-source"
            plan.append(entry)
            continue

        current_source_sha = sha256_of(source_path)
        entry["current_source_sha"] = current_source_sha
        dest_exists = dest_path.is_file()

        if mode == "seed_if_missing":
            # Existence-keyed, deliberately blind to the state file and
            # to content: plant it once when absent, then it is the
            # target's own, per the sync-policy decision.
            entry["status"] = "present" if dest_exists else "new"
            plan.append(entry)
            continue

        if mode == "overwrite":
            # Content-keyed against the source alone; local edits are
            # not protected and no conflict state exists in this mode.
            if not dest_exists:
                entry["status"] = "new"
            elif sha256_of(dest_path) != current_source_sha:
                entry["status"] = "update"
            else:
                entry["status"] = "unchanged"
            plan.append(entry)
            continue

        # mirror, the default: state-keyed three-way logic.
        record = synced.get(item["dest"])
        if record is None:
            entry["status"] = "new"
        else:
            dest_drifted = (
                dest_exists
                and sha256_of(dest_path) != record.get("dest_sha256")
            )
            source_changed = current_source_sha != record.get("source_sha256")

            if dest_drifted:
                entry["status"] = "conflict"
            elif not dest_exists:
                entry["status"] = "new"
            elif source_changed:
                entry["status"] = "update"
            else:
                entry["status"] = "unchanged"

        plan.append(entry)

    return plan


def print_plan(plan: list[dict]) -> None:
    if not plan:
        log("nothing to do: no syncable items in the manifest")
        return
    by_status: dict[str, list[dict]] = {}
    for entry in plan:
        by_status.setdefault(entry["status"], []).append(entry)

    order = ["retract", "conflict", "missing-source", "new", "update",
             "present", "retired", "unchanged"]
    labels = {
        "retract": "RETRACT  (declared absent; will be deleted)",
        "conflict": "CONFLICT  (target changed locally since last sync)",
        "missing-source": "MISSING SOURCE  (file does not exist upstream)",
        "new": "NEW  (not yet synced)",
        "update": "UPDATE  (source changed since last sync)",
        "present": "present  (seed_if_missing; the target owns it)",
        "retired": "retired  (declared absent; already gone)",
        "unchanged": "unchanged",
    }
    for status in order:
        entries = by_status.get(status)
        if not entries:
            continue
        print(f"\n{labels[status]}")
        for e in entries:
            if status in ("retract", "retired"):
                print(f"  [{e['group']}] {e['dest']}")
            else:
                print(f"  [{e['group']}] {e['source']} -> {e['dest']}")

    total_action = sum(
        len(by_status.get(s, [])) for s in ("new", "update")
    )
    n_conflict = len(by_status.get("conflict", []))
    n_missing = len(by_status.get("missing-source", []))
    n_retract = len(by_status.get("retract", []))
    print()
    log(f"{total_action} item(s) would be synced, "
        f"{n_retract} retraction(s), "
        f"{n_conflict} conflict(s), {n_missing} missing source(s)")


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_plan(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    target_root = expand(manifest["local_target_repo_path"])
    state = load_state(target_root / STATE_FILENAME)
    plan = build_plan(manifest, state)
    print_plan(plan)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    # Same computation as plan; status is the read-only framing of it.
    return cmd_plan(args)


def cmd_apply(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.manifest))
    target_root = expand(manifest["local_target_repo_path"])
    state_path = target_root / STATE_FILENAME
    state = load_state(state_path)
    plan = build_plan(manifest, state)

    actionable = [e for e in plan if e["status"] in ("new", "update")]
    retractions = [e for e in plan if e["status"] == "retract"]
    conflicts = [e for e in plan if e["status"] == "conflict"]
    missing = [e for e in plan if e["status"] == "missing-source"]

    if missing:
        log(f"{len(missing)} item(s) have no source file; skipping them:")
        for e in missing:
            print(f"  [{e['group']}] {e['source']} (not found)")

    if conflicts and not args.force:
        log(f"{len(conflicts)} mirror item(s) are in conflict and will be "
            f"skipped (target changed locally since last sync). Resolve "
            f"by hand, or overwrite just this once with --force; if the "
            f"target should never keep local edits, declare "
            f"sync_mode: overwrite in the manifest instead:")
        for e in conflicts:
            print(f"  [{e['group']}] {e['dest']}")

    if args.force:
        actionable = actionable + conflicts

    if not actionable and not retractions:
        log("nothing to apply")
        return 0

    if not args.yes:
        print()
        print_plan([e for e in plan
                    if e["status"] in ("new", "update", "retract")]
                    + (conflicts if args.force else []))
        answer = input("\nApply the above? [y/N] ").strip().lower()
        if answer != "y":
            log("aborted, nothing written")
            return 1

    synced = state.setdefault("synced", {})
    for entry in actionable:
        dest_path = entry["dest_path"]
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(entry["source_path"], dest_path)
        synced[entry["dest"]] = {
            "source_sha256": entry["current_source_sha"],
            "dest_sha256": sha256_of(dest_path),
            "synced_at": datetime.now(timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "group": entry["group"],
            "source": entry["source"],
        }
        print(f"  synced: {entry['source']} -> {entry['dest']}")

    for entry in retractions:
        entry["dest_path"].unlink()
        synced.pop(entry["dest"], None)
        print(f"  retracted: {entry['dest']}")

    save_state(state_path, state)
    log(f"{len(actionable)} item(s) synced, "
        f"{len(retractions)} retracted; state written to {state_path}")
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    # A bare `ff manifest.yaml`, no subcommand, means "apply". Rewrite argv
    # so the common case is a single argument, without complicating the
    # subparser definitions below.
    argv = sys.argv[1:]
    known = {"plan", "status", "apply", "-h", "--help"}
    if argv and argv[0] not in known:
        argv = ["apply", *argv]

    parser = argparse.ArgumentParser(
        prog="file-fairy",
        description="Config-driven file sync CLI with plan/apply/status "
                     "and checksum-based drift tracking. Also installed "
                     "as `ff`.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="Show what would change; no writes.")
    p_plan.add_argument("manifest", metavar="MANIFEST")
    p_plan.set_defaults(func=cmd_plan)

    p_status = sub.add_parser("status", help="Alias for plan.")
    p_status.add_argument("manifest", metavar="MANIFEST")
    p_status.set_defaults(func=cmd_status)

    p_apply = sub.add_parser("apply", help="Copy new/updated items "
                              "(default when no subcommand is given).")
    p_apply.add_argument("manifest", metavar="MANIFEST")
    p_apply.add_argument("--yes", action="store_true",
                          help="Skip the confirmation prompt.")
    p_apply.add_argument("--force", action="store_true",
                          help="One-off override for mirror items in "
                               "conflict: overwrite them this run. The "
                               "standing form of this intent is "
                               "sync_mode: overwrite in the manifest.")
    p_apply.set_defaults(func=cmd_apply)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
