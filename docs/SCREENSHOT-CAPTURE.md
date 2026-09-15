# Screenshot capture recipe

Two images live in this directory and both are published claims about what the deployed
app shows:

| File | What it must show |
|---|---|
| `app_headline.png` | the app's bordered headline container, whole |
| `app_policy_curve.png` | the spend policy curve, with its legend and its caption line |

They exist because Streamlit Community Cloud sleeps an app after 12 hours without traffic
and does not wake it on its own. The first reviewer to open this repository is likely to
be the visitor who resets that clock, and a sleep page is not a result. These images are
what a reviewer sees when the app is asleep, so they carry the project's headline finding
on their own.

This file is a procedure, not a description of one. Someone regenerating these images in
six months has to land on the same picture, and an unreproducible published claim is one
nobody can correct.

---

## 1. Source

**Preferred: the live app** — <https://dont-email-everyone-hillstrom.streamlit.app/>

The image's claim is *this is the deployed app*, so the deployed app is what should be
photographed. If it shows the sleep page, click **"Yes, get this app back up!"** and wait
a few seconds.

**Acceptable fallback: local.**

```
.venv/Scripts/python.exe -m streamlit run streamlit_app.py
```

Same code, same committed artifacts, same display cap, so the picture is the same picture.
Use it if Community Cloud is unavailable.

**Record which one was used** in the capture record at the foot of this file. The two are
equivalent for what is in frame, but a reader deserves to know whether they are looking at
the deployment or at a local run of the same commit.

> **Before visiting the live app, check whether a cold-start observation is outstanding.**
> Every visit resets the 12-hour sleep clock. If Phase 6's cold-start verification has not
> yet been recorded, opening the app to take a screenshot destroys the evidence that
> verification needs and pushes it out another 12 hours. Observe the sleep page first,
> record it, and only then wake the app and capture.

## 2. Page state

**Browser zoom at 100%.** Anything else rescales the type and the image stops being
evidence about what a visitor sees.

**Leave the targeting-depth control alone.** The app opens on `economics.HEADLINE_CAPACITY
= 0.20`, the pre-registered 20% anchor, and first paint *is* the anchor — no interaction is
needed to reach it.

Moving that control before capturing is the one edit that silently invalidates every
provenance assertion plan 07-03 writes. Those assertions derive the README's numbers from
`manifest.json` at `frame.capacity_k`, which is the 20% depth. An image captured at any
other depth shows numbers that are correct for the app and wrong for the README, and
nothing in the test suite can see the difference — the image is not machine-readable. The
control stays at its default.

## 3. Window width

`FIGURE_DISPLAY_WIDTH_PX = 1100` (`streamlit_app.py`) is a **cap, not a floor**.
`st.pyplot` clamps an integer width to the parent container, so a window narrower than the
cap makes the figure narrower than 1100 and the capture no longer shows what the cap
delivers. It shows what the window happened to allow.

So the capture must be taken **at** the viewport width where the cap **binds** — where the
container is just wide enough that the figure stops growing. Not below it, and — this is
the part that is easy to get wrong — **not far above it either**.

> **Do not capture maximized on a wide monitor.** `st.pyplot` is capped at 1100 px, but
> `st.caption` is **not** — it is an ordinary text element that fills the whole container.
> On a 2560 px monitor the container is roughly 2090 px, so the caption stretches to
> ~2090 px while the figure stays at 1100. No crop contains both: tight around the figure
> cuts the caption off, and wide enough for the caption strands a 1100 px chart in
> whitespace. This was hit for real during the 2026-09-15 capture and cost a re-shoot.
>
> At the binding width the container is only slightly wider than the figure, so the caption
> wraps to roughly the figure's own width and sits in a tidy block beneath it. That is the
> width where one crop gets the subheader, the figure, the legend and the caption together.

**Measure it, do not assume it.** The procedure:

1. Open the app and find the spend policy curve.
2. **Narrow** the browser window until the whitespace to the right of the chart disappears
   and the figure just starts to shrink; then widen back a little, until it stops growing.
3. That is the cap binding. The figure is at its full 1100 px and the container is as
   close to it as it gets.
4. Record that width in the capture record. (F12 shows the viewport size in the top-right
   corner while dragging, if an exact number is wanted.)

The one measurement on record: `quick-260912-jil` verified in a real browser
(`innerWidth` 2560, `devicePixelRatio` 1) that a 2560 px viewport yields roughly **2090
CSS px** of container. That is 235 px of furniture per side, which implies the cap binds
somewhere near a **1570 px viewport** — but that is one data point extrapolated by a
subtraction, and Streamlit's wide-layout padding is not guaranteed to be constant across
widths or versions. Treat 1570 as where to start looking, never as the answer, and write
down what was actually observed.

### What "legible" means here, in numbers

At the 1100 px cap, measured through the raster `st.pyplot` actually ships
(`quick-260913-knu`, 2026-09-13):

| display width | policy ticks | legend entries | vs. 16.00 px body text |
|---|---|---|---|
| 730 (the superseded cap) | 13.35 / 13.41 px | 10.01 px | legend 0.63x — rejected as marginal |
| **1100 (shipped)** | **20.11 / 20.20 px** | **15.09 px** | legend 0.94x, ticks 1.26x |
| 1235 | 22.58 / 22.68 px | 16.94 px | legend 1.06x — exceeds body text |

