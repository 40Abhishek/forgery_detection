"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 4 : OCR Extraction + Text Validation
  Libraries: easyocr, pyspellchecker, re (built-in)
  Input   : PNG image (guaranteed by Stage 1)
  Output  : ocr_score (0-100) → goes to Risk Scoring Engine
            extracted text + all validation findings
=============================================================
  Checks:
    1. OCR Extraction       – reads all text from the document
    2. Spelling Validation  – flags misspelled words
    3. Date Validation      – flags invalid dates (e.g. 31 Feb)
    4. Numeric Field Checks – Aadhaar, PAN, PIN, phone formats
=============================================================
"""

import re
import easyocr
from spellchecker import SpellChecker

path   = "C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\stage_1 Input Normalization\\mig.pdf"


# ─────────────────────────────────────────────────────────
#  SETUP
#  EasyOCR reader is expensive to initialize (loads the model)
#  so we create it once here at module level, not inside a function.
#  This means it loads once when you import this file — not on
#  every document check.
#
#  Languages: English + Hindi — covers most Indian documents
#  gpu=False  — safe default, works on all machines
#             — change to gpu=True if you have a CUDA GPU
# ─────────────────────────────────────────────────────────

print("[Stage 4] Loading EasyOCR model (first run may take a moment)...")
reader = easyocr.Reader(["en", "hi"], gpu=False)
spell  = SpellChecker()


# ─────────────────────────────────────────────────────────
#  CHECK 1 : OCR EXTRACTION
# ─────────────────────────────────────────────────────────

def extract_text(image_path):
    """
    What it does:
        Runs EasyOCR on the document image and extracts all readable text.

        EasyOCR returns a list of detections, each containing:
          - bounding box coordinates (where on the image the text is)
          - the text string
          - confidence score (0.0 to 1.0 — how sure EasyOCR is)

        We keep only detections with confidence >= 0.5 to filter out
        noise and unclear regions.

    Returns:
        full_text   : all extracted text joined as one string
        detections  : list of (text, confidence) for each detected region
        word_list   : individual words (used for spell checking)
    """

    raw = reader.readtext(image_path)

    detections = []
    for (bbox, text, confidence) in raw:
        if confidence >= 0.5:
            detections.append({
                "text"      : text.strip(),
                "confidence": round(confidence, 3)
            })

    full_text = " ".join([d["text"] for d in detections])
    word_list = full_text.split()

    return {
        "full_text"  : full_text,
        "detections" : detections,
        "word_list"  : word_list,
        "word_count" : len(word_list)
    }


# ─────────────────────────────────────────────────────────
#  CHECK 2 : SPELLING VALIDATION
# ─────────────────────────────────────────────────────────

def check_spelling(word_list):
    """
    What it does:
        Checks every extracted word against an English dictionary.
        Flags words that are not recognized.

        Why this matters for forgery:
          A genuine printed document (certificate, ID) is professionally
          typeset — spelling errors are extremely rare.
          A forged document made hastily in an image editor often has
          typos, wrong words, or garbled text from bad copy-pasting.

        We skip:
          - Numbers (roll numbers, dates, IDs)
          - Words shorter than 3 characters (too, an, of etc.)
          - All-caps words (abbreviations like DOB, GOVT, MCA)
          - Words with mixed digits (e.g. B.Tech, 12th)

    Returns:
        misspelled   : list of flagged words
        spell_score  : ratio of misspelled to total words (0.0 to 1.0)
        suspicious   : True if more than 5% of words are misspelled
    """

    # Filter words worth checking
    checkable = [
        w for w in word_list
        if len(w) >= 3
        and not w.isnumeric()
        and not w.isupper()
        and not any(char.isdigit() for char in w)
    ]

    if not checkable:
        return {
            "misspelled" : [],
            "spell_score": 0.0,
            "suspicious" : False,
            "detail"     : "No checkable words found"
        }

    misspelled  = list(spell.unknown(checkable))
    spell_score = round(len(misspelled) / len(checkable), 3) if checkable else 0.0

    return {
        "misspelled" : misspelled,
        "spell_score": spell_score,
        "suspicious" : spell_score > 0.05,   # more than 5% misspelled = suspicious
        "detail"     : f"{len(misspelled)} misspelled word(s) out of {len(checkable)} checked"
    }


# ─────────────────────────────────────────────────────────
#  CHECK 3 : DATE VALIDATION
# ─────────────────────────────────────────────────────────

# Days in each month — index 0 unused, 1=Jan ... 12=Dec
DAYS_IN_MONTH = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def is_valid_date(day, month, year):
    """Returns True if the date is logically valid."""
    if month < 1 or month > 12:
        return False
    if day < 1 or day > DAYS_IN_MONTH[month]:
        return False
    if year < 1900 or year > 2100:
        return False
    return True

def check_dates(full_text):
    """
    What it does:
        Finds all date-like patterns in the extracted text using regex.
        Validates each one logically — month must be 1-12, day must
        be valid for that month, year must be reasonable.

        Patterns detected:
          DD/MM/YYYY   DD-MM-YYYY   DD.MM.YYYY
          YYYY/MM/DD   YYYY-MM-DD
          DD Month YYYY  (e.g. 15 March 2022)

        Why this matters for forgery:
          Someone editing a date carelessly may produce impossible dates
          like 31/02/2023 (Feb has no 31st) or 00/13/2021.

    Returns:
        dates_found  : list of all date strings detected
        invalid_dates: list of dates that failed validation
        suspicious   : True if any invalid date found
    """

    # Regex patterns for common date formats
    patterns = [
        r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b',   # DD/MM/YYYY
        r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b',   # YYYY/MM/DD
    ]

    month_names = {
        "january":1, "february":2, "march":3, "april":4,
        "may":5, "june":6, "july":7, "august":8,
        "september":9, "october":10, "november":11, "december":12,
        "jan":1, "feb":2, "mar":3, "apr":4, "jun":6,
        "jul":7, "aug":8, "sep":9, "oct":10, "nov":11, "dec":12
    }

    dates_found   = []
    invalid_dates = []

    # Check numeric date patterns
    for pattern in patterns:
        for match in re.finditer(pattern, full_text):
            date_str = match.group(0)
            dates_found.append(date_str)
            parts = [int(x) for x in re.split(r'[\/\-\.]', date_str)]

            # Determine if format is DD/MM/YYYY or YYYY/MM/DD
            if parts[0] > 31:
                year, month, day = parts[0], parts[1], parts[2]
            else:
                day, month, year = parts[0], parts[1], parts[2]

            if not is_valid_date(day, month, year):
                invalid_dates.append(date_str)

    # Check text dates like "15 March 2022"
    text_date_pattern = r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\b'
    for match in re.finditer(text_date_pattern, full_text.lower()):
        date_str = match.group(0)
        dates_found.append(date_str)
        day   = int(match.group(1))
        month = month_names[match.group(2)]
        year  = int(match.group(3))
        if not is_valid_date(day, month, year):
            invalid_dates.append(date_str)

    return {
        "dates_found"  : dates_found,
        "invalid_dates": invalid_dates,
        "suspicious"   : len(invalid_dates) > 0,
        "detail"       : f"{len(dates_found)} date(s) found, {len(invalid_dates)} invalid"
    }


# ─────────────────────────────────────────────────────────
#  CHECK 4 : NUMERIC FIELD CHECKS
# ─────────────────────────────────────────────────────────

def check_numeric_fields(full_text):
    """
    What it does:
        Looks for known Indian document number formats using regex.
        Validates that they match the correct pattern.

        Fields checked:
          Aadhaar  : 12 digits, usually in groups of 4  (XXXX XXXX XXXX)
          PAN      : 5 letters + 4 digits + 1 letter    (ABCDE1234F)
          PIN code : 6 digits starting with 1-9         (110001)
          Phone    : 10 digits starting with 6-9        (9876543210)

        Why this matters for forgery:
          A forged Aadhaar might have 11 or 13 digits.
          A fake PAN might have wrong character positions.
          These are easy mistakes to make when editing in an image editor.

    Returns:
        fields     : dict of each field type with found values + validity
        flags      : list of invalid field findings
        suspicious : True if any field fails its format check
    """

    flags  = []
    fields = {}

    # Aadhaar: 12 consecutive digits (spaces between groups are stripped)
    aadhaar_pattern = r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b'
    aadhaar_matches = re.findall(aadhaar_pattern, full_text)
    if aadhaar_matches:
        for match in aadhaar_matches:
            digits = match.replace(" ", "")
            if len(digits) != 12:
                flags.append(f"Invalid Aadhaar number: '{match}' (expected 12 digits)")
        fields["aadhaar"] = aadhaar_matches

    # PAN: exactly ABCDE1234F format
    pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
    pan_matches = re.findall(pan_pattern, full_text.upper())
    if pan_matches:
        fields["pan"] = pan_matches  # regex already enforces format

    # PIN code: 6 digits, first digit not 0
    pin_pattern = r'\b[1-9][0-9]{5}\b'
    pin_matches = re.findall(pin_pattern, full_text)
    if pin_matches:
        fields["pin_code"] = pin_matches

    # Phone: 10 digits starting with 6, 7, 8, or 9
    phone_pattern = r'\b[6-9][0-9]{9}\b'
    phone_matches = re.findall(phone_pattern, full_text)
    if phone_matches:
        fields["phone"] = phone_matches

    return {
        "fields"    : fields,
        "flags"     : flags,
        "suspicious": len(flags) > 0,
        "detail"    : f"{sum(len(v) for v in fields.values())} numeric field(s) found, {len(flags)} invalid"
    }


# ─────────────────────────────────────────────────────────
#  OCR SCORE  (0 - 100)
# ─────────────────────────────────────────────────────────

def compute_ocr_score(spelling, dates, numeric):
    """
    Combines all text validation findings into one 0-100 score.
    Higher = more suspicious.

    Weights:
        Spelling errors   → 40 pts  (strong forgery signal)
        Invalid dates     → 35 pts  (hard to fake correctly)
        Invalid numbers   → 25 pts  (format errors are common in fakes)
    """

    score = 0.0

    # Spelling: scale by ratio — 10% misspelled = full 40 pts
    score += min(spelling["spell_score"] / 0.10, 1.0) * 40

    # Dates: each invalid date = 10 pts, capped at 35
    score += min(len(dates["invalid_dates"]) * 10, 35)

    # Numeric: each invalid field = 10 pts, capped at 25
    score += min(len(numeric["flags"]) * 10, 25)

    return round(score, 2)


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_ocr_extraction(image_path):
    """
    Call this from your pipeline after Stage 3.

    Args:
        image_path : path to the normalized PNG from Stage 1

    Returns:
        {
            "ocr"       : { full_text, detections, word_list, word_count }
            "spelling"  : { misspelled, spell_score, suspicious, detail }
            "dates"     : { dates_found, invalid_dates, suspicious, detail }
            "numeric"   : { fields, flags, suspicious, detail }
            "ocr_score" : float 0-100  → feed to Stage 9 Risk Engine
            "overall_suspicious" : bool
        }
    """

    print(f"\n[Stage 4] OCR Extraction + Validation")
    print(f"  Input : {image_path}")
    print("-" * 50)

    # Step 1: Extract text
    ocr = extract_text(image_path)
    print(f"  Text extracted : {ocr['word_count']} words")
    if not ocr["word_list"]:
        print("  WARNING: No text extracted — image may be too blurry or low resolution")

    # Step 2: Run all checks
    spelling = check_spelling(ocr["word_list"])
    dates    = check_dates(ocr["full_text"])
    numeric  = check_numeric_fields(ocr["full_text"])

    # Step 3: Compute score
    ocr_score          = compute_ocr_score(spelling, dates, numeric)
    overall_suspicious = ocr_score >= 30.0

    # Print summary
    for name, result in [("SPELLING", spelling), ("DATES", dates), ("NUMERIC", numeric)]:
        flag = "⚠  SUSPICIOUS" if result["suspicious"] else "✓  OK"
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


# ─────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    
    result = run_ocr_extraction(path)
    print(f"\n  → OCR score for Risk Engine : {result['ocr_score']}")
    print(f"  → Extracted text            : {result['ocr']['full_text'][:200]}...")