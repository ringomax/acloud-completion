#!/usr/bin/env python3
"""Generate a Fig specification using acloud's offline command documentation."""
import argparse
import itertools
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def invoke(executable, *args):
    return subprocess.check_output([executable, *args], text=True)


def collect(executable):
    help_text = invoke(executable, "--help")
    groups = sorted(set(re.findall(r"^  acloud ([a-z][\w-]*)", help_text, re.M)))
    commands = set()
    for group in groups:
        matches = json.loads(invoke(executable, "cli", "search", group, "--limit", "50"))
        found = {m["command"] for m in matches
                 if (m["command"] == f"acloud {group}" or m["command"].startswith(f"acloud {group} "))
                 and not m["command"].startswith("acloud api call ")}
        if len(found) >= 50:
            raise ValueError(f"Search results truncated for {group}; extend command discovery")
        commands.update(found)
    # Include documented aliases and detect commands lost to search result limits.
    for line in help_text.splitlines():
        if not line.startswith("  acloud "):
            continue
        words = []
        for word in line.strip().split()[1:]:
            if not re.fullmatch(r"[a-z][a-z-]*(?:\|[a-z][a-z-]*)*", word):
                break
            words.append(word.split("|"))
        for parts in itertools.product(*words):
            name = "acloud " + " ".join(parts)
            if name in commands or name.startswith("acloud auth platform "):
                commands.add(name)
            elif not any(c.startswith(name + " ") or name.startswith(c + " ") for c in commands):
                commands.add(name)
    docs = []
    for command in sorted(commands):
        document = json.loads(invoke(executable, "cli", "describe", command[7:]))
        docs.append({k: document[k] for k in ("command", "summary", "usage")})
    return docs


def argument(value, optional=False):
    value = value.rstrip(",")
    arg = {"name": value}
    if optional:
        arg["isOptional"] = True
    if "|" in value and all(re.fullmatch(r"[a-z][\w-]*", v) for v in value.split("|")):
        arg["suggestions"] = value.split("|")
    if value in ("true", "false"):
        arg["suggestions"] = ["true", "false"]
    if value in ("json", "table"):
        arg["suggestions"] = [value]
    if value.startswith(("https://", "http://")):
        arg["name"] = "URL"
    if value in ("FILE", "FILE|-", "POLICY_FILE"):
        arg["template"] = "filepaths"
    return arg


def parse_usage(command, usage):
    tail = usage.removeprefix(command).split(" (", 1)[0]
    options = []
    seen = set()
    # Values may be placeholders, literal formats, ranges, URLs or enums.
    for match in re.finditer(r"(--[a-z][\w-]*)(?:[ \t]+(?![-\[|])([^\s\]]+))?", tail):
        name, value = match.groups()
        if name in seen:
            continue
        seen.add(name)
        opt = {"name": name}
        if value:
            opt["args"] = argument(value)
            after = tail[match.end():]
            if after.startswith("]...") or after.startswith(" ..."):
                opt["isRepeatable"] = True
            if after.startswith(" ..."):
                opt["args"]["isVariadic"] = True
        options.append(opt)
    before_flags = tail.split("--", 1)[0]
    args = []
    for match in re.finditer(r"\b[A-Z][A-Z0-9_]*\b", before_flags):
        optional = before_flags[:match.start()].count("[") > before_flags[:match.start()].count("]")
        args.append(argument(match.group(), optional))
    return options, args


def build(docs):
    root = {"name": "acloud", "description": "Command line for Arc Cloud Platform", "subcommands": []}
    for doc in sorted(docs, key=lambda d: d["command"]):
        node = root
        for word in doc["command"].split()[1:]:
            children = node.setdefault("subcommands", [])
            child = next((c for c in children if c["name"] == word), None)
            if child is None:
                child = {"name": word}
                children.append(child)
            node = child
        node["description"] = doc["summary"].split(". ", 1)[0].rstrip(".")
        opts, args = parse_usage(doc["command"], doc["usage"])
        if opts:
            node["options"] = opts
        if args:
            node["args"] = args
    root["options"] = [
        {"name": "--project", "description": "Project ID", "isPersistent": True, "args": {"name": "PROJECT_ID"}},
        {"name": "--format", "description": "Output format", "isPersistent": True, "args": {"name": "FORMAT", "suggestions": ["table", "json"]}},
        {"name": "--platform-api-url", "description": "Platform API URL", "isPersistent": True, "args": {"name": "URL"}},
        {"name": "--help", "description": "Show help", "isPersistent": True},
    ]
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acloud", default="acloud")
    parser.add_argument("--from-catalog", type=Path)
    args = parser.parse_args()
    docs = json.loads(args.from_catalog.read_text()) if args.from_catalog else collect(args.acloud)
    (ROOT / "catalog.json").write_text(json.dumps(docs, indent=2) + "\n")
    spec = build(docs)
    (ROOT / "acloud.js").write_text("// Generated by scripts/generate.py; edit the generator to make changes.\nexport default " + json.dumps(spec, indent=2) + ";\n")
    (ROOT / "index.js").write_text('export default ["acloud"];\n')
    print(f"Generated {len(docs)} documented commands")
