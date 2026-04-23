"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 2 : Image Forensics
  Libraries: cv2 + numpy only
  Input   : PNG image (always, guaranteed by Stage 1)
  Output  : forensics_score (0-100) → goes to Risk Scoring Engine
            heatmap PNG             → goes to Forgery Report
=============================================================
  Detectors:
    1. ELA            – Error Level Analysis
    2. Noise          – Noise Inconsistency Detection
    3. Copy-Move      – Copy-Move / Clone Detection
    4. Heatmap        – Combined Tamper Heatmap (fuses 1+2+3)
=============================================================
"""

import cv2
import numpy as np


# ─────────────────────────────────────────────────────────
#  THRESHOLDS
#  These are the decision boundaries for each detector.
#  If a score crosses its threshold → that detector flags suspicious.
#  You can tune these values after testing on real documents.
# ─────────────────────────────────────────────────────────

ELA_THRESHOLD        = 15.0   # mean ELA brightness (0-255 scale)
NOISE_THRESHOLD      = 8.0    # std-dev of per-tile noise levels
CLONE_BLOCK_SIZE     = 16     # size of each block in pixels (16×16)
CLONE_SIM_THRESHOLD  = 0.995  # cosine similarity to call two blocks identical


# ─────────────────────────────────────────────────────────
#  DETECTOR 1 : ELA  (Error Level Analysis)
# ─────────────────────────────────────────────────────────

def run_ela(image_path):
    """
    What it does:
        Takes the PNG image, re-saves it as a JPEG at 90% quality,
        then checks how different each pixel is between the two versions.

        Untouched regions compress predictably → small difference → dark on map.
        Tampered regions were already compressed before → compress differently
        → larger difference → bright spots on map.

    Why JPEG for the temp even though input is PNG:
        PNG is lossless so re-saving as PNG gives zero difference every time.
        The whole point of ELA is the lossy re-save step — JPEG gives us that.
        The temp file is only used for comparison, never saved as output.

    Returns:
        ela_score  : mean brightness of the difference map (higher = more suspicious)
        ela_map    : grayscale image showing where differences are (for heatmap)
        suspicious : True if ela_score > ELA_THRESHOLD
    """

    original = cv2.imread(image_path)

    # Re-save as JPEG at 90% quality — this is the core of ELA
    temp_path = "ela_temp.jpg"
    cv2.imwrite(temp_path, original, [cv2.IMWRITE_JPEG_QUALITY, 90])
    recompressed = cv2.imread(temp_path)

    # Pixel-by-pixel absolute difference
    diff      = cv2.absdiff(original, recompressed)
    ela_gray  = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    ela_score = float(np.mean(ela_gray))

    # Stretch contrast so subtle differences are visible in the heatmap
    ela_map = cv2.normalize(ela_gray, None, 0, 255, cv2.NORM_MINMAX)

    return {
        "ela_score" : round(ela_score, 2),
        "ela_map"   : ela_map,
        "suspicious": ela_score > ELA_THRESHOLD,
        "detail"    : f"ELA mean brightness = {ela_score:.2f}  (limit {ELA_THRESHOLD})"
    }


# ─────────────────────────────────────────────────────────
#  DETECTOR 2 : NOISE INCONSISTENCY
# ─────────────────────────────────────────────────────────

def run_noise_analysis(image):
    """
    What it does:
        Every scanned or photographed document has a natural, uniform
        level of graininess (noise) across the whole page.

        When someone pastes a region from another source, that region
        has a different noise texture — smoother or rougher than the rest.

        We detect this by:
          - Applying a Laplacian filter (amplifies noise and fine texture)
          - Splitting the result into a 4×4 grid of 16 tiles
          - Measuring noise level (std-dev) in each tile
          - If noise varies a lot across tiles → something is wrong

    Returns:
        noise_score : std-dev of the 16 tile noise levels (higher = more inconsistent)
        noise_map   : the Laplacian result image (for heatmap)
        suspicious  : True if noise_score > NOISE_THRESHOLD
    """

    gray      = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    noise_map = np.abs(laplacian).astype(np.uint8)

    h, w  = noise_map.shape
    th    = h // 4
    tw    = w // 4

    tile_stds = []
    for r in range(4):
        for c in range(4):
            tile = noise_map[r*th : (r+1)*th, c*tw : (c+1)*tw]
            tile_stds.append(float(np.std(tile)))

    # High std-dev across tiles = noise is NOT uniform = suspicious
    noise_score = round(float(np.std(tile_stds)), 2)

    return {
        "noise_score": noise_score,
        "noise_map"  : noise_map,
        "tile_stds"  : [round(v, 2) for v in tile_stds],
        "suspicious" : noise_score > NOISE_THRESHOLD,
        "detail"     : f"Noise inconsistency = {noise_score:.2f}  (limit {NOISE_THRESHOLD})"
    }


# ─────────────────────────────────────────────────────────
#  DETECTOR 3 : COPY-MOVE DETECTION
# ─────────────────────────────────────────────────────────

def run_copy_move(image):
    """
    What it does:
        A common forgery technique is to copy a region of the document
        and paste it over something to hide it (e.g. cover a name, date,
        or stamp with a copy of the background).

        We catch this by:
          - Splitting the image into 16×16 pixel blocks
          - Comparing every block against every other block
          - If two non-adjacent blocks are nearly identical → copy-move detected

        Blank/white blocks are skipped because plain paper background
        naturally repeats and would cause too many false positives.

    Returns:
        clone_count : number of matching block pairs found
        clone_pairs : list of (position1, position2) for each match
        suspicious  : True if any clone pairs found
    """

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    bs   = CLONE_BLOCK_SIZE

    blocks    = []
    positions = []

    for y in range(0, h - bs, bs):
        for x in range(0, w - bs, bs):
            block = gray[y : y+bs, x : x+bs].astype(np.float32)

            # Skip blank blocks — plain white paper repeats naturally
            if np.std(block) < 3.0:
                continue

            blocks.append(block.flatten())
            positions.append((y, x))

    clone_pairs = []

    if len(blocks) > 1:
        arr    = np.array(blocks)
        norms  = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-8
        normed = arr / norms

        # Dot product of normalised vectors = cosine similarity
        # Value of 1.0 = perfectly identical blocks
        sim = normed @ normed.T

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


# ─────────────────────────────────────────────────────────
#  DETECTOR 4 : COMBINED TAMPER HEATMAP
# ─────────────────────────────────────────────────────────

def build_heatmap(image, ela_map, noise_map, clone_pairs):
    """
    What it does:
        Fuses ELA + Noise + Copy-Move results into one visual heatmap.
        Brighter/redder areas = more suspicious.
        This is the key visual output for your Forgery Report.

        Steps:
          1. Normalize ELA and Noise maps to 0-255
          2. Blend them equally (50/50 weight)
          3. Mark copy-move clone block locations in bright white
          4. Apply a color map (COLORMAP_JET: blue=clean, red=suspicious)
          5. Overlay on original image at 50% transparency

    Returns:
        heatmap : the final colored overlay image (save as PNG for report)
    """

    h, w = image.shape[:2]

    # Resize both maps to match original image size (in case of rounding)
    ela_resized   = cv2.resize(ela_map,   (w, h))
    noise_resized = cv2.resize(noise_map, (w, h))

    # Normalize both to 0-255 cleanly
    ela_norm   = cv2.normalize(ela_resized,   None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)
    noise_norm = cv2.normalize(noise_resized, None, 0, 255, cv2.NORM_MINMAX).astype(np.float32)

    # Blend: equal weight between ELA and Noise
    fused = (0.5 * ela_norm + 0.5 * noise_norm).astype(np.uint8)

    # Mark copy-move blocks as bright white spots on the fused map
    bs = CLONE_BLOCK_SIZE
    for (y1, x1), (y2, x2) in clone_pairs:
        cv2.rectangle(fused, (x1, y1), (x1 + bs, y1 + bs), 255, -1)
        cv2.rectangle(fused, (x2, y2), (x2 + bs, y2 + bs), 255, -1)

    # Apply color map: blue = clean, green = mild, red = suspicious
    colored = cv2.applyColorMap(fused, cv2.COLORMAP_JET)

    # Overlay on original image at 50% opacity
    heatmap = cv2.addWeighted(image, 0.5, colored, 0.5, 0)

    return heatmap


# ─────────────────────────────────────────────────────────
#  SCORING ENGINE
# ─────────────────────────────────────────────────────────

def compute_forensics_score(ela, noise, copy_move):
    """
    Combines all 3 detector scores into one final 0-100 score.
    Higher = more suspicious.

    Weights chosen based on detection reliability for documents:
        ELA        → 40 pts  (strongest and most direct signal)
        Copy-Move  → 35 pts  (very specific, almost no false positives)
        Noise      → 25 pts  (good supporting signal)
    """

    score = 0.0

    # ELA : scale linearly — 0 at 0, full 40 pts at 2× threshold
    ela_raw = min(ela["ela_score"], ELA_THRESHOLD * 2)
    score  += (ela_raw / (ELA_THRESHOLD * 2)) * 40

    # Copy-Move : each pair = 7 pts, capped at 35
    score += min(copy_move["clone_count"] * 7, 35)

    # Noise : scale linearly — 0 at 0, full 25 pts at 2× threshold
    noise_raw = min(noise["noise_score"], NOISE_THRESHOLD * 2)
    score    += (noise_raw / (NOISE_THRESHOLD * 2)) * 25

    return round(score, 2)


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_image_forensics(image_path, save_heatmap_path="stage2_heatmap.png"):
    """
    Call this from your pipeline after Stage 1.

    Args:
        image_path       : path to the normalized PNG from Stage 1
        save_heatmap_path: where to save the heatmap PNG for the report

    Returns:
        {
            "ela"             : { ela_score, ela_map, suspicious, detail }
            "noise"           : { noise_score, noise_map, tile_stds, suspicious, detail }
            "copy_move"       : { clone_count, clone_pairs, suspicious, detail }
            "forensics_score" : float  0-100  → feed to Stage 9 Risk Engine
            "heatmap_path"    : path to saved heatmap PNG → feed to Stage 10 Report
            "overall_suspicious" : bool
        }
    """

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    print(f"\n[Stage 2] Image Forensics")
    print(f"  Input : {image_path}")
    print("-" * 50)

    # Run all 3 detectors
    ela       = run_ela(image_path)
    noise     = run_noise_analysis(image)
    copy_move = run_copy_move(image)

    # Build and save heatmap
    heatmap = build_heatmap(image, ela["ela_map"], noise["noise_map"], copy_move["clone_pairs"])
    cv2.imwrite(save_heatmap_path, heatmap)

    # Compute final score
    forensics_score    = compute_forensics_score(ela, noise, copy_move)
    overall_suspicious = forensics_score >= 30.0

    # Print summary
    for name, result in [("ELA", ela), ("NOISE", noise), ("COPY-MOVE", copy_move)]:
        flag = "⚠  SUSPICIOUS" if result["suspicious"] else "✓  OK"
        print(f"  [{flag}]  {name:10} {result['detail']}")

    print("-" * 50)
    print(f"  Forensics Score : {forensics_score} / 100")
    print(f"  Verdict         : {'SUSPICIOUS' if overall_suspicious else 'LIKELY GENUINE'}")
    print(f"  Heatmap saved   : {save_heatmap_path}")

    return {
        "ela"               : ela,
        "noise"             : noise,
        "copy_move"         : copy_move,
        "forensics_score"   : forensics_score,
        "heatmap_path"      : save_heatmap_path,
        "overall_suspicious": overall_suspicious
    }


# ─────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    path   = sys.argv[1] if len(sys.argv) > 1 else "test_document.png"
    result = run_image_forensics(path)
    print(f"\n  → Forensics score for Risk Engine : {result['forensics_score']}")
    print(f"  → Heatmap for Report              : {result['heatmap_path']}")