#!/usr/bin/env python3
"""
VA Claims Assistant - release check. Run before every push or share.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0). Stdlib only.

  python3 tools/release_check.py [--root .] [--deny <local file of private words, one per line>]

Checks:
  markers      every source file carries an authorship marker (plugin.json excepted); NONE may reach
               anything the Veteran gets (templates copied into their folder, generated pages, filed documents)
  disclaimers  README and the opening-screen notices carry every required notice; app-page
               generators print the free-use notice and the not-legal-advice line
  filed docs   generators of filed documents (statements, letters, packets) print NO app notices
  private data no SSN-shaped numbers or private words (--deny file, kept OUTSIDE the repo) in any file
Exit code 1 if anything fails.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, os, re, sys

MARKERS = ("JOSHUAONENINE", "KILLROYWASHERE")
TEXT = (".md", ".py", ".json", ".txt", ".html", ".csv", ".yaml", ".yml")
README_MUST = {"free-use notice": r"unlawful for anyone to charge", "VSAFE": r"VSAFE\.gov",
               "not legal advice": r"[Nn]ot legal advice", "not affiliated with VA": r"[Nn]ot\s+affiliated",
               "initial release": r"[Ii]nitial release", "privacy": r"## Privacy",
               "paid plan note": r"paid\s+Claude\s+plan", "AI can make mistakes": r"AI\s+can\s+make\s+mistakes"}
NOTICES_MUST = ["## WHAT THIS APP IS AND ISN'T", "## YOUR PRIVACY", "## INITIAL RELEASE", "## FREE-USE NOTICE",
                "## CREDIT", "## TAKE A BREAK", "not affiliated with or endorsed by", "AI can make mistakes",
                "988"]
APP_PAGE_GENERATORS = ["skills/records/scripts/build_package.py", "skills/start/scripts/status.py",
                       "skills/file/scripts/final_check.py", "skills/file/scripts/ez_guide.py",
                       "skills/decision/scripts/decision_tools.py", "skills/start/references/read-me-first-template.md",
                       "skills/intake/references/key-dates-template.md"]
FILED_GENERATORS = ["skills/evidence/scripts/build_packet.py"]
# copied word for word into the Veteran's folder, so they must NOT carry markers
OUTPUT_TEMPLATES = {"skills/start/references/read-me-first-template.md", "skills/intake/references/key-dates-template.md"}
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--deny")
    ap.add_argument("--outputs", help="a sample VA-Claim-Output folder: no code word may appear in anything the Veteran gets")
    a = ap.parse_args()
    deny = []
    if a.deny:
        deny = [w.strip().lower() for w in open(a.deny, encoding="utf-8") if w.strip()]
    fails = []
    files = []
    for dp, dn, fn in os.walk(a.root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", ".pytest_cache")]
        files += [os.path.join(dp, f) for f in fn if not f.endswith(".pyc")]
    for f in files:
        rel = os.path.relpath(f, a.root)
        data = open(f, "rb").read()
        if rel.endswith(TEXT) or rel.endswith(".png"):
            if rel in OUTPUT_TEMPLATES:
                if any(m.encode() in data for m in MARKERS):
                    fails.append(f"marker in a Veteran-facing template (would print): {rel}")
            elif rel not in (os.path.join(".claude-plugin", "plugin.json"), os.path.join(".claude-plugin", "marketplace.json")) and not any(m.encode() in data for m in MARKERS):
                fails.append(f"marker missing: {rel}")
        if rel.endswith(TEXT):
            t = data.decode("utf-8", "ignore")
            if SSN.search(t) and "release_check.py" not in rel:
                fails.append(f"SSN-shaped number: {rel}")
            low = t.lower()
            for w in deny:
                if w in low:
                    fails.append(f"private word found in {rel}")
    readme = open(os.path.join(a.root, "README.md"), encoding="utf-8").read()
    for name, rx in README_MUST.items():
        if not re.search(rx, readme):
            fails.append(f"README missing: {name}")
    notices = open(os.path.join(a.root, "skills/start/references/notices.md"), encoding="utf-8").read()
    for s in NOTICES_MUST:
        if s not in notices:
            fails.append(f"notices.md missing: {s}")
    for g in APP_PAGE_GENERATORS:
        t = open(os.path.join(a.root, g), encoding="utf-8").read()
        if "VSAFE" not in t:
            fails.append(f"free-use notice missing from app page: {g}")
        if "Not legal advice" not in t:
            fails.append(f"not-legal-advice line missing from app page: {g}")
    ws = open(os.path.join(a.root, "skills/writeups/scripts/writeups_tools.py"), encoding="utf-8").read()
    for g in FILED_GENERATORS:
        if "VSAFE" in open(os.path.join(a.root, g), encoding="utf-8").read():
            fails.append(f"app notice found in a FILED document generator: {g}")
    if "VSAFE" in ws:
        fails.append("app notice found in statement/letter generator (writeups_tools.py)")
    if a.outputs:
        import zipfile
        for dp, dn, fn in os.walk(a.outputs):
            for f in fn:
                path = os.path.join(dp, f)
                try:
                    data = open(path, "rb").read()
                    if f.endswith(".docx"):
                        data = b"".join(zipfile.ZipFile(path).read(n) for n in zipfile.ZipFile(path).namelist())
                except Exception:
                    continue
                if any(m.encode() in data for m in MARKERS):
                    fails.append(f"code word in a Veteran output: {os.path.relpath(path, a.outputs)}")
    n = len(files)
    if fails:
        print(f"FAILED ({len(fails)} problems in {n} files):")
        for x in fails:
            print("  - " + x)
        sys.exit(1)
    print(f"PASSED: {n} files, markers on all, disclaimers present, no app notices in filed documents, no private data found.")


if __name__ == "__main__":
    main()
