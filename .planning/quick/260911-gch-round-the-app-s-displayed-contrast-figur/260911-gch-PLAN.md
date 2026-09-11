---
phase: quick-260911-gch
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - streamlit_app.py
  - tests/test_app.py
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
autonomous: true
requirements: [UI-SPEC-V13, UI-SPEC-V14]

must_haves:
  truths:
    - "The app's headline spend metric reads +$0.102 at first paint, not +$0.101593"
    - "The app's headline visit metric reads +0.006 at first paint, not +0.006165"
    - "Every contrasts-table cell prints at three decimals, the same precision as the headline"
    - "reports/policy.md still carries its six-decimal strings, unchanged on disk"
    - "The full tests/test_app.py suite is green with no -m deselection"
    - "V14 still fails if the app publishes a number reports/policy.md does not carry at any precision"
  artifacts:
    - path: "streamlit_app.py"
      provides: "display_value at three decimals, both formats, one code path"
      contains: ",.3f"
    - path: "tests/test_app.py"
      provides: "_money/_rate transcriptions at three decimals plus V14's rounding arm"
      contains: "_report_roundings"
    - path: ".planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md"
      provides: "dated in-place amendment of Numbers Discipline and contract statement V14"
      contains: "Amended 2026-09-11"
  key_links:
    - from: "streamlit_app.py::display_value"
      to: "streamlit_app.py::contrasts_table and the headline block"
      via: "single shared formatter, no second format path"
      pattern: "display_value\\("
    - from: "tests/test_app.py::_report_roundings"
      to: "tests/test_app.py::test_first_paint_numbers_appear_verbatim_in_the_policy_report"
      via: "the second admission arm of the per-number rule"
      pattern: "_report_roundings\\(report\\)"
---

<objective>
Round the Streamlit app's displayed contrast figures from six decimals to three, in the
one function that formats them, and repair the two test contracts and the one design
document that pin the six-decimal convention.

Purpose: the headline figures display six decimals (`+$0.101593`, `+0.006165`) on
quantities whose intervals span `-$0.03` to `+$0.30`. That precision is not supported by
the data and reads as false confidence.

Output: `streamlit_app.py::display_value` at three decimals for both formats; a V14 that
still has teeth over a rounding app; `06-UI-SPEC.md` amended in place with a dated note.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md

@streamlit_app.py
@tests/test_app.py
@.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md

<scope_boundary>
DISPLAY LAYER ONLY. Explicitly forbidden by user decision, no exceptions:

- Any committed artifact under `data/`
- Any number in `reports/` — `reports/policy.md` KEEPS its six decimals
- `dont_email_everyone/plots.py` — the figures keep their own formatting
- `dont_email_everyone/pipeline.py` and every other package module
- `tests/test_reports.py::_money`-equivalents at lines 909-910 — those transcribe the
  REPORT's format, which is unchanged

After this change the app and the report print the same quantity to different precision
BY DESIGN. That divergence is the decision, not a defect to reconcile.
</scope_boundary>

<interfaces>
The two formats today, `streamlit_app.py` lines 467-469:

    if config.OUTCOMES[outcome] == CURRENCY_UNIT:
        sign = "-" if value < 0 else "+"
        return f"{sign}${abs(value):,.6f}"
    return f"{value:+.6f}"

Their test-side transcriptions, `tests/test_app.py` lines 845 and 850:

    return sign + "$" + format(abs(value), ",.6f")
    return format(value, "+.6f")

The collector regex V14 runs over rendered text, `tests/test_app.py` line 1628:

    NUMERIC_STRING = re.compile(r"[-+]?\$?\d[\d,]*(?:\.\d+)?%?")

The rounded forms of the two headline figures, computed against the committed
artifacts: `+$0.101593` -> `+$0.102`, `+0.006165` -> `+0.006`.

`reports/policy.md` carries no escaped dollar signs (`grep -c '\\$'` returns 0), so
`NUMERIC_STRING` reads its currency strings whole.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Round display_value to three decimals and rewrite its docstring around the reason</name>
  <files>streamlit_app.py</files>
  <action>
In `display_value` (around line 446), change both format specs to three decimals:
the currency branch becomes `f"{sign}${abs(value):,.3f}"` and the raw-rate branch
becomes `f"{value:+.3f}"`.

ROUND BY FORMAT SPEC, NEVER BY ARITHMETIC. Do not introduce `round()`, `* 1000`,
`/ 1000`, `Decimal.quantize` or any other operation on `value`. The precision change
happens inside the format string and nowhere else.
`test_app_performs_no_arithmetic_on_a_displayed_number` (V13) scans this module's
non-comment body for scaling tokens, and the spirit of that rule governs here: the app
formats an artifact cell, it does not compute one.

