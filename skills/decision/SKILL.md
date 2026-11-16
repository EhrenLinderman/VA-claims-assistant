---
name: decision
description: >
  This skill should be used when a Veteran using VA Claims Assistant gets a VA decision
  letter, or says "I got my decision", "read my VA letter", "explain my rating", "what
  does my decision mean", "should I appeal", or "after the decision". It reads the
  rating decision, explains each rating in plain words, compares it with the claims,
  and shows next steps: reviews, new evidence, dependents and other benefits.
metadata:
  version: "0.14.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Step: After the Decision

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`.

`T="${CLAUDE_PLUGIN_ROOT}/skills/decision/scripts/decision_tools.py"`,
`OUT=<claim folder>/VA-Claim-Output`, `F=$OUT/Claims/claims.json`.

## 1. Get the letter

Ask the Veteran to put the decision letter (PDF from VA.gov, or a scan) in their claim
folder, or to point to it. Read it only from their folder (stage it if it lives on their
computer). It stays in their folder; never copy it or its contents to the project.

## 2. Read it

`python3 -I "$T" parse --letter <letter> > <scratch>/decision.json`.
- Check the count against the letter's "Your Benefit Information" list. A scanned letter
  can misread numbers. Items with `ocr_fix` must be confirmed by looking at the page.
- Then `python3 -I "$T" compare --claims "$F" --decision <scratch>/decision.json --out "$OUT"`.
  This saves `decision` on claims.json and writes `My-Decision-Review.md` (an app page).
- Fix any wrong matches by hand before showing the review.

## 3. Show it (one screen)

- Combined rating, and permanent and total if granted.
- A table: what VA decided, the rating, and which claim it was.
- The review deadline in bold (one day before the 1-year anniversary of the letter).
- One line: "VA often splits one claim into several ratings, for example each motion of a
  hip, or each side."

## 4. Look at each flag (button screens, one per flag)

- **Denied:** read the reason in the letter.
  - If the app had not recommended it, say so plainly.
  - Otherwise name the missing piece (usually a current diagnosis or a doctor's opinion).
  - Buttons: **Plan a Supplemental Claim** / **Talk to a VSO** / **Let it go**.
- **0% or lower than expected:** put the letter's "a higher evaluation is not warranted
  unless…" criteria beside the Veteran's own saved answers (details answers, story, VA
  exam notes).
  - Suggest a review only when the Veteran's own facts meet the next level.
  - Say what new evidence would show it: a symptom log, a lay statement, a doctor's note, or a new exam.
  - Example: migraines at 0% because the exam marked no prostrating attacks, while the
    Veteran reported lying down about every 1 to 2 months. That is the 10% level, so it
    needs a headache log and a doctor's note. Offer to make the log now (`toolkit` → symptom log).
  - Never promise a result.
- **Removed but granted:** say what happened in one line. This is a lesson for the app,
  not a problem for the Veteran.
- **Not decided:** check whether it was on the claim form. If not, it can be filed now on a
  new 21-526EZ (the copy-paste guide still works).

Review options, in plain words:
- **Supplemental Claim (20-0995):** new and relevant evidence.
- **Higher-Level Review (20-0996):** a senior reviewer looks again at the same evidence; no new evidence.
- **Board Appeal (10182):** a Veterans Law Judge.

Recommend a VSO (free) for choosing between them. After the 1-year window, a
Supplemental Claim or an increase claim (21-526EZ) still works, but benefits start from
the new filing date.

## 5. Other benefits (checklist on the review page)

- Rated 30% or more: add dependents (21-686c). Within 1 year of the letter, VA can pay
  back to the effective date.
- Permanent and total: education benefits for dependents (DEA, Chapter 35), and other
  P&T benefits.
- Retirees with 20+ years and 50% or more: CRDP. Confirm with DFAS.
- VALife insurance; state Veteran benefits.

## 6. Finish

Buttons: **Start a Supplemental Claim plan** (route to details → writeups → evidence for
that condition, with the new evidence) / **Add dependents** (explain 21-686c) /
**Done for now**.

## Rules

- Explain; don't advise on legal strategy. The Veteran decides; a VSO can help for free.
- Never suggest overstating symptoms. Suggest a review only when the Veteran's own saved facts meet higher criteria.
- No app notices in filed documents; My-Decision-Review.md is an app page.
