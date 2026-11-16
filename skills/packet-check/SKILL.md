---
name: packet-check
description: >
  This skill should be used when a Veteran using VA Claims Assistant wants to check a
  claim packet, statement or summary made somewhere else (by hand, another app or another
  AI) before filing, or says "check my packet", "check my existing claim", "are my quotes
  right", or "review what I already wrote". It checks quotes against their records, rating
  codes against the rating schedule, dates, and wording raters discount.
metadata:
  version: "0.13.0"
  author: "EhrenAL"
---
<!-- KILLROYWASHERE -->

# Any time: Check a packet made somewhere else

**Button screens:** follow `${CLAUDE_PLUGIN_ROOT}/skills/start/references/button-rules.md`.

Needs the records step done (it uses the saved page text). If it isn't, say so and offer
**Read my records first** / **Take a break**.

`K="${CLAUDE_PLUGIN_ROOT}/skills/packet-check/scripts/check_packet.py"`,
`P=<claim folder>/VA-Claim-Output/Evidence/page-text.jsonl.gz`,
`DC="${CLAUDE_PLUGIN_ROOT}/skills/cfr/references/cfr/diagnostic-codes.md"`.

1. **Which files?** Ask the Veteran to point to the packet(s): PDF, Word or text. Read
   them only from the Veteran's folder (stage them if they live on the Veteran's
   computer). Their contents stay in the Veteran's folder and are never saved to the
   project.
2. **Check each one:** `python3 -I "$K" check --packet <file> --pages "$P" --dc "$DC"`.
   For a packet with many attached record pages, add `--pages-only <n>` with the number of
   summary pages at the front, so only the written part is checked.
3. **Look before you report.** For each quote marked `not found` or `close`, open the best
   page it names (if any) and read it. A quote can fail because the record words differ a
   little (say "close: the record says ..."), because the page is a scan with poor text
   (say so), or because it isn't in the records at all. Never call a quote made up; say
   "I couldn't find these words in your records."
4. **Show the result** (one screen per packet): a short table of quotes found / close /
   not found, then the code, date and wording problems in plain words, with the fix for
   each. Example: "DC 9440 is chronic adjustment disorder, not a sleep disorder. VA rates
   sleep problems as part of PTSD."
5. Buttons: **Fix these for me** (write corrected text in a new file beside the original,
   using only words that are in the records; never change the original) / **Check another
   packet** / **I'll fix them myself** / **Take a break**.

## Rules

- Never upload the packet or its text anywhere outside the Veteran's folder.
- Be kind about problems: other tools make these mistakes often. Say what to change.
- Don't add new medical opinions or legal arguments when fixing; point to a doctor's
  letter instead.