DO NOT ADD A SECOND FORMAT PATH. Both the headline block (around line 872) and
`contrasts_table` (around line 609) read through this one function, which is why one
edit covers both and why the same quantity cannot appear at two precisions on one page.
No new parameter, no per-call-site override, no precision argument.

Rewrite the docstring. It must carry the REASON, not just the new number:

  - The quantities being displayed have intervals spanning roughly `-$0.03` to `+$0.30`.
    Six decimals is precision the data does not support and reads as false confidence.
    Three decimals is the convention, chosen for that reason.
  - The raw-rate argument SURVIVES unchanged and must stay: the visit contrast is still
    displayed as the raw rate rather than percentage points, because `plots.py` owns
    axis scaling through its own unit-scale map and this module reproducing it would be
    a second place the grain could be wrong (Pitfall 8). Rounding changes the GRAIN OF
    THE DIGITS, not the unit.
  - The sign branch and `abs` still decide only where the sign character goes.
  - State the deliberate divergence: `reports/policy.md` §5 keeps six decimals and this
    module now prints three, so the two documents print one quantity at two precisions
    BY DESIGN. Name it as the decision so a later reader does not "fix" it.

Replace the stale illustrative string on the old line 455: `+0.006165` is no longer
what this function returns. The line currently claims it is "the string the evidence
document prints"; that clause is now false about the app and must go. Also retitle the
opening line — the function no longer formats "the way `reports/policy.md` §5 prints
it"; it formats the same VALUE at a coarser precision.

SWEEP THE REST OF THE MODULE, BUT DO NOT BLANKET-REPLACE. Check every remaining
occurrence of a six-decimal literal and decide case by case:
  - `markdown_safe`'s docstring (around lines 476-495) quotes
    `+0.388832[+0.040390, +$0.757914]` and `-0.136525`. Those are the ACTUAL STRINGS of
    a past render bug the 06-07 checkpoint found. They are history and they STAY.
  - Any comment or docstring asserting what the app prints TODAY must be updated.
Run `grep -n '[-+$]\?[0-9]\.[0-9]\{6\}' streamlit_app.py` and resolve every hit under
that rule before finishing.

Expect `tests/test_app.py` to be RED after this task. That is by construction — the
suite pins the old convention and Task 2 moves it.
  </action>
  <verify>
    <automated>python -c "import streamlit_app as a; d=chr(36); assert a.display_value('spend',0.101593)=='+'+d+'0.102', a.display_value('spend',0.101593); assert a.display_value('visit',0.006165)=='+0.006', a.display_value('visit',0.006165); assert a.display_value('spend',-0.029911)=='-'+d+'0.030', a.display_value('spend',-0.029911); print('formats ok')"</automated>
    <automated>python -m pytest tests/test_app.py -k "no_arithmetic" -q</automated>
    <automated>python -c "import re,pathlib; body=pathlib.Path('streamlit_app.py').read_text(encoding='utf-8'); assert body.count(':,.3f')==1 and body.count(':+.3f')==1, 'expected exactly one currency and one rate three-decimal spec'; assert not re.search(r'round\(|[*/] ?1000', body), 'arithmetic rounding introduced'; print('format specs ok')"</automated>
  </verify>
  <done>
`display_value` returns `+$0.102` / `+0.006` / `-$0.030` for the three probe values.
V13's no-arithmetic scan still passes. Exactly two `.3f` specs exist in the module body
and no `round(`, `* 1000` or `/ 1000` was introduced. Every surviving six-decimal
literal in the file is documented history (the 06-07 render bug), not a claim about
today's output.
  </done>
</task>

<task type="auto">
  <name>Task 2: Move the test contract to three decimals and give V14 a rounding arm</name>
  <files>tests/test_app.py</files>
  <action>
THE TRANSCRIBED FORMATS (lines 837-851). `_money` and `_rate` are the contract's formats
TRANSCRIBED ON PURPOSE so the test never compares the app against itself. Move both to
three decimals: `format(abs(value), ",.3f")` and `format(value, "+.3f")`. Keep the
transcription discipline — do NOT replace either body with a call to
`streamlit_app.display_value`. Update both docstrings to say which convention they now
transcribe: the app's three-decimal display convention, which is deliberately NOT
`reports/policy.md` §5's six-decimal convention. `_money`'s current docstring claims
"the strings below are the ones `reports/policy.md` section 5 prints" — that is now
false and is the sentence most likely to mislead the next reader.

