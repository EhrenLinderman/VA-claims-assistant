<!-- JOSHUAONENINE -->
# Status bar (all steps)

The Veteran should always know where they are. `SB="${CLAUDE_PLUGIN_ROOT}/skills/start/scripts/status.py"`,
`OUT=<claim folder>/VA-Claim-Output`.

**Major steps:** 1 Set up your folder · 2 About your service & key dates · 3 Get the
latest VA rules · 4 Read your records · 5 Work each claim · 6 Build your claim packet ·
7 Final check & file with VA.

**Each claim's stages:** Found → Confirmed → Described → Evidence → Written.
- Found: on the list (from the records or added by the Veteran).
- Confirmed: the Veteran checked it in review (removed claims show as "left out").
- Described: duties/rating answers, the condition's story, and impact are all saved.
- Evidence: all 3 things VA needs (current diagnosis, proof from service, a doctor's
  link) are backed by record pages; otherwise it shows how many (for example 2/3).
- Written: the statement is done (`writeup.status` = `done`; `draft` shows as partial).

## When to show it

1. **The bar (one line)** at the top of the FIRST screen of every step and of every
   claim: `python3 -I "$SB" bar --out "$OUT"`. Show it exactly as printed.
2. **The full board** (`board`) when a major step finishes, when the Veteran
   continues a saved claim, after every 3–4 claims, and whenever they ask "where am I",
   "show my progress", or "what's left".
3. **My-Progress.html.** After any status change, run `html` to refresh
   `VA-Claim-Output/My-Progress.html`. The first time, tell them once: "You can open
   **My-Progress.html** in your folder any time to see this in your browser."

## Keep it accurate

- When a step starts, set it to `in_progress` in `progress.json`; when it ends, `done`.
- In "Work each claim", set `progress.json` → `current_claim` to the claim being
  worked on, and clear it (`null`) between claims.
- Never mark something done that wasn't. Skipped items show as skipped, not done.

## Port to app (keep this)

Tagged **PORT-TO-APP**. If the app moves to another platform, keep the status bar.
`status.py json` gives everything an app needs (percent, major steps, each claim's
stages, what each claim still needs, the current claim), and `My-Progress.html`
already works in any browser. An app version could pin it as a sidebar or top bar
that updates live.
