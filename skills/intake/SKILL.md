---
name: intake
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "About your service" step, or asks "when should I file", "what's my deadline",
  "intent to file", "BDD", or "update my service info". It asks a few button-based
  questions about service, calculates filing-window and Intent to File deadlines
  with a script, saves the answers, and writes a My Key Dates page.
metadata:
  version: "0.2.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Step: About Your Service (Intake + Key Dates)

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`. Every question needs a way out (**None of these** / **Skip**); a skipped question saves nothing.

**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`. Show the one-line bar at the top of this step's first screen (and each claim's first screen), and refresh My-Progress.html when anything changes.

Follow the same voice rules as the opening screen: plain language (about 8th-grade
reading level), short sentences, warm and calm. Use AskUserQuestion for every
choice (up to 4 questions per call; labels 1–5 words). Never show file paths,
JSON, or tool names to the Veteran. Every question can be skipped — never insist.

Before starting, find `VA-Claim-Output/progress.json` in the connected folder. If it
is missing, run the `start` skill first. Set `intake` to `in_progress`.
If `VA-Claim-Output/intake.json` already exists, show a short summary of the saved
answers and ask: **Keep these** (go to Part D) / **Update them** (go to Part A).

Tell the Veteran: "A few quick questions about your service. This takes about
3 minutes. You can skip anything."

## Part A — Service basics (one AskUserQuestion call, 3 questions)

1. "Where are you in your service right now?" → **Still on active duty** /
   **Already separated** / **Guard or Reserve** / **Not sure**
2. "Which branch?" → **Army** / **Navy** / **Air Force** / **Marine Corps**
   (Other covers Space Force, Coast Guard, and anything else.)
3. "How did you (or will you) leave the service?" → **Honorable** /
   **General** / **Other than honorable** / **Prefer not to say**
   - If the Veteran picks **Other than honorable**, add a short, kind note: "You may
     still qualify. VA decides this case by case, and a free accredited
     representative can help." Never suggest they won't qualify.
   - If they're still serving, record `still_serving`.

## Part B — Dates (ask in plain words, then confirm)

1. Ask for the **separation date** (past, or expected if still serving). Accept any
   format ("March 2026", "3/1/26"). If they give only a month and year, use the
   **last day** of that month for a future date and the **first day** for a past
   date, set `separation_date_is_estimate` to true, and say you're estimating.
2. Read the date back in words and confirm with buttons: **That's right** / **Fix it**.
3. Ask for the year and month they **entered service** (optional; skip allowed).

## Part C — Exposures, rating, and Intent to File (one AskUserQuestion call)

1. "Did you ever serve in any of these places **during these years**? Pick all that
   apply." (multiSelect). Show the years on every button:
   - **Gulf War / Middle East (Aug 1990–now)**: Iraq, Kuwait, Saudi Arabia, Bahrain,
     Qatar, UAE, Oman, Somalia (Aug 2, 1990 or later); Afghanistan, Syria, Djibouti,
     Uzbekistan, Egypt, Jordan, Lebanon, Yemen (Sept 11, 2001 or later); and the
     airspace above them.
   - **Vietnam era sites (1962–1980)**: Vietnam (1/1962–5/1975), Thailand bases
     (1/1962–6/1976), Korea DMZ (4/1968–8/1971), Laos (12/1965–9/1969), Cambodia
     (4/1969), Guam or American Samoa (1/1962–7/1980), Johnston Atoll (1/1972–9/1977).
   - **Camp Lejeune (Aug 1953–Dec 1987)**: 30+ days at Camp Lejeune or MCAS New River.
   - **Radiation exposure**: nuclear tests, Hiroshima/Nagasaki occupation, Enewetak
     cleanup (1977–1980), Palomares, Spain (1966–1967), Thule, Greenland (1968).
   Explain before asking: "These are VA's official places and years where certain
   conditions are **automatically linked** to service (set by law). Served somewhere
   else? That still counts. You'll list it in the next question." Skipping means none.
   Store as `southwest_asia`, `agent_orange_locations`, `camp_lejeune`, `radiation`,
   or `other:<text>`.
   **1b. Other places:** Right after, ask: "Where else did you deploy or serve? List
   any countries, bases, or missions (for example: Kosovo, Germany, Djibouti, a ship,
   Africa). Any exposures you remember, like burn pits, fuel, noise, or chemicals?"
   → **I'll type them** (use Other) / **None** / **Skip for now**.
   If an answer is broad (like "Africa" or "Middle East"), ask once which country,
   because some are on VA's list (Djibouti, Somalia, Egypt, and others). If it matches
   the list and years, add it to `exposure_locations` and tell the Veteran.
   Store each entry in `other_service_locations` and `exposures_reported`. Say: "Thanks.
   These aren't on VA's automatic list, but they can still support a claim. We'll
   look for them in your records."
   **Date check (backup, gentle):** The Agent Orange locations count only for certain years
   (Vietnam 1962–1975, Korea DMZ 1968–1971, Thailand 1962–1976, and the other places
   through 1980 at the latest). Camp Lejeune counts for 1953–1987. If the service
   dates show the Veteran couldn't have been there during those years, ask kindly:
   "Those places only count for certain years (for example, Vietnam 1962–1975). Were
   you there during those years?" → **Yes** / **No, it was later** / **Not sure**.
   If **No, it was later**, store it as `other:<place>, <years>` and say: "Thanks.
   The automatic link doesn't apply for those years, but you can still claim
   conditions connected to your service the regular way."
2. "Do you have a VA disability rating now?" → **No rating yet** / **Yes, I have one** /
   **I was denied before** / **Not sure**
   - If **Yes**: ask their combined percent and which conditions are already
     service-connected (plain text, optional). Say: "Conditions caused by these may
     also qualify. We'll check for that later."
