---
name: evidence
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Build your claim packet" step, or says "build my packet", "evidence packet",
  "attach my records", or "pull my evidence". It copies ONLY the earmarked record
  pages for each claim into one PDF per claim, with a cover index and bookmarks,
  and saves it next to the claim's statement.
metadata:
  version: "0.13.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Step: Build Your Claim Packet

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`.
**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`.

Setup: `progress.json` → `evidence` = `in_progress`.
`B="${CLAUDE_PLUGIN_ROOT}/skills/evidence/scripts/build_packet.py"`,
`OUT=<claim folder>/VA-Claim-Output`, `F=$OUT/Claims/claims.json`,
`REC=<records folder from progress.json>`.

1. **Say what will happen** (one short screen): "I'll copy only the record pages we
   earmarked for each claim into one PDF per claim, with an index page. Nothing else
   from your records is copied." Button: **Build my packets** / **Take a break**.
2. **Get the source files.** `python3 "$B" check --claims "$F" --records "$REC"` lists the
   files needed. Read only those files from the Veteran's records folder (stage them if
   the records live on the Veteran's computer). Never read files outside that folder.
2b. **Claim Summary (each claim, in order).** `S="${CLAUDE_PLUGIN_ROOT}/skills/evidence/scripts/claim_summary.py"`,
   `P=$OUT/Evidence/page-text.jsonl.gz`. Draft the summary JSON yourself (Claude) from the
   claim's facts only (claims.json `details`, `story`, `evidence`, `dc`, the saved statement);
   the schema is in the script's docstring. Sections, in this order, titled exactly:
   Statement for Submission · Summary of Medical History with Extracts · CFR Aligned Rating
   Language (with Residuals) · Nexus / Service Connection Rationale · Functional Impact
   Statement · Substantial Record. Rules:
   - History groups follow the packet's page order (date order) and cite only this claim's
     packet pages. Up to 6 short quotes (≤ 40 words), copied **word for word** from the page
     text. `"..."` may join two exact pieces. Never write a quote from memory.
   - Rating language: what the records and the Veteran's answers show against each DC, in
     plain words. No percentages, no "I should be rated at".
   - Nexus: the three elements with page refs and the theory (direct 3.303, secondary 3.310,
     aggravation 3.306, presumptive 3.307/3.309). The medical link comes from the records or
     a doctor's letter; never claim a medical opinion that does not exist. No boilerplate
     like "no intercurrent injury" unless a record says so.
   - Strongest record: one page and one sentence on why.
   Check: `python3 -I "$S" verify --claims "$F" --id <id> --summary <scratch>.json --pages "$P"`.
   Fix every problem it lists, then `save` the same way. Show the Veteran the section titles
   and the quotes, with buttons: **Looks right** / **Change something** / **Skip summary**.
3. **Build:** `python3 "$B" build --claims "$F" --records "$REC" --out "$OUT"`
   (or `--id <id>` for one claim). Each packet is saved as
   `Claims/<id-name>/Evidence-Packet.pdf`.
4. **Verify (always).** For each packet, check every record page against the saved page
   text (`Evidence/page-text.jsonl.gz`) by word overlap, so the right pages went in.
   Render the cover of one packet and look at it.
5. **Show the result:** a short table of claims with page counts, and one line on how to
   file ("Upload each claim's Evidence-Packet.pdf with its statement").
   Pages the Veteran explained as wrong (`contrary`) are NOT added; VA already has
   them, and the statement explains them.
5b. **526EZ claim list.** `E="${CLAUDE_PLUGIN_ROOT}/skills/evidence/scripts/ez_list.py"`.
   `python3 -I "$E" draft --claims "$F" --duties "${CLAUDE_PLUGIN_ROOT}/skills/details/references/service-duties.json"`
   gives a first draft. Edit it (Claude): a clear condition name with its main diagnosis
   (≤ 45 characters), the cause in a few words (≤ 30), one short "how it relates" line
   (≤ 60, for example "torn meniscus as cadet; ACL tear on active duty 2020"), and the
   same start date the statement uses (MM/YYYY). Secondary claims say "..., SECONDARY TO
   <condition>". Save: `python3 -I "$E" save --claims "$F" --list <scratch>.json --out "$OUT"`
   (writes `Claims/526EZ-Claim-List.docx`). Show the list; buttons **Looks right** /
   **Change something**.
6. `progress.json` → `evidence` = `done`, `current_step` = `file`. Refresh
   My-Progress.html. Button: **Next: Final check & file** / **Take a break**.

## Rules

- Packets are filing documents: no app notices, credits or markers are added.
- Every quote in a Claim Summary must pass `verify`. A packet with a quote that is not in
  the records hurts the Veteran's credibility with the rater.
- Copy only earmarked pages. Never add family members' records or unrelated pages.
- If a source file is missing, say which one and offer to skip that claim for now.
