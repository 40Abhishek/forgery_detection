import torch
import torch.nn as nn
import numpy as np
import cv2
from torchvision import transforms

# ✅ FIXED: match actual saved model name
MODEL_PATH = "model.pth"

IMAGE_SIZE = 128
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")
path = "local datastore/main.png"

# ─────────────────────────────────────────────────────────
# ✅ FIXED: EXACT SAME ARCHITECTURE AS TRAINING
# (nn.Sequential — matches how .pth was saved)
# ─────────────────────────────────────────────────────────

def build_model():
    def conv_block(in_ch, out_ch):
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

    return nn.Sequential(
        conv_block(3,   32),
        conv_block(32,  64),
        conv_block(64,  128),
        conv_block(128, 256),
        nn.Flatten(),
        nn.Linear(256 * 8 * 8, 1024),
        nn.ReLU(),
        nn.Dropout(0.5),
        nn.Linear(1024, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 1),
        nn.Sigmoid(),
    )


# ─────────────────────────────────────────────────────────
# LOAD MODEL (unchanged logic, just correct architecture)
# ─────────────────────────────────────────────────────────

print("[Stage 3] Loading CNN model...")
try:
    model = build_model().to(DEVICE)

    model.load_state_dict(
        torch.load(MODEL_PATH, map_location=DEVICE),
        strict=True   # ensures perfect match
    )

    model.eval()
    print(f"[Stage 3] Model loaded from {MODEL_PATH}")

except FileNotFoundError:
    raise FileNotFoundError(
        f"Model file not found: {MODEL_PATH}\n"
        f"Make sure stage3_model.pth is in the correct directory."
    )


# ─────────────────────────────────────────────────────────
# INFERENCE TRANSFORM (UNCHANGED)
# ─────────────────────────────────────────────────────────

inference_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5],
                         std= [0.5, 0.5, 0.5])
])


# ─────────────────────────────────────────────────────────
# INFERENCE (UNCHANGED)
# ─────────────────────────────────────────────────────────

def run_cnn_detection(image_path):

    print(f"\n[Stage 3] CNN Tamper Detection")
    print(f"  Input : {image_path}")
    print("-" * 50)

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    tensor = inference_transform(image_rgb)
    tensor = tensor.unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output    = model(tensor)
        raw_score = float(output.item())

    cnn_score = round(raw_score * 100, 2)

    flag = "⚠  SUSPICIOUS" if cnn_score >= 50.0 else "✓  OK"
    print(f"  [{flag}]  CNN confidence of forgery = {cnn_score:.2f}%")
    print("-" * 50)
    print(f"  CNN Score : {cnn_score} / 100")

    return {
        "raw_score" : round(raw_score, 4),
        "cnn_score" : cnn_score,
        "suspicious": cnn_score >= 50.0,
        "detail"    : f"CNN confidence of forgery = {cnn_score:.2f}%"
    }


# ─────────────────────────────────────────────────────────
# QUICK TEST (UNCHANGED)
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_cnn_detection(path)
    print(f"\n  → CNN score for Risk Engine : {result['cnn_score']}")