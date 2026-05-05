"""
  Detectors:
    1. ELA       – Error Level Analysis
    2. Noise     – Noise Inconsistency Detection
    3. Copy-Move – Copy-Move / Clone Detection
    4. Heatmap   – Combined Tamper Heatmap with red suspicious overlay
"""

import cv2
import numpy as np

# ── Thresholds ────────────────────────────────────────────
ELA_THRESHOLD       = 12.0
NOISE_THRESHOLD     = 6.0
CLONE_BLOCK_SIZE    = 16
CLONE_SIM_THRESHOLD = 0.995


# ── DETECTOR 1 : ELA ──────────────────────────────────────
def run_ela(image_path):
    original = cv2.imread(image_path)

    temp_path = "local datastore/ela_temp.jpg"
    cv2.imwrite(temp_path, original, [cv2.IMWRITE_JPEG_QUALITY, 90])
    recompressed = cv2.imread(temp_path)

    diff      = cv2.absdiff(original, recompressed)
    ela_gray  = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    ela_score = float(np.mean(ela_gray))
    ela_map   = cv2.normalize(cv2.multiply(ela_gray, 10), None, 0, 255, cv2.NORM_MINMAX)

    return {
        "ela_score" : round(ela_score, 3),
        "ela_map"   : ela_map,
        "suspicious": ela_score > ELA_THRESHOLD,
        "detail"    : f"ELA mean brightness = {ela_score:.3f}  (limit {ELA_THRESHOLD})"
    }


# ── DETECTOR 2 : NOISE INCONSISTENCY ──────────────────────
def run_noise_analysis(image):
    gray      = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    noise_map = np.abs(laplacian).astype(np.uint8)

    h, w = noise_map.shape
    th, tw = h // 4, w // 4

    tile_stds = []
    for r in range(4):
        for c in range(4):
            tile = noise_map[r*th:(r+1)*th, c*tw:(c+1)*tw]
            tile_stds.append(float(np.std(tile)))

    noise_score = round(float(np.std(tile_stds)), 2)

    return {
        "noise_score": noise_score,
        "noise_map"  : noise_map,
        "tile_stds"  : [round(v, 2) for v in tile_stds],
        "suspicious" : noise_score > NOISE_THRESHOLD,
        "detail"     : f"Noise inconsistency = {noise_score:.2f}  (limit {NOISE_THRESHOLD})"
    }


# ── DETECTOR 3 : COPY-MOVE ────────────────────────────────
def run_copy_move(image):
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


# ── DETECTOR 4 : HEATMAP WITH RED OVERLAY ─────────────────
def build_heatmap(image, ela_map, noise_map, clone_pairs):
    h, w = image.shape[:2]
    bs   = CLONE_BLOCK_SIZE

    ela_resized   = cv2.resize(ela_map,   (w, h))
    noise_resized = cv2.resize(noise_map, (w, h))

    ela_norm   = cv2.normalize(ela_resized,   None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)
    noise_norm = cv2.normalize(noise_resized, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)

    fused = (0.6 * ela_norm + 0.4 * noise_norm).astype(np.uint8)

    # Mark copy-move blocks on fused map
    for (y1, x1), (y2, x2) in clone_pairs:
        cv2.rectangle(fused, (x1, y1), (x1+bs, y1+bs), 255, -1)
        cv2.rectangle(fused, (x2, y2), (x2+bs, y2+bs), 255, -1)

    # ── Red overlay on suspicious pixels — 5 lines ────────
    mask            = fused > np.percentile(fused, 92)   # top 8% pixels are suspicious
    overlay         = image.copy()
    overlay[mask]   = [0, 0, 255]                        # paint those pixels red
    annotated       = cv2.addWeighted(image, 0.6, overlay, 0.4, 0)  # blend with original

    # Standard heatmap (color map version)
    colored = cv2.applyColorMap(fused, cv2.COLORMAP_JET)
    heatmap = cv2.addWeighted(image, 0.45, colored, 0.55, 0)

    return heatmap, annotated


# ── SCORING ───────────────────────────────────────────────
def compute_forensics_score(ela, noise, copy_move):
    score = 0.0

    ela_raw = min(ela["ela_score"], ELA_THRESHOLD * 2)
    score  += (ela_raw / (ELA_THRESHOLD * 2)) * 40

    score  += min(copy_move["clone_count"] * 7, 35)

    noise_raw = min(noise["noise_score"], NOISE_THRESHOLD * 2)
    score    += (noise_raw / (NOISE_THRESHOLD * 2)) * 25

    return round(score, 2)


# ── MAIN ENTRY POINT ──────────────────────────────────────
def run_image_forensics(image_path, save_folder="local datastore"):
    """
    Args:
        image_path  : path to PNG from Stage 1
        save_folder : folder to save output images — do NOT pass a filename

    Saves:
        save_folder/heatmap.png   — color intensity map
        save_folder/annotated.png — original image with red suspicious overlay
    """

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    print(f"\n[Stage 2] Image Forensics")
    print(f"  Input : {image_path}")
    print("-" * 50)

    ela       = run_ela(image_path)
    noise     = run_noise_analysis(image)
    copy_move = run_copy_move(image)

    heatmap, annotated = build_heatmap(image, ela["ela_map"], noise["noise_map"], copy_move["clone_pairs"])

    heatmap_path   = f"{save_folder}/heatmap.png"
    annotated_path = f"{save_folder}/annotated.png"
    cv2.imwrite(heatmap_path, heatmap)
    cv2.imwrite(annotated_path, annotated)

    forensics_score    = compute_forensics_score(ela, noise, copy_move)
    overall_suspicious = forensics_score >= 30.0

    for name, result in [("ELA", ela), ("NOISE", noise), ("COPY-MOVE", copy_move)]:
        flag = "SUSPICIOUS" if result["suspicious"] else "OK"
        print(f"  [{flag}]  {name:10} {result['detail']}")

    print("-" * 50)
    print(f"  Forensics Score : {forensics_score} / 100")
    print(f"  Verdict         : {'SUSPICIOUS' if overall_suspicious else 'LIKELY GENUINE'}")
    print(f"  Heatmap         : {heatmap_path}")
    print(f"  Annotated       : {annotated_path}")

    return {
        "ela"               : ela,
        "noise"             : noise,
        "copy_move"         : copy_move,
        "forensics_score"   : forensics_score,
        "heatmap_path"      : heatmap_path,
        "annotated_path"    : annotated_path,
        "overall_suspicious": overall_suspicious
    }


if __name__ == "__main__":
    path   = "local datastore/main.png"
    result = run_image_forensics(path, "local datastore")