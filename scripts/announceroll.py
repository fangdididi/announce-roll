#!/usr/bin/env python3
"""Build an announcement directory for interactive HTML controls. Stdlib only."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

VOID = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

SKIP_TEXT_TAGS = {"script", "style", "noscript", "template"}

INTERACTIVE_ROLES = {
    "button",
    "link",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "tab",
    "checkbox",
    "radio",
    "switch",
    "textbox",
    "searchbox",
    "combobox",
    "slider",
    "spinbutton",
    "option",
    "treeitem",
}

NAME_FROM_CONTENTS_ROLES = INTERACTIVE_ROLES | {
    "button",
    "link",
    "menuitem",
    "tab",
    "option",
    "treeitem",
}

LANDMARK_TAGS = {
    "nav": "navigation",
    "main": "main",
    "header": "banner",
    "footer": "contentinfo",
    "aside": "complementary",
    "form": "form",
    "section": "region",
}

LANDMARK_ROLES = {
    "navigation",
    "main",
    "banner",
    "contentinfo",
    "complementary",
    "form",
    "search",
    "region",
}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

TEXT_INPUT_TYPES = {
    "text",
    "email",
    "password",
    "search",
    "tel",
    "url",
    "number",
    "date",
    "datetime-local",
    "month",
    "week",
    "time",
    "",
}

BUTTON_INPUT_TYPES = {"button", "submit", "reset", "image"}


class Node:
    def __init__(self, tag: str, attrs: dict[str, str], parent: "Node | None"):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children: list[Node | str] = []

    def get(self, name: str, default: str | None = None) -> str | None:
        return self.attrs.get(name, default)


class TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("document", {}, None)
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        ad = {str(k).lower(): ("" if v is None else str(v)) for k, v in attrs}
        node = Node(tag, ad, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(data)


def parse_html(text: str) -> Node:
    builder = TreeBuilder()
    builder.feed(text or "")
    builder.close()
    return builder.root


def walk(node: Node):
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from walk(child)


def index_by_id(root: Node) -> dict[str, Node]:
    out: dict[str, Node] = {}
    for node in walk(root):
        nid = node.get("id")
        if nid and nid not in out:
            out[nid] = node
    return out


def ancestors(node: Node) -> list[Node]:
    out = []
    cur = node.parent
    while cur is not None:
        out.append(cur)
        cur = cur.parent
    return out


def is_aria_hidden(node: Node) -> bool:
    return (node.get("aria-hidden") or "").strip().lower() == "true"


def is_hidden_attr(node: Node) -> bool:
    if "hidden" in node.attrs:
        return True
    if (node.get("type") or "").lower() == "hidden":
        return True
    return False


def hidden_from_tree(node: Node) -> bool:
    if is_hidden_attr(node) or is_aria_hidden(node):
        return True
    return any(is_aria_hidden(a) or is_hidden_attr(a) for a in ancestors(node))


def collapse(text: str) -> str:
    return " ".join((text or "").split())


def normalize_name(text: str) -> str:
    return collapse(text).casefold()


def text_of(node: Node, exclude: Node | None = None) -> str:
    parts: list[str] = []

    def rec(n: Node) -> None:
        if n is exclude:
            return
        if n.tag in SKIP_TEXT_TAGS or n.tag == "svg":
            return
        if is_aria_hidden(n) or is_hidden_attr(n):
            return
        if n.tag == "img":
            alt = n.get("alt")
            if alt:
                parts.append(alt)
            return
        if n.tag == "br":
            parts.append(" ")
            return
        for child in n.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                rec(child)

    rec(node)
    return collapse("".join(parts))


def computed_role(node: Node) -> str:
    explicit = (node.get("role") or "").strip().lower()
    if explicit:
        return explicit
    tag = node.tag
    typ = (node.get("type") or "text").lower()
    if tag == "a" and node.get("href") is not None:
        return "link"
    if tag == "button" or (tag == "input" and typ in BUTTON_INPUT_TYPES):
        return "button"
    if tag == "summary":
        return "button"
    if tag == "select":
        return "combobox"
    if tag == "textarea":
        return "textbox"
    if tag == "input":
        if typ == "checkbox":
            return "checkbox"
        if typ == "radio":
            return "radio"
        if typ == "search":
            return "searchbox"
        if typ == "range":
            return "slider"
        if typ in TEXT_INPUT_TYPES:
            return "textbox"
        return "textbox"
    if (node.get("contenteditable") or "").lower() in {"", "true"} and "contenteditable" in node.attrs:
        return "textbox"
    return tag


def is_interactive(node: Node) -> bool:
    if hidden_from_tree(node):
        return False
    role = (node.get("role") or "").strip().lower()
    if role in INTERACTIVE_ROLES:
        return True
    tag = node.tag
    if tag == "a" and node.get("href") is not None:
        return True
    if tag in {"button", "select", "textarea", "summary"}:
        return True
    if tag == "input" and (node.get("type") or "text").lower() != "hidden":
        return True
    if "contenteditable" in node.attrs and (node.get("contenteditable") or "true").lower() != "false":
        return True
    return False


def last_heading_in(node: Node) -> str:
    found = text_of(node) if node.tag in HEADING_TAGS else ""
    for child in node.children:
        if isinstance(child, Node):
            nested = last_heading_in(child)
            if nested:
                found = nested
    return found


def nearest_heading(node: Node) -> str:
    cur = node
    while cur.parent is not None:
        parent = cur.parent
        seen_self = False
        for child in reversed(parent.children):
            if not isinstance(child, Node):
                continue
            if child is cur:
                seen_self = True
                continue
            if not seen_self:
                continue
            found = last_heading_in(child)
            if found:
                return found
        cur = parent
    return ""


def nearest_landmark(node: Node) -> str:
    for anc in ancestors(node):
        role = (anc.get("role") or "").strip().lower()
        if role in LANDMARK_ROLES:
            return role
        if anc.tag in LANDMARK_TAGS:
            return LANDMARK_TAGS[anc.tag]
    return ""


def find_label_for(root: Node, target_id: str) -> Node | None:
    for node in walk(root):
        if node.tag == "label" and node.get("for") == target_id:
            return node
    return None


def wrapping_label(node: Node) -> Node | None:
    for anc in ancestors(node):
        if anc.tag == "label":
            return anc
    return None


def accessible_name(node: Node, root: Node, by_id: dict[str, Node]) -> tuple[str, str]:
    labelledby = collapse(node.get("aria-labelledby") or "")
    if labelledby:
        parts = []
        for ref in labelledby.split():
            target = by_id.get(ref)
            if target is not None:
                parts.append(text_of(target))
        joined = collapse(" ".join(parts))
        if joined:
            return joined, "aria-labelledby"

    aria_label = collapse(node.get("aria-label") or "")
    if aria_label:
        return aria_label, "aria-label"

    tag = node.tag
    typ = (node.get("type") or "text").lower()

    if tag in {"img", "area"} or (tag == "input" and typ == "image"):
        alt = node.get("alt")
        if alt is not None and collapse(alt):
            return collapse(alt), "alt"

    if tag == "input" and typ in {"button", "submit", "reset"}:
        value = collapse(node.get("value") or "")
        if value:
            return value, "value"

    if tag in {"input", "select", "textarea"}:
        nid = node.get("id")
        if nid:
            lab = find_label_for(root, nid)
            if lab is not None:
                named = text_of(lab, exclude=node)
                if named:
                    return named, "label"
        wrap = wrapping_label(node)
        if wrap is not None:
            named = text_of(wrap, exclude=node)
            if named:
                return named, "label"

    role = computed_role(node)
    if tag in {"button", "a", "summary"} or role in NAME_FROM_CONTENTS_ROLES:
        contents = text_of(node)
        if contents:
            return contents, "contents"

    title = collapse(node.get("title") or "")
    if title:
        return title, "title"

    placeholder = collapse(node.get("placeholder") or "")
    if placeholder:
        return placeholder, "placeholder"

    if tag == "input" and typ == "submit":
        return "Submit", "implicit"
    if tag == "input" and typ == "reset":
        return "Reset", "implicit"
    if tag == "input" and typ == "image":
        return "Submit Query", "implicit"

    return "", "none"


def visible_text(node: Node, root: Node) -> str:
    tag = node.tag
    if tag in {"button", "a", "summary"}:
        return text_of(node)
    if tag == "input" and (node.get("type") or "text").lower() in BUTTON_INPUT_TYPES:
        return collapse(node.get("value") or "")
    if tag in {"input", "select", "textarea"}:
        nid = node.get("id")
        if nid:
            lab = find_label_for(root, nid)
            if lab is not None:
                named = text_of(lab, exclude=node)
                if named:
                    return named
        wrap = wrapping_label(node)
        if wrap is not None:
            named = text_of(wrap, exclude=node)
            if named:
                return named
        return collapse(node.get("value") or "")
    return text_of(node)


def label_in_name(visible: str, announced: str) -> bool:
    vis = normalize_name(visible)
    ann = normalize_name(announced)
    if not vis:
        return True
    if vis in ann:
        return True
    return False


def disabled_state(node: Node) -> bool:
    if "disabled" in node.attrs:
        return True
    if (node.get("aria-disabled") or "").strip().lower() == "true":
        return True
    return False


def collect_controls(root: Node) -> list[dict]:
    by_id = index_by_id(root)
    raw: list[dict] = []
    n = 0
    for node in walk(root):
        if node.tag == "document":
            continue
        if not is_interactive(node):
            continue
        n += 1
        name, source = accessible_name(node, root, by_id)
        vis = visible_text(node, root)
        role = computed_role(node)
        raw.append(
            {
                "id": f"c{n}",
                "tag": node.tag,
                "role": role,
                "name": name,
                "name_source": source,
                "visible_text": vis,
                "normalized": normalize_name(name) if name else "",
                "landmark": nearest_landmark(node),
                "heading": nearest_heading(node),
                "disabled": disabled_state(node),
                "href": node.get("href") or "",
                "input_type": (node.get("type") or "") if node.tag == "input" else "",
            }
        )

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in raw:
        if row["normalized"]:
            groups[(row["role"], row["normalized"])].append(row["id"])

    for row in raw:
        clash_ids = groups.get((row["role"], row["normalized"]), [])
        clashing = [i for i in clash_ids if i != row["id"]]
        row["clash_with"] = clashing
        if not row["name"]:
            row["grade"] = "MUTE"
        elif clashing:
            row["grade"] = "CLASH"
        elif row["name_source"] in {"aria-label", "aria-labelledby"} and row["visible_text"] and not label_in_name(
            row["visible_text"], row["name"]
        ):
            row["grade"] = "MASK"
        elif row["name_source"] in {"title", "placeholder", "implicit"}:
            row["grade"] = "WEAK"
        else:
            row["grade"] = "CLEAR"
        row["repair"] = repair_for(row)
    return raw


def repair_for(row: dict) -> str:
    grade = row["grade"]
    name = row["name"]
    vis = row["visible_text"]
    heading = row["heading"]
    if grade == "MUTE":
        hint = vis or heading or row["role"]
        return f"Give this {row['role']} a spoken name (visible text or an aria-label such as “{hint}”)."
    if grade == "CLASH":
        others = ", ".join(row["clash_with"])
        extra = f" under “{heading}”" if heading else ""
        return f"Make the name unique{extra}; it currently matches {others}."
    if grade == "MASK":
        return f"The page shows “{vis}” but the spoken name is “{name}”. Put the visible words inside the spoken name, or drop the override."
    if grade == "WEAK":
        return f"Name comes from {row['name_source']}. Prefer a visible label so the spoken name stays in sync."
    return ""


def clash_groups(controls: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in controls:
        if row["grade"] == "CLASH":
            groups[(row["role"], row["normalized"])].append(row)
    out = []
    for (role, norm), rows in groups.items():
        out.append(
            {
                "role": role,
                "name": rows[0]["name"],
                "ids": [r["id"] for r in rows],
                "count": len(rows),
            }
        )
    out.sort(key=lambda g: (-g["count"], g["role"], g["name"]))
    return out


def resolve_intents(controls: list[dict], intents: list[dict]) -> list[dict]:
    results = []
    for intent in intents:
        if not isinstance(intent, dict):
            continue
        phrase = collapse(str(intent.get("phrase") or intent.get("name") or ""))
        role = collapse(str(intent.get("role") or "")).lower()
        iid = str(intent.get("id") or phrase or "intent")
        named = [c for c in controls if c["name"] and (not role or c["role"] == role)]
        key = normalize_name(phrase)
        exact = [c for c in named if c["normalized"] == key]
        if len(exact) == 1:
            hit = "UNIQUE"
            matched = exact
        elif len(exact) > 1:
            hit = "AMBIGUOUS"
            matched = exact
        else:
            sub = [c for c in named if key and (key in c["normalized"] or c["normalized"] in key)]
            if len(sub) == 1:
                hit = "UNIQUE"
                matched = sub
            elif len(sub) > 1:
                hit = "AMBIGUOUS"
                matched = sub
            else:
                hit = "MISSING"
                matched = []
        results.append(
            {
                "id": iid,
                "phrase": phrase,
                "role": role,
                "hit": hit,
                "matches": [c["id"] for c in matched],
                "match_names": [c["name"] for c in matched],
            }
        )
    return results


def build_report(html: str, page: str = "", intents: list[dict] | None = None) -> dict:
    root = parse_html(html)
    controls = collect_controls(root)
    grades = Counter(c["grade"] for c in controls)
    resolved = resolve_intents(controls, intents or [])
    hits = Counter(r["hit"] for r in resolved)
    problems = grades.get("MUTE", 0) + grades.get("CLASH", 0) + grades.get("MASK", 0)
    weak = grades.get("WEAK", 0)
    intent_problems = hits.get("AMBIGUOUS", 0) + hits.get("MISSING", 0)
    if problems or intent_problems:
        status = "REPAIR"
    elif weak:
        status = "SOFT"
    else:
        status = "READY"
    return {
        "page": page,
        "status": status,
        "controls": controls,
        "grades": {k: grades.get(k, 0) for k in ("CLEAR", "WEAK", "MUTE", "CLASH", "MASK")},
        "clashes": clash_groups(controls),
        "intents": resolved,
        "intent_hits": {k: hits.get(k, 0) for k in ("UNIQUE", "AMBIGUOUS", "MISSING")},
        "summary": (
            f"{len(controls)} controls · "
            f"{grades.get('CLEAR', 0)} CLEAR · "
            f"{grades.get('WEAK', 0)} WEAK · "
            f"{grades.get('MUTE', 0)} MUTE · "
            f"{grades.get('CLASH', 0)} CLASH · "
            f"{grades.get('MASK', 0)} MASK"
        ),
    }


def format_report(report: dict) -> str:
    lines = [
        f"status  {report['status']}",
        f"summary {report['summary']}",
    ]
    if report.get("page"):
        lines.insert(0, f"page    {report['page']}")
    lines.append("")
    lines.append(f"{'id':<6}{'grade':<8}{'role':<12}{'source':<16}name")
    for row in report["controls"]:
        lines.append(
            f"{row['id']:<6}{row['grade']:<8}{row['role']:<12}{row['name_source']:<16}{row['name'] or '—'}"
        )
        extra = []
        if row["visible_text"] and row["visible_text"] != row["name"]:
            extra.append(f"visible “{row['visible_text']}”")
        if row["heading"]:
            extra.append(f"heading “{row['heading']}”")
        if row["landmark"]:
            extra.append(f"in {row['landmark']}")
        if row["disabled"]:
            extra.append("disabled")
        if extra:
            lines.append("      " + " · ".join(extra))
        if row["repair"]:
            lines.append("      repair: " + row["repair"])
    if report["clashes"]:
        lines.append("")
        lines.append("clashes")
        for g in report["clashes"]:
            lines.append(f"  {g['count']}× {g['role']} “{g['name']}” → {', '.join(g['ids'])}")
    if report["intents"]:
        lines.append("")
        lines.append("intents")
        for item in report["intents"]:
            who = ", ".join(item["matches"]) or "—"
            lines.append(f"  {item['id']:<16}{item['hit']:<12}“{item['phrase']}” → {who}")
    return "\n".join(lines) + "\n"


DEMO_HTML = """<!doctype html>
<html lang="en">
<body>
  <header>
    <h1>Corner shop</h1>
    <a href="/cart">Cart</a>
  </header>
  <main>
    <h2>Shelf</h2>
    <button>Add to cart</button>
    <ul>
      <li>Tea <button>Edit</button></li>
      <li>Honey <button>Edit</button></li>
    </ul>
    <button aria-label="Delete account">Save changes</button>
    <button type="button"><svg width="12" height="12"></svg></button>
    <label for="q">Search products</label>
    <input id="q" type="search">
    <input type="email" placeholder="Email address">
    <input type="submit">
  </main>
