"""
  Detectors:
    1. ELA            – Error Level Analysis
    2. Noise          – Noise Inconsistency Detection
    3. Copy-Move      – Copy-Move / Clone Detection
    4. Heatmap        – Combined Tamper Heatmap with RED bounding boxes
"""

import cv2
import numpy as np


# ── Thresholds ────────────────────────────────────────────────────────────────
ELA_THRESHOLD       = 12.0   # lowered from 15 — catches more subtle tampering
NOISE_THRESHOLD     = 6.0    # lowered from 8 — more sensitive to noise shifts
CLONE_BLOCK_SIZE    = 16
CLONE_SIM_THRESHOLD = 0.995

# How bright a region must be in the ELA/noise map to get a red box drawn on it
# 0-255 scale — only regions brighter than this get boxed (filters out noise)
HEATMAP_BOX_THRESHOLD = 127


# ── DETECTOR 1 : ELA ─────────────────────────────────────────────────────────
def run_ela(image_path):
    """
    Re-saves image as JPEG at 90% quality.
    Tampered regions compress differently → brighter in the difference map.
    JPEG temp is intentional — PNG re-save gives zero difference (lossless).
    """
    original = cv2.imread(image_path)

    temp_path = "/tmp/ela_temp.jpg"
    cv2.imwrite(temp_path, original, [cv2.IMWRITE_JPEG_QUALITY, 90])
    recompressed = cv2.imread(temp_path)

    diff      = cv2.absdiff(original, recompressed)
    ela_gray  = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    ela_score = float(np.mean(ela_gray))

    # Amplify × 10 so subtle differences become clearly visible
    ela_map = cv2.normalize(ela_gray * 10, None, 0, 255, cv2.NORM_MINMAX)

    return {
        "ela_score" : round(ela_score, 2),
        "ela_map"   : ela_map,
        "suspicious": ela_score > ELA_THRESHOLD,
        "detail"    : f"ELA mean brightness = {ela_score:.3f}  (limit {ELA_THRESHOLD})"
    }


# ── DETECTOR 2 : NOISE INCONSISTENCY ─────────────────────────────────────────
def run_noise_analysis(image):
    """
    Splits image into 16 tiles, measures noise per tile.
    High variation across tiles = pasted or edited region.
    """
    gray      = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    noise_map = np.abs(laplacian).astype(np.uint8)

    h, w = noise_map.shape
    th   = h // 4
    tw   = w // 4

    tile_stds = []
    for r in range(4):
        for c in range(4):
            tile = noise_map[r*th:(r+1)*th, c*tw:(c+1)*tw]
            tile_stds.append(float(np.std(tile)))

    noise_score = round(float(np.std(tile_stds)), 2)

    # Amplify noise map so it is visible
    noise_map_vis = cv2.normalize(noise_map, None, 0, 255, cv2.NORM_MINMAX)

    return {
        "noise_score": noise_score,
        "noise_map"  : noise_map_vis,
        "tile_stds"  : [round(v, 2) for v in tile_stds],
        "suspicious" : noise_score > NOISE_THRESHOLD,
        "detail"     : f"Noise inconsistency = {noise_score:.2f}  (limit {NOISE_THRESHOLD})"
    }


