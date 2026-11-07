#!/usr/bin/env python3
"""Add completion specs to Figxit while preserving the installed bundled specs."""
import argparse
import json
import os
import plistlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(app, destination, extra_specs=()):
    bundle = app / "Contents/Resources/specs"
    if not (bundle / "index.js").is_file():
        raise ValueError(f"Figxit bundled specs not found: {bundle}")
    custom = destination / "custom"
    overlay = destination / "specs"
    custom.mkdir(parents=True, exist_ok=True)
    overlay.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "acloud.js", custom / "acloud.js")
    for source in extra_specs:
        for item in source.iterdir():
            if item.name in ("index.js", "package.json"):
                continue
            target = custom / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    for source in (bundle, custom):
        for item in source.iterdir():
            if item.name in ("index.js", "package.json"):
                continue
            target = overlay / item.name
            if target.is_symlink():
                target.unlink()
            if target.exists():
                raise ValueError(f"Refusing to replace an unmanaged file: {target}")
            target.symlink_to(item, target_is_directory=item.is_dir())
    names = sorted(p.relative_to(custom).with_suffix("").as_posix() for p in custom.rglob("*.js"))
    (overlay / "package.json").write_text('{"type":"module"}\n')
    (overlay / "index.js").write_text(
        f"import bundled from {json.dumps((bundle / 'index.js').as_uri())};\n"
        f"export default [...new Set([...bundled, ...{json.dumps(names)}])];\n")
    return overlay


def activate(app, overlay):
    label = "local.figxit.custom-specs"
    uid = os.getuid()
    plist = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    plist.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"], capture_output=True)
    subprocess.run([str(app / "Contents/MacOS/figxit-engine"), "stop"], check=True)
    plist.write_bytes(plistlib.dumps({
        "Label": label,
        "ProgramArguments": ["/usr/bin/open", "-g", "-a", str(app), "--env", "FIGXIT_SPECS=" + str(overlay)],
        "RunAtLoad": True,
    }))
    subprocess.run(["launchctl", "setenv", "FIGXIT_SPECS", str(overlay)], check=True)
    subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, default=Path("/Applications/Figxit.app"))
    parser.add_argument("--destination", type=Path, default=Path.home() / "Library/Application Support/figxit-custom")
    parser.add_argument("--extra-specs", type=Path, action="append", default=[])
    parser.add_argument("--activate", action="store_true", help="Restart Figxit and launch it with the custom specs at login")
    args = parser.parse_args()
    overlay = install(args.app.resolve(), args.destination.resolve(), [p.resolve() for p in args.extra_specs])
    print(f"FIGXIT_SPECS={overlay}")
    if args.activate:
        activate(args.app.resolve(), overlay)
