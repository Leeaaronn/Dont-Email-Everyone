# Deferred items — Phase 6

Items discovered during execution that are out of scope for the plan that
found them. Each names the plan that should close it.

---

## D1 — Confirm the `\$` escape renders as a plain dollar sign, in a browser

**Raised by:** 06-07 Task 3
**Owner:** 06-08 or 06-09, whichever runs the next human-verify checkpoint

The 06-07 checkpoint found markdown pairing currency dollar signs as TeX math
delimiters and typesetting the contrasts table and the headline interval as
mathematics. The repair escapes every `$` in every markdown-rendered string
(`streamlit_app.markdown_safe`), and
`tests/test_app.py::test_no_markdown_string_carries_an_unescaped_dollar_sign`
holds the invariant at the source level.

**What is verified:** that no unescaped `$` reaches a markdown-rendered
element, and that the diagnosis is right — the reviewer's report carried
`−0.136525` with U+2212 MINUS SIGN, the glyph KaTeX emits inside math mode,
which is decisive that markdown/KaTeX is the renderer for these strings.

**What is not yet verified:** that the escaped page *looks* right. No human
has seen the post-fix render. Add to the next checkpoint's instructions:

1. Read the headline spend interval and all three spend cells of the
   contrasts table.
2. Confirm each shows a plain `$` and **no literal backslash**.
3. Confirm the bracket has its space back — `+$0.186063 [+$0.009240, ...]`,
   not `+$0.186063[+$0.009240, ...]`.

If any surface renders the backslash literally rather than consuming it, that
surface needs the non-markdown route rather than the escape. This is a display
repair on an already-correct value; it is not a figure change and does not
reach `plots.py`.
