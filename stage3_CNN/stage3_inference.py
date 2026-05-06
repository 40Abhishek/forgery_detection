import torch
import torch.nn as nn
import cv2
from torchvision import transforms
import sys
import json
import os

MODEL_PATH = "/opt/render/project/src/model.pth"
IMAGE_SIZE = 128
DEVICE = torch.device("cpu")  # 🔥 force CPU (important for Render)


# ── Model ────────────────────────────────────────────────
def conv_block(in_ch, out_ch):
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(),
        nn.MaxPool2d(2),
    )

def build_model():
    return nn.Sequential(
        conv_block(3, 32),
        conv_block(32, 64),
        conv_block(64, 128),
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


# ── Inference transform ─────────────────────────────────
inference_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])


# ── MAIN FUNCTION (SAFE) ────────────────────────────────
def run_cnn_detection(image_path):
    print("[Stage 3] Loading model...")

    model = build_model().to(DEVICE)

    model.load_state_dict(
        torch.load(MODEL_PATH, map_location=DEVICE)
    )

    model.eval()

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    tensor = inference_transform(image_rgb).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        raw_score = float(model(tensor).item())

    cnn_score = round(raw_score * 100, 2)

    result = {
        "raw_score": round(raw_score, 4),
        "cnn_score": cnn_score,
        "suspicious": cnn_score >= 50.0,
        "detail": f"CNN confidence of forgery = {cnn_score:.2f}%"
    }

    return result


# ── CLI ENTRY (for Node spawn) ──────────────────────────
if __name__ == "__main__":
    image_path = sys.argv[1]

    result = run_cnn_detection(image_path)

    print(json.dumps(result))  # 🔥 IMPORTANT