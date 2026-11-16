# claims.json — format
<!-- KILLROYWASHERE -->

Saved at `VA-Claim-Output/Claims/claims.json`. Later steps (review, statements,
evidence packets) read it. Cite pages by **file name + page number** in the records
folder, always the kept (non-duplicate) copy.

```json
{
  "version": 1,
  "generated": "YYYY-MM-DD",
  "records_folder": "<folder name>",
  "service_facts": [{"fact": "...", "cite": [["<file>", 12]]}],
  "claims": [{
    "id": "C01",
    "condition": "Plain-language name",
    "type": "direct | secondary | presumptive | aggravation",
    "secondary_to": "C0x (secondary only)",
    "system": "Musculoskeletal",
    "dc": ["5257 (instability)"],
    "strength": "strong | moderate | needs_more",
    "lead_keys": ["knee_right"],
    "separate_parts": [{"part": "...", "dc": "5257", "note": "..."}],
    "elements": {"diagnosis": "found|partial|missing", "in_service": "found|partial|missing|n/a (secondary)", "nexus": "found|partial|missing"},
    "evidence": [{"file": "<file>", "page": 80, "role": "diagnosis|in_service|nexus|severity|lay|contrary",
                  "date": "YYYY-MM-DD", "shows": "one line", "also_in": [{"file": "...", "page": 9}]}],
    "questions_for_vet": ["..."],
    "flags": ["..."],
    "vet_status": "pending | confirmed | changed | removed (set in the review step)"
  }],
  "not_recommended": [{"condition": "...", "reason": "...", "cite": [["<file>", 28]]}],
  "possible_additional": [{"condition": "...", "reason": "...", "cite": [["<file>", 143]]}],
  "record_flags": ["..."]
}
```

Rules: one claim per condition; separately rated parts go in `separate_parts` of
the same claim; one page may be cited by several claims; every cited page must
pass `verify_citations.py`.

## Added by the details step

- `details`: duties, injury, answers, `impact` {work, relationships, daily, example}, notes.
- `story` (v0.9.0): `events` [{date, date_note, kind (start, test, move, care_wait,
  treatment, surgery, finding, worse), where, what, source (record, vet, both),
  pages, injury (a `worse` event that was a new injury), staged (a surgery that
  finishes an earlier one)}], `worsened_by`, `led_to` [{condition, claim_id, how}],
  `caused_by` [{condition, claim_id, how}] (another claim that set this one off), `outcome`,
  `vet_words`, `waits` (computed by story_tools.py), `saved`.
- Evidence role `history`: a page that shows a turn in the condition's story.
- `secondary_alt` [{to, why}]: a backup secondary theory (38 CFR 3.310) if direct
  service connection is denied.
