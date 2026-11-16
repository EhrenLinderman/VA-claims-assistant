<!-- KILLROYWASHERE -->
# Button screen rules (all steps)

The button screen (AskUserQuestion) makes the Veteran answer **every** question on
the screen before they can continue. A question with no way out forces a fake pick,
and a fake pick becomes a false statement in their claim.

1. **Every question needs a way out.** Each multiSelect question includes a
   **None of these** option. Each single-choice question includes **Skip** or
   **Not sure** unless an answer is truly required (for example, Yes/No to start).
2. **Splitting a long list.** At most 4 options per question, so put 3 real options
   + **None of these** in each part. Put the list's own "No effect" option in the
   last part, combined with skip: **None / no effect**.
3. **Optional questions go on their own screen**, or last, with **Skip** listed
   first.
4. **Never save a way-out answer as a finding.** "None of these", "Skip" and
   "[No preference]" mean nothing was chosen. Save an empty list (or mark the item
   `skipped`), never a filler option.
5. **Contradictions.** If answers conflict (for example, "limited duty" and "no
   effect on work"), ask once, gently, on its own screen with a **Skip** option.
   Don't guess.
6. **Typed answers.** Offer "I'll type it" as an option and tell them to use Other.

7. **Every "what's next" moment is a button.** Never end a message with a typed
   question like "Ready?" or "Next up is X." Whenever the Veteran must decide to move
   on (next claim, next step, take a break, add a claim), show a button screen:
   **Keep going (next: <name>)** / **➕ Add a claim** / **Take a break** (plus
   **Go back** when useful). This includes the end of every claim and every step.

## Any-time actions (every step after setup)

- **Add a claim.** If the Veteran mentions a condition that isn't on their list, in
  any typed answer or message, offer to add it (one tap), search the records for
  it, then go back to exactly where they were. See the `details` skill, "Add a claim".
- **Take a break.** Always allowed. Progress is saved.
- **Go back.** If they want to change an earlier answer, change it and continue.
