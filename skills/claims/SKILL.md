---
name: claims
description: >
  This skill should be used when a Veteran using VA Claims Assistant reaches the
  "Review possible claims" step, or says "review my claims", "that's wrong",
  "I do have that condition", "you missed something", or "add a claim". It shows a
  quick summary of the claims found, lets the Veteran confirm or remove each with a
  tap, handles records the Veteran says are mistaken by searching for their own
  reports, and captures anything missed.
metadata:
  version: "0.7.1"
  author: "EhrenAL"
---
<!-- JOSHUAONENINE -->

# Step: Review Your Possible Claims (the quick check)

Goal: a fast "Is this everything you recall?" check. Keep it short, mostly taps.
Details (how bad each condition is) come in the next step, not here.

Voice rules: plain language, short, warm. AskUserQuestion for every choice. Don't
show JSON, file paths, or tool names. Never pressure the Veteran to keep or drop a
claim; it's their decision.

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`. Every question needs a way out (**None of these** / **Skip**); a skipped question saves nothing.

**Status bar:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/status-bar.md`. Show the one-line bar at the top of this step's first screen (and each claim's first screen), and refresh My-Progress.html when anything changes.

Setup: find `VA-Claim-Output/progress.json`; set `claims` to `in_progress`.
`T="${CLAUDE_PLUGIN_ROOT}/skills/claims/scripts/review_tools.py"`,
`F="<claim folder>/VA-Claim-Output/Claims/claims.json"`,
`PT="<claim folder>/VA-Claim-Output/Evidence/page-text.jsonl.gz"`.
Run `python3 -I "$T" summary --claims "$F"` to get the list.

## Screen 1: Quick summary

Show a short list, one line per claim: the plain condition name, then a few words
on why (for example "surgery records in service + VA exam"), and a strength dot
(🟢 strong, 🟡 moderate, 🟠 needs more). Group by body area if there are more than 10.
Under the list: "Here's what I found in your records. Is this everything you
recall?"

## Screen 2: Check the findings

Start with this line, in bold, exactly:

**The following conditions were found in your records. Check all that apply. Leave incorrect findings unchecked.**

Then ask with AskUserQuestion, **multiSelect**, up to 4 questions per call and 4
claims per question, grouped by body area. Every claim is an option; use the
short name as the label and the one-line why as the description.

- Checked → `set --status confirmed`.
- Unchecked → ask once, for that claim: "Why leave it out?" →
  **I don't have this** / **Not from my service** / **Already rated by VA** /
  **Not sure**. For **Not
  sure**, keep it as `pending` and say "We'll keep it on the list for now."
- **Guard before removing (always).** Run `guard --claims "$F" --id <id>` first.
  - If `level` is `stop` or `warn`, show the message and the pages, then ask:
    **Keep it as its own claim (Recommended)** / **Remove it anyway** / **Let me look at the pages**.
  - Only on **Remove it anyway**, save with `set --status removed --reason "<answer>"`.
  - The same guard runs before any merge, at any step: when the Veteran says two
    claims are "the same", merging moves the evidence but keeps every body part and side
    that has its own diagnosis or exam as its own claim.

  Why: in testing, a shoulder claim was merged away; VA later granted each shoulder 20%.

### Screen 2a: Add anything we missed (always, before confirming)

Say: "**Did we miss anything?** Here are some common claims that aren't on your
list yet. Check any you have, or type something else."

First show one line naming the common claims that are **already on their list**, so
nothing looks missing: "Already on your list: tinnitus, PTSD, back, …" If the
Veteran picks or types one of those anyway, say "That one's already on your list ✅"
and move on.

Build options from `${CLAUDE_PLUGIN_ROOT}/skills/claims/references/common-claims.json`,
showing **only items NOT already on the Veteran's list**, grouped (AskUserQuestion,
multiSelect, up to 4 questions × 4 options per call; use a second call if needed).
Every question also gets **None of these**. Include a final question: "Anything
else from your service?" → **No, that's everything** / **Yes, I'll type it** (Other).

For each item they check or type:
1. `add --condition "<label>"`.
2. Search the records with that item's `terms`
   (`search --pages "$PT" --terms "<terms>" --positive`). Render and look at likely
   form pages for checkboxes. Attach what you find with `addev`.
3. Tell them in one line what you found, for example "Found it: your 2007
   post-deployment form," or "Nothing in your records yet. Your own statement
   still counts, and a doctor's visit can add a diagnosis."

### Screen 2c: Possible connections (secondary conditions)

Say: "Some conditions can cause or worsen others. VA calls these **secondary**
conditions. Here are connections that fit your list."

