"""
Document Tamper Detection System
main.py — runs the full pipeline stage by stage
Output : result.json in local datastore folder (for website)
OPTIMIZED: Memory cleanup between stages + garbage collection
NO DEPENDENCIES: Uses only gc and torch (no psutil needed)
"""

import os
import json
import gc
import sys

from stage1_Normalization.stage1    import run_input_normalization
from stage2_Image_forensics.stage2  import run_image_forensics
from stage3_CNN.stage3_inference    import run_cnn_detection
from stage4_PDF_forensics.stage4    import run_pdf_forensics
from stage5_OCR.stage5              import run_ocr_extraction
from stage6_Risk_scoring.stage6     import run_risk_scoring


# ── Memory Management ───────────────────────────────────

def cleanup_memory(stage_name=""):
    """Force garbage collection and cleanup"""
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except:
        pass
    
    if stage_name:
        print(f"✅ [{stage_name}] Memory cleanup done")


# ── JSON Output ───────────────────────────────────────────

def build_json_output(file_info, all_results, risk_result):
    """
    Builds a clean JSON-serializable dict for the website.
    Excludes numpy arrays and image maps — only scores, flags, and text.
    """

    output = {
        "file": {
            "name"     : os.path.basename(file_info["input_path"]),
            "type"     : file_info["file_type"],
            "pipeline" : risk_result["pipeline_type"]
        },
        "verdict"    : risk_result["verdict"],
        "risk_score" : risk_result["final_score"],
        "risk_level" : risk_result["risk_level"],
        "breakdown"  : risk_result["breakdown"],
        "anomalies"  : [],
        "ocr_text"   : "",
        "stages"     : {}
    }

    # Stage 2 — Image Forensics
    if "stage2" in all_results:
        s2 = all_results["stage2"]
        output["stages"]["image_forensics"] = {
            "forensics_score": s2["forensics_score"],
            "overall_suspicious": s2["overall_suspicious"],
            "ela": {
                "score"     : s2["ela"]["ela_score"],
                "suspicious": s2["ela"]["suspicious"],
                "detail"    : s2["ela"]["detail"]
            },
            "noise": {
                "score"     : s2["noise"]["noise_score"],
                "suspicious": s2["noise"]["suspicious"],
                "detail"    : s2["noise"]["detail"]
            },
            "copy_move": {
                "count"     : s2["copy_move"]["clone_count"],
                "suspicious": s2["copy_move"]["suspicious"],
                "detail"    : s2["copy_move"]["detail"]
            },
            "heatmap_path"   : s2.get("heatmap_path", ""),
            "annotated_path" : s2.get("annotated_path", "")
        }
        for key in ["ela", "noise", "copy_move"]:
            if s2[key].get("suspicious"):
                output["anomalies"].append({
                    "stage" : "Image Forensics",
                    "check" : key.upper(),
                    "detail": s2[key]["detail"]
                })

    # Stage 3 — CNN
    if "stage3" in all_results:
        s3 = all_results["stage3"]
        output["stages"]["cnn"] = {
            "cnn_score" : s3["cnn_score"],
            "raw_score" : s3["raw_score"],
            "suspicious": s3["suspicious"],
            "detail"    : s3["detail"]
        }
        if s3.get("suspicious"):
            output["anomalies"].append({
                "stage" : "CNN Detection",
                "check" : "CNN",
                "detail": s3["detail"]
            })

    # Stage 4 — PDF Forensics
    if "stage4" in all_results:
        s4 = all_results["stage4"]
        output["stages"]["pdf_forensics"] = {
            "pdf_score"         : s4["pdf_score"],
            "overall_suspicious": s4["overall_suspicious"],
            "metadata_flags"    : s4["metadata"]["flags"],
            "incremental_flags" : s4["incremental"]["flags"],
            "font_flags"        : s4["fonts"]["flags"],
            "producer_flags"    : s4["producers"]["flags"]
        }
        for key in ["metadata", "incremental", "fonts", "producers"]:
            for flag in s4[key].get("flags", []):
                output["anomalies"].append({
                    "stage" : "PDF Forensics",
                    "check" : key.upper(),
                    "detail": flag
                })

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
        output["ocr_text"] = s5["ocr"]["full_text"][:1000]   # first 1000 chars for website

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
    reset   = "\033[0m"

    print("\n-->>DOCUMENT TAMPER DETECTION - FINAL REPORT")
    print(f"  File      : {os.path.basename(file_info['input_path'])}")
    print(f"  Type      : {file_info['file_type']}")
    print(f"  Pipeline  : {risk_result['pipeline_type'].upper()}")
    print()
    print(f" VERDICT     : {verdict}{reset}")
    print(f"  RISK SCORE  : {score} / 100")
    print(f"  RISK LEVEL  : {risk_result['risk_level']}")
    print()

    print("SCORE:")
    for key, value in risk_result["breakdown"].items():
        if "_score" in key:
            label        = key.replace("_score", "").replace("_", " ").upper()
            weight_key   = key.replace("_score", "_weight")
            weighted_key = key.replace("_score", "_weighted")
            print(f"{label} {value} x {risk_result['breakdown'].get(weight_key, '')} = {risk_result['breakdown'].get(weighted_key, '')}")

    print("\nANOMALIES FOUND:")
    anomalies_found = False

    if "stage2" in all_results:
        s2 = all_results["stage2"]
        for key in ["ela", "noise", "copy_move"]:
            if s2[key].get("suspicious"):
                print(f"    [Image Forensics] {s2[key]['detail']}")
                anomalies_found = True

    if "stage3" in all_results and all_results["stage3"].get("suspicious"):
        print(f"    [CNN Detection]   {all_results['stage3']['detail']}")
        anomalies_found = True

    if "stage4" in all_results:
        s4 = all_results["stage4"]
        for key in ["metadata", "incremental", "fonts", "producers"]:
            for flag in s4[key].get("flags", []):
                print(f"    [PDF Forensics]   {flag}")
                anomalies_found = True

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
        print("    No anomalies found.")

    if "stage5" in all_results:
        text = all_results["stage5"]["ocr"]["full_text"]
        if text:
            print(f"\n  EXTRACTED TEXT (first 300 chars):")
            print(f"    {text[:300]}...")


