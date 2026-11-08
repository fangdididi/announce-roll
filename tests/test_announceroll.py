#!/usr/bin/env python3
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import announceroll as ar  # noqa: E402


def report_of(html: str, intents=None):
    return ar.build_report(html, page="t", intents=intents or [])


def by_name(report, name):
    return [c for c in report["controls"] if c["name"] == name]


def by_grade(report, grade):
    return [c for c in report["controls"] if c["grade"] == grade]


class NameSources(unittest.TestCase):
    def test_button_uses_contents(self):
        r = report_of("<button>Save changes</button>")
        self.assertEqual(len(r["controls"]), 1)
        row = r["controls"][0]
        self.assertEqual(row["name"], "Save changes")
        self.assertEqual(row["name_source"], "contents")
        self.assertEqual(row["role"], "button")
        self.assertEqual(row["grade"], "CLEAR")

    def test_aria_label_overrides_and_masks_when_visible_differs(self):
        r = report_of('<button aria-label="Delete account">Save changes</button>')
        row = r["controls"][0]
        self.assertEqual(row["name"], "Delete account")
        self.assertEqual(row["name_source"], "aria-label")
        self.assertEqual(row["visible_text"], "Save changes")
        self.assertEqual(row["grade"], "MASK")

    def test_aria_label_ok_when_visible_words_are_inside(self):
        r = report_of('<button aria-label="Save changes now">Save changes</button>')
        row = r["controls"][0]
        self.assertEqual(row["grade"], "CLEAR")
        self.assertEqual(row["name"], "Save changes now")

    def test_aria_labelledby(self):
        html = '<span id="n">Download invoice</span><button aria-labelledby="n">PDF</button>'
        r = report_of(html)
        row = r["controls"][0]
        self.assertEqual(row["name"], "Download invoice")
        self.assertEqual(row["name_source"], "aria-labelledby")
        self.assertEqual(row["grade"], "MASK")  # visible "PDF" not in announced name

    def test_label_for(self):
        html = '<label for="q">Search products</label><input id="q" type="search">'
        r = report_of(html)
        row = r["controls"][0]
        self.assertEqual(row["role"], "searchbox")
        self.assertEqual(row["name"], "Search products")
        self.assertEqual(row["name_source"], "label")
        self.assertEqual(row["grade"], "CLEAR")

    def test_wrapping_label(self):
        html = "<label>Email address<input type=\"email\"></label>"
        r = report_of(html)
        row = r["controls"][0]
        self.assertEqual(row["name"], "Email address")
        self.assertEqual(row["name_source"], "label")

    def test_image_inside_link_uses_alt(self):
        r = report_of('<a href="/home"><img alt="Home"></a>')
        row = r["controls"][0]
        self.assertEqual(row["role"], "link")
        self.assertEqual(row["name"], "Home")
        self.assertEqual(row["name_source"], "contents")

    def test_placeholder_is_weak(self):
        r = report_of('<input type="email" placeholder="Email address">')
        row = r["controls"][0]
        self.assertEqual(row["name"], "Email address")
        self.assertEqual(row["name_source"], "placeholder")
        self.assertEqual(row["grade"], "WEAK")

    def test_title_is_weak(self):
        r = report_of('<button title="More actions"></button>')
        row = r["controls"][0]
        self.assertEqual(row["name"], "More actions")
        self.assertEqual(row["name_source"], "title")
        self.assertEqual(row["grade"], "WEAK")

    def test_implicit_submit(self):
        r = report_of('<input type="submit">')
        row = r["controls"][0]
        self.assertEqual(row["name"], "Submit")
        self.assertEqual(row["name_source"], "implicit")
        self.assertEqual(row["grade"], "WEAK")


class HiddenAndMute(unittest.TestCase):
    def test_mute_icon_button(self):
        r = report_of('<button type="button"><svg width="8" height="8"></svg></button>')
        self.assertEqual(r["controls"][0]["grade"], "MUTE")
        self.assertEqual(r["controls"][0]["name"], "")

    def test_skips_hidden_attribute(self):
        r = report_of('<button hidden>Ghost</button><button>Live</button>')
        self.assertEqual([c["name"] for c in r["controls"]], ["Live"])

    def test_skips_aria_hidden_ancestor(self):
        r = report_of('<div aria-hidden="true"><button>Secret</button></div><button>Ok</button>')
        self.assertEqual([c["name"] for c in r["controls"]], ["Ok"])

    def test_skips_input_type_hidden(self):
        r = report_of('<input type="hidden" value="token"><button>Go</button>')
        self.assertEqual(len(r["controls"]), 1)
        self.assertEqual(r["controls"][0]["name"], "Go")

    def test_skips_script_text_inside_button(self):
        r = report_of("<button>Save<script>alert(1)</script></button>")
        self.assertEqual(r["controls"][0]["name"], "Save")


