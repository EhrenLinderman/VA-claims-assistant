#!/usr/bin/env python3
"""
VA Claims Assistant - read every PDF in the records folder, page by page.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0).

Outputs (JSON Lines, one line per page) with: file, page, chars, ocr (bool),
text, dates, icd10 codes, names-seen check, exact + near-duplicate keys.
Needs: poppler-utils (pdftotext, pdftoppm, pdfinfo). Optional: tesseract (for
pages with no text layer). Standard library otherwise.

Usage:
  python3 extract_pages.py --records <folder> --out pages.jsonl [--expect-name "Doe Jane"]
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile

MIN_CHARS = 40  # below this, try OCR
DATE_RX = re.compile(r"\b(?:(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}"
                     r"|(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])"
                     r"|\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (?:19|20)\d{2}"
                     r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? (?:19|20)\d{2})\b")
ICD_RX = re.compile(r"\b([A-TV-Z]\d{2}(?:\.[0-9A-Z]{1,4})?)\b")
WS = re.compile(r"\s+")


def pages_text(pdf):
    out = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, errors="replace").stdout
    pages = out.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def ocr_page(pdf, n):
    if not shutil.which("tesseract"):
        return ""
    with tempfile.TemporaryDirectory() as td:
        base = os.path.join(td, "p")
        subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-r", "200", "-gray", "-png", pdf, base],
                       capture_output=True)
        imgs = [os.path.join(td, f) for f in os.listdir(td) if f.endswith(".png")]
        if not imgs:
            return ""
        r = subprocess.run(["tesseract", imgs[0], "-", "--psm", "1"], capture_output=True, text=True, errors="replace")
        return r.stdout


def norm(t):
    return WS.sub(" ", re.sub(r"[^a-z0-9 ]", " ", t.lower())).strip()


def simhash(t, bits=64):
    toks = norm(t).split()
    if len(toks) < 3:
        return 0
    v = [0] * bits
    for i in range(len(toks) - 2):
        h = int(hashlib.md5(" ".join(toks[i:i + 3]).encode()).hexdigest()[:16], 16)
        for b in range(bits):
            v[b] += 1 if (h >> b) & 1 else -1
    return sum(1 << b for b in range(bits) if v[b] > 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-name", default="")
    a = ap.parse_args()
    expect = [w.lower() for w in a.expect_name.split() if len(w) > 2]
    files = []
    for root, _, fs in os.walk(a.records):
        if "VA-Claim-Output" in root:
            continue
        for f in fs:
            if f.lower().endswith(".pdf"):
                files.append(os.path.join(root, f))
    files.sort()
    n_pages = n_ocr = 0
    with open(a.out, "w", encoding="utf-8") as out:
        for pdf in files:
            rel = os.path.relpath(pdf, a.records)
            for i, txt in enumerate(pages_text(pdf), start=1):
                ocr = False
                if len(txt.strip()) < MIN_CHARS:
                    o = ocr_page(pdf, i)
                    if len(o.strip()) > len(txt.strip()):
                        txt, ocr = o, True
                        n_ocr += 1
                nt = norm(txt)
                low = txt.lower()
                rec = {
                    "file": rel, "page": i, "chars": len(txt.strip()), "ocr": ocr,
                    "dates": sorted(set(DATE_RX.findall(txt)))[:40],
                    "icd10": sorted(set(c for c in ICD_RX.findall(txt) if not re.fullmatch(r"[A-Z]\d{2}", c) or c[0] in "MGSFHRIJKN"))[:40],
                    "name_ok": all(w in low for w in expect) if expect else None,
                    "exact_key": hashlib.sha1(nt.encode()).hexdigest() if len(nt) > 30 else None,
                    "simhash": str(simhash(txt)),
                    "text": txt,
                }
                out.write(json.dumps(rec) + "\n")
                n_pages += 1
            print(f"read {rel}", file=sys.stderr)
    print(json.dumps({"files": len(files), "pages": n_pages, "ocr_pages": n_ocr}))


if __name__ == "__main__":
    main()
