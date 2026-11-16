# intake.json — format
<!-- KILLROYWASHERE -->

Saved at `<vet folder>/VA-Claim-Output/intake.json`. Later steps use it to find
presumptive conditions, secondary claims, and deadlines. Store only what's listed.
Never store an SSN, service number, or bank info.

```json
{
  "saved": "YYYY-MM-DD",
  "status": "active_duty | separated | guard_reserve | unsure",
  "branch": "Army | Navy | Air Force | Space Force | Marine Corps | Coast Guard | Guard/Reserve (<branch>) | other",
  "service_start": "YYYY-MM or null",
  "separation_date": "YYYY-MM-DD (past or expected) or null",
  "separation_date_is_estimate": false,
  "discharge_character": "honorable | general | oth | bad_conduct_or_dishonorable | still_serving | prefer_not_to_say",
  "exposure_locations": ["southwest_asia", "agent_orange_locations", "camp_lejeune", "radiation", "other:<text>"],
  "other_service_locations": ["<plain text, e.g. Kosovo 2006, Germany 2008-2010>"],
  "exposures_reported": ["<plain text, e.g. burn pits, jet fuel, noise>"],
  "current_rating": {"status": "none | rated | denied_before | unsure", "percent": null},
  "service_connected_conditions": ["<plain text>"],
  "intent_to_file": {"status": "filed | not_filed | unsure", "date": "YYYY-MM-DD or null"},
  "filing_window": { "...": "the full JSON output of filing_window.py" }
}
```
