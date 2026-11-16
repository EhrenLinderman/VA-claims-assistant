---
name: records
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Read your records" step, or says "add my medical records", "show you my
  records", "change my records folder", or "read my records". It has the Veteran
  pick the one folder that directly holds their medical records, checks that the
  folder looks right, and (in later versions) reads the records to build an
  evidence index.
metadata:
  version: "0.6.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Step: Read Your Records

Voice rules: plain language (about 8th-grade reading level), short, calm. Use
AskUserQuestion for every choice. Don't show file paths, JSON, or tool names.
Never search, browse, or list anything on the Veteran's computer outside the folders
they have chosen.

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`. Every question needs a way out (**None of these** / **Skip**); a skipped question saves nothing.

**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`. Show the one-line bar at the top of this step's first screen (and each claim's first screen), and refresh My-Progress.html when anything changes.

Before starting, find `VA-Claim-Output/progress.json` in the claim folder. If it's
missing, run `start` first. Set `records` to `in_progress`.
If `records_folder` is already set, show its name and ask: **Use this folder** /
**Pick a different folder**.

## Part A — Show the app where your medical records are

### A1. Explain (show this first)

"Now show the app where your **medical records** are.

Pick the folder that **directly holds your medical records**, the one you'd open to
see the record files themselves.

- ✅ Good: a folder like **My VA Records** or **Medical Records**. Subfolders inside
  it are fine, as long as they're all medical records.
- ❌ Avoid: a big folder with lots of other things in it, like Documents, Desktop,
  or Downloads.
- Only **your own** records. Keep a spouse's, child's, or parent's records out of it.

The app only reads files inside the folder you pick. It never changes them."

### A2. Where are they?

Ask with AskUserQuestion: "Where are your medical records right now?"

| Button | What to do |
|---|---|
| Inside my claim folder | The records sit somewhere inside the folder already chosen for the claim. Go to A3 (pick from inside). |
| In a different folder | Go to A4 (connect a folder). |
| In different places | Explain in short steps: make one new folder (suggest **My VA Records**), copy (don't move) your records into it, and leave out family members' records. Then ask "Ready?" → **Done, it's ready** (go to A4) / **Take a break**. |
| I don't have them yet | Say the app needs them to find claims. List where to get them: VA.gov (download your VA health records with Blue Button), service treatment records (request through VA.gov or milConnect), and private doctors' offices (ask for copies). Offer **Take a break**. Progress is saved. |

### A3. Pick from inside the claim folder

The Veteran already gave access to the claim folder, so listing **inside it only**
is OK.

1. List the folders **directly inside** the claim folder, not files and not deeper
   levels. Skip `VA-Claim-Output`.
2. Ask: "Which folder holds your medical records?" Show up to 3 folder names as
   buttons, plus **Not listed here**. (If there are more than 3, show the 3 whose
   names look most like records, and let the Veteran type the name in Other.)
3. After they pick, list the folders directly inside that one. If there are any,
   ask: "Are your records right here, or in a folder inside it?" →
   **Right here** / one button per subfolder (up to 3). Repeat until they choose
   **Right here**. Go one level at a time and never jump ahead.
4. **Not listed here:** go to A4.

### A4. Connect a folder (records are outside the claim folder)

Show the same three steps and pictures as the claim folder setup, with Step 3
worded for records:

1. **Step 1: Click the +** below the Reply box.
   Picture: `${CLAUDE_PLUGIN_ROOT}/skills/start/assets/add-folder-step1.png`
2. **Step 2: Click Add folder.**
   Picture: `${CLAUDE_PLUGIN_ROOT}/skills/start/assets/add-folder-step2.png`
3. **Step 3: A folder window opens.** Find the folder that **holds your medical
   records**. Click it once, then click **Select Folder**.

Then ask: **I added it** / **I need help** / **Take a break**. After **I added it**,
read back the folder name and confirm: **Yes, that's right** /
**Pick a different folder**. Use only the folder the Veteran confirms.

### A5. Quick check of the folder

Look at what's inside the chosen records folder (including subfolders) and count:
files by type (PDF, images, Word, text, other), subfolders, and any cloud-only
files (stored online and not downloaded yet).

Show a short summary in plain words, for example: "This folder has **42 files** (38
PDFs, 4 pictures) in **3 folders**." Then ask: "Does this folder hold only your
medical records?" → **Yes** / **Some other things are in here** /
**Pick a different folder**.

- **Some other things are in here:** offer **Pick a narrower folder** (go back to A3
  starting from this folder) or **Keep it. Skip anything that isn't medical.** If
  they keep it, record `skip_non_medical: true`.
- Warn gently if the folder looks too broad: more than 500 files, more than 25
  subfolders, or mostly non-record file types (music, video, program files). Say:
  "This looks like a big folder with more than medical records. Picking the folder
  that holds just your records will be faster and avoids mix-ups." Offer
  **Pick a narrower folder** / **It's fine, continue**.
- **Cloud-only files:** say "Some files are stored online (for example in OneDrive)
  and will be downloaded to your computer so the app can read them." Ask
  **OK, continue** / **Take a break**.

### A6. Save

1. In `progress.json`, set `records_folder` (and `skip_non_medical` if chosen) and
   `updated` = today.
