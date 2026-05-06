"""
  Checks:
    1. OCR Extraction       : reads all text from the document
    2. Spelling Validation  : flags misspelled words
    3. Date Validation      : flags invalid dates (e.g. 31 Feb)
    4. Numeric Field Checks : Aadhaar, PAN, PIN, phone formats

  Supports both image files (via EasyOCR) and PDF files (via pypdf).
"""

import re
import os
import easyocr
from spellchecker import SpellChecker
from pypdf import PdfReader

path = "local datastore/main.pdf"

print("[Stage 5] Loading EasyOCR model")
reader = easyocr.Reader(["en", "hi"], gpu=False)
spell  = SpellChecker()


# ── Text Extraction ───────────────────────────────────────

def extract_text_from_image(image_path):
    """Uses EasyOCR to extract text from image files (JPG, PNG)."""
    raw        = reader.readtext(image_path)
    detections = [{"text": text.strip(), "confidence": round(conf, 3)}
                  for (_, text, conf) in raw if conf >= 0.5]
    full_text  = " ".join([d["text"] for d in detections])
    word_list  = full_text.split()
    return {
        "full_text" : full_text,
        "detections": detections,
        "word_list" : word_list,
        "word_count": len(word_list),
        "source"    : "easyocr"
    }


def extract_text_from_pdf(pdf_path):
    """
    Uses pypdf to extract embedded text from vector PDFs.
    Much more accurate than OCR for PDFs since text is already stored as characters.
    """
    reader_pdf = PdfReader(pdf_path)
    all_text   = ""
    for page in reader_pdf.pages:
        text = page.extract_text()
        if text:
            all_text += text + " "

    full_text = all_text.strip()
    word_list = full_text.split()
    return {
        "full_text" : full_text,
        "detections": [],          # no per-word confidence for PDF text
        "word_list" : word_list,
        "word_count": len(word_list),
        "source"    : "pypdf"
    }


# ── Checks ────────────────────────────────────────────────

def check_spelling(word_list):
    checkable = [
        w for w in word_list
        if len(w) >= 3
        and not w.isnumeric()
        and not w.isupper()
        and not any(char.isdigit() for char in w)
    ]
    if not checkable:
        return {"misspelled": [], "spell_score": 0.0, "suspicious": False,
                "detail": "No checkable words found"}

    misspelled  = list(spell.unknown(checkable))
    spell_score = round(len(misspelled) / len(checkable), 3)
    return {
        "misspelled" : misspelled,
        "spell_score": spell_score,
        "suspicious" : spell_score > 0.05,
        "detail"     : f"{len(misspelled)} misspelled word(s) out of {len(checkable)} checked"
    }


DAYS_IN_MONTH = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def is_valid_date(day, month, year):
    if month < 1 or month > 12:    return False
    if day < 1 or day > DAYS_IN_MONTH[month]: return False
    if year < 1900 or year > 2100: return False
    return True

def check_dates(full_text):
    month_names = {
        "january":1, "february":2, "march":3, "april":4, "may":5, "june":6,
        "july":7, "august":8, "september":9, "october":10, "november":11, "december":12,
        "jan":1, "feb":2, "mar":3, "apr":4, "jun":6, "jul":7,
        "aug":8, "sep":9, "oct":10, "nov":11, "dec":12
    }
    dates_found, invalid_dates = [], []

    for pattern in [r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b',
                    r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b']:
        for match in re.finditer(pattern, full_text):
            date_str = match.group(0)
            dates_found.append(date_str)
            parts = [int(x) for x in re.split(r'[\/\-\.]', date_str)]
            if parts[0] > 31:
                year, month, day = parts[0], parts[1], parts[2]
            else:
                day, month, year = parts[0], parts[1], parts[2]
            if not is_valid_date(day, month, year):
                invalid_dates.append(date_str)

    text_pattern = r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b'
    for match in re.finditer(text_pattern, full_text.lower()):
        date_str = match.group(0)
        dates_found.append(date_str)
        day, month, year = int(match.group(1)), month_names[match.group(2)], int(match.group(3))
        if not is_valid_date(day, month, year):
            invalid_dates.append(date_str)

    return {
        "dates_found"  : dates_found,
        "invalid_dates": invalid_dates,
        "suspicious"   : len(invalid_dates) > 0,
        "detail"       : f"{len(dates_found)} date(s) found, {len(invalid_dates)} invalid"
    }


def check_numeric_fields(full_text):
    flags, fields = [], {}

    aadhaar_matches = re.findall(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b', full_text)
    if aadhaar_matches:
        for match in aadhaar_matches:
            if len(match.replace(" ", "")) != 12:
                flags.append(f"Invalid Aadhaar: '{match}'")
        fields["aadhaar"] = aadhaar_matches

    pan_matches = re.findall(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', full_text.upper())
    if pan_matches:
        fields["pan"] = pan_matches

    pin_matches = re.findall(r'\b[1-9][0-9]{5}\b', full_text)
    if pin_matches:
        fields["pin_code"] = pin_matches

    phone_matches = re.findall(r'\b[6-9][0-9]{9}\b', full_text)
    if phone_matches:
        fields["phone"] = phone_matches

    return {
        "fields"    : fields,
        "flags"     : flags,
        "suspicious": len(flags) > 0,
        "detail"    : f"{sum(len(v) for v in fields.values())} numeric field(s) found, {len(flags)} invalid"
    }


def compute_ocr_score(spelling, dates, numeric):
    score  = min(spelling["spell_score"] / 0.10, 1.0) * 40
    score += min(len(dates["invalid_dates"]) * 10, 35)
    score += min(len(numeric["flags"]) * 10, 25)
    return round(score, 2)


# ── Main Entry Point ──────────────────────────────────────

def run_ocr_extraction(file_path):
    """
    Works for both image files and PDFs.
    Detects file type by extension and uses the correct extractor.
    All checks (spelling, dates, numeric) are identical for both.
    """

    print(f"\n[Stage 5] OCR Extraction + Validation")
    print(f"  Input : {file_path}")
    print("-" * 50)

    # Choose extractor based on file type
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        ocr = extract_text_from_pdf(file_path)
        print(f"  Source : pypdf (direct text extraction)")
    else:
        ocr = extract_text_from_image(file_path)
        print(f"  Source : EasyOCR")

    print(f"  Words extracted : {ocr['word_count']}")
    if not ocr["word_list"]:
        print("  WARNING: No text extracted")

    spelling = check_spelling(ocr["word_list"])
    dates    = check_dates(ocr["full_text"])
    numeric  = check_numeric_fields(ocr["full_text"])
    ocr_score          = compute_ocr_score(spelling, dates, numeric)
    overall_suspicious = ocr_score >= 30.0

    for name, result in [("SPELLING", spelling), ("DATES", dates), ("NUMERIC", numeric)]:
        flag = "SUSPICIOUS" if result["suspicious"] else "OK"
        print(f"  [{flag}]  {name:10} {result['detail']}")

    print("-" * 50)
    print(f"  OCR Score  : {ocr_score} / 100")
    print(f"  Verdict    : {'SUSPICIOUS' if overall_suspicious else 'LIKELY GENUINE'}")

    return {
        "ocr"               : ocr,
        "spelling"          : spelling,
        "dates"             : dates,
        "numeric"           : numeric,
        "ocr_score"         : ocr_score,
        "overall_suspicious": overall_suspicious
    }


if __name__ == "__main__":
    result = run_ocr_extraction(path)
    print(f"\n  → OCR score for Risk Engine : {result['ocr_score']}")
    print(f"  → Extracted text            : {result['ocr']['full_text'][:200]}...")
