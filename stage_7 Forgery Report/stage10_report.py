"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 10 : Forgery Risk Report
  Libraries : base64, datetime (both built-in, zero installs)
  Input     : all stage results collected by main.py
  Output    : report.html — opens in any browser
=============================================================
  The report contains:
    - Final verdict (large, color-coded)
    - Risk score with visual bar
    - Per-stage score breakdown
    - All flags raised across all stages
    - Extracted OCR text
    - Tamper heatmap (image pipeline only)
    - Document metadata
=============================================================
"""

import os
import base64
from datetime import datetime


# ─────────────────────────────────────────────────────────
#  VERDICT COLORS
# ─────────────────────────────────────────────────────────

VERDICT_COLORS = {
    "GENUINE"    : "#22c55e",   # green
    "SUSPICIOUS" : "#f59e0b",   # amber
    "FORGED"     : "#ef4444"    # red
}

VERDICT_BG = {
    "GENUINE"    : "#f0fdf4",
    "SUSPICIOUS" : "#fffbeb",
    "FORGED"     : "#fef2f2"
}


# ─────────────────────────────────────────────────────────
#  HELPER : EMBED IMAGE AS BASE64
#  Embeds heatmap directly into HTML so the report is
#  one self-contained file — no external dependencies.
# ─────────────────────────────────────────────────────────

def embed_image(image_path):
    """Reads a PNG and returns a base64 data URI for embedding in HTML."""
    if not image_path or not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


# ─────────────────────────────────────────────────────────
#  HELPER : FLAGS TABLE
# ─────────────────────────────────────────────────────────

def build_flags_section(all_results):
    """
    Collects all suspicious flags raised across all stages
    and formats them as an HTML list.
    """

    flags = []

    # Stage 2 flags
    if "stage2" in all_results:
        s2 = all_results["stage2"]
        for key in ["ela", "noise", "copy_move", "edge"]:
            if key in s2 and s2[key].get("suspicious"):
                flags.append(f"[Image Forensics] {s2[key]['detail']}")

    # Stage 3 flag
    if "stage3" in all_results:
        s3 = all_results["stage3"]
        if s3.get("suspicious"):
            flags.append(f"[CNN Detection] {s3['detail']}")

    # Stage 4 flags
    if "stage4" in all_results:
        s4 = all_results["stage4"]
        if s4.get("spelling", {}).get("suspicious"):
            flags.append(f"[OCR Spelling] {s4['spelling']['detail']}")
            misspelled = s4["spelling"].get("misspelled", [])
            if misspelled:
                flags.append(f"[OCR Spelling] Misspelled words: {', '.join(misspelled[:10])}")
        if s4.get("dates", {}).get("suspicious"):
            flags.append(f"[OCR Dates] {s4['dates']['detail']}")
            invalid = s4["dates"].get("invalid_dates", [])
            if invalid:
                flags.append(f"[OCR Dates] Invalid dates found: {', '.join(invalid)}")
        if s4.get("numeric", {}).get("suspicious"):
            flags.append(f"[OCR Numeric] {s4['numeric']['detail']}")
            for f in s4["numeric"].get("flags", []):
                flags.append(f"[OCR Numeric] {f}")

    # Stage 8 flags
    if "stage8" in all_results:
        s8 = all_results["stage8"]
        for key in ["metadata", "incremental", "fonts", "producers"]:
            if key in s8 and s8[key].get("suspicious"):
                for f in s8[key].get("flags", []):
                    flags.append(f"[PDF Forensics] {f}")

    if not flags:
        return "<p style='color:#22c55e'>✓ No suspicious flags raised across all checks.</p>"

    items = "\n".join([
        f"<li style='margin-bottom:6px'>⚠ {flag}</li>"
        for flag in flags
    ])
    return f"<ul style='margin:0;padding-left:20px'>{items}</ul>"


# ─────────────────────────────────────────────────────────
#  HELPER : SCORE BAR
# ─────────────────────────────────────────────────────────

def score_bar(score, color):
    """Renders a visual progress bar for a score."""
    return f"""
    <div style="background:#e5e7eb;border-radius:8px;height:12px;width:100%;margin-top:4px">
        <div style="background:{color};width:{score}%;height:12px;border-radius:8px;
                    transition:width 0.3s"></div>
    </div>"""


# ─────────────────────────────────────────────────────────
#  BUILD SCORE BREAKDOWN TABLE
# ─────────────────────────────────────────────────────────

def build_breakdown_table(risk_result):
    """Renders the per-stage score breakdown as HTML rows."""

    breakdown = risk_result["breakdown"]
    rows      = ""
    color     = VERDICT_COLORS[risk_result["verdict"]]

    for key, value in breakdown.items():
        if "_score" not in key:
            continue
        label        = key.replace("_score", "").replace("_", " ").title()
        weight_key   = key.replace("_score", "_weight")
        weighted_key = key.replace("_score", "_weighted")
        weight       = breakdown.get(weight_key, "—")
        weighted     = breakdown.get(weighted_key, "—")

        rows += f"""
        <tr>
            <td style="padding:10px;font-weight:500">{label}</td>
            <td style="padding:10px;text-align:center">{value} / 100
                {score_bar(value, color)}
            </td>
            <td style="padding:10px;text-align:center;color:#6b7280">{weight}</td>
            <td style="padding:10px;text-align:center;font-weight:600">{weighted}</td>
        </tr>"""

    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead>
            <tr style="background:#f9fafb;border-bottom:2px solid #e5e7eb">
                <th style="padding:10px;text-align:left">Stage</th>
                <th style="padding:10px;text-align:center">Raw Score</th>
                <th style="padding:10px;text-align:center">Weight</th>
                <th style="padding:10px;text-align:center">Contribution</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""


# ─────────────────────────────────────────────────────────
#  BUILD FULL HTML REPORT
# ─────────────────────────────────────────────────────────

def build_html_report(file_info, all_results, risk_result):
    """
    Assembles the complete HTML report as a string.

    Args:
        file_info    : dict with input_path, file_type, output_path
        all_results  : dict with keys stage2, stage3, stage4, stage8
        risk_result  : output from Stage 9

    Returns:
        HTML string
    """

    verdict     = risk_result["verdict"]
    final_score = risk_result["final_score"]
    risk_level  = risk_result["risk_level"]
    color       = VERDICT_COLORS[verdict]
    bg_color    = VERDICT_BG[verdict]
    timestamp   = datetime.now().strftime("%d %B %Y, %I:%M %p")
    filename    = os.path.basename(file_info.get("input_path", "Unknown"))
    file_type   = file_info.get("file_type", "Unknown").replace("_", " ").title()

    # Heatmap (only for image pipeline)
    heatmap_html = ""
    heatmap_path = all_results.get("stage2", {}).get("heatmap_path")
    if heatmap_path:
        heatmap_data = embed_image(heatmap_path)
        if heatmap_data:
            heatmap_html = f"""
            <div style="background:#fff;border-radius:12px;padding:24px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:24px">
                <h2 style="margin:0 0 16px;font-size:16px;color:#111827">
                    Tamper Heatmap
                </h2>
                <p style="color:#6b7280;font-size:13px;margin:0 0 12px">
                    Blue = clean regions &nbsp;|&nbsp; Red = suspicious regions
                </p>
                <img src="{heatmap_data}"
                     style="width:100%;border-radius:8px;border:1px solid #e5e7eb">
            </div>"""

    # OCR extracted text
    ocr_text = ""
    if "stage4" in all_results:
        ocr_text = all_results["stage4"].get("ocr", {}).get("full_text", "")

    ocr_html = f"""
    <div style="background:#fff;border-radius:12px;padding:24px;
                box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:24px">
        <h2 style="margin:0 0 16px;font-size:16px;color:#111827">
            Extracted Text (OCR)
        </h2>
        <div style="background:#f9fafb;border-radius:8px;padding:16px;
                    font-size:13px;color:#374151;line-height:1.7;
                    white-space:pre-wrap;max-height:200px;overflow-y:auto;
                    border:1px solid #e5e7eb">
            {ocr_text if ocr_text else "No text extracted."}
        </div>
    </div>""" if "stage4" in all_results else ""

    # PDF metadata (only for PDF pipeline)
    pdf_meta_html = ""
    if "stage8" in all_results:
        meta = all_results["stage8"].get("metadata", {}).get("metadata", {})
        rows = "\n".join([
            f"<tr><td style='padding:8px;color:#6b7280;font-size:13px'>{k}</td>"
            f"<td style='padding:8px;font-size:13px'>{v}</td></tr>"
            for k, v in meta.items()
        ])
        pdf_meta_html = f"""
        <div style="background:#fff;border-radius:12px;padding:24px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:24px">
            <h2 style="margin:0 0 16px;font-size:16px;color:#111827">PDF Metadata</h2>
            <table style="width:100%;border-collapse:collapse">{rows}</table>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forgery Detection Report — {filename}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f3f4f6;
            color: #111827;
            padding: 32px 16px;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
    </style>
