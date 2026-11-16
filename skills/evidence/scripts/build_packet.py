#!/usr/bin/env python3
"""
VA Claims Assistant - build one evidence packet (PDF) per claim from the earmarked pages.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0).
Needs pypdf and reportlab.

  python3 build_packet.py check --claims F --records <records folder>          which source files are needed / missing
  python3 build_packet.py build --claims F --records <records folder> --out <VA-Claim-Output> [--id C01]

Each packet: a cover index (date, what the page shows, source file and page, packet page)
followed by ONLY the earmarked pages, in date order, with a bookmark per page.
Packets are filing documents: no app notices or markers are added to them.
"""
_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove

import argparse, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import date

ROLE_ORDER = {"in_service": 0, "history": 1, "diagnosis": 2, "nexus": 3, "severity": 4, "lay": 5}
SKIP_ROLES = {"contrary"}  # VA already has these; the statement explains them


def load(p):
    return json.load(open(p, encoding="utf-8"))


def short(name):
    s = re.split(r"\s*[(:,]", name)[0].strip()
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:40]


def clean_title(name):
    return re.split(r"\s*[(:]", name)[0].strip()


def sort_key(e):
    d = (e.get("date") or "9999")
    d = re.sub(r"[^0-9-]", "", d) or "9999"
    return (d[:10], ROLE_ORDER.get(e.get("role"), 9))