# ── DETECTOR 3 : COPY-MOVE ───────────────────────────────────────────────────
def run_copy_move(image):
    """
    Finds near-identical 16×16 blocks at different locations.
    Cosine similarity >= 0.995 = copy-move pair.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    bs   = CLONE_BLOCK_SIZE

    blocks, positions = [], []

    for y in range(0, h - bs, bs):
        for x in range(0, w - bs, bs):
            block = gray[y:y+bs, x:x+bs].astype(np.float32)
            if np.std(block) < 3.0:
                continue
            blocks.append(block.flatten())
            positions.append((y, x))

    clone_pairs = []
    if len(blocks) > 1:
        arr    = np.array(blocks)
        norms  = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-8
        normed = arr / norms
        sim    = normed @ normed.T
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                if sim[i, j] >= CLONE_SIM_THRESHOLD:
                    clone_pairs.append((positions[i], positions[j]))

    return {
        "clone_count": len(clone_pairs),
        "clone_pairs": clone_pairs,
        "suspicious" : len(clone_pairs) > 0,
        "detail"     : f"Matching block pairs found = {len(clone_pairs)}"
    }


# ── HELPER : find suspicious regions and draw red boxes ──────────────────────
def draw_suspicious_boxes(base_image, heat_gray, label, box_min_area=200):
    """
    Takes a grayscale heatmap, thresholds it, finds contours of
    bright (suspicious) regions, and draws RED bounding boxes on the image.

    box_min_area : ignore tiny blobs smaller than this many pixels
                   (filters out noise specks)
    """
    # Threshold — only keep bright suspicious regions
    _, thresh = cv2.threshold(heat_gray, HEATMAP_BOX_THRESHOLD, 255, cv2.THRESH_BINARY)

    # Morphological closing — merges nearby suspicious blobs into one region
    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
    thresh  = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Find contours of suspicious regions
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    box_count = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < box_min_area:
            continue  # skip tiny noise blobs

        x, y, w, h = cv2.boundingRect(contour)

        # Red bounding box — thick, clearly visible
        cv2.rectangle(base_image, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # Label above the box
        cv2.putText(base_image, label, (x, max(y - 6, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)
        box_count += 1

    return base_image, box_count


# ── DETECTOR 4 : HEATMAP WITH RED BOXES ──────────────────────────────────────
def build_heatmap(image, ela_map, noise_map, clone_pairs,
                  save_ela_path, save_heatmap_path):
    """
    Builds two output images:

    1. ELA annotated image (save_ela_path):
       Original image with red boxes drawn on suspicious ELA regions.

    2. Full heatmap (save_heatmap_path):
       Fused ELA+Noise colormap overlay on original with red boxes for:
         - ELA suspicious regions
         - Noise suspicious regions
         - Copy-move matched block locations
    """
    h, w = image.shape[:2]

    ela_resized   = cv2.resize(ela_map,   (w, h))
    noise_resized = cv2.resize(noise_map, (w, h))

    ela_norm   = cv2.normalize(ela_resized,   None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)
    noise_norm = cv2.normalize(noise_resized, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)

    # ── ELA annotated image ──────────────────────────────────────────────────
    ela_annotated = image.copy()
    ela_annotated, ela_boxes = draw_suspicious_boxes(
        ela_annotated, ela_norm.astype(np.uint8), "ELA")

    cv2.imwrite(save_ela_path, ela_annotated)

    # ── Full heatmap ─────────────────────────────────────────────────────────
    # Fuse ELA and noise maps
    fused = (0.6 * ela_norm + 0.4 * noise_norm).astype(np.uint8)  # ELA gets more weight

    # Apply JET colormap (blue=clean → green=mild → red=suspicious)
    colored = cv2.applyColorMap(fused, cv2.COLORMAP_JET)

    # Overlay on original at 50% opacity
    heatmap = cv2.addWeighted(image, 0.5, colored, 0.5, 0)

    # Draw red boxes for ELA suspicious regions
    heatmap, _ = draw_suspicious_boxes(heatmap, ela_norm.astype(np.uint8), "ELA")

    # Draw red boxes for noise suspicious regions
    heatmap, _ = draw_suspicious_boxes(heatmap, noise_norm.astype(np.uint8), "Noise")

    # Draw red boxes on copy-move matched block pairs
    bs = CLONE_BLOCK_SIZE
    for (y1, x1), (y2, x2) in clone_pairs:
        cv2.rectangle(heatmap, (x1, y1), (x1+bs, y1+bs), (0, 0, 255), 2)
        cv2.rectangle(heatmap, (x2, y2), (x2+bs, y2+bs), (0, 0, 255), 2)
        cv2.putText(heatmap, "Clone", (x1, max(y1-4, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    cv2.imwrite(save_heatmap_path, heatmap)
    return ela_boxes


# ── SCORING ───────────────────────────────────────────────────────────────────
def compute_forensics_score(ela, noise, copy_move):
    score = 0.0

    # ELA: 0 at 0, full 40 pts at 2× threshold
    ela_raw = min(ela["ela_score"], ELA_THRESHOLD * 2)
    score  += (ela_raw / (ELA_THRESHOLD * 2)) * 40

    # Copy-Move: each pair = 7 pts, capped at 35
    score += min(copy_move["clone_count"] * 7, 35)

    # Noise: 0 at 0, full 25 pts at 2× threshold
    noise_raw = min(noise["noise_score"], NOISE_THRESHOLD * 2)
    score    += (noise_raw / (NOISE_THRESHOLD * 2)) * 25

    return round(score, 2)


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────
def run_image_forensics(image_path,
                        save_heatmap_path="local datastore/heatmap.png",
                        save_ela_path="local datastore/ela_annotated.png"):
    """
    Args:
        image_path        : path to normalized PNG from Stage 1
        save_heatmap_path : full file path to save heatmap PNG  ← must end in .png
        save_ela_path     : full file path to save ELA annotated PNG

    Returns dict with forensics_score (0-100) → feeds Stage 6 Risk Engine
    """

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    print(f"\n[Stage 2] Image Forensics")
    print(f"  Input : {image_path}")

    #run all 
    ela       = run_ela(image_path)
    noise     = run_noise_analysis(image)
    copy_move = run_copy_move(image)

    ela_boxes = build_heatmap(
        image, ela["ela_map"], noise["noise_map"], copy_move["clone_pairs"],
        save_ela_path, save_heatmap_path
    )

    forensics_score    = compute_forensics_score(ela, noise, copy_move)
    overall_suspicious = forensics_score >= 30.0

    for name, result in [("ELA", ela), ("NOISE", noise), ("COPY-MOVE", copy_move)]:
        flag = "SUSPICIOUS" if result["suspicious"] else "OK"
        print(f"  [{flag}]  {name:10} {result['detail']}")

    print(f"  Forensics Score : {forensics_score} / 100")
    print(f"  Verdict         : {'SUSPICIOUS' if overall_suspicious else 'LIKELY GENUINE'}")
    print(f"  ELA boxes drawn : {ela_boxes}")
    print(f"  Heatmap saved   : {save_heatmap_path}")
    print(f"  ELA map saved   : {save_ela_path}")

    return {
        "ela"               : ela,
        "noise"             : noise,
        "copy_move"         : copy_move,
        "forensics_score"   : forensics_score,
        "heatmap_path"      : save_heatmap_path,
        "ela_path"          : save_ela_path,
        "overall_suspicious": overall_suspicious
    }


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    path   = "local datastore/main.png"
    result = run_image_forensics(
        path,
        save_heatmap_path = "local datastore/heatmap.png",     # ← full path with .png
        save_ela_path     = "local datastore/ela_annotated.png" # ← full path with .png
    )