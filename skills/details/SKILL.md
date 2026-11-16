---
name: details
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Describe each condition" step, or says "describe my conditions", "rating
  questions", "how bad is it", or "what caused it in service". For each confirmed
  claim it captures the service duties that contributed (rucking, airborne, armored
  vehicles, Ranger School, etc.), answers VA's rating-criteria questions in plain
  language, captures each condition's story (how it started, what made it worse,
  waits for care, moves, surgeries), records impact on work, relationships and
  daily life, and lets the Veteran add a claim at any time. Also use when the
  Veteran says "add a claim", "I just remembered", or "it got worse when...".
metadata:
  version: "0.13.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Step: Describe Each Condition

Two parts: **A. Your service duties** (asked once), then **B. One short screen set
per claim**. Mostly taps. Let the Veteran skip, pause, or come back at any point.

Voice rules: plain language, warm, short. AskUserQuestion for every choice. No JSON,
paths or tool names. **Honesty rule:** ask what is TRUE on typical days and on bad
days. Never hint which answer gets a higher rating, never suggest an answer, and
never "round up." The Veteran signs their statements under penalty of law.

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`. Every question needs a way out (**None of these** / **Skip**); a skipped question saves nothing.

**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`. Show the one-line bar at the top of this step's first screen (and each claim's first screen), and refresh My-Progress.html when anything changes.

Setup: `progress.json` → `details` = `in_progress`.
`DT="${CLAUDE_PLUGIN_ROOT}/skills/details/scripts/details_tools.py"`,
`REF="${CLAUDE_PLUGIN_ROOT}/skills/details/references"`,
`F=<claim folder>/VA-Claim-Output/Claims/claims.json`,
`I=<claim folder>/VA-Claim-Output/intake.json`,
`PT=<claim folder>/VA-Claim-Output/Evidence/page-text.jsonl.gz`.

## A. Your service duties (once)

Why: for wear-and-tear conditions (knees, back, hips, ankles, shoulders, neck), the
"something that happened in service" is often **years of hard duty**, not one
injury. VA must consider the places, types and circumstances of service
(38 U.S.C. 1154(a); 38 CFR 3.303(a)).

1. Run `python3 -I "$DT" duties --pages "$PT" --duties "$REF/service-duties.json"`
   to see which duties already appear in the records.
2. Say, in bold: **The following service duties may have worn on your body. Check
   all that apply. Leave the rest unchecked.** Show all 13 duties from
   `service-duties.json` (multiSelect, 4 per question). In each description, add
   "(found in your records)" where step 1 found it.
3. Ask one follow-up in plain words: "Roughly how many years, jumps or
   deployments?" Optional; skip allowed.
4. Save: `setduties --intake "$I" --ids <ids> --note "<their numbers>"`.
5. Add the record pages from step 1 to `service_facts` in `claims.json`, so they can
   be cited later.

## B. Each confirmed claim

Run `plan --claims "$F" --questions "$REF/rating-questions.json" --duties "$REF/service-duties.json" --intake "$I"`.
Go claim by claim in the order shown. Set `progress.json` → `current_claim` to the
claim's id, show the status bar, then start with its name and strength dot.
Offer **Skip this one for now** on every screen.

**Add a claim (any time).** The Veteran may think of another condition at any point:
in a typed answer, in a story ("…and then my hamstring tore"), or by asking. When
that happens:
1. Check the list. If it's already there, say "That one's already on your list ✅"
   and say which claim it is.
2. If not, confirm in one tap: "Add <condition> as a new claim?" → **Yes, add it** /
   **Not now**.
3. On yes: `review_tools.py add --condition "<their words>"`, search the records for
   it (`search --positive`), attach what you find with `addev`, and say in one line
   what you found.
4. Ask: **Describe it now** / **Add it to the end of my list**. Then go back to
   exactly where you were.
Also offer **➕ Add a claim** on the screen between claims (with **Keep going** /
**Take a break**).

**B1. What caused it.** Bold: **Which of these duties contributed to your
<condition>? Check all that apply.** Options are the claim's `duties_offer`, with
the duties they checked in Part A pre-listed first. Add **A specific injury** (type
it) and **Not sure**. These become the in-service event and a talking point for a
doctor's opinion. If `duties_offer` is empty (for example, scars or GERD), skip B1
and just ask about a specific cause.

**Same condition?** If the Veteran says a claim is "the same" as another, or should be
merged or dropped, run `review_tools.py guard` on it first (see the claims step) and
follow its buttons. Never merge away a body part or side that has its own diagnosis or
VA exam.

