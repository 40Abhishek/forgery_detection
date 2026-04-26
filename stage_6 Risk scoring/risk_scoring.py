"""
  Stage 9 : Risk Scoring Engine
"""


THRESHOLD_GENUINE    = 30   # 0  to 30  = GENUINE
THRESHOLD_SUSPICIOUS = 60   # 31 to 60  = SUSPICIOUS
                            # 61 to 100 = FORGED


#  Weights chosen based on signal strength:
#   CNN stage 3 → 40 pts  (learned detector, strongest signal)
#      Stage 2  → 35 pts  (pixel-level forensics, very reliable)
#      Stage 5  → 15 pts  (text validation, supporting signal)

IMAGE_WEIGHTS = { "cnn_score": 0.40, "forensics_score" : 0.35, "ocr_score": 0.15}

#  Weights:
#      Stage 4  → 65 pts  (structural PDF analysis, primary signal)
#      Stage 5  → 35 pts  (text validation, strong for PDFs since
#                           text is directly extracted, very accurate)

PDF_WEIGHTS = {"pdf_score" : 0.65, "ocr_score" : 0.35}

def score_image_pipeline(forensics_score, cnn_score, ocr_score):
    weighted_forensics = forensics_score * IMAGE_WEIGHTS["forensics_score"]
    weighted_cnn = cnn_score * IMAGE_WEIGHTS["cnn_score"]
    weighted_ocr = ocr_score * IMAGE_WEIGHTS["ocr_score"]

    final_score = round(weighted_forensics + weighted_cnn + weighted_ocr, 2)

    breakdown = {
        "forensics_score"    : forensics_score,
        "forensics_weighted" : round(weighted_forensics, 2),
        "forensics_weight"   : "35%",
        "cnn_score"          : cnn_score,
        "cnn_weighted"       : round(weighted_cnn, 2),
        "cnn_weight"         : "40%",
        "ocr_score"          : ocr_score,
        "ocr_weighted"       : round(weighted_ocr, 2),
        "ocr_weight"         : "25%",
    }

    return final_score, breakdown


def score_pdf_pipeline(pdf_score, ocr_score):
    weighted_pdf = pdf_score  * PDF_WEIGHTS["pdf_score"]
    weighted_ocr = ocr_score  * PDF_WEIGHTS["ocr_score"]

    final_score = round(weighted_pdf + weighted_ocr, 2)

    breakdown = {
        "pdf_score"     : pdf_score,
        "pdf_weighted"  : round(weighted_pdf, 2),
        "pdf_weight"    : "65%",
        "ocr_score"     : ocr_score,
        "ocr_weighted"  : round(weighted_ocr, 2),
        "ocr_weight"    : "35%",
    }

    return final_score, breakdown



def run_risk_scoring(pipeline_type, stage_results):
    print(f"  Pipeline : {pipeline_type.upper()}")

    if pipeline_type == "image":
        final_score, breakdown = score_image_pipeline(
            forensics_score = stage_results["forensics_score"],
            cnn_score       = stage_results["cnn_score"],
            ocr_score       = stage_results["ocr_score"]
        )
    elif pipeline_type == "pdf":
        final_score, breakdown = score_pdf_pipeline(
            pdf_score = stage_results["pdf_score"],
            ocr_score = stage_results["ocr_score"]
        )
    else:
        print(f"Give valid document type: \"image\", \"pdf\" ")
        return None

    #get verdict
    if final_score <= THRESHOLD_GENUINE:
        verdict = "GENUINE"
    elif final_score <= THRESHOLD_SUSPICIOUS:
        verdict = "SUSPICIOUS"
    else:
        verdict = "FORGED"
    
    #get risk level
    if final_score <= THRESHOLD_GENUINE:
        risk_level = "LOW"
    elif final_score <= THRESHOLD_SUSPICIOUS:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
        
    #print results
    print(f"  Final Score : {final_score} / 100")
    print(f"  Risk Level  : {risk_level}")
    print(f"  Verdict     : {verdict}")

    return {
        "pipeline_type": pipeline_type,
        "final_score"  : final_score,
        "verdict"      : verdict,
        "risk_level"   : risk_level,
        "breakdown"    : breakdown
    }


if __name__ == "__main__":
    print("\n>>RISK SCORING")

    # image pipeline
    print("---- Image risk scoring ----")
    result = run_risk_scoring("image", {
        "forensics_score": 55.0,
        "cnn_score"      : 72.0,
        "ocr_score"      : 30.0
    })
    
    # PDF pipeline
    print("\n--- PDF risk scoring --")
    result = run_risk_scoring("pdf", {
        "pdf_score": 73.15,
        "ocr_score": 10.0
    })
