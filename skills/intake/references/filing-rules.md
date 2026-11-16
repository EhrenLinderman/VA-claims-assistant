# Filing-Window Rules (reference)
<!-- JOSHUAONENINE -->

Use `scripts/filing_window.py` to calculate dates. Use this file to explain them,
or to calculate by hand **only if Python cannot run**. Always be conservative
when doing it by hand.

Sources: VA.gov pages on pre-discharge claims, effective dates, and Intent to File;
38 CFR 3.155 (Intent to File) and 3.400(b)(2) (effective dates). Checked 2026-10-05.

## Windows

| Window | When | What it means |
|---|---|---|
| Before BDD | More than 180 days before separation | Too early for BDD. Start gathering records now. BDD opens 180 days before separation. |
| BDD | 180 to 90 days before separation | File through Benefits Delivery at Discharge. Faster decisions. Must be available for VA exams within 45 days after filing. Must submit the Separation Health Assessment Part A (Self-Assessment). |
| Under 90 days | 1 to 89 days before separation | BDD is closed. They can still file a pre-discharge claim, but VA may not process it until after discharge. |
| First year | Separation day through 1 year after | A claim received within 1 year after separation can be paid back to the day after separation. |
| After first year | More than 1 year after separation | There is no deadline. Benefits generally start from the date VA receives the claim (or the Intent to File date). |

## BDD exclusions (they can't use BDD; they file the standard way)

- Need case management for a serious injury or illness, or are terminally ill
- Are getting treatment at a VA or military facility during the separation window
- Are waiting on a Character of Discharge determination
- Can't attend VA exams within 45 days after filing

## Intent to File (ITF)

- It sets a possible start date for benefits.
- After filing it, the Veteran has **1 year** to file the complete claim. If they do,
  the claim counts as filed on the ITF date.
- If the ITF is filed within the first year after separation, and the complete
  claim is filed before the ITF deadline, benefits can still start the day after
  separation.
- If the year passes without a complete claim, the ITF expires. File a new ITF.
- **How to file** (free, takes minutes):
  - Online: VA.gov → "Your intent to file a VA claim" (VA Form 21-0966)
  - Phone: VA benefits line **800-827-1000** (TTY 711)
  - Mail VA Form 21-0966, or go to a VA regional office
  - Or ask a VA-accredited representative or VSO to file it

## Conservative-date rules (always)

- "File no later than" = one day **before** the 1-year anniversary.
- Also show a **target date** 30 days earlier as a safety buffer.
- When two deadlines apply, show the one that protects the earliest effective date.
- Never tell a Veteran a deadline is later than these rules give.
- Always add: "VA counts the date it receives your filing. Filing online gives
  you proof right away."

## Timeline estimates (used by scripts/timeline.py)

- VA's average time to complete disability claims: **69.2 days (October 2026)**,
  from VA.gov "The VA claim process after you file your claim." Update `AVG_DAYS`
  in timeline.py when VA posts a newer figure.
- BDD: be available for VA exams for 45 days from the date you apply.
- 38 CFR 3.31: payment starts the first day of the month after the effective date.
- VA Form 21-8764: payments arrive at the start of each month for the prior month.
  The first payment comes after the decision, and back pay covers earlier months.
