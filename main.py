"""
Document Tamper Detection System
main.py — runs the full pipeline stage by stage

Folder structure (change folder names below if needed):
    project/
        main.py
        stage1/    ← put stage1_normalization.py here
        stage2/    ← put stage2_image_forensics.py here
        stage3/    ← put stage3_inference.py here
        stage4/    ← put stage8_pdf_forensics.py here  (PDF forensics)
        stage5/    ← put stage4_ocr.py here            (OCR)
        stage6/    ← put stage9_risk_scoring.py here   (Risk scoring)

Usage:
    python main.py path/to/document.pdf
    python main.py path/to/document.png
"""

import sys
import os


# ── Folder names — CHANGE THESE if you rename your stage folders ──────────────

STAGE1_FOLDER = "stage1"   # Input Normalization
STAGE2_FOLDER = "stage2"   # Image Forensics
STAGE3_FOLDER = "stage3"   # CNN Tamper Detection
STAGE4_FOLDER = "stage4"   # PDF Forensics
STAGE5_FOLDER = "stage5"   # OCR Extraction
STAGE6_FOLDER = "stage6"   # Risk Scoring Engine


# ── Add all stage folders to Python path so imports work ──────────────────────

for folder in [stage1_Normalization, stage2_image_forensics, stage3_CNN, 
                stage4_PDF_forensics,stage5_OCR, stage6_Risk_scoring    ]:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), folder))

# ── Import all stages ──────────────────────────────────────────────────────────

from stage1_Normalization  import run_input_normalization
from stage2_image_forensics import run_image_forensics
from stage3_CNN       import run_cnn_detection
from stage8_pdf_forensics   import run_pdf_forensics   # file is still named stage8
from stage4_ocr             import run_ocr_extraction
from stage9_risk_scoring    import run_risk_scoring


# ── Helper : print final report to terminal ───────────────────────────────────

def print_final_report(file_info, all_results, risk_result):
    """Prints a clean summary of all findings to terminal."""

    verdict    = risk_result["verdict"]
    score      = risk_result["final_score"]
    pipeline   = risk_result["pipeline_type"]

    # Verdict colors in terminal
    colors = {"GENUINE": "\033[92m", "SUSPICIOUS": "\033[93m", "FORGED": "\033[91m"}
    reset  = "\033[0m"
    color  = colors.get(verdict, "")

    print("\n" + "=" * 60)
    print("  DOCUMENT TAMPER DETECTION — FINAL REPORT")
    print("=" * 60)
    print(f"  File      : {os.path.basename(file_info['input_path'])}")
    print(f"  Type      : {file_info['file_type']}")
    print(f"  Pipeline  : {pipeline.upper()}")
    print("-" * 60)
    print(f"  {color}VERDICT     : {verdict}{reset}")
    print(f"  RISK SCORE  : {score} / 100")
    print(f"  RISK LEVEL  : {risk_result['risk_level']}")
    print("-" * 60)

    # Score breakdown
    print("\n  SCORE BREAKDOWN:")
    for key, value in risk_result["breakdown"].items():
        if "_score" in key:
            label = key.replace("_score", "").replace("_", " ").upper()
            weight_key   = key.replace("_score", "_weight")
            weighted_key = key.replace("_score", "_weighted")
            print(f"    {label:20} {value:6} × {risk_result['breakdown'].get(weight_key, '')} = {risk_result['breakdown'].get(weighted_key, '')}")

    # Anomalies found per stage
    print("\n  ANOMALIES FOUND:")

    anomalies_found = False

    # Stage 2 — Image Forensics
    if "stage2" in all_results:
        s2 = all_results["stage2"]
        for key in ["ela", "noise", "copy_move"]:
            if key in s2 and s2[key].get("suspicious"):
                print(f"    [Image Forensics] {s2[key]['detail']}")
                anomalies_found = True

    # Stage 3 — CNN
    if "stage3" in all_results:
        s3 = all_results["stage3"]
        if s3.get("suspicious"):
            print(f"    [CNN Detection]   {s3['detail']}")
            anomalies_found = True

    # Stage 4 — PDF Forensics
    if "stage4" in all_results:
        s4 = all_results["stage4"]
        for key in ["metadata", "incremental", "fonts", "producers"]:
            if key in s4 and s4[key].get("suspicious"):
                for flag in s4[key].get("flags", []):
                    print(f"    [PDF Forensics]   {flag}")
                    anomalies_found = True

    # Stage 5 — OCR
    if "stage5" in all_results:
        s5 = all_results["stage5"]
        if s5.get("spelling", {}).get("suspicious"):
            print(f"    [OCR Spelling]    {s5['spelling']['detail']}")
            print(f"                      Words: {', '.join(s5['spelling'].get('misspelled', [])[:10])}")
            anomalies_found = True
        if s5.get("dates", {}).get("suspicious"):
            print(f"    [OCR Dates]       {s5['dates']['detail']}")
            print(f"                      Invalid: {', '.join(s5['dates'].get('invalid_dates', []))}")
            anomalies_found = True
        if s5.get("numeric", {}).get("suspicious"):
            print(f"    [OCR Numeric]     {s5['numeric']['detail']}")
            for flag in s5["numeric"].get("flags", []):
                print(f"                      {flag}")
            anomalies_found = True

    if not anomalies_found:
        print("    No anomalies found across all stages.")

    # OCR extracted text
    if "stage5" in all_results:
        text = all_results["stage5"].get("ocr", {}).get("full_text", "")
        if text:
            print(f"\n  EXTRACTED TEXT (first 300 chars):")
            print(f"    {text[:300]}...")

    print("\n" + "=" * 60)

    return risk_result


