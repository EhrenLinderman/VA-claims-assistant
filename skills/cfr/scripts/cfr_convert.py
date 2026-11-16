#!/usr/bin/env python3
"""
VA Claims Assistant - convert eCFR XML (38 CFR Part 3 / Part 4) into a clean,
searchable Markdown reference: one file per section, plus indexes.
Created by EhrenAL. Free for non-commercial use (CC BY-NC-SA 4.0).
Standard library only.

Usage:
  python3 cfr_convert.py --xml part3.xml --xml part4.xml --out <dir> --as-of YYYY-MM-DD
Output:
  <out>/part-3/3.309.md ...   one Markdown file per section
  <out>/index.md              every section number + title
  <out>/diagnostic-codes.md   Part 4 diagnostic codes -> name -> section
  <out>/meta.json             as-of date, source, file hashes, counts
"""

_PROVENANCE = "JOSHUAONENINE"  # inactive authorship marker - created by EhrenAL; do not remove
_BUILD = "KILLROYWASHERE"  # inactive build marker

import argparse, hashlib, json, os, re
import xml.etree.ElementTree as ET
from datetime import date

WS = re.compile(r"\s+")

def text_of(el):
    """All text inside an element, with inline italics/bold kept simple."""
    parts = []
    def walk(e):
        if e.text: parts.append(e.text)
        for c in e:
            walk(c)
            if c.tail: parts.append(c.tail)
    walk(el)
    return WS.sub(" ", "".join(parts)).strip()

def indent_level(td):
    m = re.search(r"indent-hanging-(\d+)", td.get("class", "") or "")
    return int(m.group(1)) if m else 0

def render_table(tbl, lines, dcs, section):
    cap = tbl.find("CAPTION")
    if cap is not None and text_of(cap):
        lines.append(f"\n**{text_of(cap)}**\n")
    headers = [text_of(th) for th in tbl.iter("TH")]
    hdr = " | ".join(h for h in headers if h)
    if hdr:
        lines.append(f"*Columns: {hdr}*\n")
    current_dc = None
    for tr in tbl.iter("TR"):
        tds = tr.findall("TD")
        if not tds:
            continue
        first = text_of(tds[0])
        rest = [text_of(td) for td in tds[1:] if text_of(td)]
        if not first and not rest:
            continue
        lvl = indent_level(tds[0])
        m = re.match(r"^(\d{4})\s+(.+)$", first)
        if m and lvl == 0 and section.startswith("4."):
            current_dc = m.group(1)
            dcs.append((m.group(1), m.group(2).rstrip(":").strip(), section))
            first = f"**DC {m.group(1)}** {m.group(2)}"
        val = (" — **" + " / ".join(rest) + ("%**" if all(re.fullmatch(r"\d+", r) for r in rest) else "**")) if rest else ""
        lines.append("  " * lvl + f"- {first}{val}")
    lines.append("")

def render_section(div8, dcs, missing_images):
    num = div8.get("N")
    head = text_of(div8.find("HEAD")) if div8.find("HEAD") is not None else f"§ {num}"
    lines = [f"# {head}", ""]
    def walk(e):
        for c in e:
            tag = c.tag
            if tag == "HEAD":
                continue
            if tag in ("P", "FP", "PSPACE") or tag.startswith("FP-"):
                t = text_of(c)
                if not t:
                    continue
                m = re.match(r"^(\d{4})\s+(.+)$", t)
                if m and num.startswith("4."):
                    dcs.append((m.group(1), m.group(2).strip(), num))
                    lines.append(f"- **DC {m.group(1)}** {m.group(2)}")
                else:
                    lines.append(("  " if tag.startswith("FP-") else "") + t + "\n")
            elif tag == "TABLE":
                render_table(c, lines, dcs, num)
            elif tag.lower() == "img":
                src = c.get("src", "")
                missing_images.append((num, src))
                lines.append(f"> **[Table/figure shown as an image in eCFR, not included as text. "
                             f"See https://www.ecfr.gov/current/title-38/section-{num} "
                             f"(image: https://www.ecfr.gov{src})]**\n")
            elif tag == "EXTRACT":
                walk(c)
            elif tag in ("NOTE", "EDNOTE"):
                t = text_of(c)
                if t: lines.append("> " + t + "\n")
            elif tag in ("CITA", "SECAUTH", "PARAUTH", "APPRO", "CROSSREF"):
                t = text_of(c)
                if t: lines.append(f"*{t}*\n")
            elif tag == "DIV9":
                h = c.find("HEAD")
                if h is not None: lines.append(f"## {text_of(h)}\n")
                walk(c)
            else:
                walk(c)
    walk(div8)
    return num, head, "\n".join(lines).strip() + "\n"

def convert(xml_paths, out, as_of):
    os.makedirs(out, exist_ok=True)
    index, dcs, meta_files, missing_images = [], [], [], []
    for p in xml_paths:
        raw = open(p, "rb").read()
        root = ET.fromstring(raw)
        part = root.get("N")
        meta_files.append({"part": part, "file": os.path.basename(p),
                           "sha256": hashlib.sha256(raw).hexdigest()})
        pdir = os.path.join(out, f"part-{part}")
        os.makedirs(pdir, exist_ok=True)
        part_head = text_of(root.find("HEAD"))
        index.append(f"\n## {part_head}\n")
        for sub in root.iter("DIV6"):
            sh = sub.find("HEAD")
            index.append(f"\n### {text_of(sh) if sh is not None else 'Subpart ' + sub.get('N')}\n")
            for div8 in sub.iter("DIV8"):
                num, head, md = render_section(div8, dcs, missing_images)
                fn = f"{num}.md"
                with open(os.path.join(pdir, fn), "w") as f:
                    f.write(f"<!-- 38 CFR {num} | eCFR as of {as_of} | {_BUILD} -->\n" + md)
                index.append(f"- [{head}](part-{part}/{fn})")
    with open(os.path.join(out, "index.md"), "w") as f:
        f.write(f"# 38 CFR Index (eCFR as of {as_of})\n<!-- {_BUILD} -->\n" + "\n".join(index) + "\n")
    seen, rows = set(), []
    for code, name, sec in sorted(dcs, key=lambda d: d[0]):
        if code in seen: continue
        seen.add(code); rows.append(f"| {code} | {name} | [38 CFR {sec}](part-4/{sec}.md) |")
    with open(os.path.join(out, "diagnostic-codes.md"), "w") as f:
        f.write(f"# Part 4 Diagnostic Codes (eCFR as of {as_of})\n<!-- {_BUILD} -->\n\n| DC | Condition | Section |\n|---|---|---|\n" + "\n".join(rows) + "\n")
    meta = {"build": _BUILD, "source": "eCFR (ecfr.gov), Title 38 Chapter I", "as_of": as_of,
            "converted": date.today().isoformat(), "files": meta_files,
            "sections": sum(1 for l in index if l.startswith("- [")), "diagnostic_codes": len(rows),
            "image_only_tables": sorted({n for n, _ in missing_images})}
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    return meta

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--as-of", required=True)
    a = ap.parse_args()
    print(json.dumps(convert(a.xml, a.out, a.as_of), indent=2))
