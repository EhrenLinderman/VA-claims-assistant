---
name: cfr
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Get the latest VA rules" step, asks to "update the VA rules" or "check for CFR
  changes", or when another VA Claims Assistant step needs to look up 38 CFR Part 3
  (claims, service connection, presumptive conditions) or Part 4 (rating schedule,
  diagnostic codes). It checks eCFR for newer rules, keeps a dated local copy, and
  explains how to look things up in the built-in reference.
metadata:
  version: "0.3.0"
  author: "EhrenAL"
---
<!-- JOSHUAONENINE -->

# Step: Get the Latest VA Rules (38 CFR Parts 3 and 4)

**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`. Show the one-line bar at the top of this step's first screen (and each claim's first screen), and refresh My-Progress.html when anything changes.

## Part 1 — Run the step (Veteran-facing, about 1 minute)

Voice rules: plain language, short, calm. Don't show file paths or JSON.

1. Find `VA-Claim-Output/progress.json`. If it's missing, run `start` first.
   Set `cfr` to `in_progress`.
2. Say: "Checking for the newest VA rules. This takes a few seconds."
3. Run:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/cfr/scripts/cfr_update.py" \
     --bundled "${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/cfr" \
     --local "<vet folder>/VA-Claim-Output/VA-Rules"
   ```

4. Tell the Veteran based on `status` (write dates in words):
   - `up_to_date`: "You have the latest VA rules (current as of <as_of>)."
   - `updated`: "VA updated its rules since this app was made. I downloaded the new
     version (current as of <as_of>)."
   - `offline`: "I couldn't reach the government rules website, so I'll use the copy
     built into the app (current as of <as_of>). That's usually fine. You can try
     again later."
     If Python can't run at all, treat it as `offline` using the bundled copy.
5. Save in `progress.json`: `cfr` = `done`, plus `"rules": {"use_dir": ..., "as_of":
   ..., "checked": today}`, `current_step` = `records`, `updated` = today.
6. Ask: "Next up: Read your records. Ready?" → **Let's go** / **Take a break**.
   **Let's go** starts the `records` skill (if not installed: "That step is coming
   soon. Your progress is saved."). **Take a break** shows the TAKE A BREAK block
   from `${CLAUDE_PLUGIN_ROOT}/skills/start/references/notices.md`.

## Part 2 — How every step looks up the rules (internal)

Use the folder in `progress.json` → `rules.use_dir`. If it's missing, use
`${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/cfr`.

| Need | Open |
|---|---|
| Which claim type fits, and the three elements | `${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/claim-theories.md` |
| PACT Act conditions and locations (newer than the CFR text) | `${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/pact-act-supplement.md` |
| Find a section by topic | `<rules>/index.md` |
| Find a diagnostic code (DC) by condition name | `<rules>/diagnostic-codes.md` (search the name or common synonyms) |
| Read a section | `<rules>/part-3/3.309.md`, `<rules>/part-4/4.130.md`, etc. |

Rules for using the CFR:

- Search with `grep -ril "<term>" <rules>/part-3 <rules>/part-4` rather than
  loading whole folders. Read only the sections you need.
- Quote rule language exactly when it matters, and cite it as "38 CFR <section>".
- Part 4 rating rows look like `- <criteria> — **30%**`. Indented rows belong to the
  DC above them.
- Some tables exist only as images in eCFR (listed in `meta.json` →
  `image_only_tables`, e.g., the hearing-loss Tables VI, VIa, and VII in 4.85, and the
  vision tables in 4.76a and 4.77). For those, don't guess numbers. Explain that VA
  calculates the rating from test results (audiogram, eye exam), and link the eCFR
  page given in the file.
- When CFR text and `pact-act-supplement.md` differ, include the condition and cite
  both.
- Never present a rating percentage as a promise. Say "VA's rating criteria for
  this condition range from X% to Y%."

## Bundled copy

- 38 CFR Part 3 (Adjudication) and Part 4 (Schedule for Rating Disabilities),
  eCFR as of 2026-10-01: 405 sections and 729 diagnostic codes.
- Rebuild from eCFR XML with `scripts/cfr_convert.py` (see the script header).
