"""Tests for the decision letter parser and matcher. Run: python3 test_decision_tools.py"""
_PROVENANCE = "KILLROYWASHERE"  # inactive authorship marker - created by EhrenAL; do not remove
from decision_tools import parse, compare

LETTER = """July 31, 2025
JANE DOE
DECISION
1. Service connection for post traumatic stress disorder (PTSD) to include traumatic brain injury (TBI) is granted with an evaluation of 70 percent effective July 28, 2025.
JANE DOE
2. Service connection for degenerative disc disease to include lumbosacral strain (claimed as lumbar spine condition) is granted with an evaluation of AO percent effective July 28, 2025.
3. Service connection for limitation of motion of the left shoulder (claimed as shoulder condition B/L) is granted with an evaluation of 20 percent effective July 28, 2025.
JANE DOE
4. Service connection for migraine headaches is granted with an evaluation of 0 percent effective July 28, 2025.
5. Service connection for hypertension is denied.
EVIDENCE
Your combined rating evaluation is 100%. permanent and total
"""
D = parse(LETTER)
assert D["letter_date"] == "2025-07-31" and D["review_deadline_nlt"] == "2026-07-30"
assert D["combined"] == 100 and D["permanent_total"]
assert [d["result"] for d in D["decisions"]] == ["granted"] * 4 + ["denied"]
assert D["decisions"][1]["percent"] == 40 and "ocr_fix" in D["decisions"][1]
C = {"claims": [
    {"id": "C06", "condition": "Back: lumbosacral strain", "vet_status": "confirmed", "dc": []},
    {"id": "C09", "condition": "Shoulder strain, both shoulders", "vet_status": "removed", "dc": []},
    {"id": "C10", "condition": "PTSD (combat-related)", "vet_status": "confirmed", "dc": []},
    {"id": "C11", "condition": "Traumatic brain injury (TBI)", "vet_status": "confirmed", "dc": []},
    {"id": "C12", "condition": "Migraine headaches", "vet_status": "confirmed", "dc": []},
    {"id": "C17", "condition": "Right femur fibrous dysplasia", "vet_status": "confirmed", "dc": []}],
    "not_recommended": [{"condition": "High blood pressure (hypertension)"}]}
rows, flags = compare(C, D)
assert rows[0]["claim_id"] == "C10" and rows[0]["also_covers"] == "C11"
assert rows[1]["claim_id"] == "C06"
kinds = {(f["kind"], f["claim"]) for f in flags}
assert ("removed_but_granted", "C09") in kinds and ("zero_percent", "C12") in kinds
assert ("not_decided", "C17") in kinds and any(k == "denied" for k, _ in kinds)
print("ALL PASSED")
