#!/usr/bin/env python3
"""install-ff.py -- manage file-fairy in user-space, OSAT Fluent style.

Installs the version in this checkout (see VERSION) into a versioned
directory with its own virtual environment, and renders `ff` and
`file-fairy` wrappers so the fairy runs from anywhere. Same shape as
osat-manager-slugify's install-slug.py and osat-fluent-python-tool.

Layout (Linux, macOS):
  source   ~/.local/share/file-fairy/<version>/src/     (snapshot of this checkout)
  venv     ~/.local/share/file-fairy/<version>/.venv/
  wrappers ~/.local/bin/ff, ~/.local/bin/file-fairy

Layout (Windows):
  source   %LOCALAPPDATA%\\file-fairy\\<version>\\src\\
  venv     %LOCALAPPDATA%\\file-fairy\\<version>\\.venv\\
  wrappers %LOCALAPPDATA%\\Programs\\ff.cmd, file-fairy.cmd

XDG_DATA_HOME and XDG_BIN_HOME are honoured when set.

The install is a snapshot, not editable: pulling or editing the checkout
changes nothing until you run --install again. The venv is built with the
interpreter running this script, for example a python-tool install:
  python3.12 install-ff.py --install

Usage:
  install-ff.py --install          Install this checkout's version and point the wrappers at it
  install-ff.py --switch VERSION   Point the wrappers at another installed version
  install-ff.py --status           Show installed and active versions
  install-ff.py --remove VERSION   Remove an installed version (not the active one)
  install-ff.py --version          Show this manager's version

Requires Python 3.8+ (standard library only) to run the manager itself.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
TOOL_NAME = "file-fairy"
COMMANDS = ("ff", "file-fairy")
SOURCE_FILES = ("file_fairy.py", "pyproject.toml", "README.md", "VERSION")
MIN_PYTHON = (3, 8)


class InstallError(RuntimeError):
    """Raised for any condition that should stop the manager with a clear message."""


def log(message: str) -> None:
    print(f"[install-ff] {message}")


def fail(message: str) -> None:
    raise InstallError(message)


def manager_version() -> str:
    try:
        return (REPO_DIR / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        fail(f"VERSION file missing at {REPO_DIR / 'VERSION'} (repo checkout is incomplete)")


def refuse_root() -> None:
    if os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() == 0:
        fail(f"refusing to run as root. {TOOL_NAME} installs entirely in user-space under $HOME.")
    if os.name == "nt":
        try:
            import ctypes

            if ctypes.windll.shell32.IsUserAnAdmin():
                fail(f"refusing to run as Administrator. {TOOL_NAME} installs entirely in user-space under %LOCALAPPDATA%.")
        except InstallError:
            raise
        except Exception:
            pass


class Paths:
    def __init__(self) -> None:
        self.is_windows = os.name == "nt"
        home = Path.home()
        if self.is_windows:
            local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
            self.bin_dir = local / "Programs"
            self.tool_root = local / TOOL_NAME
        else:
            self.bin_dir = Path(os.environ.get("XDG_BIN_HOME", home / ".local" / "bin"))
            self.tool_root = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / TOOL_NAME

    def wrapper(self, command: str) -> Path:
        return self.bin_dir / (f"{command}.cmd" if self.is_windows else command)

    def version_dir(self, version: str) -> Path:
        return self.tool_root / version

    def src_dir(self, version: str) -> Path:
        return self.version_dir(version) / "src"

    def venv_bin(self, version: str) -> Path:
        venv = self.version_dir(version) / ".venv"
        return venv / "Scripts" if self.is_windows else venv / "bin"

    def venv_python(self, version: str) -> Path:
        return self.venv_bin(version) / ("python.exe" if self.is_windows else "python")

    def entry_point(self, version: str, command: str) -> Path:
        return self.venv_bin(version) / (f"{command}.exe" if self.is_windows else command)

    def installed_versions(self) -> list:
        if not self.tool_root.is_dir():
            return []
        return sorted(p.name for p in self.tool_root.iterdir() if p.is_dir())

    def active_version(self):
        """Version the `ff` wrapper currently points at, or None."""
        try:
            content = self.wrapper(COMMANDS[0]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        for version in self.installed_versions():
            if str(self.version_dir(version)) + os.sep in content:
                return version
        return None


def make_owner_only(root: Path) -> None:
    if os.name == "nt":
        return
    for path in [root, *root.rglob("*")]:
        if path.is_symlink():
            continue
        try:
            if path.is_dir():
                path.chmod(stat.S_IRWXU)
            else:
                mode = stat.S_IRUSR | stat.S_IWUSR
                if os.access(path, os.X_OK):
                    mode |= stat.S_IXUSR
                path.chmod(mode)
        except OSError:
            continue


def run(cmd: list) -> None:
    result = subprocess.run([str(c) for c in cmd])
    if result.returncode != 0:
        fail(f"command failed ({result.returncode}): {' '.join(str(c) for c in cmd)}")


def render_wrappers(paths: Paths, version: str) -> list:
    template_path = REPO_DIR / "scripts" / ("windows/ff-wrapper.cmd" if paths.is_windows else "nix/ff-wrapper")
    if not template_path.exists():
        fail(f"wrapper template missing: {template_path} (repo checkout is incomplete)")
    template = template_path.read_text(encoding="utf-8")
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    newline = "\r\n" if paths.is_windows else "\n"
    written = []
    for command in COMMANDS:
        target = paths.entry_point(version, command)
        if not target.exists():
            fail(f"entry point missing after install: {target}")
        wrapper = paths.wrapper(command)
        with open(wrapper, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(template.format(target=target))
        if not paths.is_windows:
            wrapper.chmod(stat.S_IRWXU)
        written.append(wrapper)
    return written


def warn_environment(paths: Paths) -> None:
    separator = ";" if paths.is_windows else ":"
    on_path = [Path(p) for p in os.environ.get("PATH", "").split(separator) if p]
    if paths.bin_dir not in on_path:
        log(f"warning: {paths.bin_dir} is not on PATH. Add it to run 'ff' from anywhere.")
        return
    for command in COMMANDS:
        found = shutil.which(command)
        if found and Path(found).resolve() != paths.wrapper(command).resolve():
            log(f"warning: '{command}' resolves to {found}, which shadows {paths.wrapper(command)}.")
    if os.environ.get("VIRTUAL_ENV"):
        log("note: a virtual environment is active; its own 'ff', if any, wins until you deactivate it.")


def do_install(paths: Paths, force: bool) -> int:
    if sys.version_info < MIN_PYTHON:
        fail(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required to build the venv; running {sys.version.split()[0]}")
    version = manager_version()
    version_dir = paths.version_dir(version)

    if version_dir.exists() and not force:
        if paths.active_version() == version and paths.entry_point(version, COMMANDS[0]).exists():
            log(f"{version} is already installed and active. Pass --force to reinstall.")
            return 0
    if version_dir.exists():
        log(f"removing existing install at {version_dir}...")
        shutil.rmtree(version_dir)

    # Snapshot the sources first so the build never writes build/ or
    # *.egg-info into the checkout, and the install can't drift from it.
    src = paths.src_dir(version)
    src.mkdir(parents=True)
    for name in SOURCE_FILES:
        source = REPO_DIR / name
        if not source.exists():
            fail(f"{source} missing (repo checkout is incomplete)")
        shutil.copy2(source, src / name)

    log(f"creating venv with {sys.executable} (Python {sys.version.split()[0]})...")
    run([sys.executable, "-m", "venv", "--prompt", f"{TOOL_NAME}-{version}", version_dir / ".venv"])
    log("installing file-fairy and its dependencies...")
    run([paths.venv_python(version), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", src])

    make_owner_only(version_dir)
    for wrapper in render_wrappers(paths, version):
        log(f"wrapper installed: {wrapper} -> {version}")
    warn_environment(paths)
    log("done. Try: ff --help")
    return 0


def do_switch(paths: Paths, version: str) -> int:
    if not paths.entry_point(version, COMMANDS[0]).exists():
        fail(f"{version} is not installed. Installed: {', '.join(paths.installed_versions()) or '(none)'}")
    render_wrappers(paths, version)
    log(f"active version is now {version}")
    return 0


def do_status(paths: Paths) -> int:
    active = paths.active_version()
    installed = paths.installed_versions()
    log(f"manager version: {manager_version()}")
    log(f"install root:    {paths.tool_root}")
    for command in COMMANDS:
        wrapper = paths.wrapper(command)
        log(f"wrapper:         {wrapper}{'' if wrapper.exists() else ' (missing)'}")
    if not installed:
        log("installed:       (none)")
    for version in installed:
        log(f"installed:       {version}{'  (active)' if version == active else ''}")
    return 0


def do_remove(paths: Paths, version: str) -> int:
    if version not in paths.installed_versions():
        fail(f"{version} is not installed.")
    if version == paths.active_version():
        fail(f"{version} is active. Switch to another version first, or remove the wrappers in {paths.bin_dir} by hand.")
    shutil.rmtree(paths.version_dir(version))
    log(f"removed {version}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage file-fairy (ff) in user-space.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="install this checkout's version and activate it")
    group.add_argument("--switch", metavar="VERSION", help="point the wrappers at an installed version")
    group.add_argument("--status", action="store_true", help="show installed and active versions")
    group.add_argument("--remove", metavar="VERSION", help="remove an installed, inactive version")
    group.add_argument("--version", action="store_true", help="show this manager's version")
    parser.add_argument("--force", action="store_true", help="with --install, reinstall even if already current")
    args = parser.parse_args()

    try:
        if args.version:
            print(manager_version())
            return 0
        refuse_root()
        paths = Paths()
        if args.install:
            return do_install(paths, args.force)
        if args.switch:
            return do_switch(paths, args.switch)
        if args.status:
            return do_status(paths)
        return do_remove(paths, args.remove)
    except InstallError as exc:
        print(f"[install-ff] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
