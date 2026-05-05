"""
  Checks:
    1. Metadata Analysis  
    2. Incremental Updates  EOF
    3. Font Consistency     multiple font sources
    4. Multiple Producers   traces of more than one tool used
"""

import re
from datetime import datetime
from pypdf import PdfReader


#Known editing tools
EDITING_TOOLS = [
    "ilovepdf", "smallpdf", "sejda", "pdf24", "pdfcandy",
    "adobe acrobat", "foxit", "nitro", "inkscape", "gimp",
    "libreoffice draw", "pdfescapecom", "pdfescape",
    "canva", "photoshop", "illustrator"
]

# Legitimate tools
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
          - No metadata at all (stripped)
          - Creation date is in the future
    """

    flags    = []
    metadata = {}

    info = reader.metadata
    # print(info)
    if not info:
        flags.append("No metadata found")
        return {
            "metadata"  : metadata,
            "flags"     : flags,
            "suspicious": 1,
            "detail"    : "Metadata completely missing"
        }

    # print(str(info.get("/Producer")).strip())
    
    # Extract key fields safely
    creator  = str(info.get("/Creator")).strip()
    producer = str(info.get("/Producer")).strip()
    created  = str(info.get("/CreationDate")).strip()
    modified = str(info.get("/ModDate")).strip()

    # Check if producer/creator is a known editing tool
    creator_lower=creator.lower()
    producer_lower=producer.lower()
    if creator_lower in EDITING_TOOLS:
        flags.append(f"Editing tool detected in creator: '{creator_lower}'")
    if producer_lower in EDITING_TOOLS:
        flags.append(f"Editing tool detected in producer: '{producer_lower}'")

    # Check date gap between creation and modification
    if created and modified and created != modified:
        try:
            # PDF dates are in format: D:YYYYMMDDHHmmSS
            dt_created  = datetime.strptime(created[2:14], "%Y%m%d%H%M%S")
            dt_modified = datetime.strptime(modified[2:14], "%Y%m%d%H%M%S")

            gap_days = (dt_modified - dt_created).days
            
            if gap_days > 30:
                flags.append(f"Large gap between creation and modification: {gap_days} days")
            elif gap_days < 0:
                flags.append("Modification date is before creation date — impossible")

        except Exception:
            pass  # date parsing failed 
        
    # Check if creation date is in the future

    if created:
        try:
            dt_created = datetime.strptime(created[2:14], "%Y%m%d%H%M%S")
            if dt_created > datetime.now():
                flags.append(f"Creation date is in the future: {created}")
        except Exception:
            pass
    else:
        flags.append("No creator info present")

    return {
        "metadata"  : metadata,
        "flags"     : flags,
        "suspicious": len(flags)>0,
        "detail"    : f"{len(flags)} metadata flag(s): {'; '.join(flags) if flags else 'None'}"
    }



def check_EOF(pdf_path):
    #checks EOF(end of file) in data
    
    f=open(pdf_path, "rb")
    lines = f.read()

    # Count %%EOF in raw bytes
    eof_count = lines.count(b"%%EOF")

    flags = []
    if eof_count > 1:
        flags.append("Edited : "+str(eof_count-1)+" times")

    return {
        "eof_count" : eof_count,
        "flags"     : flags,
        "suspicious": eof_count > 1,
    }


def check_fonts(reader):
    fonts, subsets = set(), set()

    try:
        page = reader.pages[0]
        font_dict = (page.get("/Resources") or {}).get("/Font") or {}

        for f in font_dict.values():
            f = f.get_object()
            name = f.get("/BaseFont")
            if not name:
                continue

            name = str(name).lstrip("/")              # normalize
            fonts.add(name)

            if re.match(r'^[A-Z]{6}\+', name):        # subset check
                subsets.add(name)

    except Exception:
        raise ValueError("Invalid PDF: unable to extract font data")

    # derive base families
    base_families = {
        re.sub(r'^[A-Z]{6}\+', '', f) for f in fonts
    }

    flags = []
    if len(base_families) > 4:
        flags.append(f"High font variety: {len(base_families)} — {sorted(base_families)}")

    if len(subsets) > 6:
        flags.append(f"Too many subsets: {len(subsets)}")

    # print(len(fonts))

    return {
        "fonts": sorted(fonts),
        "base_families": sorted(base_families),
        "subset_count": len(subsets),
        "flags": flags,
        "suspicious": bool(flags)
    }


def check_multiple_producers(pdf_path):
   #check multiple producers other than metadata

    f=open(pdf_path, "rb")
    content = f.read().decode("latin-1", errors="ignore")
    #content has the whole pdf in forced readble and contain producer and creator
    f.close()

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
        if p.lower() in EDITING_TOOLS:
            flags.append(f"Editing tool signature found in file body: '{p}'")
            break

    return {
        "producers" : unique_producers,
        "creators"  : unique_creators,
        "flags"     : flags,
        "suspicious": len(flags) > 0,
        "detail"    : f"{len(unique_producers)} producer(s), {len(unique_creators)} creator(s)"
    }


def compute_pdf_score(metadata, incremental, fonts, producers):
    '''
    Combines all 4 check results into one 0-100 score.
    Weights:
        Incremental updates  → 50 pts  (strongest structural signal)
        Metadata flags       → 50 pts  (editing tool traces)
        Multiple producers   → 30 pts  (multi-tool usage)
        Font inconsistency   → 10 pts  (supporting signal)
    '''

    score = 0.0

    # Metadata
    if metadata["suspicious"]:
        score += 50

    # Incremental updates
    if incremental["suspicious"]:
        score += 50
    
    # Multiple producers
    if producers["suspicious"]:
        score += 30

    # Font inconsistency:
    if fonts["suspicious"]:
        score += 10

    
    score=score/1.4

    return round(score, 2)


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
    EOF = check_EOF(pdf_path)
    fonts       = check_fonts(reader)
    producers   = check_multiple_producers(pdf_path)

    # Compute score
    pdf_score = compute_pdf_score(metadata, EOF, fonts, producers)
    overall_suspicious = pdf_score >= 35.0

    # Print summary
    summary=[("METADATA", metadata),("INCREMENTAL", EOF),("FONTS", fonts),("PRODUCERS", producers)]
    
    for name, result in summary:
        flag = "SUS" if result["suspicious"] else "OK"
        print(f"  [{flag}] {name:12} {result['flags']}")

    print(f"\n  PDF Score  : {pdf_score} / 100")
    print(f"  Verdict    : {'SUSPICIOUS' if overall_suspicious else 'Likey Genuine'}")

    return {
        "metadata"          : metadata,
        "incremental"       : EOF,
        "fonts"             : fonts,
        "producers"         : producers,
        "pdf_score"         : pdf_score,
        "overall_suspicious": overall_suspicious
    }


if __name__ == "__main__":
    path   = "C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\stage_1 Input Normalization\\admit.pdf"
    result = run_pdf_forensics(path)