# ── Main Pipeline ──────────────────────────────────────────────────────────────

def run_pipeline(input_path):
    """
    Runs the full tamper detection pipeline on one document.

    Args:
        input_path : path to the document file (JPG, PNG, or PDF)

    Returns:
        dict with all stage results + final risk score + verdict
    """

    all_results = {}

    print("\n" + "=" * 60)
    print("  DOCUMENT TAMPER DETECTION SYSTEM")
    print(f"  Input: {input_path}")
    print("=" * 60)

    # ── STAGE 1 : Input Normalization ─────────────────────────────────────────
    stage1 = run_input_normalization(input_path)

    if stage1["status"] == "error":
        print(f"\n[ERROR] Stage 1 failed: {stage1['message']}")
        return None

    file_info   = stage1
    output_path = stage1["output_path"]
    next_stage  = stage1["next_stage"]

    # ── IMAGE PIPELINE (JPG / PNG / image-based PDF) ──────────────────────────
    if next_stage == 2:

        # STAGE 2 : Image Forensics
        stage2 = run_image_forensics(output_path)
        all_results["stage2"] = stage2

        # STAGE 3 : CNN Tamper Detection
        stage3 = run_cnn_detection(output_path)
        all_results["stage3"] = stage3

        # STAGE 5 : OCR Extraction
        stage5 = run_ocr_extraction(output_path)
        all_results["stage5"] = stage5

        # STAGE 6 : Risk Scoring
        risk_result = run_risk_scoring("image", {
            "forensics_score": stage2["forensics_score"],
            "cnn_score"      : stage3["cnn_score"],
            "ocr_score"      : stage5["ocr_score"]
        })

    # ── PDF PIPELINE (vector PDF) ─────────────────────────────────────────────
    elif next_stage == 8:

        # STAGE 4 : PDF Forensics
        stage4 = run_pdf_forensics(output_path)
        all_results["stage4"] = stage4

        # STAGE 5 : OCR Extraction
        stage5 = run_ocr_extraction(output_path)
        all_results["stage5"] = stage5

        # STAGE 6 : Risk Scoring
        risk_result = run_risk_scoring("pdf", {
            "pdf_score": stage4["pdf_score"],
            "ocr_score": stage5["ocr_score"]
        })

    # ── Print and return final report ─────────────────────────────────────────
    print_final_report(file_info, all_results, risk_result)

    # Return everything for Stage 0 (UI) to use
    return {
        "file_info"  : file_info,
        "all_results": all_results,
        "risk_result": risk_result,
        "verdict"    : risk_result["verdict"],
        "score"      : risk_result["final_score"],
        "risk_level" : risk_result["risk_level"]
    }


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python main.py path/to/document")
        print("Example: python main.py documents/aadhaar.png")
        sys.exit(1)

    input_path = sys.argv[1]
    result     = run_pipeline(input_path)

    if result:
        print(f"\nPipeline complete.")
        print(f"Verdict    : {result['verdict']}")
        print(f"Risk Score : {result['score']} / 100")
