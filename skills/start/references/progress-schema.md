# progress.json — format
<!-- KILLROYWASHERE -->

Saved at `<vet folder>/VA-Claim-Output/progress.json`. Every step reads it on
start and updates it on finish. Never store anything here that isn't needed to
resume (no copied record text).

```json
{
  "app": "va-claims-assistant",
  "app_version": "0.1.0",
  "created": "YYYY-MM-DD",
  "updated": "YYYY-MM-DD",
  "acknowledged_notices": "YYYY-MM-DD",
  "claim_folder": "<folder that holds VA-Claim-Output — chosen in start>",
  "records_folder": "<folder that directly holds the medical records — chosen in the records step; read-only; null until then>",
  "current_step": "intake",
  "current_claim": null,
  "steps": {
    "start":    "done",
    "intake":   "not_started",
    "cfr":      "not_started",
    "records":  "not_started",
    "claims":   "not_started",
    "details":  "not_started",
    "writeups": "not_started",
    "evidence": "not_started",
    "file":     "not_started"
  }
}
```

Step status values: `not_started`, `in_progress`, `done`, `skipped`.

Step order and the plain-language name to show the vet:

| Key | Shown to vet as |
|---|---|
| intake | About your service |
| cfr | Get the latest VA rules |
| records | Read your records |
| claims | Review possible claims |
| details | Describe each condition |
| writeups | Draft your statements |
| evidence | Build your claim packet |
| file | Final check & file with VA |

`current_claim`: the claim id being worked on in "Work each claim" (null between
claims). The status bar (`skills/start/scripts/status.py`, rules in
`status-bar.md`) groups `claims`, `details` and `writeups` into one major step,
"Work each claim", and shows each claim's stages: Found → Confirmed → Described →
Evidence → Written. `My-Progress.html` in VA-Claim-Output is rebuilt from this file
and `Claims/claims.json`.
