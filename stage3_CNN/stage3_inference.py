import torch
import torch.nn as nn
import numpy as np
import cv2
from torchvision import transforms

MODEL_PATH = "model.pth"
IMAGE_SIZE = 128
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

path = "local datastore\main.png"

# ─────────────────────────────────────────────────────────
#  CNN ARCHITECTURE
#  Must be defined identically to stage3_train.py
#  PyTorch saves only the weights, not the architecture —
#  so we must rebuild the same structure to load into.
# ─────────────────────────────────────────────────────────

class ForgeryDetectorCNN(nn.Module):

    def __init__(self):
        super(ForgeryDetectorCNN, self).__init__()

        self.conv_block1 = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.conv_block2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.conv_block3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.conv_block4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        self.fc = nn.Sequential(
            nn.Linear(256 * 8 * 8, 1024),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        x = self.conv_block3(x)
        x = self.conv_block4(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        return x


# ─────────────────────────────────────────────────────────
#  LOAD MODEL ONCE AT IMPORT
#  Expensive operation — done once when pipeline starts,
#  not on every document check.
# ─────────────────────────────────────────────────────────

print("[Stage 3] Loading CNN model...")
try:
    model = ForgeryDetectorCNN().to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE), strict=True)
    model.eval()   # set to evaluation mode — disables dropout
    print(f"[Stage 3] Model loaded from {MODEL_PATH}")
except FileNotFoundError:
    raise FileNotFoundError(
        f"Model file not found: {MODEL_PATH}\n"
        f"Run stage3_train.py first to generate the model."
    )


# ─────────────────────────────────────────────────────────
#  INFERENCE TRANSFORM
#  Same as validation transform in training —
#  no augmentation, just resize and normalize.
# ─────────────────────────────────────────────────────────

inference_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5],
                         std= [0.5, 0.5, 0.5])
])


# ─────────────────────────────────────────────────────────
#  INFERENCE
# ─────────────────────────────────────────────────────────

def run_cnn_detection(image_path):
    """
    What it does:
        Loads the document PNG, applies the same preprocessing
        used during training, passes it through the trained CNN,
        and returns a forgery probability score.

        Model output is a single sigmoid value:
            0.0 = model is confident this is GENUINE
            1.0 = model is confident this is FORGED

        We scale to 0-100 to match all other stage scores.

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

    print(f"\n[Stage 3] CNN Tamper Detection")
    print(f"  Input : {image_path}")
    print("-" * 50)

    # Load image with OpenCV — already PNG from Stage 1
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    # Convert BGR → RGB (OpenCV loads BGR, PyTorch expects RGB)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Apply transforms: resize → tensor → normalize
    tensor = inference_transform(image_rgb)

    # Add batch dimension: (3, 128, 128) → (1, 3, 128, 128)
    tensor = tensor.unsqueeze(0).to(DEVICE)

    # Run through model — no gradient needed for inference
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
#  QUICK TEST
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_cnn_detection(path)
    print(f"\n  → CNN score for Risk Engine : {result['cnn_score']}")
