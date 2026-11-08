# announce-roll

[中文](README.zh-CN.md) | **English**

An **announcement directory for interactive page controls**. Read HTML you already have, list every control the way a screen reader or a name-based agent would hear it, and mark mute names, collisions, and overrides that hide the visible words. Optional intents resolve to one control — or tell you they cannot.

This skill does not open a browser or click anything. It builds the directory an agent should use *before* it tries to operate the page.

## Features

- **Spoken roll** — role, announced name, name source, landmark, nearby heading, disabled flag
- **Five grades** — `CLEAR`, `WEAK`, `MUTE`, `CLASH`, `MASK` (not a ship/hold gate)
- **Intent resolver** — each phrase becomes `UNIQUE`, `AMBIGUOUS`, or `MISSING`
- **Repair notes** — each problem row suggests how to make the name unique and truthful
- **Stdlib helper** — `scripts/announceroll.py` (`lint` / `roll` / `resolve` / `demo`) plus unit tests

## Install

```bash
git clone https://github.com/fangdididi/announce-roll.git
cd announce-roll
```

### Claude Code / Codex / Cursor-style agents

- Place or symlink the repo where your agent loads skills from, **or**
- Open the folder and say: “Follow SKILL.md (announce-roll) and build a directory for this page before clicking anything.”

No API keys. The helper is Python 3 from the standard library.

## Usage

```bash
# parse and count
python3 scripts/announceroll.py lint examples/shelf-clear.html

# print the directory
python3 scripts/announceroll.py roll examples/shelf-clear.html
python3 scripts/announceroll.py roll examples/shelf-clash.html
python3 scripts/announceroll.py roll examples/shelf-mute.html
python3 scripts/announceroll.py roll examples/shelf-mask.html

# resolve intents
python3 scripts/announceroll.py resolve examples/shelf-clash.html examples/intents.json

# built-in mixed page
python3 scripts/announceroll.py demo

# machine-readable
python3 scripts/announceroll.py --json roll examples/shelf-clear.html

# tests
python3 -m unittest discover -s tests -v
```

Typical agent flow:

1. Save the page or component HTML you have the right to inspect.
2. Write the actions that must work into an intents file (see `templates/intents.json`).
3. Run `roll` / `resolve`, then rename mute, clashing, or masked controls until every intent is `UNIQUE`.

## Examples

| File | What you should see |
| --- | --- |
| `examples/shelf-clear.html` | `READY` — unique names, including a labelled search field |
| `examples/shelf-clash.html` | `REPAIR` — two `Edit` buttons |
| `examples/shelf-mute.html` | `REPAIR` — an icon-only button with no spoken name |
| `examples/shelf-mask.html` | `REPAIR` — visible “Save changes”, spoken “Delete account” |

## File structure

```
announce-roll/
├── SKILL.md
├── SKILL.zh-CN.md
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/announceroll.py
├── templates/intents.json
├── examples/
└── tests/test_announceroll.py
```

## License

MIT