def pages_for(c):
    seen, out = set(), []
    for e in sorted(c.get("evidence", []), key=sort_key):
        if e.get("role") in SKIP_ROLES:
            continue
        k = (e["file"], int(e["page"]))
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def _esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cover_pdf(c, rows, total_pages, out=None):
    """Claim Summary (if saved on the claim) + Substantial Record index."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    buf = io.BytesIO()
    title = f"Evidence: {clean_title(c['condition'])}"
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch, title=title)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=10, leading=13, spaceAfter=4)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8.5, leading=10.5)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4,
                        textColor=colors.HexColor("#1f3a5f"))
    h3 = ParagraphStyle("h3", parent=ss["Heading3"], fontSize=10.5, spaceBefore=6, spaceAfter=2)
    bullet = ParagraphStyle("bul", parent=body, leftIndent=14, bulletIndent=4, spaceAfter=2)
    quote = ParagraphStyle("q", parent=body, leftIndent=24, textColor=colors.HexColor("#333333"),
                           fontName="Helvetica-Oblique", fontSize=9.5, leading=12)
    S = c.get("summary")
    pp = {(e["file"], int(e["page"])): p for e, p in rows}

    def ref(r):
        n = pp.get((r["file"], int(r["page"])))
        return f'{_esc(r["file"])}, p. {r["page"]}' + (f" (packet p. {n})" if n else "")

    story = [Paragraph(_esc(clean_title(c["condition"])) + " \u2014 Claim Summary" if S else title, ss["Title"])]
    story.append(Paragraph("Veteran: ______________________________ &nbsp;&nbsp; VA file number or SSN (last 4): __________", ss["Normal"]))
    story.append(Spacer(1, 6))
    if S:
        dcs = c.get("dc") or []
        story.append(Paragraph("<b>Diagnostic code(s):</b> " + _esc("; ".join(dcs)), body))
        if S.get("claim_type"):
            story.append(Paragraph("<b>Claim type:</b> " + _esc(S["claim_type"]), body))
        if S.get("onset"):
            story.append(Paragraph("<b>Onset:</b> " + _esc(S["onset"]), body))
        st = ""
        if out:
            from claim_summary import statement_text
            st = statement_text(out, c)
        if st:
            story.append(Paragraph("Statement for Submission", h2))
            for para in [x.strip() for x in st.split("\n\n") if x.strip()]:
                story.append(Paragraph(_esc(para), body))
            story.append(Paragraph("<i>The signed copy of this statement is filed separately.</i>", small))
        story.append(Paragraph("Summary of Medical History with Extracts", h2))
        def _pp(it):
            return pp.get((it["file"], int(it["page"])), 10 ** 6)
        groups = sorted(S.get("history", []), key=lambda g: min([_pp(x) for x in g.get("items", [])] or [10 ** 6]))
        for i, g in enumerate(groups, 1):  # follows the order of the attached pages
            story.append(Paragraph(f"{i}. " + _esc(g.get("period", "")), h3))
            for it in sorted(g.get("items", []), key=_pp):
                story.append(Paragraph(_esc(it.get("label", "")) + f" \u2192 {ref(it)}", bullet, bulletText="\u2022"))
                if it.get("quote"):
                    story.append(Paragraph("\u201c" + _esc(it["quote"]) + "\u201d", quote))
        story.append(Paragraph("CFR Aligned Rating Language", h2))
        for r in S.get("rating", []):
            story.append(Paragraph("DC " + _esc(r.get("dc", "")), h3))
            for p_ in r.get("points", []):
                story.append(Paragraph(_esc(p_), bullet, bulletText="\u2022"))
        if S.get("residuals"):
            story.append(Paragraph("Residuals", h3))
            for p_ in S["residuals"]:
                story.append(Paragraph(_esc(p_), bullet, bulletText="\u2022"))
        nx = S.get("nexus") or {}
        story.append(Paragraph("Nexus / Service Connection Rationale", h2))
        if nx.get("theory"):
            story.append(Paragraph("<b>Theory:</b> " + _esc(nx["theory"]) + (f" ({_esc(nx['cfr'])})" if nx.get("cfr") else ""), body))
        for p_ in nx.get("points", []):
            story.append(Paragraph(_esc(p_), bullet, bulletText="\u2022"))
        if nx.get("refs"):
            story.append(Paragraph("See: " + "; ".join(ref(r) for r in nx["refs"]), small))
        story.append(Paragraph("Functional Impact Statement", h2))
        for p_ in S.get("impact", []):
            story.append(Paragraph(_esc(p_), bullet, bulletText="\u2022"))
        story.append(Paragraph("Substantial Record", h2))
        if S.get("strongest"):
            sg = S["strongest"]
            story.append(Paragraph(f"<b>Most substantial record:</b> {ref(sg)}. " + _esc(sg.get("why", "")), body))
            story.append(Spacer(1, 4))
    else:
        story.append(Spacer(1, 2))
    story.append(Paragraph(f"This packet contains {len(rows)} record page(s) copied from my service treatment records and "
                           "VA examination records, in date order. The source file and page are listed for each.", ss["Normal"]))
    story.append(Spacer(1, 8))
    strong = (S or {}).get("strongest") or {}
    data = [[Paragraph("<b>#</b>", small), Paragraph("<b>Packet page</b>", small), Paragraph("<b>Date</b>", small),
             Paragraph("<b>What it shows</b>", small), Paragraph("<b>Source (file, page)</b>", small)]]
    for i, (e, p_) in enumerate(rows, 1):
        star = (e["file"], int(e["page"])) == (strong.get("file"), int(strong.get("page") or -1))
        data.append([Paragraph(str(i) + (" *" if star else ""), small), Paragraph(str(p_), small),
                     Paragraph(e.get("date") or "", small), Paragraph(_esc(e.get("shows")), small),
                     Paragraph(f'{_esc(e["file"])}, p. {e["page"]}', small)])
    t = Table(data, colWidths=[0.35 * inch, 0.6 * inch, 0.85 * inch, 3.4 * inch, 1.9 * inch], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8edf3")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    if strong:
        story.append(Paragraph("* = most substantial record", small))
    doc.build(story)
    return buf.getvalue()


def build_one(c, records, out):
    from pypdf import PdfReader, PdfWriter
    pages = pages_for(c)
    if not pages:
        return None, "no earmarked pages"
    readers = {}
    for e in pages:
        if e["file"] not in readers:
            p = os.path.join(records, e["file"])
            if not os.path.exists(p):
                return None, f"missing source file: {e['file']}"
            readers[e["file"]] = PdfReader(p)
    # cover first pass to learn its length
    tmp = [(e, 0) for e in pages]
    n_cover = len(PdfReader(io.BytesIO(cover_pdf(c, tmp, 0, out))).pages)
    # second pass: page numbers shift if the cover length changes
    for _ in range(2):
        rows = [(e, n_cover + i + 1) for i, e in enumerate(pages)]
        n2 = len(PdfReader(io.BytesIO(cover_pdf(c, rows, 0, out))).pages)
        if n2 == n_cover:
            break
        n_cover = n2
    rows = [(e, n_cover + i + 1) for i, e in enumerate(pages)]
    cover = PdfReader(io.BytesIO(cover_pdf(c, rows, n_cover + len(pages), out)))
    w = PdfWriter()
    for p in cover.pages:
        w.add_page(p)
    w.add_outline_item("Claim summary and index" if c.get("summary") else "Index of evidence", 0)
    for i, (e, pp) in enumerate(rows):
        r = readers[e["file"]]
        idx = int(e["page"]) - 1
        if idx < 0 or idx >= len(r.pages):
            return None, f"page {e['page']} not in {e['file']}"
        w.add_page(r.pages[idx])
        label = f'{e.get("date") or ""} - {(e.get("shows") or "")[:70]}'.strip(" -")
        w.add_outline_item(label, pp - 1)
    w.add_metadata({"/Title": f"Evidence: {clean_title(c['condition'])}"})
    d = os.path.join(out, "Claims", f'{c["id"]}-{short(c["condition"])}')
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "Evidence-Packet.pdf")
    with open(path, "wb") as f:
        w.write(f)
    return path, f"{len(rows)} record pages + {n_cover} index page(s)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "build"])
    ap.add_argument("--claims", required=True)
    ap.add_argument("--records", required=True)
    ap.add_argument("--out")
    ap.add_argument("--id")
    a = ap.parse_args()
    C = load(a.claims)
    claims = [c for c in C["claims"] if c.get("vet_status") == "confirmed" and (not a.id or c["id"] == a.id)]
    if a.cmd == "check":
        need = sorted({e["file"] for c in claims for e in pages_for(c)})
        print(json.dumps({"needed": need, "missing": [f for f in need if not os.path.exists(os.path.join(a.records, f))]}, indent=1))
        return
    results = []
    for c in claims:
        path, msg = build_one(c, a.records, a.out)
        if path:
            c["packet"] = {"status": "done", "file": os.path.relpath(path, a.out), "pages": len(pages_for(c)),
                           "built": date.today().isoformat()}
        results.append({"id": c["id"], "ok": bool(path), "note": msg})
    json.dump(C, open(a.claims, "w"), indent=1)
    print(json.dumps(results, indent=1))
    if not all(r["ok"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