**B2. Your condition's story (how it started and what made it worse).** VA rates
how a condition is NOW, but the story explains WHY it is this bad: a first injury,
more wear from duty, a wait for care, a move in the middle of care, a surgery that
found more damage, a second surgery, slow healing. Every step that happened in
service is part of the service-connected condition, and each surgery can leave
separately rated parts (meniscus, scars, arthritis). Build it in four short screens.

1. **Draft from the records (Claude, before asking).** Run
   `python3 -I "$ST" draft --claims "$F" --id <id> --pages "$PT" --terms "${CLAUDE_PLUGIN_ROOT}/skills/records/references/condition-terms.json"`
   (`ST=${CLAUDE_PLUGIN_ROOT}/skills/details/scripts/story_tools.py`). The output is
   noisy on purpose. Open the candidate pages, keep only real events, merge repeats,
   and write each event in one plain line with its date, place and page. Look hard
   for: the first injury, where it was diagnosed, plans that were put off ("follow up
   with a surgeon at the next duty station"), a PCS or deployment, referral and
   surgery dates, what each surgery FOUND (operative report "findings"), and later
   setbacks. If the records give different dates for the same injury, list them
   (`injury_dates_reported`) and ask which is right. Don't guess.
2. **Show the story and check it.** "Here's the story your records tell about your
   <condition>:" then a short dated list (5–9 lines, oldest first) with the wait
   times. Ask: **Looks right** / **Something's wrong or missing** / **Skip**.
   If something's wrong, ask what (Other) and fix it.
3. **What made it worse? (check all that apply).** Up to three questions, 3 + **None of these** each
   (skip any option the records and the Veteran have already covered):
   - **A new injury or re-injury** / **More wear from duty** / **Waited a long time for care** / **None of these**
   - **Moved or deployed in the middle of care** / **Missed or called something minor at first** / **Surgery or tests found more damage** / **None of these**
   - **Had to push to get care myself** / **Another surgery, complications or slow healing** / **None of these**
   For each one checked that the records don't already show, ask one short follow-up
   (when, where, what happened; typed). Then search the records for it
   (`review_tools.py search ... --positive`) and attach any page found
   (`addev --role history`). Mark each event `source`: `record`, `vet` or `both`.
4. **Did it lead to other problems?** Show the confirmed claims that may be linked
   (for example: favoring this knee → the other knee, ankles, back; the knee giving
   way → a hamstring tear) as a multiSelect with **None of these**, plus
   **Something else (type it)**. A linked condition that is NOT on the list yet is a
   new claim: use **Add a claim** (below), then come back. Save links in `led_to`.
5. **Today compared to before** (multiSelect, 3 + **None of these**): **Less motion
   than before** / **Healing took longer than expected** / **More pain or symptoms
   than before**. Save in `outcome`.

Save with `python3 -I "$ST" save --claims "$F" --id <id> --story <scratch>.json`, where the file is
`{"events": [{"date": "2020-05-11", "date_note": "", "kind": "start|test|move|care_wait|treatment|surgery|finding|worse",
"where": "...", "what": "...", "source": "record|vet|both", "pages": [{"file": "...", "page": 0}]}],
"worsened_by": [...], "led_to": [{"condition": "...", "claim_id": "C03", "how": "..."}], "outcome": [...], "vet_words": "..."}`.
Add `"injury": true` to a `worse` event that was a new injury (a re-tear, a fall), so
waits count from it; a `worse` event that just means "it got worse" has no flag. Add
`"staged": true` to a surgery that finishes an earlier one (the first operative
report planned it), so the wait counts from the original injury. The script adds the
waits (injury → surgery, first seen → surgery). Show the result with
`show`. Honesty rule applies: record what happened. Never call a delay malpractice or
blame anyone; just say what happened and how long it took.

If the claim has no story to tell (for example, tinnitus that came on slowly), ask
only: "When did you first notice it?" → **During a specific event** / **Slowly
during service** / **After a deployment** / **Not sure**, and save it as one event.

**B2m. Mental health claims (PTSD, depression, anxiety): the events behind it.** Do this
instead of B2 for a mental health claim. Be gentle: say first, "You only need to share
what you're comfortable with. You can skip any question, and you don't need to give
graphic details." `SM=${CLAUDE_PLUGIN_ROOT}/skills/details/scripts/stressor_tools.py`;
`python3 -I "$SM" options` gives the button lists.

1. **What kind of event(s)?** (multiSelect) **Combat** / **Something else (accident,
   disaster, saw a death or injury)** / **A personal attack or military sexual trauma** /
   **I'd rather not say**. For MST or personal assault, add once: "VA accepts other kinds
   of evidence for these, like changes in behavior. You can also get free, confidential
   help at any VA medical center or Vet Center." Never push for details.
2. **For each event (up to 3, most important first)**, one screen: draft from the records
   first (post-deployment health assessments, the VA PTSD exam, combat action awards,
   blast screens) and show it: "Your records mention: <event>. Is this one of them?" →
   **Yes** / **Change it** / **Skip this one**. Then fill the gaps with typed answers:
   what happened (one or two sentences), where, about when (month and year), unit, and
   whether anyone was hurt or killed (optional). "Not sure" is a fine answer.
3. **What changed after?** multiSelect from `behavior_changes` (4 per screen + **None of
   these**), then one optional typed detail.
4. **Who could back this up?** multiSelect from `sources` + **None of these**; and "Was an
   official report filed?" → **Yes** / **No** / **Doesn't apply**.
5. Save: `python3 -I "$SM" save --claims "$F" --id <id> --data <scratch>.json`, then make the
   worksheet: `python3 -I "$SM" worksheet --claims "$F" --id <id> --out "$OUT"`. Tell the
   Veteran in one line: "Filing online? The online claim asks these questions; copy your
   answers from Form-21-0781-Worksheet.docx. Filing on paper? Copy them onto VA Form 21-0781."
   Also save one `start` event in the story (first event's date) so the status bar
   and statements see it.

**B3. Rating questions.** Ask the `common` questions plus the questions for each
`families` entry from `rating-questions.json` (skip any already answered clearly in
the records or VA exams; say "Your VA exam already covers this"). For the mental
health family, start with: "These are personal. Skip anything you want." If they
check thoughts of death or self-harm, stop and show the TAKE A BREAK block with the
Veterans Crisis Line first.

**B3b. Impact on your life (required for every claim, never skip).** Ask the
`impact` questions from `rating-questions.json` in this order: **work**,
**relationships**, **daily**, then **example**. Use the claim's name in each question.
Split long lists as the button rules say: 3 real options + **None of these** per
part, with the list's "No effect" option in the last part as **None / no effect**.
Relationships may be skipped by the Veteran, but always offer them. **Active family
life:** if the claim's family is in `impact.relationships.active_family.families`
(joints, back, muscles, nerves, TBI, migraines, sleep apnea), put **Can't play
sports or do active things with my kids or family** first, with the examples in its
description. If they check it, ask the one-line `follow_up` (typed, **Skip**
allowed) and save the activities in `impact.active_family`. Ask
**example** on its own screen with **Skip** first. If work answers conflict, ask
once on its own screen. Save under `"impact": {"work": [...], "relationships": [...],
"active_family": "...", "daily": [...], "example": "..."}`. If the Veteran says they can't work at all, note
it for the statements step (it may support TDIU, 38 CFR 4.16).

**B4. The claim's own questions.** Ask its `questions_for_vet` (for example, a
prescribed brace or a CPAP).

**B5. Save.** Write the answers to a scratch JSON
`{"duties": [...], "injury": "...", "answers": {"<question>": "<answer>"}, "impact": {"work": [...], "relationships": [...], "daily": [...], "example": "..."}, "notes": "..."}`
and run `save --claims "$F" --id <id> --answers <file>` (the story from B2 is saved
separately with `story_tools.py save`). Say "Saved."

After every claim, refresh My-Progress.html, then offer **Keep going** /
**➕ Add a claim** / **Take a break**. After every 3–4 claims, show the full board.

## C. Finish

1. Show a short recap: each claim with ✅ (described) or ⏭ (skipped), its top
   1–2 contributing duties, the one or two biggest turns in its story (for example
   "waited 8 months for surgery after a PCS"), and its work and relationship impact
   in a few words. Ask one last time: "Anything else to add before we write your
   statements?" → **No, that's everything** / **➕ Add a claim**.
2. Rebuild `Possible-Claims.md` with `build_package.py` (same command as in the
   claims step).
3. `progress.json` → `details` = `done`, `current_step` = `writeups`.
4. Ask: "Next up: Draft your statements. Ready?" → **Let's go** / **Take a break**.
   (If `writeups` isn't installed: "That step is coming soon. Your answers are saved.")

## Notes for Claude

- Rating criteria change. When unsure, open the DC in the bundled CFR
  (`skills/cfr/references/cfr/part-4/...`) and match the current wording.
- **GERD (DC 7206):** current criteria rate on a documented esophageal stricture.
  Without one, the rating is 0%. Say so honestly, and add that service connection
  still matters for the future and for secondary claims.
- **Tinnitus (DC 6260)** is a single 10% whether one ear or both.
- **Sleep apnea (DC 6847):** a prescribed breathing device (CPAP) = 50%. Daytime
  sleepiness alone = 30%.
- Never give a final rating. You may say what the criteria are based on.
