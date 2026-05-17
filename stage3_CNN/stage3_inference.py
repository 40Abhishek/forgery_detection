import torch
import torch.nn as nn
import numpy as np
import cv2
from torchvision import transforms
import os

IMAGE_SIZE = 128
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Global model variable
_model = None

# ── Model architecture ───────────────────────────────────────
def conv_block(in_ch, out_ch):
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(),
        nn.MaxPool2d(2),
    )

def build_model():
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
    ).to(DEVICE)


# ✅ LAZY LOAD: Only load model when needed
def get_model():
    global _model
    if _model is None:
        print("[Stage 3] Loading CNN model...")
        MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../model.pth")
        try:
            _model = build_model()
            _model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
            _model.eval()
            print(f"[Stage 3] Model loaded from {MODEL_PATH}")
        except FileNotFoundError:
            print("CURRENT DIR:::::", os.getcwd())
            raise FileNotFoundError(f"Model not found: {MODEL_PATH} — run stage3_train.py first")
    return _model


# ── Inference transform ──────────────────────────────────────
inference_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
])


# ── Inference ────────────────────────────────────────────────
def run_cnn_detection(image_path):
    print(f"\n[Stage 3] CNN Tamper Detection")
    print(f"  Input : {image_path}")

    # ✅ Load model only when detection is actually needed
    model = get_model()

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    tensor    = inference_transform(image_rgb).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        raw_score = float(model(tensor).item())

    cnn_score = round(raw_score * 100, 2)
    flag      = "SUSPICIOUS" if cnn_score >= 50.0 else "OK"

    print(f"  [{flag}]  CNN confidence of forgery = {cnn_score:.2f}%")
    print(f"  CNN Score : {cnn_score} / 100")

    return {
        "raw_score" : round(raw_score, 4),
        "cnn_score" : cnn_score,
        "suspicious": cnn_score >= 50.0,
        "detail"    : f"CNN confidence of forgery = {cnn_score:.2f}%"
    }


if __name__ == "__main__":
    result = run_cnn_detection("/tmp/main.png")
    print(f"\n  → CNN score for Risk Engine : {result['cnn_score']}")