</head>
<body>
<div class="container">

    <!-- HEADER -->
    <div style="background:#111827;border-radius:12px;padding:24px;
                margin-bottom:24px;color:white">
        <div style="font-size:12px;color:#9ca3af;margin-bottom:4px;
                    text-transform:uppercase;letter-spacing:.05em">
            Document Forgery Detection System
        </div>
        <h1 style="font-size:22px;font-weight:700;margin-bottom:4px">
            Forensic Analysis Report
        </h1>
        <div style="font-size:13px;color:#9ca3af">
            {filename} &nbsp;·&nbsp; {file_type} &nbsp;·&nbsp; {timestamp}
        </div>
    </div>

    <!-- VERDICT CARD -->
    <div style="background:{bg_color};border:2px solid {color};border-radius:12px;
                padding:28px;margin-bottom:24px;text-align:center">
        <div style="font-size:13px;color:#6b7280;margin-bottom:8px;
                    text-transform:uppercase;letter-spacing:.08em">
            Final Verdict
        </div>
        <div style="font-size:48px;font-weight:800;color:{color};
                    letter-spacing:.05em;margin-bottom:12px">
            {verdict}
        </div>
        <div style="font-size:28px;font-weight:700;color:#111827;margin-bottom:8px">
            Risk Score: {final_score} / 100
        </div>
        {score_bar(final_score, color)}
        <div style="margin-top:10px;font-size:13px;color:#6b7280">
            Risk Level: <strong style="color:{color}">{risk_level}</strong>
        </div>
    </div>

    <!-- SCORE BREAKDOWN -->
    <div style="background:#fff;border-radius:12px;padding:24px;
                box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:24px">
        <h2 style="margin:0 0 16px;font-size:16px;color:#111827">
            Score Breakdown
        </h2>
        {build_breakdown_table(risk_result)}
    </div>

    <!-- FLAGS -->
    <div style="background:#fff;border-radius:12px;padding:24px;
                box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:24px">
        <h2 style="margin:0 0 16px;font-size:16px;color:#111827">
            Suspicious Findings
        </h2>
        <div style="font-size:14px;line-height:1.8;color:#374151">
            {build_flags_section(all_results)}
        </div>
    </div>

    <!-- HEATMAP -->
    {heatmap_html}

    <!-- OCR TEXT -->
    {ocr_html}

    <!-- PDF METADATA -->
    {pdf_meta_html}

    <!-- FOOTER -->
    <div style="text-align:center;font-size:12px;color:#9ca3af;margin-top:16px">
        Generated by Document Forgery Detection System &nbsp;·&nbsp; {timestamp}
        <br>This report is for forensic analysis purposes only.
    </div>

</div>
</body>
</html>"""

    return html


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_report_generation(file_info, all_results, risk_result,
                          output_path="pipeline_working/report.html"):
    """
    Call this from main.py as the final step.

    Args:
        file_info    : Stage 1 result dict
        all_results  : dict with stage2/3/4/8 result dicts
        risk_result  : Stage 9 result dict
        output_path  : where to save the HTML report

    Returns:
        path to the saved HTML report
    """

    print(f"\n[Stage 10] Generating Forgery Risk Report...")

    html = build_html_report(file_info, all_results, risk_result)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Report saved : {output_path}")
    print(f"  Verdict      : {risk_result['verdict']}")
    print(f"  Final Score  : {risk_result['final_score']} / 100")
    print(f"\n  Open {output_path} in any browser to view the report.")

    return output_path