V14 (`test_first_paint_numbers_appear_verbatim_in_the_policy_report`, line 2025).
KEEP THE TEST NAME. It is still a verbatim search — over the report's NUMBERS rather
than over the report's strings — and renaming it would break the user's own reference
and any `-k` selector. The rule changes, the name does not.

Its per-number rule becomes a two-arm admission. A number the app renders at first paint
is admitted if it is EITHER a string `reports/policy.md` carries verbatim, OR the
three-decimal rendering of a number `reports/policy.md` carries.

Implement the second arm GENERALLY, as a helper beside `_displayed_numbers`:

  - Sweep `NUMERIC_STRING` over the full report text.
  - Skip any match ending in `%`. The percentage convention is a different grain and is
    already handled by `POLICY_REPORT_ALLOWLIST`; admitting it here would let a
    percentage's digits launder a rate.
  - Strip `$` and `,`, parse to `float`, skip anything that will not parse.
  - Add BOTH `_money(value)` and `_rate(value)` to the admitted set — the two
    transcribed conventions, so the arm is built from the contract's formats and not
    from the app's.
  - Name it `_report_roundings(report)` and give it a docstring stating
    the property it preserves: the app never publishes a quantity the evidence document
    does not carry; it may publish it at coarser grain.

Then `missing` excludes numbers found in `_report_roundings(report)` as well as those
found verbatim and those in the allowlist. Update the assertion message so it names the
new arm — a reviewer reading a V14 failure needs to know that "round it" is not a repair.

DO NOT weaken V14 to a tolerance comparison, and DO NOT add the six rounded headline and
bound strings to `POLICY_REPORT_ALLOWLIST` as hand-written literals. Both defeat the
point. The allowlist's two existing entries (`6.8%`, `139.7%`) are unrelated to this
change and STAY exactly as they are, including the block comment above them at line 1667
— extend that comment only to note that the allowlist is no longer the only non-verbatim
admission path.

KEEP THE PRECONDITIONS THAT MAKE THE REST NON-VACUOUS:
  - The `len(numbers) >= 20` collector check stays untouched.
  - The two named headline literals at line 2057 move to their rounded forms:
    `("+$0.102", "+0.006")`. They still fire when the collector stops reading the
    headline block. Update the assertion message: the old one says a failure may mean
    "the app is now publishing a rounded version of a figure the evidence document
    publishes in full", which is now the INTENDED state and would misdirect the repair.

ADD ONE NEW PRECONDITION so the rounding arm cannot silently become dead code: assert
that `"+$0.102"` is NOT a substring of the report. If someone later rounds the report
too, the second arm stops being exercised and V14 quietly reverts to a verbatim-only
check; this assertion fails first and says so. Note in the same place that `+0.006` IS
an accidental substring of the report's `+0.006165`, so the rate strings would pass the
first arm on their own and the money strings are what prove the arm is load-bearing.

Rewrite V14's docstring. It currently opens "A SUBSTRING SEARCH, NOT A TOLERANCE" and
argues that a tolerance "would let the app round where the report does not". The app now
rounds where the report does not, on purpose, so that paragraph is the one thing in the
file most directly contradicted. The replacement must state: still not a tolerance — no
epsilon anywhere, every displayed number is matched against a SPECIFIC number the report
carries, either as its own string or as its three-decimal rendering — and state the
reason the app rounds (precision the data does not support).

THE OTHER COMMENTS. Check each six-decimal literal and do NOT blanket-replace:
  - Line 278 — "the headline figures are the one place in this app where a bare
    `+$0.101593` is correct" — asserts what the app prints TODAY. Update to `+$0.102`.
  - Line 1031 — "`+$0.101593` there is both correct and the string reports/policy.md
    prints" — asserts today's render AND claims it is the report's string. Update the
    literal to `+$0.102` and DROP the "and the string reports/policy.md prints" clause;
    it is no longer true and this is the exact sentence the divergence invalidates.
  - Line 1476 (`test_app_performs_no_arithmetic_on_a_displayed_number`) — "displayed as
    the RAW RATE, exactly as `reports/policy.md` section 5 prints it". The raw-rate half
    is still true and load-bearing; "exactly as ... prints it" is not. Amend the clause,
    keep the Pitfall 8 argument.
  - Lines 1006, 1008, 1011, 1061, 1737-1738 — the 06-07 render bug's actual strings
    (`+0.388832[+0.040390, +$0.757914]`, `-0.136525`, `+\$0.040390`). HISTORY. They stay.
Run `grep -n '[-+$]\?[0-9]\.[0-9]\{6\}' tests/test_app.py` and resolve every hit under
that rule.