</body>
</html>
"""

DEMO_INTENTS = [
    {"id": "add", "phrase": "Add to cart", "role": "button"},
    {"id": "edit", "phrase": "Edit", "role": "button"},
    {"id": "save", "phrase": "Save changes", "role": "button"},
    {"id": "checkout", "phrase": "Checkout", "role": "button"},
]


def load_intents(path: str | None) -> list[dict]:
    if not path:
        return []
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and isinstance(raw.get("intents"), list):
        return raw["intents"]
    if isinstance(raw, list):
        return raw
    raise ValueError("intents file must be a list or an object with an intents array")


def cmd_lint(path: str) -> int:
    text = Path(path).read_text(encoding="utf-8")
    root = parse_html(text)
    count = sum(1 for node in walk(root) if node.tag != "document" and is_interactive(node))
    print(f"ok {path}: parsed, {count} interactive controls")
    return 0


def cmd_roll(path: str, intents_path: str | None, as_json: bool) -> int:
    text = Path(path).read_text(encoding="utf-8")
    try:
        intents = load_intents(intents_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"invalid intents: {exc}", file=sys.stderr)
        return 3
    report = build_report(text, page=path, intents=intents)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report), end="")
    return {"READY": 0, "SOFT": 0, "REPAIR": 2}.get(report["status"], 2)


def cmd_demo(as_json: bool) -> int:
    report = build_report(DEMO_HTML, page="demo", intents=DEMO_INTENTS)
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report), end="")
    return {"READY": 0, "SOFT": 0, "REPAIR": 2}.get(report["status"], 2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an announcement directory of interactive page controls."
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lint = sub.add_parser("lint", help="parse a page and count interactive controls")
    p_lint.add_argument("html")

    p_roll = sub.add_parser("roll", help="print the announcement directory")
    p_roll.add_argument("html")
    p_roll.add_argument("intents", nargs="?", help="optional intents.json")

    p_resolve = sub.add_parser("resolve", help="same as roll; requires intents")
    p_resolve.add_argument("html")
    p_resolve.add_argument("intents")

    sub.add_parser("demo", help="run the built-in mixed page")

    args = parser.parse_args(argv)
    if args.cmd == "lint":
        return cmd_lint(args.html)
    if args.cmd == "roll":
        return cmd_roll(args.html, args.intents, args.json)
    if args.cmd == "resolve":
        return cmd_roll(args.html, args.intents, args.json)
    if args.cmd == "demo":
        return cmd_demo(args.json)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