Use `${CLAUDE_PLUGIN_ROOT}/skills/claims/references/secondary-links.json`: for each
link whose `from` matches a confirmed claim, search the records with its `terms` and
check what's actually there (for example, count blood pressure readings that meet
VA's definition, or count pages showing long-term NSAID use). Show only links with
something real to say, one line each, in three kinds:

- **Backup reason for a claim you already have.** For example: "GERD may also be
  from years of ibuprofen and Celebrex for your joints (on 185 record pages)." Save
  it as `secondary_alt` on that claim; it can be argued if the direct claim is denied.
- **A new secondary claim** where a diagnosis exists. Ask to add it with `add`.
- **Watch item** where there's no diagnosis yet. For example: "Only 5 of 80 blood
  pressure readings were high. That's not hypertension for VA yet. If it becomes a
  diagnosis, it can be claimed as secondary to PTSD." Record it in
  `possible_additional`.

Start with, in bold: **The following connections were found. Check all that apply. Leave incorrect findings unchecked.** Then ask (multiSelect) with one option per connection. Always note: "A
secondary claim needs a doctor's opinion that one condition caused or worsened the
other. We'll prepare a letter for your doctor later."

### Screen 2b: Confirm before moving on (always)

Show two lists covering conditions AND connections:

**✅ You checked (will be claimed):** each condition in the SAME format as Screen 1: grouped by body area, with its strength dot (🟢 strong, 🟡 moderate, 🟠 needs more) and the few words of why
**⬜ You left unchecked (won't be claimed):** each condition, with the reason

Then ask: "Is this right?" → **Yes, that's right** / **Change something**.
- **Change something:** ask which ones to switch (multiSelect over all conditions),
  update the status, and show 2b again.
- Don't move on until the Veteran taps **Yes, that's right**.

## Screen 3: Records that disagree with you

For every claim that has `contrary` evidence and no explanation yet, show that
record in plain words:

"One record says: *'Patient denied tinnitus'* (hearing check, June 2015)."

Ask: **That's a mistake. I do have it** / **I didn't understand the question
then** / **That's right**.

- **That's a mistake** or **I didn't understand**:
  1. Save with `explain --why mistake|misunderstood` (add the Veteran's short note
     if they give one). This also adds a point to cover in their statement later.
  2. Search for the Veteran's own reports:
     `search --pages "$PT" --terms "<condition words>" --positive`.
  3. Many reports are **checkboxes on scanned forms** that text can't show. For
     likely pages (post-deployment forms DD 2796/2900, separation forms DD 2807-1,
     TBI screens), render the page image with
     `render --records "<records folder>" --file X --page N --out <scratch>.png`,
     look at it, and read the marked boxes yourself. Never guess a checkbox.
  4. For each page that supports the Veteran, add it:
     `addev --role lay` (their own report) or `--role in_service` (a report made
     during service), with a one-line "shows".
  5. Tell the Veteran what you found, specifically: "You're right. Your May 2007
     post-deployment form says ringing in the ears began after the blast." If you
     find nothing, say so kindly and note that their own statement still counts as
     evidence.
- **That's right**: save with `explain --why correct`. Ask whether to keep the claim.

## Screen 4: Last chance to add (optional)

Ask: "Did I miss anything you remember, an injury, illness, or problem from your
service?" → **No, that's everything** / **Yes, add something** /
**Show what you left off**.

- **Yes, add something**: they type it (Other). Save with `add --condition`. Then
  search the records for it (as in Screen 3, step 2) and attach any pages found.
- **Show what you left off**: list `not_recommended` (with the reason in plain
  words) and `possible_additional`. Let them add any back with `add`.

## Screen 5: Save and show the checklist

1. Rebuild the Veteran's list:
   `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/records/scripts/build_package.py" --pages "$PT" --leads <leads.json if available> --claims "$F" --out "<claim folder>/VA-Claim-Output"`
   (If `leads.json` is gone, rerun `condition_scan.py` on `$PT` first.)
2. Show a short final checklist: ✅ the confirmed claims, ➖ the removed ones (with
   the reason), ❓ the ones still unsure.
3. Update `progress.json`: `claims` = `done`, `current_step` = `details`.
4. Ask: "Next up: Describe each condition. Ready?" → **Let's go** / **Take a break**.
   Start the `details` skill.

## Always

- Use the Veteran's words. If they say a record is wrong, treat that seriously.
  Look for proof, and never argue.
- Never add or confirm a claim the Veteran didn't choose.
- Offer **Take a break** if they seem tired or upset, and show the TAKE A BREAK block
  from `${CLAUDE_PLUGIN_ROOT}/skills/start/references/notices.md` if needed.
