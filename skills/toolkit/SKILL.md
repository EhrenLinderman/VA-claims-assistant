---
name: toolkit
description: >
  This skill should be used when a Veteran using VA Claims Assistant wants to get ready
  for a VA exam, keep a symptom log, get a buddy statement, or hand their claim to a VSO,
  or says "exam prep", "C&P exam", "symptom log", "headache log", "buddy statement",
  "lay statement from my wife", or "send it to my VSO". It makes exam prep sheets,
  printable symptom logs, buddy statement guides with a witness form, and a VSO hand-off folder.
metadata:
  version: "0.16.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Toolkit: Exam Prep, Symptom Logs, Buddy Statements, VSO Hand-Off

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`.

`V="${CLAUDE_PLUGIN_ROOT}/skills/toolkit/scripts/vet_docs.py"`, `OUT=<claim folder>/VA-Claim-Output`,
`F=$OUT/Claims/claims.json`, `I=$OUT/intake.json`.

Start with: **What do you need?** → **Prep for a VA exam** / **Start a symptom log** /
**Get a buddy statement** / **Send it all to my VSO**. Then ask which claim(s), using the
confirmed claims as options (multiSelect, plus **All of them**).

## Exam prep sheet

`python3 -I "$V" exam --claims "$F" --id <id> --out "$OUT"` → `Claims/<id-name>/Exam-Prep.docx`.

The sheet covers:
- what VA's exam (DBQ) measures for that kind of condition (`references/exam-guide.json`);
- what to tell the examiner;
- the Veteran's own saved answers and key dates, as reminders;
- what to bring;
- what to do after.

Say in one line: "Read it the day before. Describe your typical and your bad days; be
honest and specific." Never coach anyone to exaggerate. The sheet only helps the Veteran
remember true facts.

## Symptom log

`python3 -I "$V" log --claims "$F" --id <id> --out "$OUT"` → `Claims/<id-name>/Symptom-Log.docx`.

- The kind is picked automatically: headaches, flare-ups, sleep, mental health, or general.
  Override with `--kind`.
- It is printable, about 8 weeks long, and ends with a certification and signature line, so
  it can be uploaded as evidence.
- It is most useful for conditions rated on how often things happen (migraines: prostrating
  attacks; flare-ups; sleep).

Tell the Veteran: "Fill in a line each time it happens. After a few weeks, upload the
signed log with your claim or review."

## Buddy statement guide

`python3 -I "$V" buddy --claims "$F" --id <id> --out "$OUT"` → `Claims/<id-name>/Buddy-Statement-Guide.docx`.

- **Part 1 (for the Veteran):** who makes a good witness, the rules, and how it's filed (VA
  Form 21-10210, online or PDF).
- **Part 2 (the witness form):** blanks for the witness to fill in and sign.

Never draft the witness's words. The statement must be their own account of what they saw.

## VSO hand-off folder

`python3 -I "$V" vso --claims "$F" --intake "$I" --out "$OUT"` → a `VSO-Handoff/` folder and
`VSO-Handoff.zip`.

It contains:
- a cover memo with the claims table and open items;
- the 526EZ guide and claim list;
- each claim's statement, packet, letters, worksheets, prep sheet, buddy guide and log;
- the filing checklist and decision review.

Originals are untouched; these are copies. Tell the Veteran: "This holds your medical
information. Give it only to your accredited representative, in person or through their
secure upload. Don't email it unencrypted." Make the folder fresh each time.

## Rules

- Logs, witness forms and the cover memo may be filed or shared, so they carry no app
  notices or code words. Prep sheets are for the Veteran only.
- Names are never stored. Every form has blanks to fill in by hand.
- Afterward, refresh the status page. Buttons: **Make another** / **Back to my claim** / **Take a break**.