`test_headline_tracks_the_committed_curve` (line 1077, `@pytest.mark.slow`) needs no
edit of its own — it formats through `_DISPLAY`, which is `_money`/`_rate` — but it IS
one of the tests this change breaks and it MUST be run. Its
`len(seen[outcome]) > 1` assertion survives rounding (the swept depths render distinct
three-decimal strings on both outcomes), but confirm it rather than assume it.
  </action>
  <verify>
    <automated>python -m pytest tests/test_app.py -q</automated>
    <automated>python -c "import pathlib; s=pathlib.Path('tests/test_app.py').read_text(encoding='utf-8'); assert 'def _report_roundings' in s, 'rounding helper missing'; assert s.count('_report_roundings')>=2, 'helper defined but never called'; assert ',.3f' in s and '+.3f' in s, 'transcribed formats not moved to three decimals'; print('rounding arm present')"</automated>
    <automated>python -m pytest tests/test_app.py -q -k "first_paint_numbers or headline_tracks" -p no:cacheprovider</automated>
  </verify>
  <done>
`python -m pytest tests/test_app.py` is green with NO `-m "not slow"` deselection, so
`test_headline_tracks_the_committed_curve` actually ran. V14 admits the rounded strings
through a general rounding arm, not through hand-written allowlist literals; its
`len(numbers) >= 20` check, its two (now rounded) headline literals and its new
arm-is-alive assertion are all present and firing. `_money`/`_rate` are still
transcriptions, not calls into `streamlit_app`. Every surviving six-decimal literal in
the file is 06-07 history.
  </done>
</task>

<task type="auto">
  <name>Task 3: Amend 06-UI-SPEC.md in place, dated, so the contract stops pinning six decimals</name>
  <files>.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md</files>
  <action>
Two things in this file are now wrong: `## Numbers Discipline` pins the six-decimal
formats, and contract statement V14 states a verbatim-match contract.

AMEND IN PLACE, LEGIBLY AS AN AMENDMENT. Match how the 06-07 checkpoint's amendments
were recorded in this project: an italic parenthetical carrying the date, the ORIGINAL
WORDING QUOTED, and the reason — the pattern used at lines 81, 344-345, 354, 361, 456-461
and 283. Do not rewrite the document's history and do not silently restate its numbers.

1. `## Numbers Discipline` — add a dated amendment note under the heading:
   - Dated 2026-09-11.
   - The change: both display formats move from six decimals to three.
   - The reason, which is the whole point of the note: the headline figures displayed
     six decimals on quantities whose intervals span roughly `-$0.03` to `+$0.30`. That
     precision is not supported by the data and reads as false confidence.
   - The scope: the app only. `reports/policy.md` keeps its six decimals, and the two
     documents now print one quantity at two precisions BY DESIGN.
   - One sentence disarming the rest of the file: the six-decimal strings elsewhere in
     this document (the Q1 worked-example table around lines 427-428, the shipped-cell
     row at line 220, the provenance table at lines 638-644) are ARTIFACT VALUES AS
     READ, not display strings, and are deliberately left as they were read on
     2026-09-10.

2. The pinned-format table at lines 625-626 — amend the two rows in place:
   `"$" + f"{v:+,.3f}"` -> `+$0.102` and `f"{v:+.3f}"` -> `+0.006`, each carrying a
   short italic "(Amended 2026-09-11 — was `,.6f` / `+0.101593`. See the note above.)".
   Leave the `capacity` and `counts` rows untouched.

3. The two element-spec rows at lines 504 and 509 (`3.3 value` and `3.7 value`) carry
   the same format expressions. Amend both the same way, same note.

4. Line 616's prose — "the visit contrast is displayed as the raw rate `+0.006165`
   exactly as `reports/policy.md` §5 prints it". The RAW-RATE claim survives and must
   stay (it is the Pitfall 8 argument and V13 still enforces it). The "exactly as §5
   prints it" clause does not. Amend so the sentence says: displayed as the raw rate
   `+0.006` — same grain as the report, coarser precision.

5. The "A test this enables" paragraph immediately under the format table, which says
   every numeric string "appears **verbatim**" and "the check is a substring search
   rather than a tolerance" — amend to the two-arm rule: every first-paint numeric
   string is either a string the report carries verbatim or the three-decimal rendering
   of a number the report carries. State that it is still not a tolerance.

6. Contract statement V14 at line 676 — amend the statement cell to the two-arm rule and
   the method cell to "substring search plus report-number rounding". Keep the row's
   position and its ID.

