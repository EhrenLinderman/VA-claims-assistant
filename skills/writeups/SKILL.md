---
name: writeups
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Draft your statements" step, or says "write my statements", "draft my
  statement", "doctor's letter", "nexus letter", or "write up my claims". For each
  described claim it drafts the Veteran's personal statement (text for VA's online
  Lay/Witness Statement, VA Form 21-10210, plus a Word file to sign), reviews it
  claim by claim with buttons, and prepares a doctor's letter template for claims
  that still need a medical link.
metadata:
  version: "0.13.0"
  author: "EhrenAL"
---
<!-- JOSHUAONENINE -->

# Step: Draft Your Statements

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`. Every question needs a way out; every "what's next" moment is a button.
**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`.

Setup: `progress.json` → `writeups` = `in_progress`.
`W="${CLAUDE_PLUGIN_ROOT}/skills/writeups/scripts/writeups_tools.py"`,
`OUT=<claim folder>/VA-Claim-Output`, `F=$OUT/Claims/claims.json`, `I=$OUT/intake.json`,
`D="${CLAUDE_PLUGIN_ROOT}/skills/details/references/service-duties.json"`.

**Deadline check first.** Read `intake.json` → `filing_window.key_deadline`. If it is
within 45 days, show it at the top in bold (for example "BDD window closes Dec 1,
2026: 24 days left") and say statements can be filed with the claim or added later.

## A. Each claim (in order, skip removed claims)

1. Set `current_claim`, show the bar, then get the fact sheet:
   `python3 -I "$W" facts --claims "$F" --intake "$I" --duties "$D" --id <id>`.
2. **Write the statement yourself (Claude), from the fact sheet only.** Rules:
   - First person, the Veteran's voice, plain words, short paragraphs, 250–500 words.
   - Order: (1) who I am and what I'm claiming; (2) how it started in service and the
     duties that wore on it, with dates and places; (3) the story: what made it
     worse (waits, moves, missed diagnoses, surgeries, setbacks) with dates;
     (4) how it is now on typical days and bad days (flare-ups, devices,
     symptoms); (5) impact on work, family (including active things with the
     kids), and daily life, with the Veteran's example; (6) explanations of
     records that disagree (`contrary_explained`), in the Veteran's words;
     (7) for secondary claims, how the other condition caused or worsened it.
   - Use **only** facts in the sheet. Do not add diagnoses, numbers, or symptoms the
     Veteran didn't give. Don't ask for a rating, don't argue law, don't cite CFR.
   - Don't mention VA exam errors unless the Veteran asked for that.
   - Never call a delay malpractice or blame anyone.
   - No app notices, markers or credits in filed documents.
2b. **Depth check.** Save the draft to `<scratch>.txt`, then
   `python3 -I "$W" depth --claims "$F" --id <id> --text <scratch>.txt`.
   If `ok` is false, ask the `ask` questions first (one button screen, up to 3 questions,
   each with **Skip this one**). Typical answers make good buttons, for example
   "Weekly / Monthly / Rarely" for flare-ups. Then redraft with the new facts and save them
   to `details` (impact example, answers). Skipped answers are not saved. Never pad a
   statement to reach the word count; short and true beats long.
3. Show the draft in full (SendUserMessage), then ask: **Looks right** /
   **Change something** (they type it with Other) / **Skip for now**.
   - Change something → revise and show again.
   - Looks right → save:
     `python3 -I "$W" save --claims "$F" --id <id> --text <scratch>.txt --out "$OUT" --status done`
     (writes `Claims/<id-name>/Statement.txt` and `Statement.docx`; the certification
     and signature lines are added automatically).
   - Skip → leave it; it stays "not yet" on the status bar.
4. Doctor's letter, by `doctor_letter_level`:
   - `needed` → make the template:
     `python3 -I "$W" letter --claims "$F" --intake "$I" --duties "$D" --id <id> --out "$OUT"`.
     Tell the Veteran in one line: "A doctor's letter template is in this claim's
     folder. Take it to a doctor who knows your case; they review, edit and sign it.
     The opinion must be the doctor's own."
   - `optional` → the condition was diagnosed on active duty and the claim is filed
     early (BDD or within a year of discharge), so VA usually grants it without a letter.
     Ask: **Skip the letter (Recommended)** / **Make a template anyway**. Say: "If VA
     denies it, a doctor's letter is the first thing to add."
   - `no` → nothing.
5. Refresh My-Progress.html. Button: **Keep going (next: <name>)** / **➕ Add a claim** /
   **Take a break**.

## B. Finish

1. Show the board. List which claims have a doctor's letter template to take to a doctor.
2. `progress.json` → `writeups` = `done`, `current_step` = `evidence`.
3. Button: **Next: Build your claim packet** / **Take a break**.

## Deepen saved statements (any time)

`python3 -I "$W" depth --claims "$F" --out "$OUT"` lists every saved statement under 250
words or missing key parts. Offer buttons: **Deepen the short ones** (go claim by claim
through 2b → 3) / **They're fine** / **Take a break**.

## How the Veteran files these

- **Online:** paste `Statement.txt` into VA's online Lay/Witness Statement (VA Form
  21-10210) or upload the signed `Statement.docx` (saved as PDF) with the claim.
- **Mail:** print, sign and date `Statement.docx`.
- **Doctor's letter:** the doctor signs it; the Veteran uploads it as evidence.
