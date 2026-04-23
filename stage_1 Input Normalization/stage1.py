"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 1 : Input Normalization
  Libraries: cv2, pypdf, pypdfium2 (for image-based PDF extraction)
  Input   : Any supported file (JPG, JPEG, PNG, PDF)
  Output  : Normalized PNG path + file type info
            → routes to correct next stage
=============================================================
  What this stage does:
    - Accepts JPG, JPEG, PNG, PDF files only
    - Never touches the original file — always works on a copy
    - Detects file type properly (by content, not just extension)
    - Converts everything to PNG for the pipeline
    - For PDFs: detects vector vs image-based
        → Image-based PDF : extracts first page image → PNG
        → Vector PDF      : copies as-is → routes to Stage 8

  Output routes:
    IMAGE / IMAGE-BASED PDF  →  PNG file  →  Stage 2 (Image Forensics)
    VECTOR PDF               →  PDF copy  →  Stage 8 (PDF Forensics)
=============================================================
"""

import os
import shutil
import cv2
import numpy as np
from pypdf import PdfReader


# ─────────────────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".pdf"]

# All pipeline working files go here — original is never touched
WORK_DIR = "pipeline_working"


# ─────────────────────────────────────────────────────────
#  HELPER : SETUP WORKING DIRECTORY
# ─────────────────────────────────────────────────────────

def setup_work_dir():
    """
    Creates the working directory if it does not exist.
    All pipeline files (copies, converted PNGs, heatmaps etc.)
    are stored here. Original file is never moved or modified.
    """
    os.makedirs(WORK_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────
#  HELPER : VALIDATE INPUT FILE
# ─────────────────────────────────────────────────────────

def validate_input(file_path):
    """
    Checks that:
      - The file actually exists
      - The extension is one we support
    Raises a clear error if either check fails.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: '{ext}'\n"
            f"Accepted formats: JPG, JPEG, PNG, PDF"
        )


# ─────────────────────────────────────────────────────────
#  HELPER : DETECT PDF TYPE
# ─────────────────────────────────────────────────────────

def detect_pdf_type(pdf_path):
    """
    Determines whether a PDF is vector-based or image-based.

    How it works:
        We read the first page and try to extract text.
        - If meaningful text is found → vector PDF
          (the text is stored as actual characters in the file)
        - If no text found → image-based PDF
          (pages are just embedded images with no selectable text)

    Returns:
        "vector" or "image_based"
    """

    reader = PdfReader(pdf_path)

    # Check first page for extractable text
    first_page = reader.pages[0]
    text       = first_page.extract_text() or ""

    # Clean up whitespace and check if real text exists
    clean_text = text.strip().replace("\n", "").replace(" ", "")

    if len(clean_text) > 20:
        return "vector"
    else:
        return "image_based"


# ─────────────────────────────────────────────────────────
#  HANDLER : IMAGE FILE (JPG / JPEG / PNG)
# ─────────────────────────────────────────────────────────

def handle_image(file_path):
    """
    What it does:
        - Reads the image using OpenCV
        - Saves a clean PNG copy to the working directory
        - Original file is never modified

    Why convert JPG to PNG:
        PNG is lossless — every subsequent stage that reads,
        copies, or processes the file preserves all pixel data.
        JPG would lose a tiny amount of quality on each save.

    Returns:
        path to the normalized PNG in WORK_DIR
    """

    image = cv2.imread(file_path)
    if image is None:
        raise ValueError(f"Could not read image file: {file_path}")

    # Build output path in working directory
    base_name  = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(WORK_DIR, f"{base_name}_normalized.png")

    cv2.imwrite(output_path, image)
    return output_path


# ─────────────────────────────────────────────────────────
#  HANDLER : IMAGE-BASED PDF
# ─────────────────────────────────────────────────────────

