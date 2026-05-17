"""
Document Tamper Detection System - LIGHTWEIGHT VERSION
main.py — runs minimal pipeline to fit in 512MB (Render free tier)
Output : result.json in local datastore folder (for website)

✅ This version skips heavy stages (Stage 2, 3, 4) and only runs:
   - Stage 1: Normalization (light)
   - Stage 5: OCR (medium)
   - Stage 6: Basic risk scoring
"""

import os
import json
import gc
import sys
import psutil

from stage1_Normalization.stage1    import run_input_normalization
from stage5_OCR.stage5              import run_ocr_extraction
from stage6_Risk_scoring.stage6     import run_risk_scoring


# ── Memory Management ───────────────────────────────────

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def cleanup_memory(stage_name=""):
    """Force garbage collection and cleanup"""
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except:
        pass
    
    mem = get_memory_usage()
    if stage_name:
        print(f"✅ [{stage_name}] Memory after cleanup: {mem:.1f} MB")
    return mem


# ── JSON Output ───────────────────────────────────────────

def build_json_output(file_info, all_results, risk_result):
    """
    Builds a clean JSON-serializable dict for the website.
    Lightweight version - only OCR and basic risk scoring.
    """

    output = {
        "file": {
            "name"     : os.path.basename(file_info["input_path"]),
            "type"     : file_info["file_type"],
            "pipeline" : "lightweight_ocr"  # Lightweight mode
        },
        "verdict"    : risk_result["verdict"],
        "risk_score" : risk_result["final_score"],
        "risk_level" : risk_result["risk_level"],
        "breakdown"  : risk_result["breakdown"],
        "anomalies"  : [],
        "ocr_text"   : "",
        "stages"     : {},
        "note"       : "Lightweight mode: Only OCR analysis (no forensics/CNN)"
    }

    # Stage 5 — OCR
    if "stage5" in all_results:
        s5 = all_results["stage5"]
        output["stages"]["ocr"] = {
            "ocr_score"         : s5["ocr_score"],
            "overall_suspicious": s5["overall_suspicious"],
            "word_count"        : s5["ocr"]["word_count"],
            "source"            : s5["ocr"].get("source", "easyocr"),
            "spelling": {
                "misspelled": s5["spelling"]["misspelled"][:10],
                "score"     : s5["spelling"]["spell_score"],
                "suspicious": s5["spelling"]["suspicious"],
                "detail"    : s5["spelling"]["detail"]
            },
            "dates": {
                "found"     : s5["dates"]["dates_found"],
                "invalid"   : s5["dates"]["invalid_dates"],
                "suspicious": s5["dates"]["suspicious"],
                "detail"    : s5["dates"]["detail"]
            },
            "numeric": {
                "fields"    : s5["numeric"]["fields"],
                "flags"     : s5["numeric"]["flags"],
                "suspicious": s5["numeric"]["suspicious"],
                "detail"    : s5["numeric"]["detail"]
            }
        }
        output["ocr_text"] = s5["ocr"]["full_text"][:1000]

        if s5["spelling"]["suspicious"]:
            output["anomalies"].append({
                "stage" : "OCR",
                "check" : "SPELLING",
                "detail": s5["spelling"]["detail"]
            })
        if s5["dates"]["suspicious"]:
            output["anomalies"].append({
                "stage" : "OCR",
                "check" : "DATES",
                "detail": s5["dates"]["detail"]
            })
        if s5["numeric"]["suspicious"]:
            output["anomalies"].append({
                "stage" : "OCR",
                "check" : "NUMERIC",
                "detail": s5["numeric"]["detail"]
            })

    return output


# ── Terminal Report ───────────────────────────────────────