NOTHING ELSE IN THIS FILE CHANGES. No number is recomputed, no worked example is
restated, no provenance date is touched.
  </action>
  <verify>
    <automated>python -c "import pathlib; d=chr(36); s=pathlib.Path('.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md').read_text(encoding='utf-8'); assert s.count('Amended 2026-09-11')>=4, 'expected a dated note plus in-place amendments at the four format sites'; assert s.count(',.3f')>=2 and s.count('+.3f')>=2, 'format sites not moved to three decimals'; assert '+'+d+'0.102' in s and '+0.006 ' in s.replace(chr(96),' '), 'rounded worked examples missing'; print('numbers discipline amended')"</automated>
    <automated>python -c "s=[l for l in open('.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md',encoding='utf-8') if l.startswith('| V14')]; assert len(s)==1, s; assert 'round' in s[0].lower(), s[0]; print('V14 statement amended')"</automated>
    <automated>git diff --stat -- reports/ data/ dont_email_everyone/ | python -c "import sys; out=sys.stdin.read().strip(); assert out=='', 'out-of-scope files changed: '+out; print('scope boundary held')"</automated>
  </verify>
  <done>
`## Numbers Discipline` opens with a dated 2026-09-11 amendment note giving the reason
in the user's terms and scoping the change to the app. The four format sites (table rows
625-626, element rows 504 and 509) read `.3f` with their originals quoted. Line 616 keeps
the raw-rate argument and drops the "exactly as §5 prints it" clause. The enabling
paragraph and contract statement V14 both state the two-arm rule. The Q1 worked-example
table, the shipped-cell row and the provenance table are byte-identical.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| app -> public reviewer | The only boundary this change crosses. Displayed precision is a claim about evidential strength made to a reader who cannot check it. |
| app -> committed artifacts | Read-only, unchanged by this plan. No input crosses inward. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-QGCH-01 | Information disclosure (overstatement) | `display_value` | mitigate | Three decimals on quantities whose 95% intervals span ~0.33 in the same unit; the interval is displayed beside every point estimate at the same precision, so the reader sees the width. |
| T-QGCH-02 | Tampering | `test_first_paint_numbers_appear_verbatim_in_the_policy_report` | mitigate | The rounding arm is general (parse report -> re-render through the transcribed formats), never per-number literals, so it cannot be widened one string at a time. A dedicated assertion fails if the arm stops being exercised. |
| T-QGCH-03 | Repudiation | `06-UI-SPEC.md` | mitigate | Amended in place with the date, the original wording quoted and the reason, per the 06-07 precedent — the contract's history stays readable rather than being overwritten. |
| T-QGCH-SC | Tampering | npm/pip/cargo installs | accept | No package install task exists in this plan; no dependency is added or changed. |
</threat_model>

<verification>
1. `python -m pytest tests/test_app.py` — green, NO `-m` deselection, so the slow
   `test_headline_tracks_the_committed_curve` actually runs.
2. `python -m pytest` — the full suite green. `tests/test_reports.py` must pass
   untouched; it pins the REPORT's six-decimal convention and this plan does not move it.
3. `git status --porcelain data/ reports/ dont_email_everyone/` — EMPTY. Any hit here is
   a scope violation of the user's locked decision 4.
4. `git diff --stat` — exactly three files: `streamlit_app.py`, `tests/test_app.py`,
   `.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md`.
5. `grep -c '+\$0\.101593' reports/policy.md` — still non-zero. The report keeps its
   six decimals.
</verification>

<success_criteria>
- `display_value` returns `+$0.102` and `+0.006` for the two headline values, from two
  three-decimal format specs and no arithmetic on the value.
- The headline block and the contrasts table print the same quantity at the same
  precision, because both still read through the one formatter.
- `python -m pytest` is green across the whole repo with no marker deselection.
- V14 still fails if the app renders a number `reports/policy.md` does not carry at any
  precision; it was not weakened to a tolerance and grew no per-number literals.
- `06-UI-SPEC.md` reads as amended, dated 2026-09-11, with the originals quoted.
- Nothing under `data/`, `reports/` or `dont_email_everyone/` changed.
</success_criteria>

<commit_discipline>
Small, frequent commits — one per task, per this project's standing preference:
- Task 1: `fix(quick-gch): round the app's displayed contrasts to three decimals`
- Task 2: `test(quick-gch): move the display contract to three decimals and give V14 a rounding arm`
- Task 3: `docs(quick-gch): amend 06-UI-SPEC's numbers discipline and V14 in place`
</commit_discipline>

<output>
Create `.planning/quick/260911-gch-round-the-app-s-displayed-contrast-figur/260911-gch-SUMMARY.md` when done.
</output>