The binding constraint is the legend, not the ticks. If the legend in the captured image
looks smaller than the page's body text, the cap did not bind and the window was too
narrow — go back to step 3.

## 4. Crops

Both crops are bounded **by element**, never by pixel coordinates. Pixel bounds do not
survive a font change, a Streamlit version bump or a different display.

### `app_headline.png`

The bordered container, whole. **Its border is the crop boundary** — convenient, and not a
coincidence: it is the app's only bordered container, so there is nothing to mistake it
for.

All six children must be inside the crop, in this order
(`streamlit_app.py`, the `st.container(border=True)` block):

1. the **Recommendation** line — the send budget, the list size, the top-20% rule
2. the grey caption beginning "Both numbers below come from the same experiment"
3. the **extra revenue** metric, its "95% interval ..." line, its verdict line, its caption
4. the **extra site visits** metric, its "95% interval ..." line, its verdict line, its caption

Both verdict lines and both small grey captions are inside the crop. The verdicts are the
point of the image — a pair of numbers without them is the headline this project exists
not to publish.

### `app_policy_curve.png`

The **spend** policy curve, beneath the subheader "Where the gain is, and is not,
detectable". Spend, not visits: spend is the weaker of the two results and the decision on
record is that the weaker result must not be reachable only by scrolling.

The crop includes the figure, **its legend**, and **the `curve_caption` line directly
below it**. The caption is not optional — it carries the zero-by-construction explanation
for the orange square, and a figure cropped away from that explanation reads as a bug in
the chart.

## 5. What must not be in frame

This repository is **public**, and none of this is recoverable once pushed.

- no browser chrome of any kind
- no address bar — a URL bar can carry a `file:///C:/Users/<name>/` path
- no bookmarks bar
- no tab strip
- no OS window title bar — it can carry a machine name
- no taskbar or dock
- no notification pop-up

Check both images against this list *before* saving them, not after committing them.

## 6. Staleness

**There is no honest automated test that these images are current.**

Detecting a stale screenshot means reading the numbers out of a raster, and reading
numbers out of a raster means OCR, which means a dependency this project's library
constraint does not permit and would not want. Every cheaper substitute was considered and
each one is a test that fails on correct code:

- *Compare the image's commit date against `streamlit_app.py`'s.* Fails on a comment-only
  edit to the app, which changes no pixel. `tests/test_reports.py` already recorded what
  happens to a test that fails on correct code: it gets deleted, and the artifact ends up
  with no coverage at all.
- *Compare image bytes against a recorded checksum.* Pins nothing about the content and
  fails the moment anyone recompresses the file.
- *Assert the image's dimensions.* True of any image of that size, including a stale one.

What is done instead is a **coupling rather than a detector**. The README restates, in text
immediately beside each image, the numbers that image shows — and those restated numbers
are derived from `manifest.json` at test time by
`tests/test_readme.py::test_readme_headline_numbers_trace_to_the_manifest` (plan 07-03). If
a published number moves, that test fails, and whoever repairs the caption is standing in
front of the image with the old number in it. The image is not watched; the claim beside it
is, and the repair path runs through the image.

The standing manual check, which takes one command:

```
git log --oneline <recorded-capture-sha>..HEAD -- streamlit_app.py
```

Empty output means the app's source has not moved since capture. Non-empty output means
read the commits and decide whether any of them changed what is in frame.

`tests/test_readme.py` asserts only that the recorded SHA is a real commit in this
repository's history — it proves the record is **real**, not that it is **current**, and
that distinction is the whole of what it claims.

---

## Capture record

Filled in at capture time. The SHA is what makes the staleness check above runnable.

| Field | Value |
|---|---|
| Date captured | **2026-09-15** |
| Source used | **the live app** — <https://dont-email-everyone-hillstrom.streamlit.app/> |
| Browser | not recorded at capture time |
| Browser zoom | **100%** |
| Window width at capture | **~1600 px**, the width at which the 1100 px cap binds |
| `streamlit_app.py` at capture | **`4833d67e781da968575a4dba43506c6a6b53f070`** |

```
git log -1 --format=%H -- streamlit_app.py
```

Confirmed at capture time:

- [x] the six headline numbers in frame matched the working tree's published values
- [x] both verdict lines are legible in `app_headline.png`
- [x] the legend and the caption line are inside `app_policy_curve.png`
- [x] neither image contains browser chrome, a window title, a taskbar or a notification

Produced: `app_headline.png` at 1127x604, `app_policy_curve.png` at 1226x910.

The window width is recorded as approximate because that is how it was measured — by
dragging to the binding point rather than by setting a number. The binding point is the
reproducible target; 1600 is where it fell on this monitor, and a different browser's
furniture will move it slightly without changing the picture.

The headline capture includes the page title and standfirst above the bordered container.
That is wider than the crop this recipe specifies and it was kept deliberately: the image
is displayed standalone at the top of the README, where the title gives it context that the
bare container would not have.

Both images were checked against `data/processed/manifest.json` after capture, not only by
eye. The headline's six values and the curve legend's `+$0.1016 (95% band -$0.0299 to
+$0.3034)` agree with the committed manifest.

### Capture history

| Date | What changed | Why |
|---|---|---|
| 2026-09-15 | first capture | — |
| 2026-09-15 | `app_policy_curve.png` re-shot | the first attempt was taken maximized on a 2560 px monitor, where the uncapped caption stretches to ~2090 px while the figure stays at 1100, so no crop held both. Re-taken at the binding width. See the warning in §3. |