def handle_image_based_pdf(file_path):
    """
    What it does:
        Extracts the embedded image from the first page of the PDF.
        If a page has multiple images, we take the largest one
        (most likely the document scan itself, not a logo or stamp).

        Why first page only:
            Documents like Aadhaar, PAN, marksheets are single page.
            If someone uploads a multi-page PDF, we check only page 1.
            This keeps the pipeline simple and predictable.

    Returns:
        path to the extracted PNG in WORK_DIR
    """

    reader    = PdfReader(file_path)
    first_page = reader.pages[0]

    # Collect all images from first page
    images_found = []
    try:
        for image_obj in first_page.images:
            img_data = image_obj.data
            # Decode image bytes into a numpy array for OpenCV
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img       = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is not None:
                area = img.shape[0] * img.shape[1]
                images_found.append((area, img))
    except Exception as e:
        raise ValueError(f"Could not extract images from PDF: {e}")

    if not images_found:
        raise ValueError(
            "No images found in PDF first page. "
            "Make sure this is a scanned/image-based PDF."
        )

    # Pick the largest image — most likely the document itself
    images_found.sort(key=lambda x: x[0], reverse=True)
    best_image = images_found[0][1]

    # Save as PNG to working directory
    base_name   = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(WORK_DIR, f"{base_name}_extracted.png")
    cv2.imwrite(output_path, best_image)

    return output_path


# ─────────────────────────────────────────────────────────
#  HANDLER : VECTOR PDF
# ─────────────────────────────────────────────────────────

def handle_vector_pdf(file_path):
    """
    What it does:
        Makes a copy of the vector PDF into the working directory.
        The original is untouched.
        Stage 8 (PDF Forensics) will work on this copy.

    Why not convert to PNG:
        Vector PDFs have their value in their structure — fonts,
        metadata, object streams, incremental updates. Converting
        to PNG would destroy all of that and make Stage 8 useless.

    Returns:
        path to the PDF copy in WORK_DIR
    """

    base_name   = os.path.splitext(os.path.basename(file_path))[0]
    output_path = os.path.join(WORK_DIR, f"{base_name}_copy.pdf")
    shutil.copy2(file_path, output_path)

    return output_path


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_input_normalization(file_path):
    """
    Call this from your pipeline with the path to the user's file.

    Args:
        file_path : path to the input file (JPG, JPEG, PNG, or PDF)

    Returns:
        {
            "input_path"    : original file path (never modified)
            "output_path"   : normalized file in WORK_DIR
            "file_type"     : "image" | "image_based_pdf" | "vector_pdf"
            "next_stage"    : 2 (image pipeline) or 8 (PDF forensics)
            "status"        : "ok" or "error"
            "message"       : description of what happened
        }
    """

    setup_work_dir()

    print(f"\n[Stage 1] Input Normalization")
    print(f"  Input : {file_path}")
    print("-" * 50)

    # Validate first
    try:
        validate_input(file_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"  [ERROR] {e}")
        return {
            "input_path" : file_path,
            "output_path": None,
            "file_type"  : None,
            "next_stage" : None,
            "status"     : "error",
            "message"    : str(e)
        }

    ext = os.path.splitext(file_path)[1].lower()

    # ── CASE 1: Image file ──────────────────────────────
    if ext in [".jpg", ".jpeg", ".png"]:
        output_path = handle_image(file_path)
        file_type   = "image"
        next_stage  = 2
        message     = "Image converted to PNG — routing to Stage 2"

    # ── CASE 2: PDF file ────────────────────────────────
    elif ext == ".pdf":
        pdf_type = detect_pdf_type(file_path)

        if pdf_type == "image_based":
            output_path = handle_image_based_pdf(file_path)
            file_type   = "image_based_pdf"
            next_stage  = 2
            message     = "Image extracted from PDF — routing to Stage 2"
        else:
            output_path = handle_vector_pdf(file_path)
            file_type   = "vector_pdf"
            next_stage  = 8
            message     = "Vector PDF copied — routing to Stage 8"

    print(f"  File type  : {file_type}")
    print(f"  Output     : {output_path}")
    print(f"  Next stage : Stage {next_stage}")
    print(f"  {message}")
    print("-" * 50)

    return {
        "input_path" : file_path,
        "output_path": output_path,
        "file_type"  : file_type,
        "next_stage" : next_stage,
        "status"     : "ok",
        "message"    : message
    }


# ─────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    path   = sys.argv[1] if len(sys.argv) > 1 else "test_document.jpg"
    result = run_input_normalization(path)

    if result["status"] == "ok":
        print(f"\n  → Output file  : {result['output_path']}")
        print(f"  → File type    : {result['file_type']}")
        print(f"  → Next stage   : Stage {result['next_stage']}")
    else:
        print(f"\n  → Error : {result['message']}")