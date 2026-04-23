"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 3 : CNN Tamper Detection — INFERENCE
  Library : TensorFlow / Keras
  Input   : PNG image (guaranteed by Stage 1)
  Output  : cnn_score (0-100) → goes to Stage 9 Risk Engine
=============================================================
  This script loads the trained model (stage3_model.keras)
  and runs it on one document image to get a tamper score.

  Run stage3_train.py first to generate stage3_model.keras.
  After that, this script is what the pipeline calls every
  time a new document needs to be checked.
=============================================================
"""

import cv2
import numpy as np
import tensorflow as tf


# ─────────────────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────────────────

MODEL_PATH = "stage3_model.keras"   # saved by stage3_train.py
IMAGE_SIZE = (224, 224)             # must match training size


# ─────────────────────────────────────────────────────────
#  LOAD MODEL ONCE
#  Loading is expensive so we do it at module level.
#  When pipeline imports this file, model loads once and
#  stays in memory for all subsequent calls.
# ─────────────────────────────────────────────────────────

print("[Stage 3] Loading CNN model...")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print(f"[Stage 3] Model loaded from {MODEL_PATH}")
except Exception as e:
    raise FileNotFoundError(
        f"Could not load model: {MODEL_PATH}\n"
        f"Run stage3_train.py first to generate the model.\n"
        f"Error: {e}"
    )


# ─────────────────────────────────────────────────────────
#  INFERENCE
# ─────────────────────────────────────────────────────────

def run_cnn_inference(image_path):
    """
    What it does:
        Loads the document image, resizes it to 224×224,
        preprocesses it the same way training data was processed,
        then passes it through the trained MobileNetV2 model.

        The model outputs a single value between 0.0 and 1.0:
            0.0 = model is confident this is GENUINE
            1.0 = model is confident this is FORGED

        We scale this to 0-100 to match other stage scores.

    Args:
        image_path : path to normalized PNG from Stage 1

    Returns:
        {
            "raw_score"  : float 0.0-1.0  (direct model output)
            "cnn_score"  : float 0-100    (scaled, feeds Stage 9)
            "suspicious" : bool
            "detail"     : human readable summary
        }
    """

    # Load and resize image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Convert BGR (OpenCV) to RGB (what the model expects)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_resized = cv2.resize(image_rgb, IMAGE_SIZE)

    # Preprocess exactly as during training — scale pixels to [-1, +1]
    image_array = tf.keras.applications.mobilenet_v2.preprocess_input(
        np.array(image_resized, dtype=np.float32)
    )

    # Add batch dimension: (224, 224, 3) → (1, 224, 224, 3)
    image_batch = np.expand_dims(image_array, axis=0)

    # Run through model
    prediction = model.predict(image_batch, verbose=0)
    raw_score  = float(prediction[0][0])   # single sigmoid output
    cnn_score  = round(raw_score * 100, 2) # scale to 0-100

    return {
        "raw_score" : round(raw_score, 4),
        "cnn_score" : cnn_score,
        "suspicious": cnn_score >= 50.0,
        "detail"    : f"CNN confidence of forgery = {cnn_score:.2f}%"
    }


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

def run_cnn_detection(image_path):
    """
    Call this from your pipeline after Stage 2.

    Args:
        image_path : path to normalized PNG from Stage 1

    Returns:
        cnn result dict with cnn_score → feeds Stage 9
    """

    print(f"\n[Stage 3] CNN Tamper Detection")
    print(f"  Input : {image_path}")
    print("-" * 50)

    result = run_cnn_inference(image_path)

    flag = "⚠  SUSPICIOUS" if result["suspicious"] else "✓  OK"
    print(f"  [{flag}]  {result['detail']}")
    print("-" * 50)
    print(f"  CNN Score : {result['cnn_score']} / 100")

    return result


# ─────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    path   = sys.argv[1] if len(sys.argv) > 1 else "test_document.png"
    result = run_cnn_detection(path)
    print(f"\n  → CNN score for Risk Engine : {result['cnn_score']}")
