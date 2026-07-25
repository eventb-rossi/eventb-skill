#!/usr/bin/env python3
"""Validate every skill in this repository.

Three groups of rules, in increasing cost:

1. Spec conformance — the Agent Skills specification (https://agentskills.io/specification):
   frontmatter shape, allowed fields, name and description constraints.
2. Repository conventions — line budgets, routing-table completeness, no orphan
   reference files, no absolute paths.
3. Event-B gates — every bundled example is formatted, validated, built, model-checked
   and WD-checked with `rossi` and `eventb-animate`. Skipped with a warning when those
   tools are absent; see --require-tools / --no-tools.

Standard library only, so CI needs nothing but a Python interpreter for groups 1 and 2.

Exit status: 0 when every rule passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"

# --- Limits from the specification -------------------------------------------------
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
ALLOWED_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}

# --- Limits this repository imposes on itself ---------------------------------------
# The spec recommends SKILL.md stay under 500 lines; we enforce it.
MAX_SKILL_LINES = 500
# References are loaded whole, so each must stay readable in one bite. 420 is the
# ceiling rather than a rounder number because tooling.md (401 lines) is a single CLI
# surface: splitting it would scatter one command's flags across two files. Anything
# that grows past this budget should be split by topic instead of raising the limit.
MAX_REFERENCE_LINES = 420
# Descriptions are matched against a task before the body is ever read, so they have to
# say when to fire. See https://agentskills.io/skill-creation/optimizing-descriptions.
TRIGGER_PHRASES = ("use for", "use when", "use this", "use it when")
ABSOLUTE_PATH_PATTERNS = (r"/Users/", r"/home/[a-z]", r"C:\\Users\\")
# Directories a SKILL.md may route into. Keeps the routing table flat, which is what
# makes progressive disclosure predictable.
ROUTABLE_DIRS = ("references", "examples", "scripts", "assets", "agents")


@dataclass
class Result:
    """One rule applied to one skill."""

    skill: str
    rule: str
    messages: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.messages


class Report:
    def __init__(self, verbose: bool) -> None:
        self.verbose = verbose
        self.results: list[Result] = []
        self.warnings: list[str] = []

    def check(self, skill: str, rule: str, messages: list[str] | str | None) -> None:
        if isinstance(messages, str):
            messages = [messages]
        self.results.append(Result(skill, rule, list(messages or [])))

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def failures(self) -> list[Result]:
        return [r for r in self.results if not r.ok]

    def emit(self) -> int:
        for result in self.results:
            if result.ok:
                if self.verbose:
                    print(f"\u2713 {result.skill}: {result.rule}")
                continue
            for message in result.messages:
                print(f"\u2717 {result.skill}: {result.rule}: {message}")
        for warning in self.warnings:
            print(f"! {warning}")
        checked = len(self.results)
        failed = len(self.failures)
        if failed:
            print(f"\n{failed} of {checked} checks failed.")
            return 1
        print(f"\n{checked} checks passed.")
        return 0


# ---------------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------------
# The reference implementation parses frontmatter with strictyaml, which does no
# implicit typing. Rather than depend on it, parse the subset the spec permits and
# report anything unrecognised as a failure — never drop a line silently, which is how
# a "required" field ends up unvalidated.

BLOCK_SCALAR = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<style>[|>])(?P<chomp>[-+]?)\s*$")
SCALAR = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*?)\s*$")
NESTED = re.compile(r"^(?P<indent>\s+)(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*?)\s*$")


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict[str, object], list[str]]:
    """Parse a SKILL.md frontmatter block into a dict, plus a list of parse errors."""
    data: dict[str, object] = {}
    errors: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue

        block = BLOCK_SCALAR.match(line)
        if block:
            key = block.group("key")
            body: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1].isspace()):
                body.append(lines[i].strip())
                i += 1
            if block.group("style") == ">":
                # Folded: blank lines separate paragraphs, everything else joins.
                paragraphs, current = [], []
                for entry in body:
                    if entry:
                        current.append(entry)
                    elif current:
                        paragraphs.append(" ".join(current))
                        current = []
                if current:
                    paragraphs.append(" ".join(current))
                value = "\n".join(paragraphs)
            else:
                value = "\n".join(body).rstrip()
            data[key] = value.strip()
            continue

        scalar = SCALAR.match(line)
        if scalar and not line[:1].isspace():
            key, value = scalar.group("key"), scalar.group("value")
            if value:
                data[key] = unquote(value)
                i += 1
                continue
            # An empty value introduces a nested mapping.
            nested: dict[str, str] = {}
            i += 1
            while i < len(lines) and lines[i].strip() and lines[i][:1].isspace():
                child = NESTED.match(lines[i])
                if not child:
                    errors.append(f"line {i + 1}: cannot parse nested entry {lines[i]!r}")
                    i += 1
                    continue
                nested[child.group("key")] = unquote(child.group("value"))
                i += 1
            data[key] = nested
            continue

        errors.append(f"line {i + 1}: cannot parse {line!r}")
        i += 1
    return data, errors


# Values a typing YAML parser would not hand back as a string.
TYPED_SCALAR = re.compile(
    r"^(-?\d+(\.\d+)*|true|false|yes|no|on|off|null|~)$", re.IGNORECASE
)


def unquoted_metadata(frontmatter: str) -> list[str]:
    """Report metadata values that a typing YAML parser would not read as a string."""
    problems: list[str] = []
    inside = False
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        if not line[:1].isspace():
            inside = line.strip() == "metadata:"
            continue
        if not inside:
            continue
        child = NESTED.match(line)
        if child and TYPED_SCALAR.match(child.group("value")):
            problems.append(
                f"metadata.{child.group('key')} value {child.group('value')!r} must be "
                "quoted, or a typing YAML parser will read it as a number or boolean"
            )
    return problems


def split_skill_md(path: Path) -> tuple[str, str, list[str]]:
    """Return (frontmatter, body, errors) for a SKILL.md."""
    raw = path.read_bytes()
    errors: list[str] = []
    if raw.startswith(b"\xef\xbb\xbf"):
        errors.append("file starts with a UTF-8 BOM; the frontmatter must begin at byte 0")
        raw = raw[3:]
    text = raw.decode("utf-8")
    if not text.startswith("---"):
        errors.append("must start with YAML frontmatter (---) on the first line")
        return "", text, errors
    parts = text.split("---", 2)
    if len(parts) < 3:
        errors.append("frontmatter is not closed with ---")
        return "", text, errors
    return parts[1], parts[2], errors


# ---------------------------------------------------------------------------------
# Rule groups
# ---------------------------------------------------------------------------------
def check_spec(report: Report, skill_dir: Path) -> dict[str, object]:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"

    report.check(name, "skill-md-present", [] if skill_md.is_file() else "missing SKILL.md")
    if not skill_md.is_file():
        return {}

    frontmatter, body, errors = split_skill_md(skill_md)
    report.check(name, "frontmatter-delimited", errors)
    if errors:
        return {}

    data, parse_errors = parse_frontmatter(frontmatter)
    report.check(name, "frontmatter-parses", parse_errors)

    extra = sorted(set(data) - ALLOWED_FIELDS)
    report.check(
        name,
        "allowed-fields",
        [
            f"unexpected frontmatter field {f!r}; the spec allows only "
            f"{', '.join(sorted(ALLOWED_FIELDS))}"
            for f in extra
        ],
    )

    missing = [f for f in ("name", "description") if not data.get(f)]
    report.check(name, "required-fields", [f"missing required field {f!r}" for f in missing])

    declared = data.get("name")
    problems = []
    if isinstance(declared, str) and declared:
        normalized = unicodedata.normalize("NFKC", declared).strip()
        if len(normalized) > MAX_NAME:
            problems.append(f"name is {len(normalized)} characters; the limit is {MAX_NAME}")
        if normalized != normalized.lower():
            problems.append(f"name {normalized!r} must be lowercase")
        if normalized.startswith("-") or normalized.endswith("-"):
            problems.append("name must not start or end with a hyphen")
        if "--" in normalized:
            problems.append("name must not contain consecutive hyphens")
        if not all(c.isalnum() or c == "-" for c in normalized):
            problems.append(f"name {normalized!r} may contain only letters, digits and hyphens")
    report.check(name, "name-format", problems)

    report.check(
        name,
        "name-matches-directory",
        []
        if declared == skill_dir.name
        else f"frontmatter name {declared!r} must equal the directory name {skill_dir.name!r}",
    )

    description = data.get("description") or ""
    report.check(
        name,
        "description-limit",
        []
        if len(description) <= MAX_DESCRIPTION
        else f"description is {len(description)} characters; the limit is {MAX_DESCRIPTION}",
    )
    report.check(
        name,
        "description-has-trigger",
        []
        if any(p in description.lower() for p in TRIGGER_PHRASES)
        else "description must say when to use the skill; expected one of "
        + ", ".join(repr(p) for p in TRIGGER_PHRASES),
    )

    compatibility = data.get("compatibility")
    problems = []
    if compatibility is not None:
        if not isinstance(compatibility, str):
            problems.append("compatibility must be a string")
        elif len(compatibility) > MAX_COMPATIBILITY:
            problems.append(
                f"compatibility is {len(compatibility)} characters; "
                f"the limit is {MAX_COMPATIBILITY}"
            )
    report.check(name, "compatibility-limit", problems)

    metadata = data.get("metadata")
    problems = []
    if metadata is not None:
        if not isinstance(metadata, dict):
            problems.append("metadata must be a mapping")
        else:
            for key, value in metadata.items():
                if not value:
                    problems.append(f"metadata.{key} is empty")
    report.check(name, "metadata-values-present", problems)

    # The spec defines metadata values as strings, but clients parse frontmatter with
    # whatever YAML library they already have. An unquoted 1.0 is a string under
    # strictyaml and a float under PyYAML, so require quoting for anything a typing
    # parser would convert.
    report.check(name, "metadata-values-quoted", unquoted_metadata(frontmatter))

    body_lines = len(body.strip().splitlines())
    report.check(
        name,
        "skill-body-length",
        []
        if body_lines <= MAX_SKILL_LINES
        else f"SKILL.md body is {body_lines} lines; the budget is {MAX_SKILL_LINES}",
    )
    return data


def check_conventions(report: Report, skill_dir: Path) -> None:
    name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    skill_text = skill_md.read_text() if skill_md.is_file() else ""
    references = skill_dir / "references"

    # Reference budget.
    problems = []
    if references.is_dir():
        for ref in sorted(references.rglob("*.md")):
            lines = len(ref.read_text().splitlines())
            if lines > MAX_REFERENCE_LINES:
                problems.append(
                    f"{ref.relative_to(skill_dir)} is {lines} lines; the budget is "
                    f"{MAX_REFERENCE_LINES} — split it by topic rather than raising the limit"
                )
    report.check(name, "reference-length", problems)

    # Every reference must be reachable from the routing table, and every path the
    # routing table names must exist. Paths are written as inline code, not links, so
    # match on the mention rather than on markdown link syntax.
    problems = []
    if references.is_dir():
        for ref in sorted(references.rglob("*.md")):
            rel = ref.relative_to(skill_dir).as_posix()
            if rel not in skill_text:
                problems.append(f"{rel} is never named in SKILL.md (orphan reference)")
    report.check(name, "no-orphan-references", problems)

    problems = []
    for match in re.finditer(r"`((?:%s)/[^`\s]+)`" % "|".join(ROUTABLE_DIRS), skill_text):
        target = skill_dir / match.group(1).rstrip("/")
        if not target.exists():
            problems.append(f"SKILL.md names {match.group(1)!r}, which does not exist")
    report.check(name, "routed-paths-exist", problems)

    # Relative links must resolve and stay inside the skill.
    problems = []
    for md in sorted(skill_dir.rglob("*.md")):
        for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", md.read_text()):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            resolved = (md.parent / target.split("#")[0]).resolve()
            rel = md.relative_to(skill_dir)
            if not resolved.exists():
                problems.append(f"{rel} links to {target!r}, which does not exist")
            elif not resolved.is_relative_to(skill_dir.resolve()):
                problems.append(f"{rel} links to {target!r}, which escapes the skill directory")
    report.check(name, "links-resolve", problems)

    # Absolute paths and leftover markers.
    problems = []
    markers = []
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml", ".eventb"}:
            continue
        text = path.read_text()
        rel = path.relative_to(skill_dir)
        for pattern in ABSOLUTE_PATH_PATTERNS:
            if re.search(pattern, text):
                problems.append(f"{rel} contains a machine-specific absolute path ({pattern})")
        for marker in re.finditer(r"\b(TODO|FIXME|XXX)\b", text):
            markers.append(f"{rel} contains a {marker.group(1)} marker")
    report.check(name, "no-absolute-paths", problems)
    report.check(name, "no-unfinished-markers", markers)

    # Examples: documented and self-describing.
    examples = skill_dir / "examples"
    structure, documented = [], []
    if examples.is_dir():
        example_dirs = sorted(d for d in examples.iterdir() if d.is_dir())
        if not example_dirs:
            structure.append("examples/ exists but contains no example directories")
        for example in example_dirs:
            readme = example / "README.md"
            models = sorted(example.glob("*.eventb"))
            rel = example.relative_to(skill_dir)
            if not readme.is_file():
                structure.append(f"{rel} has no README.md")
            if not models:
                structure.append(f"{rel} contains no .eventb component")
            if readme.is_file():
                readme_text = readme.read_text()
                for model in models:
                    if model.name not in readme_text:
                        documented.append(
                            f"{rel}/{model.name} is not described in {rel}/README.md"
                        )
            if f"examples/{example.name}" not in skill_text:
                structure.append(f"{rel} is never named in SKILL.md")
    report.check(name, "example-structure", structure)
    report.check(name, "example-files-documented", documented)


# ---------------------------------------------------------------------------------
# Event-B gates
# ---------------------------------------------------------------------------------
REQUIRED_TOOLS = ("rossi", "eventb-animate")


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def machines_of(example: Path) -> list[str]:
    names = []
    for model in sorted(example.glob("*.eventb")):
        names += re.findall(r"^MACHINE\s+(\S+)", model.read_text(), re.MULTILINE)
    return sorted(names)


def check_example_model(report: Report, skill: str, example: Path, workdir: Path) -> None:
    rel = example.name
    problems = []
    # --deny-warnings, not just the default exit code: rossi's advisory lints (dead
    # variable, unmodified variable, incomplete INITIALISATION, shadowed name) exit 0, and
    # a shipped example teaches whatever it contains. Needs rossi 0.1.8+.
    for args, label in (
        (["rossi", "validate", "--deny-warnings", "."], "rossi-validate"),
        (["rossi", "fmt", "--check", "."], "rossi-fmt-check"),
    ):
        proc = run(args, cwd=example)
        if proc.returncode != 0:
            problems.append(f"{rel}: {label} failed: {(proc.stderr or proc.stdout).strip()}")
    report.check(skill, f"example-static[{rel}]", problems)
    if problems:
        return

    archive = workdir / f"{rel}.zip"
    proc = run(["rossi", "build", str(example), "-o", str(archive)])
    if proc.returncode != 0 or not archive.exists():
        report.check(
            skill,
            f"example-build[{rel}]",
            f"{rel}: rossi build failed: {(proc.stderr or proc.stdout).strip()}",
        )
        return
    report.check(skill, f"example-build[{rel}]", [])

    # SKILL.md requires the model check and the WD gate at every refinement level, so
    # hold the bundled examples to the same standard rather than only checking the
    # machine the animator auto-selects.
    for machine in machines_of(example):
        problems = []
        report_path = workdir / f"{rel}-{machine}.json"
        proc = run(
            [
                "eventb-animate",
                "-m",
                machine,
                "--json",
                str(report_path),
                str(archive),
            ]
        )
        if not report_path.exists():
            problems.append(
                f"{machine}: no JSON report written: {(proc.stderr or proc.stdout).strip()}"
            )
        else:
            data = json.loads(report_path.read_text())
            if data.get("status") != "ok":
                problems.append(f"{machine}: report status is {data.get('status')!r}, expected 'ok'")
            for entry in data.get("checks", []):
                if entry.get("outcome") != "passed":
                    problems.append(
                        f"{machine}: {entry.get('name')} check outcome is "
                        f"{entry.get('outcome')!r}, expected 'passed'"
                    )
        report.check(skill, f"example-modelcheck[{rel}/{machine}]", problems)

        wd_path = workdir / f"{rel}-{machine}-wd.json"
        proc = run(["eventb-animate", "wd", "-m", machine, "--json", str(wd_path), str(archive)])
        problems = []
        if not wd_path.exists():
            problems.append(
                f"{machine}: no WD report written: {(proc.stderr or proc.stdout).strip()}"
            )
        else:
            data = json.loads(wd_path.read_text())
            if data.get("status") != "ok":
                problems.append(
                    f"{machine}: WD status is {data.get('status')!r}, expected 'ok'"
                )
            for entry in data.get("checks", []):
                if entry.get("outcome") not in (None, "passed"):
                    problems.append(
                        f"{machine}: WD check {entry.get('name')} outcome is "
                        f"{entry.get('outcome')!r}"
                    )
        report.check(skill, f"example-wd[{rel}/{machine}]", problems)


def check_models(report: Report, skill_dir: Path, require_tools: bool) -> None:
    name = skill_dir.name
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    if missing:
        message = (
            f"{', '.join(missing)} not on PATH; skipping the Event-B gates. "
            "Install from https://github.com/eventb-rossi or pass --no-tools to silence this."
        )
        if require_tools:
            report.check(name, "eventb-tools-available", message)
        else:
            report.warn(message)
        return
    report.check(name, "eventb-tools-available", [])

    examples = skill_dir / "examples"
    if not examples.is_dir():
        return
    with tempfile.TemporaryDirectory(prefix="eventb-skill-validate-") as tmp:
        workdir = Path(tmp)
        for example in sorted(d for d in examples.iterdir() if d.is_dir()):
            check_example_model(report, name, example, workdir)


# ---------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verbose", "-v", action="store_true", help="also list passing checks")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--no-tools",
        action="store_true",
        help="skip the Event-B gates entirely (no rossi or eventb-animate needed)",
    )
    group.add_argument(
        "--require-tools",
        action="store_true",
        help="fail instead of warning when rossi or eventb-animate is missing",
    )
    args = parser.parse_args()

    if not SKILLS_DIR.is_dir():
        print(f"\u2717 no skills/ directory at {SKILLS_DIR}")
        return 1
    skill_dirs = sorted(d for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").is_file())
    if not skill_dirs:
        print(f"\u2717 no skills found under {SKILLS_DIR}")
        return 1

    # A SKILL.md outside skills/ would be picked up by `skills add --full-depth` and
    # published as a second, unintended skill.
    stray = [
        p.relative_to(REPO)
        for p in REPO.rglob("SKILL.md")
        if ".git" not in p.parts and SKILLS_DIR not in p.parents
    ]
    report = Report(args.verbose)
    report.check(
        "repository",
        "no-stray-skill-md",
        [f"{p} is outside skills/; it would be discovered as a separate skill" for p in stray],
    )

    for skill_dir in skill_dirs:
        check_spec(report, skill_dir)
        check_conventions(report, skill_dir)
        if not args.no_tools:
            check_models(report, skill_dir, args.require_tools)

    return report.emit()


if __name__ == "__main__":
    sys.exit(main())
