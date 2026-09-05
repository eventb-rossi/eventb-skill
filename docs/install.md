# Installing the Event-B skill

Two things have to be in place: the **skill** (documentation the agent reads) and the
**tools** it drives (`rossi` and `eventb-animate`). The skill is inert without them — its
first step is to check both and stop if either is missing.

## 1. Install the tools

The skill requires `rossi` 0.2.0+ and `eventb-animate` 6.4+ on `PATH`, and a Java 21+
runtime for `eventb-animate`.

### macOS and Linux (Homebrew)

```sh
brew install eventb-rossi/tap/rossi eventb-rossi/tap/eventb-animate
```

### Debian and Ubuntu (APT)

```sh
sudo install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://eventb-rossi.github.io/apt/KEY.gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/eventb.gpg
. /etc/os-release
echo "deb [signed-by=/etc/apt/keyrings/eventb.gpg] https://eventb-rossi.github.io/apt ${VERSION_CODENAME} main" \
  | sudo tee /etc/apt/sources.list.d/eventb.list
sudo apt-get update && sudo apt-get install rossi eventb-animate
```

### Fedora (COPR) and Windows (Scoop)

See [eventb-copr](https://github.com/eventb-rossi/eventb-copr) and
[scoop-eventb](https://github.com/eventb-rossi/scoop-eventb).

### From the releases directly

`rossi` ships prebuilt binaries for macOS, Linux and Windows on x86-64 and aarch64;
`eventb-animate` ships a runnable JAR. Both publish a `SHA256SUMS` file — verify against
it. For scripting that, each tool ships the installer its own GitHub Action runs:
[eventb-animate](https://github.com/eventb-rossi/eventb-animate)'s
`scripts/install-eventb-animate.sh`, and
[rossi-action](https://github.com/eventb-rossi/rossi-action)'s `scripts/install-rossi.sh`,
which covers all six release targets.

### Verify

```sh
command -v rossi eventb-animate
rossi --version          # expect 0.1.8 or newer
eventb-animate --version # expect 6.4 or newer
```

## 2. Install the skill

### With the skills CLI (recommended)

```sh
npx skills add eventb-rossi/eventb-skill
```

The CLI detects which agents you have and installs into each one's skills directory. Useful flags:

| Flag | Effect |
|---|---|
| `-g`, `--global` | Install for the user rather than the current project |
| `-a`, `--agent claude-code` | Target one specific agent |
| `-l`, `--list` | List the skills in the repository without installing |
| `--copy` | Copy files instead of symlinking |

### Manually

The skill is one self-contained directory, so copying it is enough. Pick the path your
client uses:

| Client | Project path | User path |
|---|---|---|
| Claude Code | `.claude/skills/eventb/` | `~/.claude/skills/eventb/` |
| Codex | `.agents/skills/eventb/` | `~/.agents/skills/eventb/` |
| Cross-client convention | `.agents/skills/eventb/` | `~/.agents/skills/eventb/` |

```sh
git clone https://github.com/eventb-rossi/eventb-skill
mkdir -p ~/.claude/skills
cp -R eventb-skill/skills/eventb ~/.claude/skills/
```

Other clients use their own directory (`.cursor/`, `.windsurf/`, `.gemini/`, `.opencode/`
and so on); the skills CLI knows all of them, which is why it is the easier route. The
directory must stay named `eventb` — the specification requires the directory name to
match the `name` in the frontmatter.

### Without skills support: fetch on demand

If your client has no skills mechanism, point the agent at
[`llms.txt`](../llms.txt). It lists the entry point and every reference with a raw URL,
so the agent can read `SKILL.md` first and pull a single reference only when it needs it.
[`skills/index.json`](../skills/index.json) carries the same information as JSON.

## 3. Confirm it works

Ask the agent for something small and Event-B shaped — "model a two-position turnstile
that must never open while a coin is unpaid" — and watch for the skill's own workflow:

1. it checks `rossi --version` and `eventb-animate --version` first;
2. it writes a requirement sheet before any `.eventb`;
3. it runs `rossi fmt -i .`, `rossi validate .`, `rossi build`, then
   `eventb-animate --json` and `eventb-animate wd`;
4. it reports completeness, event coverage and the WD result — and distinguishes "no bug
   found within the bound" from "proved".

If the agent writes `.eventb` files without running the gate, the skill did not load.
Check that the directory is named `eventb`, that `SKILL.md` sits directly inside it, and
that the client lists the skill (`npx skills list`).

## Codex specifics

`skills/eventb/agents/openai.yaml` carries the Codex interface metadata — display name,
short description, a default prompt, and `allow_implicit_invocation: true` so the skill
can trigger without being named. It is ignored by clients that do not read it.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| The agent never mentions the skill | Wrong directory, or the directory name does not match the frontmatter `name`. It must be `eventb`. |
| `eventb-animate: command not found` after installing | The JAR is installed but the wrapper is not on `PATH`, or Java is older than 21. Check `java -version`. |
| The agent stops and asks you to install tools | Working as intended — it will not install or upgrade them itself. |
| A model check reports `incomplete` | Not a failure. The state space was not exhausted; see `references/tooling.md` for the ProB caps to raise and when an exhaustive result is required. |

## Publishing (maintainers)

The repository is indexed on [skills.sh](https://skills.sh) automatically: the listing is
seeded the first time someone runs `npx skills add eventb-rossi/eventb-skill` with
telemetry enabled. The CLI disables telemetry in CI, so a CI install will not do it — run
it once from a workstation after the repository is public.
