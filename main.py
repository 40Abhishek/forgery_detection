"""
Document Tamper Detection System
main.py — runs the full pipeline stage by stage
Output : result.json in local datastore folder (for website)

✅ FIXED: Handles both folder structures (main.py at root or inside stage0_web)
"""

import os
import json
import gc
import sys

# ✅ FIX: Add parent directory to Python path
# This allows imports to work regardless of where main.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # Go up one level
root_dir = os.path.dirname(parent_dir)      # Go up two levels

# Add all potential paths
for path in [current_dir, parent_dir, root_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f" Added to sys.path: {path}", flush=True)

print(f"Current directory: {current_dir}", flush=True)
print(f"Parent directory: {parent_dir}", flush=True)
print(f"Root directory: {root_dir}", flush=True)
print(f"sys.path: {sys.path}", flush=True)

print("\n[IMPORT] Loading modules...", flush=True)

try:
    print("  → Importing stage1_Normalization.stage1...", flush=True)
    from stage1_Normalization.stage1 import run_input_normalization
    print("     Success", flush=True)
except ImportError as e:
    print(f"     FAILED: {e}", flush=True)
    print(f"     Available in {current_dir}: {os.listdir(current_dir)}", flush=True)
    if os.path.exists(parent_dir):
        print(f"     Available in {parent_dir}: {os.listdir(parent_dir)}", flush=True)
    sys.exit(1)

try:
    print("  → Importing stage2_Image_forensics.stage2...", flush=True)
    from stage2_Image_forensics.stage2 import run_image_forensics
    print("      Success", flush=True)
except ImportError as e:
    print(f"      WARNING: {e}", flush=True)

try:
    print("  → Importing stage3_CNN.stage3_inference...", flush=True)
    from stage3_CNN.stage3_inference import run_cnn_detection
    print("      Success", flush=True)
except ImportError as e:
    print(f"       WARNING: {e}", flush=True)

try:
    print("  → Importing stage4_PDF_forensics.stage4...", flush=True)
    from stage4_PDF_forensics.stage4 import run_pdf_forensics
    print("      Success", flush=True)
except ImportError as e:
    print(f"       WARNING: {e}", flush=True)

try:
    print("  → Importing stage5_OCR.stage5...", flush=True)
    from stage5_OCR.stage5 import run_ocr_extraction
    print("     Success", flush=True)
except ImportError as e:
    print(f"       WARNING: {e}", flush=True)
    sys.exit(1)

try:
    print("  → Importing stage6_Risk_scoring.stage6...", flush=True)
    from stage6_Risk_scoring.stage6 import run_risk_scoring
    print("      Success", flush=True)
except ImportError as e:
    print(f"       WARNING: {e}", flush=True)

print("\n[IMPORTS] Modules loaded successfully!", flush=True)


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
        print(f" [{stage_name}] Memory cleanup done", flush=True)


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

    print("\n-->>DOCUMENT TAMPER DETECTION - FINAL REPORT", flush=True)
    print(f"  File      : {os.path.basename(file_info['input_path'])}", flush=True)
    print(f"  Type      : {file_info['file_type']}", flush=True)
    print(f"  Pipeline  : {risk_result['pipeline_type'].upper()}", flush=True)
    print(f"\n VERDICT     : {verdict}{reset}", flush=True)
    print(f"  RISK SCORE  : {score} / 100", flush=True)
    print(f"  RISK LEVEL  : {risk_result['risk_level']}", flush=True)

    print("\nANOMALIES FOUND:", flush=True)
    anomalies_found = False

    if "stage2" in all_results:
        s2 = all_results["stage2"]
        for key in ["ela", "noise", "copy_move"]:
            if s2[key].get("suspicious"):
                print(f"    [Image Forensics] {s2[key]['detail']}", flush=True)
                anomalies_found = True

    if "stage3" in all_results and all_results["stage3"].get("suspicious"):
        print(f"    [CNN Detection]   {all_results['stage3']['detail']}", flush=True)
        anomalies_found = True

    if "stage5" in all_results:
        s5 = all_results["stage5"]
        if s5["spelling"]["suspicious"]:
            print(f"    [OCR Spelling]    {s5['spelling']['detail']}", flush=True)
            anomalies_found = True

    if not anomalies_found:
        print("    No anomalies found.", flush=True)


# ── Pipeline ───────────────────────────────────────────

def run_pipeline(input_path, json_output_path="/tmp/result.json"):
    """
    Runs the full pipeline and saves result as JSON.

    Args:
        input_path      : path to the document
        json_output_path: where to save result.json for the website
    """

    all_results = {}

    print("\n-->> DOCUMENT TAMPER DETECTION SYSTEM", flush=True)
    print(f"Input: {input_path}", flush=True)

    stage1 = run_input_normalization(input_path)
    cleanup_memory("Stage 1")
    
    if stage1["status"] == "error":
        print(f"\n[ERROR] Stage 1 failed: {stage1['message']}", flush=True)
        return None

    file_info   = stage1
    output_path = stage1["output_path"]
    next_stage  = stage1["next_stage"]

    if next_stage == 2:
        print("\n[Stage 2] Running image forensics...", flush=True)
        stage2 = run_image_forensics(output_path)
        all_results["stage2"] = stage2
        cleanup_memory("Stage 2")

        print("\n[Stage 3] Loading CNN model...", flush=True)
        stage3 = run_cnn_detection(output_path)
        all_results["stage3"] = stage3
        cleanup_memory("Stage 3")

        print("\n[Stage 5] Extracting text via OCR...", flush=True)
        stage5 = run_ocr_extraction(output_path)
        all_results["stage5"] = stage5
        cleanup_memory("Stage 5")

        print("\n[Stage 6] Calculating risk score...", flush=True)
        risk_result = run_risk_scoring("image", {
            "forensics_score": stage2["forensics_score"],
            "cnn_score"      : stage3["cnn_score"],
            "ocr_score"      : stage5["ocr_score"]
        })
        cleanup_memory("Stage 6")

    elif next_stage == 4:
        print("\n[Stage 4] Running PDF forensics...", flush=True)
        stage4 = run_pdf_forensics(output_path)
        all_results["stage4"] = stage4
        cleanup_memory("Stage 4")

        print("\n[Stage 5] Extracting text via OCR...", flush=True)
        stage5 = run_ocr_extraction(output_path)
        all_results["stage5"] = stage5
        cleanup_memory("Stage 5")

        print("\n[Stage 6] Calculating risk score...", flush=True)
        risk_result = run_risk_scoring("pdf", {
            "pdf_score": stage4["pdf_score"],
            "ocr_score": stage5["ocr_score"]
        })
        cleanup_memory("Stage 6")

    print_final_report(file_info, all_results, risk_result)

    json_output = build_json_output(file_info, all_results, risk_result)
    with open(json_output_path, "w") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON saved : {json_output_path}", flush=True)

    return json_output


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python main.py <file_path> [output_path]", flush=True)
        sys.exit(1)

    input_path = sys.argv[1]
    json_output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/result.json"

    print(f"✅ File found: {input_path}\n", flush=True)

    if not os.path.exists(input_path):
        print(f"[ERROR] File not found: {input_path}", flush=True)
        sys.exit(1)

    result = run_pipeline(input_path, json_output_path)

    if result:
        print(f"\n✅ Pipeline complete.", flush=True)
        print(f"   Verdict    : {result['verdict']}", flush=True)
        print(f"   Risk Score : {result['risk_score']} / 100", flush=True)
    else:
        print(f"\n❌ Pipeline failed.", flush=True)
        sys.exit(1)