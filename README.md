# VA Claims Assistant
<!-- KILLROYWASHERE -->

> **⚠ FREE TOOL.** No one should charge you to use it. According to VA, it is
> unlawful for anyone to charge a fee for preparing an initial VA claim.
> Report it: VSAFE.gov or 1-833-38V-SAFE (1-833-388-7233).

**Status: v0.16.0, an initial release.** It works end to end, but it has been tested on
one Veteran's de-identified records and checked against that Veteran's VA decision.
Expect rough edges and check everything it makes.

A push-button helper for Veterans building a VA disability claim in Claude Cowork. It
reads your records, finds possible claims, asks simple button questions, drafts your
statements, builds an evidence packet for each claim, checks everything before you file,
and explains your VA decision when it comes.

## What you get

- **Possible claims** found in your own records, with the pages that support each one.
- **Your statement** for each claim, in your own words (text for VA's online Lay/Witness
  Statement, plus a Word file to sign).
- **An evidence packet** per claim: a Claim Summary (statement, history with quotes checked
  word for word against your records, rating criteria, service connection, functional
  impact, most substantial record), then only the record pages that matter.
- **Filing help:** a final check, a filing checklist, and a 21-526EZ copy-and-paste guide.
- **Toolkit:** exam prep sheets, printable symptom logs, buddy statement guides, and a
  hand-off folder for your VSO.
- **After the decision:** a plain-language read of your VA decision letter and your options.

## Quick start

1. **Get the Claude desktop app with Cowork.** It needs a **paid Claude plan** (Pro or
   higher). The tool is free; the Claude subscription is a cost of the AI app, not a fee
   for preparing your claim.
2. **Get the plugin.** Download `va-claims-assistant.plugin` from this repository's
   **Releases** page and add it in Cowork as a plugin. (Claude Code users:
   `/plugin marketplace add EhrenLinderman/va-claims-assistant`, then
   `/plugin install va-claims-assistant@va-claims-assistant`.)
3. **Make a folder** on your computer and put your medical records (PDFs) in it: service
   treatment records, VA exams, private records.
4. **Say "start my VA claim."** Every step is a button screen. Stop any time; your
   progress is saved.

## Everyday commands

| Say | What happens |
|---|---|
| "start my VA claim" / "continue my claim" | Opens the app or picks up where you left off |
| "where am I?" | Shows your status board |
| "add a claim" | Adds a condition at any step |
| "exam prep" / "symptom log" / "buddy statement" / "send it to my VSO" | Toolkit documents |
| "check my packet" | Checks a packet made somewhere else |
| "I got my decision" | Reads and explains your VA decision letter |

## What gets created (in your folder only)

Everything goes into a **VA-Claim-Output** folder inside the folder you choose. Your
original records are never moved, renamed or changed.

## Privacy and safety (please read)

- **Your records stay yours.** Nothing from your records is stored in this app, and nothing
  is sent to the author. Sharing the app shares none of your information.
- **How reading works.** To help you, Claude reads the pages it needs. They are processed in
  your own private Claude session (on your computer, or in a private workspace for your
  session), under the privacy terms of the Claude app you use.
- **No sensitive IDs needed.** The app never asks for your SSN, date of birth, address or
  bank details. Forms leave blanks for you to fill in by hand.
- **Keep it private.** Don't put your records or claim folder in a shared project, a public
  place, or an issue on this page.
- **AI can make mistakes.** The app checks its own quotes against your records, but check
  every fact, date and quote yourself before you file.
- **It will not file for you.** It drafts. You decide, you sign, and you submit.
- **Crisis:** call or text 988, then press 1 (Veterans Crisis Line).

## Disclaimers

- **Not legal advice.** The app is not a lawyer, a doctor, or the VA, and it is not
  affiliated with or endorsed by the Department of Veterans Affairs. It cannot promise a
  rating or a result.
- **Your own words, only true facts.** It never makes up symptoms, events or medical
  opinions. Doctor's letter templates are for your doctor to edit and sign; the opinion
  must be the doctor's own. Buddy statements must be the witness's own words.
- **Free help:** VA-accredited representatives (VSOs) help for free:
  va.gov/get-help-from-accredited-representative
- Provided as is, without warranty (see LICENSE.md).

## How it works

| # | Step |
|---|---|
| 1 | Opening screen and claim folder setup |
| 2 | About your service, and your filing-window dates (BDD, Intent to File) |
| 3 | Get the latest VA rules (38 CFR Parts 3 and 4) |
| 4 | Read your records: page reading, duplicates, evidence index, possible claims |
| 5 | Review possible claims (guards against dropping a condition VA examined) |
| 6 | Describe each condition: duties, its story, mental health events (21-0781 worksheet), rating questions, impact on work and family |
| 7 | Draft your statements, with a depth check; doctor's letter templates only where needed |
| 8 | Build your claim packet and the 526EZ claim list |
| 9 | Final check & file, with a 21-526EZ copy-and-paste guide |
| 10 | After the decision |
| any time | Toolkit (exam prep, symptom logs, buddy statements, VSO folder) and packet check |

## Honest limitations

- Tested on one Veteran's claim so far. Other branches, Guard and Reserve, PACT Act and
  increase claims need more testing.
- Scanned records with poor print can be misread; the app flags what it can't verify.
- It explains VA rules in plain words but does not replace a VSO or attorney.
- It needs a paid Claude plan to run.

## Ideas for the next version

A scored test set of more Veterans, symptom-log reminders, a combined-rating estimate,
a mode for VSOs, and a standalone app.

## Report a problem

Open an issue on the **Issues** page using the problem template. Never post your records,
your name, or anything from your claim folder. See CONTRIBUTING.md to help.

## License and credits

Created by EhrenAL. Free for non-commercial use under CC BY-NC-SA 4.0 (see LICENSE.md).
Credit is required, and it may not be sold or used to charge Veterans.

For maintainers: before every release, run
`python3 tools/release_check.py --deny <private word list> --outputs <a test output folder>`,
keeping the word list outside the repository.
