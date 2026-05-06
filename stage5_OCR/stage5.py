import re
import os
import cv2
import pytesseract
from spellchecker import SpellChecker
from pypdf import PdfReader

# OPTIONAL: only needed if Render doesn't auto-detect tesseract
# pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

path = "local datastore/main.pdf"


# ── Text Extraction ───────────────────────────────────────

def extract_text_from_image(image_path):
    """Uses Tesseract OCR to extract text from image files (JPG, PNG)."""

    print("[Stage 5] Using Tesseract OCR")

    # Read image
    image = cv2.imread(image_path)

    # 🔥 Preprocessing (important for accuracy + lower memory)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.2, fy=1.2)
    gray = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

    # OCR
    full_text = pytesseract.image_to_string(gray)

    word_list = full_text.split()

    # Simulate detections (since Tesseract doesn’t give same format as EasyOCR)
    detections = [{"text": w, "confidence": None} for w in word_list]

    return {
        "full_text": full_text,
        "detections": detections,
        "word_list": word_list,
        "word_count": len(word_list),
        "source": "tesseract"
    }


def extract_text_from_pdf(pdf_path):
    """
    Uses pypdf to extract embedded text from vector PDFs.
    """
    reader_pdf = PdfReader(pdf_path)
    all_text = ""

    for page in reader_pdf.pages:
        text = page.extract_text()
        if text:
            all_text += text + " "

    full_text = all_text.strip()
    word_list = full_text.split()

    return {
        "full_text": full_text,
        "detections": [],
        "word_list": word_list,
        "word_count": len(word_list),
        "source": "pypdf"
    }


# ── Checks (UNCHANGED) ────────────────────────────────────
# (Everything below remains exactly same as your original)

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

    spell = SpellChecker()
    misspelled = list(spell.unknown(checkable))
    spell_score = round(len(misspelled) / len(checkable), 3)

    return {
        "misspelled": misspelled,
        "spell_score": spell_score,
        "suspicious": spell_score > 0.05,
        "detail": f"{len(misspelled)} misspelled word(s) out of {len(checkable)} checked"
    }


DAYS_IN_MONTH = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def is_valid_date(day, month, year):
    if month < 1 or month > 12: return False
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

    return {
        "dates_found": dates_found,
        "invalid_dates": invalid_dates,
        "suspicious": len(invalid_dates) > 0,
        "detail": f"{len(dates_found)} date(s) found, {len(invalid_dates)} invalid"
    }


def check_numeric_fields(full_text):
    flags, fields = [], {}

    aadhaar_matches = re.findall(r'\b\d{4}\s\d{4}\s\d{4}\b|\b\d{12}\b', full_text)
    if aadhaar_matches:
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
        "fields": fields,
        "flags": flags,
        "suspicious": len(flags) > 0,
        "detail": f"{sum(len(v) for v in fields.values())} numeric field(s) found"
    }


def compute_ocr_score(spelling, dates, numeric):
    score = min(spelling["spell_score"] / 0.10, 1.0) * 40
    score += min(len(dates["invalid_dates"]) * 10, 35)
    score += min(len(numeric["flags"]) * 10, 25)
    return round(score, 2)


# ── Main Entry ────────────────────────────────────────────

def run_ocr_extraction(file_path):
    print(f"\n[Stage 5] OCR Extraction + Validation")
    print(f"  Input : {file_path}")
    print("-" * 50)

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        ocr = extract_text_from_pdf(file_path)
        print("  Source : pypdf")
    else:
        ocr = extract_text_from_image(file_path)
        print("  Source : Tesseract")

    print(f"  Words extracted : {ocr['word_count']}")

    spelling = check_spelling(ocr["word_list"])
    dates = check_dates(ocr["full_text"])
    numeric = check_numeric_fields(ocr["full_text"])

    ocr_score = compute_ocr_score(spelling, dates, numeric)

    return {
        "ocr": ocr,
        "spelling": spelling,
        "dates": dates,
        "numeric": numeric,
        "ocr_score": ocr_score
    }


if __name__ == "__main__":
    result = run_ocr_extraction(path)
    print(result)