# ── Pipeline ───────────────────────────────────────────

def run_pipeline(input_path, json_output_path="/tmp/result.json"):
    """
    Runs the full pipeline and saves result as JSON.
    
    OPTIMIZED: Cleans up memory after each stage
    NO EXTRA DEPS: No psutil needed

    Args:
        input_path      : path to the document
        json_output_path: where to save result.json for the website
    """

    all_results = {}

    print("-->> DOCUMENT TAMPER DETECTION SYSTEM")
    print(f"Input: {input_path}")

    # ── STAGE 1 ────────────────────────────────────────
    stage1 = run_input_normalization(input_path)
    cleanup_memory("Stage 1")
    
    if stage1["status"] == "error":
        print(f"\n[ERROR] Stage 1 failed: {stage1['message']}")
        return None

    file_info   = stage1
    output_path = stage1["output_path"]
    next_stage  = stage1["next_stage"]

    if next_stage == 2:
        # ── STAGE 2: IMAGE FORENSICS ──────────────────────
        print("\n[Stage 2] Running image forensics...")
        stage2 = run_image_forensics(output_path)
        all_results["stage2"] = stage2
        cleanup_memory("Stage 2")

        # ── STAGE 3: CNN DETECTION ────────────────────────
        print("\n[Stage 3] Loading CNN model...")
        stage3 = run_cnn_detection(output_path)
        all_results["stage3"] = stage3
        cleanup_memory("Stage 3")

        # ── STAGE 5: OCR EXTRACTION ───────────────────────
        print("\n[Stage 5] Extracting text via OCR...")
        stage5 = run_ocr_extraction(output_path)
        all_results["stage5"] = stage5
        cleanup_memory("Stage 5")

        # ── STAGE 6: RISK SCORING ─────────────────────────
        print("\n[Stage 6] Calculating risk score...")
        risk_result = run_risk_scoring("image", {
            "forensics_score": stage2["forensics_score"],
            "cnn_score"      : stage3["cnn_score"],
            "ocr_score"      : stage5["ocr_score"]
        })
        cleanup_memory("Stage 6")

    elif next_stage == 4:
        # ── STAGE 4: PDF FORENSICS ───────────────────────
        print("\n[Stage 4] Running PDF forensics...")
        stage4 = run_pdf_forensics(output_path)
        all_results["stage4"] = stage4
        cleanup_memory("Stage 4")

        # ── STAGE 5: OCR EXTRACTION ───────────────────────
        print("\n[Stage 5] Extracting text via OCR...")
        stage5 = run_ocr_extraction(output_path)
        all_results["stage5"] = stage5
        cleanup_memory("Stage 5")

        # ── STAGE 6: RISK SCORING ─────────────────────────
        print("\n[Stage 6] Calculating risk score...")
        risk_result = run_risk_scoring("pdf", {
            "pdf_score": stage4["pdf_score"],
            "ocr_score": stage5["ocr_score"]
        })
        cleanup_memory("Stage 6")

    print_final_report(file_info, all_results, risk_result)

    json_output = build_json_output(file_info, all_results, risk_result)
    with open(json_output_path, "w") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    
    print(f"\n JSON saved : {json_output_path}")

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
        print(f"\n Pipeline complete.")
        print(f"   Verdict    : {result['verdict']}")
        print(f"   Risk Score : {result['risk_score']} / 100")
    else:
        print(f"\nPipeline failed.")
        sys.exit(1)