#!/usr/bin/env python3
# test_file_fairy.py
"""
test_file_fairy.py, offline test suite for file_fairy.py's sync modes.

Builds scratch source and target trees with a generated manifest and
exercises every sync_mode from decision--file-fairy-manifest-declared-
sync-policy: mirror's three-way protection, seed_if_missing's
existence-keyed planting, overwrite's no-vote semantics, reference_only
at group and item level, the --force one-off override, and the unknown-
mode refusal.

Usage:
    python3 test_file_fairy.py

Exit 0 with a PASS line per check, or exit 1 at the first failure.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "file_fairy.py"

PASSED = 0


def ok(name):
    global PASSED
    PASSED += 1
    print(f"  PASS  {name}")


def check(cond, name, detail=""):
    if not cond:
        print(f"  FAIL  {name}\n{detail}", file=sys.stderr)
        sys.exit(1)
    ok(name)


def write_manifest(root, source, target, groups_yaml):
    m = root / "manifest.yaml"
    m.write_text(
        f'local_source_repo_path: "{source}"\n'
        f'local_target_repo_path: "{target}"\n'
        f"groups:\n{groups_yaml}")
    return m


def ff(manifest, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "apply", str(manifest),
         "--yes", *extra],
        capture_output=True, text=True)


def ff_plan(manifest):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "plan", str(manifest)],
        capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "source"
        target = root / "target"
        for d in (source, target):
            d.mkdir()

        (source / "mirrored.md").write_text("mirrored v1\n")
        (source / "seeded.md").write_text("seed content\n")
        (source / "owned.md").write_text("owned v1\n")
        (source / "cited.md").write_text("cited\n")

        manifest = write_manifest(root, source, target, """\
  conventions:
    items:
      - source: mirrored.md
        dest: mirrored.md
      - source: seeded.md
        dest: seeded.md
        sync_mode: seed_if_missing
      - source: owned.md
        dest: owned.md
        sync_mode: overwrite
      - source: cited.md
        dest: cited.md
        sync_mode: reference_only
""")

        # ── First apply: mirror, seed, overwrite all plant; cited never ──
        r = ff(manifest)
        check(r.returncode == 0, "first apply exits 0", r.stderr)
        check((target / "mirrored.md").read_text() == "mirrored v1\n"
              and (target / "seeded.md").read_text() == "seed content\n"
              and (target / "owned.md").read_text() == "owned v1\n",
              "mirror, seed_if_missing, and overwrite items are planted")
        check(not (target / "cited.md").exists(),
              "reference_only item is never touched")

        # ── seed_if_missing: target owns it from now on ──
        (target / "seeded.md").write_text("the target's own version\n")
        (source / "seeded.md").write_text("seed content v2\n")
        r = ff(manifest)
        check(r.returncode == 0, "apply after seed edit exits 0", r.stderr)
        check((target / "seeded.md").read_text()
              == "the target's own version\n",
              "seed_if_missing leaves the target's edit alone, even "
              "with a changed source")
        p = ff_plan(manifest)
        check("present" in p.stdout,
              "plan reports the seeded item as present")

        # ── mirror: local edit is protected, --force overrides once ──
        (target / "mirrored.md").write_text("local hand-edit\n")
        (source / "mirrored.md").write_text("mirrored v2\n")
        r = ff(manifest)
        check(r.returncode == 0 and "conflict" in (r.stdout + r.stderr)
              and (target / "mirrored.md").read_text()
              == "local hand-edit\n",
              "mirror conflict is reported and the local edit survives")
        check("sync_mode: overwrite" in (r.stdout + r.stderr),
              "conflict message points at the standing alternative")
        r = ff(manifest, "--force")
        check((target / "mirrored.md").read_text() == "mirrored v2\n",
              "--force overwrites the mirror conflict this run",
              r.stderr)

        # ── overwrite: the target never gets a vote, no force needed ──
        (target / "owned.md").write_text("target tries an edit\n")
        r = ff(manifest)
        check(r.returncode == 0
              and (target / "owned.md").read_text() == "owned v1\n",
              "overwrite reclaims a local edit without --force",
              r.stderr)

        # ── seed_if_missing on first contact with a pre-existing file ──
        source2 = root / "s2"
        target2 = root / "t2"
        source2.mkdir()
        target2.mkdir()
        (source2 / "VERSION").write_text("9.9.9\n")
        (target2 / "VERSION").write_text("0.1.0\n")
        m2 = write_manifest(root, source2, target2, """\
  scaffolding:
    sync_mode: seed_if_missing
    items:
      - source: VERSION
        dest: VERSION
""")
        r = ff(m2)
        check(r.returncode == 0
              and (target2 / "VERSION").read_text() == "0.1.0\n",
              "first-ever apply never clobbers a pre-existing "
              "seed_if_missing target (the VERSION case)")

        # ── group-level mode inheritance and item override ──
        source3 = root / "s3"
        target3 = root / "t3"
        source3.mkdir()
        target3.mkdir()
        (source3 / "a.md").write_text("a\n")
        (source3 / "b.md").write_text("b\n")
        m3 = write_manifest(root, source3, target3, """\
  styles:
    sync_mode: overwrite
    items:
      - source: a.md
        dest: a.md
      - source: b.md
        dest: b.md
        sync_mode: reference_only
""")
        r = ff(m3)
        check(r.returncode == 0 and (target3 / "a.md").is_file()
              and not (target3 / "b.md").exists(),
              "group mode inherits; item-level reference_only overrides")

        # ── unknown sync_mode refuses ──
        m4 = write_manifest(root, source3, target3, """\
  broken:
    sync_mode: yolo
    items:
      - source: a.md
        dest: a.md
""")
        r = ff(m4)
        check(r.returncode != 0 and "unknown sync_mode" in r.stderr
              and "yolo" in r.stderr,
              "unknown sync_mode is a manifest error, not a default")

    print(f"\n[test-file-fairy] {PASSED} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
