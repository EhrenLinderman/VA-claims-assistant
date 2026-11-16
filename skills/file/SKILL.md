---
name: file
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Final check & file" step, or says "final check", "am I ready to file", "how do I
  file", "submit my claim", or "file with VA". It checks every claim's statement,
  packet, quotes, rating codes and dates for problems, writes a filing checklist, and
  walks the Veteran through filing online, by mail, in person or with a VSO, or adding
  evidence to a claim already filed.
metadata:
  version: "0.13.0"
  author: "EhrenAL"
---
<!-- JOSHUAONENINE -->

# Step: Final Check & File

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`.
**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`.
Filing facts: `${CLAUDE_PLUGIN_ROOT}/skills/intake/references/filing-rules.md`.

Setup: `progress.json` → `file` = `in_progress`. `OUT=<claim folder>/VA-Claim-Output`,
`FC="${CLAUDE_PLUGIN_ROOT}/skills/file/scripts/final_check.py"`,
`DC="${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/cfr/diagnostic-codes.md"`.

## 1. Deadline first

Re-run the filing-window script for today's date (see the intake skill) and show the key
deadline in bold at the top, with the days left. If BDD has under 14 days left, say
plainly: "File first. Statements, doctor's letters and other evidence can be added
after you file."

## 2. Have you already filed?

Ask: **Not yet** / **Yes, my claim is pending** / **Yes, I got a decision**.

- **Not yet** → section 3.
- **Pending** → evidence can be added to the open claim: on VA.gov, go to "Check your
  claim or appeal status" and upload files to that claim. Statements and packets for
  conditions ALREADY on the claim go there. Conditions NOT on the claim need a new
  claim: list them, using the 526EZ list. Then go to section 3, which checks only those files.
- **Decision** → ask which conditions were denied or rated lower than expected. New and
  relevant evidence for a decided condition goes with a Supplemental Claim (VA Form
  20-0995), usually within 1 year of the decision to protect the effective date. Other
  review options are a Higher-Level Review (20-0996) or a Board appeal (10182); point the
  Veteran to a VSO to choose. New conditions go on a new 526EZ. Never guess the outcome.

## 3. Final check

`python3 "$FC" check --out "$OUT" --dc "$DC" --md`. It writes `My-Filing-Checklist.md`
in the claim folder (an app page; the free-use notice is on it).

Show one screen per level:
- **Fix before filing** (`fix`): each item with a button to fix it now, which goes to
  the right step (statement → writeups; packet or summary → evidence; code → claims),
  or **Skip**. After fixes, run the check again.
- **Take a look** (`check`): each item in plain words, with **It's fine** /
  **Fix it**. Date conflicts: open the record, statement and list, and ask which
  date is right. Don't guess.
- **Can follow the claim** (`todo`): doctor's letters and the like, in one list. "These
  can be added after you file."

## 3b. 526EZ copy-and-paste guide

One button screen (4 questions, each with **Skip**): retiring / separating / medical
retirement; place of separation (typed); deployment months (typed, or "years only");
filed a VA claim before? Save the answers in `intake.json` → `filing_answers` (never SSN,
date of birth, address, phone or bank). Then
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/file/scripts/ez_guide.py" build --out "$OUT" --answers <scratch>.json`
→ `Claims/526EZ-Copy-Paste-Guide.docx` (and `.md`). It covers every section of the form
in the paper form's item order and fills in what the app knows. Point out its notes:
- **20D:** in-service records from before the entry date (for example, academy cadet time).
- **Item 26:** retiree pay.
- **15A:** toxic exposure.

## 4. How to file (buttons)

Ask: **Online at VA.gov (recommended)** / **With a VSO (free help)** / **By mail** /
**In person**.

- **Online:** Your claim date is set when you start the online form. VA saves an
  unfinished application for up to 365 days. Walk through it once:
  1. Start the disability claim (21-526EZ) on VA.gov. For BDD, choose the pre-discharge
     (BDD) option.
  2. Follow `Claims/526EZ-Copy-Paste-Guide.docx`, section by section; enter each condition from its claim table.
  3. Mental health claims: answer the event questions with the 21-0781 worksheet.
  4. Upload each claim's `Evidence-Packet.pdf` and statement (paste `Statement.txt` into
     the Lay/Witness Statement (VA Form 21-10210), or upload the signed `Statement.docx`
     saved as a PDF).
  5. BDD: upload the Separation Health Assessment Part A (Self-Assessment). Online, VA
     gets your service treatment records for you.
  If an upload is refused for size, split that packet into two PDFs; the bookmarks and
  index still work.
- **VSO:** A VA-accredited Veterans Service Officer files for free. Bring the claim
  folder: the 526EZ list, statements, packets and worksheets.
- **Mail:** Print and sign the 21-526EZ, statements and forms. Mail them to the
  Department of Veterans Affairs, Claims Intake Center, PO Box 4444, Janesville, WI
  53547-4444. On paper, BDD claims must include a copy of the service treatment records.
- **In person:** Take everything to a VA regional office.

Always add: "VA counts the date it receives your claim. Filing online gives you proof
right away. For BDD, be available for VA exams for 45 days after you file."

## 5. After filing

- Upload signed doctor's letters when you get them. You have up to 1 year after VA
  receives your claim to add evidence.
- Go to every VA exam. Make an exam prep sheet for each condition first (`toolkit`), bring
  your statement, and describe bad days, not just today.
- Save the confirmation page or number in your claim folder.

## 6. Finish

`progress.json` → `file` = `done`. Refresh My-Progress.html and show the board.
Buttons: **I filed my claim** (save the date in `progress.json` → `filed_on`) /
**I'll file later** / **Show my checklist**.

## Rules

- Never file, sign or submit anything for the Veteran. The Veteran presses submit.
- Never enter the Veteran's SSN or account details anywhere; they type them on VA.gov.
- No app notices in filed documents; the checklist is an app page.