def print_final_report(file_info, all_results, risk_result):
    verdict = risk_result["verdict"]
    score   = risk_result["final_score"]

    print("\n-->> DOCUMENT TAMPER DETECTION - LIGHTWEIGHT REPORT")
    print(f"  File      : {os.path.basename(file_info['input_path'])}")
    print(f"  Type      : {file_info['file_type']}")
    print(f"  Mode      : LIGHTWEIGHT (OCR only)")
    print()
    print(f"  VERDICT     : {verdict}")
    print(f"  RISK SCORE  : {score} / 100")
    print(f"  RISK LEVEL  : {risk_result['risk_level']}")
    print()

    print("ANOMALIES FOUND:")
    anomalies_found = False

    if "stage5" in all_results:
        s5 = all_results["stage5"]
        if s5["spelling"]["suspicious"]:
            print(f"    [OCR Spelling]    {s5['spelling']['detail']}")
            anomalies_found = True
        if s5["dates"]["suspicious"]:
            print(f"    [OCR Dates]       {s5['dates']['detail']}")
            anomalies_found = True
        if s5["numeric"]["suspicious"]:
            print(f"    [OCR Numeric]     {s5['numeric']['detail']}")
            anomalies_found = True

    if not anomalies_found:
        print("    No anomalies found in OCR analysis.")

    if "stage5" in all_results:
        text = all_results["stage5"]["ocr"]["full_text"]
        if text:
            print(f"\n  EXTRACTED TEXT (first 300 chars):")
            print(f"    {text[:300]}...")


# ── Pipeline ───────────────────────────────────────────

def run_pipeline(input_path, json_output_path="/tmp/result.json"):
    """
    LIGHTWEIGHT PIPELINE: Only runs Stage 1 (Normalization) and Stage 5 (OCR)
    Designed to fit in Render free tier (512MB)
    
    ⚠️  Heavy stages skipped:
        - Stage 2: Image Forensics (skip)
        - Stage 3: CNN Detection (skip)
        - Stage 4: PDF Forensics (skip)
    """

    all_results = {}

    print("-->> DOCUMENT TAMPER DETECTION SYSTEM (LIGHTWEIGHT MODE)")
    print(f"Input: {input_path}")
    print(f"Starting memory: {get_memory_usage():.1f} MB")

    # ── STAGE 1 ────────────────────────────────────────
    stage1 = run_input_normalization(input_path)
    cleanup_memory("Stage 1")
    
    if stage1["status"] == "error":
        print(f"\n[ERROR] Stage 1 failed: {stage1['message']}")
        return None

    file_info   = stage1
    output_path = stage1["output_path"]

    # ── STAGE 5: OCR EXTRACTION (Only heavy stage) ──────
    print("\n[Stage 5] Extracting text via OCR...")
    stage5 = run_ocr_extraction(output_path)
    all_results["stage5"] = stage5
    cleanup_memory("Stage 5")

    # ── STAGE 6: BASIC RISK SCORING ───────────────────
    print("\n[Stage 6] Calculating risk score (OCR only)...")
    
    # Lightweight risk scoring - only based on OCR
    risk_result = run_risk_scoring("lightweight_ocr", {
        "ocr_score": stage5["ocr_score"]
    })
    cleanup_memory("Stage 6")

    print_final_report(file_info, all_results, risk_result)

    json_output = build_json_output(file_info, all_results, risk_result)
    with open(json_output_path, "w") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ JSON saved : {json_output_path}")
    print(f"Final memory: {get_memory_usage():.1f} MB")
    print(f"\n⚠️  NOTE: This is LIGHTWEIGHT mode.")
    print(f"   For full analysis (CNN, Forensics), upgrade to Render Starter plan.")

    return json_output


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python main.py <file_path> [output_path]")
        sys.exit(1)

    input_path = sys.argv[1]
    json_output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/result.json"

    print("file found:", input_path, "\n")

    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    result = run_pipeline(input_path, json_output_path)

    if result:
        print(f"\n✅ Pipeline complete.")
        print(f"   Verdict    : {result['verdict']}")
        print(f"   Risk Score : {result['risk_score']} / 100")
    else:
        print(f"\n❌ Pipeline failed.")
        sys.exit(1)