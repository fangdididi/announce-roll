---
name: announce-roll
description: >-
  Build an announcement directory of every interactive control a page would
  speak — role, spoken name, name source, landmark and heading — then mark
  each row CLEAR, WEAK, MUTE, CLASH or MASK. Resolve user intents to UNIQUE,
  AMBIGUOUS or MISSING so an agent clicks by one name instead of guessing
  from pixels or brittle CSS selectors. Use when a coding agent must operate
  a page, when you are making a UI agent-operable, or when duplicate “Edit”
  buttons and icon-only controls keep sending the wrong click.
---

# announce-roll

A page can look finished and still be impossible to drive by name. Two rows both say “Edit”. A trash-can icon says nothing. A button reads “Save changes” on screen while its spoken name is “Delete account”. People using a screen reader, speech input, or an agent that picks controls by role and name all hear the same directory — and they all get lost when that directory is mute, duplicated, or lying.

**announce-roll** reads HTML you already have (a saved page, a component fixture, or markup the agent just wrote) and builds that directory. It does not open a live browser, take screenshots, or rewrite the site for you. It tells you what the page would announce, where names collide, and whether a stated intent resolves to exactly one control.

## When to use

- An agent needs to click, fill, or follow something on a page and should address it by **role + spoken name**, not by CSS path or screenshot coordinates
- You are reviewing or writing UI and want every intended action to have **exactly one** announced name
- Duplicate actions (row-level Edit, icon toolbars, card menus) keep sending the agent to the wrong control
- Visible labels and programmatic names have drifted apart

Do **not** use this to crawl a site you do not own, to bypass bot checks, to drive a live authenticated session, or to audit visual design, color contrast, or interaction-state coverage — those are different jobs.

## Core idea

1. **Roll**: every interactive control becomes a row with a role, a spoken name, where that name came from, nearby heading and landmark, and a grade.
2. **Grades** describe the directory, not a ship/hold gate:
   - `CLEAR` — unique name from a solid source (contents, associated label, `alt`, or an override that still contains the visible words)
   - `WEAK` — a name exists only as `title`, `placeholder`, or an implicit browser fallback such as “Submit”
   - `MUTE` — nothing to announce
   - `CLASH` — another control shares the same role and normalized name
   - `MASK` — `aria-label` / `aria-labelledby` replaced the visible words, and those words are not inside the spoken name
3. **Intents** (optional): phrases a person would say (“Add to cart”, “Edit tea”). Each resolves to `UNIQUE`, `AMBIGUOUS`, or `MISSING`.
4. **Status** of the whole directory: `READY` (nothing to fix), `SOFT` (only weak names), or `REPAIR` (mute, clash, mask, or a failed intent).

The helper implements a practical naming walk: labelled-by references, then `aria-label`, then native label/`alt`/`value`, then contents, then `title` / `placeholder`, then a few implicit input names. It skips `hidden` nodes, `type="hidden"` inputs, and anything under `aria-hidden="true"`. It is a directory builder, not a full browser accessibility engine.

## Steps

1. Save the page or component as HTML you have the right to inspect. A single fixture is better than a production dump that includes other people’s private data.
2. List the actions the agent or user must be able to take. Put them in `templates/intents.json` as `{id, phrase, role}`. Roles are optional filters (`button`, `link`, `textbox`, `searchbox`, …).
3. Run the helper:

   ```bash
   python3 scripts/announceroll.py lint path/to/page.html
   python3 scripts/announceroll.py roll path/to/page.html
   python3 scripts/announceroll.py resolve path/to/page.html path/to/intents.json
   python3 scripts/announceroll.py demo
   ```

4. Read the roll top to bottom. For every `MUTE`, give the control visible text or a truthful spoken name. For every `CLASH`, include the row’s subject (“Edit tea”, not “Edit”). For every `MASK`, either drop the override or put the visible words inside the spoken name.
5. Re-run `resolve` until every listed intent is `UNIQUE` and the status is `READY` or an accepted `SOFT`.
6. When the agent later operates the live page, it should click by the directory’s role and name. If a name is still `AMBIGUOUS`, do not pick the first match and do not count siblings; go back to step 4.

### Exit codes

| Code | Status | Meaning |
| --- | --- | --- |
| `0` | `READY` or `SOFT` | Directory is usable; weak names are noted |
| `2` | `REPAIR` | Mute, clash, mask, or an intent that is not unique |
| `3` | — | File or intents JSON could not be read |

## Examples

**Two row actions named “Edit”.** The roll marks both `CLASH`. An intent `{phrase: "Edit", role: "button"}` is `AMBIGUOUS`. Repair: “Edit tea” and “Edit honey”, using the nearby heading or list text as the subject.

**Icon-only toolbar button.** The roll marks it `MUTE`. Repair: visible text, or an `aria-label` that says the action (“Search”, “Close”, “Share”) — not “icon” or “button2”.

**Visible “Save changes”, spoken “Delete account”.** The roll marks `MASK`. An intent for “Save changes” is `MISSING`, because a name-based agent never hears those words. Repair: announce “Save changes”, or change the visible label so both sides agree.

**Search field with `<label for="q">Search products</label>`.** The roll marks `CLEAR`, source `label`. The agent should fill `searchbox` “Search products”, not `#q`.

See `examples/shelf-clear.html`, `examples/shelf-clash.html`, `examples/shelf-mute.html`, and `examples/shelf-mask.html`.

## Tips

- Prefer visible words as the name. Overrides are for controls that truly have no text (icon-only, image).
- Unique among the same role is what matters. A `button` “Save” and a `link` “Save” do not clash with each other, but an intent that omits the role still might.
- `placeholder` and `title` keep the control off `MUTE`, yet they disappear or fail to translate — treat `WEAK` as unfinished labeling.
- Nearby headings belong in the directory so a repair can borrow “Billing” or “Tea” instead of inventing a new vocabulary.
- The helper does not see CSS `display:none` or names computed after JavaScript runs. If the live page builds controls in the client, save the rendered DOM (or the component’s fixture after it renders) and run the roll on that.
- Never paste secrets, session tokens, or other people’s personal data into a fixture just to build a roll.

## Helper

`scripts/announceroll.py` is Python 3 from the standard library: `lint`, `roll`, `resolve`, and `demo`. Add `--json` when another tool needs the directory as data. Run `python3 -m unittest discover -s tests -v` after you change naming rules.