class ClashAndContext(unittest.TestCase):
    def test_two_edit_buttons_clash(self):
        r = report_of("<button>Edit</button><button>Edit</button>")
        self.assertEqual([c["grade"] for c in r["controls"]], ["CLASH", "CLASH"])
        self.assertEqual(r["controls"][0]["clash_with"], ["c2"])
        self.assertEqual(len(r["clashes"]), 1)
        self.assertEqual(r["clashes"][0]["count"], 2)

    def test_same_name_different_roles_do_not_clash(self):
        r = report_of('<button>Save</button><a href="/x">Save</a>')
        self.assertEqual({c["grade"] for c in r["controls"]}, {"CLEAR"})

    def test_heading_and_landmark_context(self):
        html = "<main><h2>Billing</h2><button>Pay</button></main>"
        r = report_of(html)
        row = r["controls"][0]
        self.assertEqual(row["heading"], "Billing")
        self.assertEqual(row["landmark"], "main")

    def test_disabled_is_listed(self):
        r = report_of("<button disabled>Pay</button>")
        self.assertTrue(r["controls"][0]["disabled"])
        self.assertEqual(r["controls"][0]["name"], "Pay")


class IntentsAndStatus(unittest.TestCase):
    def test_unique_intent(self):
        r = report_of(
            "<button>Add to cart</button><button>Edit</button>",
            intents=[{"id": "add", "phrase": "Add to cart", "role": "button"}],
        )
        self.assertEqual(r["intents"][0]["hit"], "UNIQUE")
        self.assertEqual(r["intents"][0]["matches"], ["c1"])

    def test_ambiguous_intent(self):
        r = report_of(
            "<button>Edit</button><button>Edit</button>",
            intents=[{"id": "edit", "phrase": "Edit", "role": "button"}],
        )
        self.assertEqual(r["intents"][0]["hit"], "AMBIGUOUS")
        self.assertEqual(r["intents"][0]["matches"], ["c1", "c2"])
        self.assertEqual(r["status"], "REPAIR")

    def test_missing_intent(self):
        r = report_of(
            "<button>Add to cart</button>",
            intents=[{"id": "pay", "phrase": "Checkout", "role": "button"}],
        )
        self.assertEqual(r["intents"][0]["hit"], "MISSING")
        self.assertEqual(r["status"], "REPAIR")

    def test_mask_makes_visible_phrase_missing(self):
        r = report_of(
            '<button aria-label="Delete account">Save changes</button>',
            intents=[{"id": "save", "phrase": "Save changes", "role": "button"}],
        )
        self.assertEqual(r["intents"][0]["hit"], "MISSING")
        self.assertEqual(r["controls"][0]["grade"], "MASK")

    def test_clean_page_is_ready(self):
        r = report_of("<nav><a href='/'>Home</a></nav><main><button>Subscribe</button></main>")
        self.assertEqual(r["status"], "READY")
        self.assertEqual(r["grades"]["CLEAR"], 2)

    def test_weak_only_is_soft(self):
        r = report_of('<input type="email" placeholder="Email">')
        self.assertEqual(r["status"], "SOFT")


class Cli(unittest.TestCase):
    def test_demo_reports_mixed_grades(self):
        report = ar.build_report(ar.DEMO_HTML, page="demo", intents=ar.DEMO_INTENTS)
        self.assertGreaterEqual(report["grades"]["CLASH"], 2)
        self.assertGreaterEqual(report["grades"]["MUTE"], 1)
        self.assertGreaterEqual(report["grades"]["MASK"], 1)
        hits = {i["id"]: i["hit"] for i in report["intents"]}
        self.assertEqual(hits["add"], "UNIQUE")
        self.assertEqual(hits["edit"], "AMBIGUOUS")
        self.assertEqual(hits["save"], "MISSING")
        self.assertEqual(hits["checkout"], "MISSING")
        self.assertEqual(report["status"], "REPAIR")
        self.assertEqual(ar.cmd_demo(as_json=True), 2)

    def test_lint_and_roll_examples(self):
        page = ROOT / "examples" / "shelf-clear.html"
        self.assertEqual(ar.cmd_lint(str(page)), 0)
        code = ar.main(["roll", str(page)])
        self.assertEqual(code, 0)
        code = ar.main(["resolve", str(ROOT / "examples" / "shelf-clash.html"), str(ROOT / "examples" / "intents.json")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
