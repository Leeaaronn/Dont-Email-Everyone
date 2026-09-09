- [04-06] STATE.md frontmatter `progress.percent` and the body progress bar disagree (43 vs 88%).
  `state.update-progress` writes the bar from completed plans (23/26 = 88%) while the frontmatter
  `percent` is recomputed elsewhere from completed phases (3/7 = 43%). Pre-existing SDK
  inconsistency, out of scope for this plan; the body bar and ROADMAP row are both correct.
