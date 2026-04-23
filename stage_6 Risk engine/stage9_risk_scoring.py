"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 9 : Risk Scoring Engine
  Libraries: none (pure Python)
  Input   : scores from all previous stages
  Output  : final_score (0-100) + verdict
=============================================================
  Verdict thresholds:
      0  - 30  → GENUINE
      31 - 60  → SUSPICIOUS
      61 - 100 → FORGED

  Two scoring paths depending on document type:
      Image pipeline : Stage 2 + Stage 3 + Stage 4 scores
      PDF pipeline   : Stage 8 + Stage 4 scores
=============================================================
"""


# ─────────────────────────────────────────────────────────
#  VERDICT THRESHOLDS
# ─────────────────────────────────────────────────────────

THRESHOLD_GENUINE    = 30   # 0  to 30  = GENUINE
THRESHOLD_SUSPICIOUS = 60   # 31 to 60  = SUSPICIOUS
                             # 61 to 100 = FORGED


# ─────────────────────────────────────────────────────────
#  IMAGE PIPELINE SCORING
#  Used when input was: JPG / PNG / image-based PDF
#  Stages available: 2 (image forensics) + 3 (CNN) + 4 (OCR)
#
#  Weights chosen based on signal strength:
#      CNN      → 40 pts  (learned detector, strongest signal)
#      Stage 2  → 35 pts  (pixel-level forensics, very reliable)
#      Stage 4  → 25 pts  (text validation, supporting signal)
# ─────────────────────────────────────────────────────────

IMAGE_WEIGHTS = {
    "cnn_score"       : 0.40,
    "forensics_score" : 0.35,
    "ocr_score"       : 0.25
}


# ─────────────────────────────────────────────────────────
#  PDF PIPELINE SCORING
#  Used when input was: vector PDF
#  Stages available: 8 (PDF forensics) + 4 (OCR)
#  Note: No image forensics or CNN — PDF structure is the signal
#
#  Weights:
#      Stage 8  → 65 pts  (structural PDF analysis, primary signal)
#      Stage 4  → 35 pts  (text validation, strong for PDFs since
#                           text is directly extracted, very accurate)
# ─────────────────────────────────────────────────────────

PDF_WEIGHTS = {
    "pdf_score" : 0.65,
    "ocr_score" : 0.35
}


# ─────────────────────────────────────────────────────────
#  VERDICT LOGIC
# ─────────────────────────────────────────────────────────

def get_verdict(final_score):
    """
    Converts a numeric score into a human verdict.

    Thresholds are intentionally conservative:
        - We prefer to call a forged doc SUSPICIOUS rather than
          miss it entirely (false negative is worse than false positive
          in a forgery detection system)
        - GENUINE requires a low score across ALL detectors
    """

    if final_score <= THRESHOLD_GENUINE:
        return "GENUINE"
    elif final_score <= THRESHOLD_SUSPICIOUS:
        return "SUSPICIOUS"
    else:
        return "FORGED"


def get_risk_level(final_score):
    """Returns a color-coded risk level for the report."""
    if final_score <= THRESHOLD_GENUINE:
        return "LOW"
    elif final_score <= THRESHOLD_SUSPICIOUS:
        return "MEDIUM"
    else:
        return "HIGH"


# ─────────────────────────────────────────────────────────
#  SCORING : IMAGE PIPELINE
# ─────────────────────────────────────────────────────────

def score_image_pipeline(forensics_score, cnn_score, ocr_score):
    """
    Combines Stage 2 + Stage 3 + Stage 4 scores.

    Each score is already 0-100 from its respective stage.
    We apply weights and sum them up.

    Args:
        forensics_score : from stage2_image_forensics.py
        cnn_score       : from stage3_inference.py
        ocr_score       : from stage4_ocr.py

    Returns:
        final_score, verdict, breakdown dict
    """

    weighted_forensics = forensics_score * IMAGE_WEIGHTS["forensics_score"]
    weighted_cnn       = cnn_score       * IMAGE_WEIGHTS["cnn_score"]
    weighted_ocr       = ocr_score       * IMAGE_WEIGHTS["ocr_score"]

    final_score = round(
        weighted_forensics + weighted_cnn + weighted_ocr, 2
    )

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


# ─────────────────────────────────────────────────────────
#  SCORING : PDF PIPELINE
# ─────────────────────────────────────────────────────────

def score_pdf_pipeline(pdf_score, ocr_score):
    """
    Combines Stage 8 + Stage 4 scores for vector PDFs.

    Args:
        pdf_score  : from stage8_pdf_forensics.py
        ocr_score  : from stage4_ocr.py

    Returns:
        final_score, verdict, breakdown dict
    """

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


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_risk_scoring(pipeline_type, stage_results):
    """
    Call this from main.py after all relevant stages complete.

    Args:
        pipeline_type : "image" or "pdf"
        stage_results : dict containing stage outputs, e.g.
            For image pipeline:
                {
                    "forensics_score": 42.5,   # from Stage 2
                    "cnn_score"      : 67.0,   # from Stage 3
                    "ocr_score"      : 15.0    # from Stage 4
                }
            For PDF pipeline:
                {
                    "pdf_score" : 55.0,        # from Stage 8
                    "ocr_score" : 20.0         # from Stage 4
                }

    Returns:
        {
            "pipeline_type" : "image" or "pdf"
            "final_score"   : float 0-100
            "verdict"       : "GENUINE" | "SUSPICIOUS" | "FORGED"
            "risk_level"    : "LOW" | "MEDIUM" | "HIGH"
            "breakdown"     : per-stage weighted scores
        }
    """

    print(f"\n[Stage 9] Risk Scoring Engine")
    print(f"  Pipeline : {pipeline_type.upper()}")
    print("-" * 50)

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
        raise ValueError(f"Unknown pipeline type: '{pipeline_type}' — use 'image' or 'pdf'")

    verdict    = get_verdict(final_score)
    risk_level = get_risk_level(final_score)

    # Print breakdown
    for key, value in breakdown.items():
        if "weighted" not in key and "weight" not in key:
            weight_key   = key.replace("_score", "_weight")
            weighted_key = key.replace("_score", "_weighted")
            print(
                f"  {key:20} {value:6}  "
                f"× {breakdown.get(weight_key, '')}  "
                f"= {breakdown.get(weighted_key, '')}"
            )

    print("-" * 50)
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


# ─────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Test image pipeline
    print("=== TEST: Image Pipeline ===")
    result = run_risk_scoring("image", {
        "forensics_score": 55.0,
        "cnn_score"      : 72.0,
        "ocr_score"      : 30.0
    })
    print(f"\n  → Verdict : {result['verdict']}")

    # Test PDF pipeline
    print("\n=== TEST: PDF Pipeline ===")
    result = run_risk_scoring("pdf", {
        "pdf_score": 40.0,
        "ocr_score": 10.0
    })
    print(f"\n  → Verdict : {result['verdict']}")