3. "Have you filed an Intent to File?" → **Yes, I filed one** / **No, not yet** /
   **What is that?** / **Not sure**
   - **Yes:** ask for the date and confirm it.
   - **What is that?:** explain in 2–3 sentences using
     `${CLAUDE_PLUGIN_ROOT}/skills/intake/references/filing-rules.md`, then ask again.
   - **Not sure:** suggest they check VA.gov or call 800-827-1000; treat as not filed.

## Part D — Calculate the key dates (always use the script)

Run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/intake/scripts/filing_window.py" \
  --separation YYYY-MM-DD [--itf YYYY-MM-DD]
```

- Use the script's output exactly. **Never** compute deadlines in your head when the
  script can run.
- If Python cannot run, calculate by hand from `filing-rules.md`, follow its
  conservative-date rules, and tell the Veteran: "Please double-check these dates
  on VA.gov."
- If there is no separation date (skipped), skip the calculation and explain that
  deadlines depend on it.

Show the Veteran, in this order:

1. **Your most important date (always first):** the `key_deadline` label, date (in
   words), days left, and the 30-day target date.
2. **What this window means**, in plain words:
   - `bdd`:
     - **What BDD is:** "BDD stands for Benefits Delivery at Discharge. It lets you
       file your claim while you're still in uniform, 180 to 90 days before you
       separate."
     - **Why it matters:** "VA starts working on your claim before you leave. Your
       exams can happen while you're still on duty, near medical care you already
       have, and you may get a decision soon after you separate, instead of waiting
       months with no VA pay."
     - **What you need:** be available for VA exams within 45 days after filing;
       submit the Separation Health Assessment Part A (Self-Assessment); provide
       service treatment records if not filing online.
     - **Who can't use BDD:** the exclusions from `filing-rules.md`.
     - **If you miss it:** "You can still file before you separate, or any time in the
       year after. If you file by <one-year NLT>, your benefits can still start the
       day after you separate. You'd just likely wait longer for a decision."
   - `before_bdd`: when BDD opens and closes, the same what-it-is and why-it-matters
     lines, and "Good time to gather your records."
   - `pre_discharge_under_90`: when BDD closed; they can still file a pre-discharge
     claim, but VA may not process it until after discharge; the one-year date.
   - `first_year` / `after_first_year`: the `summary` in plain words.
3. **All your dates** in a short table with plain labels (BDD closes, Separation,
   Benefits can start (day after separation), Last day to file and keep that start
   date).
4. **Your timeline (picture):** run

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/intake/scripts/timeline.py" \
     --separation YYYY-MM-DD [--itf YYYY-MM-DD] [--file-by YYYY-MM-DD] \
     --svg "<claim folder>/VA-Claim-Output/My-Claim-Timeline.svg"
   ```

   Show the picture. It covers building the claim, the goal filing date, the BDD
   window, VA exams, separation, the expected rating decision, when benefits start,
   and the approximate first payment. Then explain in one or two lines:
   - "Dates after you file are **estimates**. VA's average to decide a claim was
     about 68 days in September 2026. Yours may be faster or slower."
   - "VA pays at the start of each month for the month before. If your decision
     comes later, you get back pay to your start date."
   If the Veteran wants a different goal date, rerun with `--file-by`.
5. End with: "VA counts the date it receives your filing. Filing online gives you
   proof right away."

## Part E — Intent to File prompt

If the ITF was not filed, or it has expired (`file_itf_now`, `file_new_itf_now`,
`consider_itf`, or `file_pre_discharge_or_itf` in `actions`), explain in one or two
sentences why it helps (it can lock in an earlier start date for benefits while
they build the claim), then ask:
"Want to file your free Intent to File now?" →
**File online now** / **Call VA instead** / **Ask a free representative** / **Remind me later**

- **File online now:** give `https://www.va.gov/resources/your-intent-to-file-a-va-claim/`.
  Say: "Come back and tell me the date you filed, and I'll update your deadlines."
- **Call VA instead:** 800-827-1000 (TTY 711).
- **Ask a free representative:** va.gov/get-help-from-accredited-representative
- **Remind me later:** note it on the Key Dates page under Intent to File.

When the Veteran later reports an ITF date, save it and rerun Part D.

## Part F — Save

In `VA-Claim-Output/`:

1. Write `intake.json` per
   `${CLAUDE_PLUGIN_ROOT}/skills/intake/references/intake-schema.md`, including the
   full script output under `filing_window`.
2. Write `My-Key-Dates.md` from
   `${CLAUDE_PLUGIN_ROOT}/skills/intake/references/key-dates-template.md`. Write dates
   in words. Keep the free-use notice and credit lines exactly. This page is for the
   Veteran, not for filing.
3. Update `progress.json`: `intake` = `done`, `current_step` = `cfr`, `updated` = today.
4. Write nothing outside `VA-Claim-Output/`.

Then say: "Saved. Your key dates are in your folder on a page called My Key Dates."

## Part G — Next

Ask: "Next up: Get the latest VA rules. Ready?" → **Let's go** / **Take a break**.
- **Let's go:** start the `cfr` skill. If it isn't installed yet, say "That step is
  coming soon. Your progress is saved."
- **Take a break:** show the TAKE A BREAK block from
  `${CLAUDE_PLUGIN_ROOT}/skills/start/references/notices.md`.

## Always

- Never ask for an SSN, service number, or bank details.
- Never promise a rating, an outcome, or a payment amount.
- If the Veteran seems upset, offer **Take a break** and show the TAKE A BREAK block.