2. In `VA-Claim-Output/READ-ME-FIRST.md`, replace the records-folder line with the
   chosen folder's name. Change nothing else.
3. Never create, rename, move, edit, or delete anything in the records folder.
4. Say: "Got it. Your records folder is **<name>**."

## Part B — Read the records and build the possible-claims list

Tell the Veteran: "Reading your records now. Big folders can take a few minutes.
I'll show you what I find." Work in a scratch folder (not the records folder).

### B1. Read every page

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/records/scripts"
python3 -I "$S/extract_pages.py" --records "<records folder>" --out pages.jsonl --expect-name "<Veteran's name>"
python3 -I "$S/dedupe_pages.py"  --pages pages.jsonl --out pages_dedup.jsonl
python3 -I "$S/condition_scan.py" --pages pages_dedup.jsonl \
  --terms "${CLAUDE_PLUGIN_ROOT}/skills/records/references/condition-terms.json" --out leads.json
```

- `extract_pages` reads text page by page and uses OCR (tesseract) only for pages with
  no text layer.
- `dedupe_pages` marks pages that are copies of another page (exact text, near-exact,
  or the same page re-saved in a different file) so each page counts once. It always
  keeps the first copy and cites only that one.
- `condition_scan` gives **leads** (possible conditions and their best pages). Leads
  are not diagnoses.
- Report the counts in plain words (pages read, copies set aside).

### B2. Review like a claims expert (Claude)

Read in this order and stop reading a condition once its three elements are covered:

1. **VA exams already done** (DBQs, Separation Health Assessment, DD 2807-1): they
   list current diagnoses, history, functional impact, and sometimes medical
   opinions. Note that checkboxes often can't be read in scanned text. Never infer a
   checked box. Ask the Veteran or view the page image instead.
2. **In-service proof** for each condition: operative reports, imaging, profiles,
   line-of-duty, sick call, post-deployment assessments.
3. **Service facts:** dates, deployments, exposures, cadet or academy service (counts
   as active duty, 38 CFR 3.6(b)(4)).

Use `${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/claim-theories.md`, the PACT
supplement, and the CFR files to decide the claim type and the rating codes.

### B3. One claim per condition. Earmark the evidence.

Write `VA-Claim-Output/Claims/claims.json` per
`${CLAUDE_PLUGIN_ROOT}/skills/records/references/claims-schema.md`:

- **One claim per condition**, no matter how many records mention it. Merge repeats.
- **One condition can have several separately rated parts** (for example, knee
  instability DC 5257 plus meniscus DC 5258/5259 plus limited motion DC 5260/5261).
  List them under `separate_parts` of the **same** claim. Never make duplicate claims.
- **One record can support several claims.** Cite it in each.
- For every claim, earmark 2–10 **key evidence** pages with a role (`diagnosis`,
  `in_service`, `nexus`, `severity`, `lay`, `contrary`) and a one-line "shows".
  Include contrary evidence honestly.
- Mark each of the three elements `found` / `partial` / `missing`, and the strength
  `strong` / `moderate` / `needs_more`.
- Add `questions_for_vet` for facts only the Veteran knows (prescribed brace? CPAP?
  prostrating headaches?).
- Put conditions with no current diagnosis under `not_recommended`, with the reason,
  and possible PACT Act or other leads under `possible_additional`.
- Add `record_flags` for privacy leaks (an SSN in a de-identified file), date
  conflicts, and duplicate files.
- Never invent a diagnosis, date, opinion or event. Cite only pages you read.

### B4. Verify, then build the Veteran's files

```bash
python3 -I "$S/verify_citations.py" --pages pages_dedup.jsonl --claims "<out>/Claims/claims.json" --fix
python3 -I "$S/build_package.py" --pages pages_dedup.jsonl --leads leads.json \
  --claims "<out>/Claims/claims.json" --out "<claim folder>/VA-Claim-Output"
```

Then keep the page text for later steps (it stays in the Veteran's own folder):
`gzip -c pages_dedup.jsonl > "<claim folder>/VA-Claim-Output/Evidence/page-text.jsonl.gz"`

Fix anything the verifier reports before continuing. This creates:
- `Possible-Claims.md`: the plain-language list for the Veteran (an app page with
  the free-use notice; not for filing).
- `Evidence/evidence-index.csv`: every page with kept/duplicate status, possible
  conditions, and which claims it is earmarked for.

Update `progress.json`: `records` = `done`, `current_step` = `claims`.

### B5. Show the Veteran

Show the summary table of possible claims (condition, type, strength), then any
**Things to check in your records** flags (privacy first). Say: "Next, you'll go
through these one at a time and confirm, change or remove each one, and add anything
I missed." Then ask **Let's review them** / **Take a break**. (If the `claims` skill
isn't installed yet: "Reviewing claims is coming soon. Your list is saved.")

## Always

- The records folder is **read-only**.
- If a document appears to belong to someone else (a different name or date of
  birth), never use it without asking the Veteran first.
- Offer **Take a break** whenever the Veteran seems tired or upset, and show the
  TAKE A BREAK block from `${CLAUDE_PLUGIN_ROOT}/skills/start/references/notices.md`.
