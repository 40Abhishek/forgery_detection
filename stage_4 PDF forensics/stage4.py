"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 4 : PDF Forensics
  Library : pypdf only
  Input   : Vector PDF file (routed here by Stage 1)
  Output  : pdf_score (0-100) → goes to Risk Scoring Engine
=============================================================
  This stage runs ONLY for vector PDFs.
  Image-based PDFs are converted to PNG in Stage 1 and go
  through the normal image pipeline (Stage 2, 3, 4).

  Checks:
    1. Metadata Analysis     – creator/producer mismatch, date gaps
    2. Incremental Updates   – appended edits on top of original
    3. Font Consistency      – multiple font sources = suspicious
    4. Multiple Producers    – traces of more than one tool used
    5. Object Stream Check   – overlapping/duplicate text objects
=============================================================
"""

import re
from datetime import datetime
from pypdf import PdfReader


# ─────────────────────────────────────────────────────────
#  KNOWN EDITING TOOLS
#  These are producer/creator strings left by common online
#  PDF editors. If we see these in a document that claims to
#  be an official certificate or government document, that is
#  a strong red flag.
# ─────────────────────────────────────────────────────────

EDITING_TOOLS = [
    "ilovepdf", "smallpdf", "sejda", "pdf24", "pdfcandy",
    "adobe acrobat", "foxit", "nitro", "inkscape", "gimp",
    "libreoffice draw", "pdfescapecom", "pdfescape",
    "canva", "photoshop", "illustrator"
]

# Legitimate tools that generate original government/institutional docs
LEGITIMATE_TOOLS = [
    "microsoft word", "microsoft office", "libreoffice writer",
    "wkhtmltopdf", "reportlab", "fpdf", "latex", "pdflatex",
    "prince", "chromium", "google docs"
]

def check_metadata(reader):
    """
    Flags raised:
          - Creator or Producer matches a known editing tool
          - Modification date exists and is significantly later
            than creation date (gap > 30 days = suspicious)
          - No metadata at all (stripped — common after editing)
          - Creation date is in the future (impossible = fake)

    sus level= 30+30+30 each check
    """

    flags    = []
    metadata = {}
    suspicious_level=0

    info = reader.metadata
    # print(info)
    if not info:
        flags.append("No metadata found")
        return {
            "metadata"  : metadata,
            "flags"     : flags,
            "suspicious": 90,
            "detail"    : "Metadata completely missing"
        }

    # print(str(info.get("/Producer")).strip())
    
    # Extract key fields safely
    creator  = str(info.get("/Creator")).strip()
    producer = str(info.get("/Producer")).strip()
    created  = str(info.get("/CreationDate")).strip()
    modified = str(info.get("/ModDate")).strip()

    metadata = {"creator" : creator,"producer": producer,"created" : created,"modified": modified}
    # print(metadata)

    # Check if producer/creator is a known editing tool
    for field_name, field_value in [("Creator", creator), ("Producer", producer)]:
        field_lower = field_value.lower()
        for tool in EDITING_TOOLS:
            if tool in field_lower:
                flags.append(f"Editing tool detected in {field_name}: '{field_value}'")
                break

    # Check date gap between creation and modification
    if created and modified and created != modified:
        try:
            # PDF dates are in format: D:YYYYMMDDHHmmSS
            dt_created  = datetime.strptime(created[2:14], "%Y%m%d%H%M%S")
            dt_modified = datetime.strptime(modified[2:14], "%Y%m%d%H%M%S")

            gap_days = (dt_modified - dt_created).days
            
            if gap_days > 30:
                flags.append(f"Large gap between creation and modification: {gap_days} days")
                suspicious_level+=30
            elif gap_days < 0:
                flags.append("Modification date is before creation date — impossible")
                suspicious_level=90

        except Exception:
            pass  # date parsing failed 
        
    # Check if creation date is in the future

    if created:
        try:
            dt_created = datetime.strptime(created[2:14], "%Y%m%d%H%M%S")
            if dt_created > datetime.now():
                flags.append(f"Creation date is in the future: {created}")
                suspicious_level=90
        except Exception:
            pass
    else:
        flags.append("No creator info present")
        suspicious_level=90

    return {
        "metadata"  : metadata,
        "flags"     : flags,
        "suspicious": suspicious_level,
        "detail"    : f"{len(flags)} metadata flag(s): {'; '.join(flags) if flags else 'None'}"
    }


# ─────────────────────────────────────────────────────────
#  CHECK 2 : INCREMENTAL UPDATES
# ─────────────────────────────────────────────────────────

def check_incremental_updates(pdf_path):
    """
    What it does:
        Reads the raw bytes of the PDF file and counts how many
        times "%%EOF" appears.

        Every PDF ends with %%EOF. When an online editor saves
        changes, it appends the edits to the end of the file
        instead of rebuilding it — this adds another %%EOF.

        So:
          1 × %%EOF = original, unmodified PDF
          2 × %%EOF = one round of edits applied
          3+× %%EOF = multiple rounds of editing

    Why this matters:
        This is the strongest structural signal for post-creation
        edits. It is very hard to fake and easy to explain.
    """

    with open(pdf_path, "rb") as f:
        content = f.read()

    # Count occurrences of %%EOF in raw bytes
    eof_count = content.count(b"%%EOF")

    flags = []
    if eof_count > 1:
        flags.append(
            f"PDF has {eof_count} %%EOF markers — "
            f"{eof_count - 1} incremental update(s) detected"
        )

    return {
        "eof_count" : eof_count,
        "flags"     : flags,
        "suspicious": eof_count > 1,
        "detail"    : f"%%EOF count = {eof_count} ({'edited' if eof_count > 1 else 'original'})"
    }


# ─────────────────────────────────────────────────────────
#  CHECK 3 : FONT CONSISTENCY
# ─────────────────────────────────────────────────────────

def check_fonts(reader):
    """
    What it does:
        Collects all fonts used across all pages of the PDF.
        A genuine document is typeset consistently — one or two
        font families throughout.

        When someone edits text in an online tool, the new text
        is often rendered in a different font or an embedded
        font subset with a different name prefix.

        Font name prefixes like "ABCDEF+FontName" are subsets —
        each unique prefix means a separately embedded font chunk.
        Too many subsets = suspicious.

    Flags raised:
        - More than 4 distinct font families used
        - More than 6 font subsets (XXXXXX+ prefixed names)
    """

    flags      = []
    all_fonts  = set()
    subsets    = set()

    for page in reader.pages:
        try:
            resources = page.get("/Resources")
            if not resources:
                continue
            font_dict = resources.get("/Font")
            if not font_dict:
                continue
            for key in font_dict:
                font_obj  = font_dict[key]
                font_name = str(font_obj.get("/BaseFont", "")).replace("/", "")
                if font_name:
                    all_fonts.add(font_name)
                    # Subset fonts have a 6-char prefix e.g. ABCDEF+Arial
                    if re.match(r'^[A-Z]{6}\+', font_name):
                        subsets.add(font_name)
        except Exception:
            continue

    # Strip subset prefix to get base family names
    base_families = set()
    for font in all_fonts:
        base = re.sub(r'^[A-Z]{6}\+', '', font)
        base_families.add(base)

    if len(base_families) > 4:
        flags.append(
            f"High font variety: {len(base_families)} font families found — "
            f"{sorted(base_families)}"
        )

    if len(subsets) > 6:
        flags.append(
            f"Too many font subsets: {len(subsets)} — "
            f"may indicate text added from multiple sources"
        )

    return {
        "fonts"        : sorted(all_fonts),
        "base_families": sorted(base_families),
        "subset_count" : len(subsets),
        "flags"        : flags,
        "suspicious"   : len(flags) > 0,
        "detail"       : f"{len(base_families)} font family/families, {len(subsets)} subset(s)"
    }


# ─────────────────────────────────────────────────────────
#  CHECK 4 : MULTIPLE PRODUCERS
# ─────────────────────────────────────────────────────────

def check_multiple_producers(pdf_path):
    """
    What it does:
        Scans the raw PDF content for all Producer and Creator
        strings embedded anywhere in the file — not just the
        metadata header.

        When a PDF is edited and saved, the new tool often writes
        its own producer string into the appended section.
        Finding more than one unique producer = multiple tools used.

    Why this matters:
        If a certificate was generated by "ReportLab" but also
        contains a "Sejda" producer string buried in the file,
        that's a clear sign of post-generation editing.
    """

    with open(pdf_path, "rb") as f:
        content = f.read().decode("latin-1", errors="ignore")

    # Find all Producer and Creator entries in raw content
    producers = re.findall(r'/Producer\s*\(([^)]+)\)', content)
    creators  = re.findall(r'/Creator\s*\(([^)]+)\)',  content)

    unique_producers = list(set(producers))
    unique_creators  = list(set(creators))

    flags = []
    if len(unique_producers) > 1:
        flags.append(f"Multiple producers found: {unique_producers}")
    if len(unique_creators) > 1:
        flags.append(f"Multiple creators found: {unique_creators}")

    # Check if any producer is a known editing tool
    for p in unique_producers + unique_creators:
        for tool in EDITING_TOOLS:
            if tool in p.lower():
                flags.append(f"Editing tool signature found in file body: '{p}'")
                break

    return {
        "producers" : unique_producers,
        "creators"  : unique_creators,
        "flags"     : flags,
        "suspicious": len(flags) > 0,
        "detail"    : f"{len(unique_producers)} producer(s), {len(unique_creators)} creator(s)"
    }


# ─────────────────────────────────────────────────────────
#  PDF SCORE  (0 - 100)
# ─────────────────────────────────────────────────────────

def compute_pdf_score(metadata, incremental, fonts, producers):
    """
    Combines all 4 check results into one 0-100 score.
    Higher = more suspicious.

    Weights:
        Incremental updates  → 35 pts  (strongest structural signal)
        Metadata flags       → 30 pts  (editing tool traces)
        Multiple producers   → 25 pts  (multi-tool usage)
        Font inconsistency   → 10 pts  (supporting signal)
    """

    score = 0.0

    # Incremental updates: each extra EOF = 10 pts, capped at 35
    extra_eof = max(0, incremental["eof_count"] - 1)
    score    += min(extra_eof * 10, 35)

    # Metadata: each flag = 10 pts, capped at 30
    score += min(len(metadata["flags"]) * 10, 30)

    # Multiple producers: each flag = 10 pts, capped at 25
    score += min(len(producers["flags"]) * 10, 25)

    # Font inconsistency: each flag = 5 pts, capped at 10
    score += min(len(fonts["flags"]) * 5, 10)

    return round(score, 2)


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_pdf_forensics(pdf_path):
    """
    returns a dict:
        {
            "metadata"    : { metadata dict, flags, suspicious, detail }
            "incremental" : { eof_count, flags, suspicious, detail }
            "fonts"       : { fonts, base_families, subset_count, flags, suspicious, detail }
            "producers"   : { producers, creators, flags, suspicious, detail }
            "pdf_score"   : float 0-100 → feed to Stage 9 Risk Engine
            "overall_suspicious" : bool
        }
    """

    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        raise ValueError(f"Could not read PDF: {pdf_path} — {e}")

    print("\nPDF Forensics")
    print("  Input : ",pdf_path.split("\\")[-1])
    print("  Pages : ",len(reader.pages))
    print("\n")

    # Run all checks
    metadata    = check_metadata(reader)
    return 0
    incremental = check_incremental_updates(pdf_path)
    fonts       = check_fonts(reader)
    producers   = check_multiple_producers(pdf_path)

    # Compute score
    pdf_score          = compute_pdf_score(metadata, incremental, fonts, producers)
    overall_suspicious = pdf_score >= 30.0

    # Print summary
    summary=[("METADATA", metadata),("INCREMENTAL", incremental),("FONTS", fonts),("PRODUCERS", producers)]
    
    for name, result in summary:
        flag = "SUS" if result["suspicious"] else "OK"
        print(f"  [{flag}] {name:12} {result['detail']}")

    print(f"\n  PDF Score  : {pdf_score} / 100")
    print(f"  Verdict    : {'SUSPICIOUS' if overall_suspicious else 'Likey Genuine'}")

    return {
        "metadata"          : metadata,
        "incremental"       : incremental,
        "fonts"             : fonts,
        "producers"         : producers,
        "pdf_score"         : pdf_score,
        "overall_suspicious": overall_suspicious
    }


if __name__ == "__main__":
    path   = "C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\stage_1 Input Normalization\\mig.pdf"
    result = run_pdf_forensics(path)