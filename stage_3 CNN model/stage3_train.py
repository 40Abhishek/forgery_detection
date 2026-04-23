"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 3 : CNN Tamper Detection — TRAINING
  Library : PyTorch
=============================================================
  Custom CNN architecture (built from scratch):
      Conv Block 1 : Conv → BatchNorm → ReLU → MaxPool
      Conv Block 2 : Conv → BatchNorm → ReLU → MaxPool
      Conv Block 3 : Conv → BatchNorm → ReLU → MaxPool
      Conv Block 4 : Conv → BatchNorm → ReLU → MaxPool
      Fully Connected 1 : Linear → ReLU → Dropout
      Fully Connected 2 : Linear → Sigmoid (output)

  Input  : CASIA dataset (Au/ = genuine, Tp/ = forged)
  Output : stage3_model.pth — saved trained model weights

  Run this ONCE. After training use stage3_inference.py.

  Dataset folder structure:
      casia_dataset/
          Au/    ← original untampered images (label 0)
          Tp/    ← tampered / forged images   (label 1)
      Casia2 Ground Truth/ is ignored entirely.

  Usage:
      python stage3_train.py
=============================================================
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import numpy as np


# ─────────────────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────────────────

DATASET_PATH = "casia_dataset"   # folder with Au/ and Tp/ subfolders
MODEL_SAVE   = "stage3_model.pth"
IMAGE_SIZE   = 128               # resize all images to 128×128
BATCH_SIZE   = 32
EPOCHS       = 25
LEARNING_RATE = 0.001

# Use GPU if available, otherwise CPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ─────────────────────────────────────────────────────────
#  STEP 1 : DATASET CLASS
# ─────────────────────────────────────────────────────────

class CASIADataset(Dataset):
    """
    Custom PyTorch Dataset for loading CASIA images.

    What it does:
        - Walks through Au/ and Tp/ folders
        - Assigns label 0 to genuine (Au) and 1 to forged (Tp)
        - Applies transforms (resize, normalize) on each image load
        - Accepts JPG, JPEG, and PNG files

    PyTorch Dataset requires two methods:
        __len__  : returns total number of images
        __getitem__ : returns one (image_tensor, label) pair by index
    """

    def __init__(self, dataset_path, transform=None):
        self.samples   = []   # list of (image_path, label) tuples
        self.transform = transform

        categories = {"Au": 0, "Tp": 1}

        for category, label in categories.items():
            folder = os.path.join(dataset_path, category)

            if not os.path.exists(folder):
                raise FileNotFoundError(
                    f"Folder not found: {folder}\n"
                    f"Expected: {dataset_path}/Au/  and  {dataset_path}/Tp/"
                )

            files = os.listdir(folder)
            print(f"  Loading {category}: {len(files)} files...")

            for filename in files:
                if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                path = os.path.join(folder, filename)
                self.samples.append((path, label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, torch.tensor(label, dtype=torch.float32)


# ─────────────────────────────────────────────────────────
#  STEP 2 : TRANSFORMS
# ─────────────────────────────────────────────────────────

def get_transforms():
    """
    What it does:
        Prepares image transformations applied to every image.

        Training transforms include augmentation:
          - Random horizontal flip  : makes model robust to mirrored docs
          - Random rotation (±10°)  : handles slightly tilted scans
          - Resize to 128×128       : uniform input size for the CNN
          - ToTensor                : converts PIL image to PyTorch tensor
          - Normalize               : scales pixel values to mean=0.5, std=0.5
                                      (maps 0-1 range to -1 to +1)

        Validation transforms skip augmentation — we want clean evaluation.
    """

    train_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5],
                             std= [0.5, 0.5, 0.5])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5],
                             std= [0.5, 0.5, 0.5])
    ])

    return train_transform, val_transform


# ─────────────────────────────────────────────────────────
#  STEP 3 : CNN MODEL
# ─────────────────────────────────────────────────────────

class ForgeryDetectorCNN(nn.Module):
    """
    Custom CNN built from scratch for binary forgery classification.

    Architecture:
        Conv Block 1 : 3  → 32  filters, 3×3 kernel → BN → ReLU → MaxPool
        Conv Block 2 : 32 → 64  filters, 3×3 kernel → BN → ReLU → MaxPool
        Conv Block 3 : 64 → 128 filters, 3×3 kernel → BN → ReLU → MaxPool
        Conv Block 4 : 128→ 256 filters, 3×3 kernel → BN → ReLU → MaxPool
        Flatten
        FC1          : 256×8×8 → 512 → ReLU → Dropout(0.5)
        FC2          : 512 → 1 → Sigmoid

    Why these choices:
        - Each conv block doubles the filters — learns increasingly
          complex features (edges → textures → patterns → artifacts)
        - BatchNorm after each conv — stabilizes training from scratch
        - MaxPool halves spatial size each block — 128→64→32→16→8
        - Dropout 0.5 — prevents overfitting on CASIA training set
        - Sigmoid output — gives probability 0.0 (genuine) to 1.0 (forged)
    """

    def __init__(self):
        super(ForgeryDetectorCNN, self).__init__()

        # Convolutional blocks
        self.conv_block1 = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2)          # 128 → 64
        )

        self.conv_block2 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2)          # 64 → 32
        )

        self.conv_block3 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(2)          # 32 → 16
        )

        self.conv_block4 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(2)          # 16 → 8
        )

        # Fully connected layers
        # After 4 maxpools: 128 → 8, so feature map is 256 × 8 × 8
        self.fc = nn.Sequential(
            nn.Linear(256 * 8 * 8, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 1),
            nn.Sigmoid()             # output: 0.0 = genuine, 1.0 = forged
        )

    def forward(self, x):
        x = self.conv_block1(x)
        x = self.conv_block2(x)
        x = self.conv_block3(x)
        x = self.conv_block4(x)
        x = x.view(x.size(0), -1)   # flatten: (batch, 256, 8, 8) → (batch, 16384)
        x = self.fc(x)
        return x


# ─────────────────────────────────────────────────────────
#  STEP 4 : TRAIN ONE EPOCH
# ─────────────────────────────────────────────────────────

def train_epoch(model, loader, optimizer, criterion):
    """Runs one full pass over the training data."""

    model.train()
    total_loss    = 0.0
    total_correct = 0

    for images, labels in loader:
        images = images.to(DEVICE)
        labels = labels.to(DEVICE).unsqueeze(1)   # shape (batch,) → (batch, 1)

        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss    += loss.item()
        predictions    = (outputs >= 0.5).float()
        total_correct += (predictions == labels).sum().item()

    avg_loss = total_loss    / len(loader)
    accuracy = total_correct / len(loader.dataset)
    return round(avg_loss, 4), round(accuracy * 100, 2)


# ─────────────────────────────────────────────────────────
#  STEP 5 : VALIDATE ONE EPOCH
# ─────────────────────────────────────────────────────────

def validate_epoch(model, loader, criterion):
    """Runs one full pass over the validation data — no gradient updates."""

    model.eval()
    total_loss    = 0.0
    total_correct = 0

    with torch.no_grad():   # no gradient computation during validation
        for images, labels in loader:
            images = images.to(DEVICE)
            labels = labels.to(DEVICE).unsqueeze(1)

            outputs = model(images)
            loss    = criterion(outputs, labels)

            total_loss    += loss.item()
            predictions    = (outputs >= 0.5).float()
            total_correct += (predictions == labels).sum().item()

    avg_loss = total_loss    / len(loader)
    accuracy = total_correct / len(loader.dataset)
    return round(avg_loss, 4), round(accuracy * 100, 2)


# ─────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  Stage 3 : CNN Training (PyTorch — from scratch)")
    print(f"  Device  : {DEVICE}")
    print("=" * 55)

    # Transforms
    train_transform, val_transform = get_transforms()

    # Load full dataset
    print("\n[1/4] Loading dataset...")
    full_dataset = CASIADataset(DATASET_PATH, transform=train_transform)
    total        = len(full_dataset)
    print(f"  Total images : {total}")

    # 80/20 train/val split
    train_size = int(0.8 * total)
    val_size   = total - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        full_dataset, [train_size, val_size]
    )

    # Apply val transform to validation set
    val_dataset.dataset.transform = val_transform

    print(f"  Train : {train_size}   Val : {val_size}")

    # DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)

    # Build model
    print("\n[2/4] Building model...")
    model     = ForgeryDetectorCNN().to(DEVICE)
    criterion = nn.BCELoss()                        # Binary Cross Entropy
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # Learning rate scheduler — reduces LR if val loss plateaus
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", patience=3, factor=0.5
    )

    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Total parameters : {total_params:,}")

    # Training loop
    print(f"\n[3/4] Training for up to {EPOCHS} epochs...")
    print("-" * 55)

    best_val_accuracy = 0.0
    patience_counter  = 0
    early_stop_patience = 5   # stop if no improvement for 5 epochs

    for epoch in range(1, EPOCHS + 1):
        train_loss, train_acc = train_epoch(model, train_loader, optimizer, criterion)
        val_loss,   val_acc   = validate_epoch(model, val_loader, criterion)

        scheduler.step(val_loss)

        print(
            f"  Epoch {epoch:02d}/{EPOCHS} | "
            f"Train Loss: {train_loss:.4f}  Acc: {train_acc:.2f}% | "
            f"Val Loss: {val_loss:.4f}  Acc: {val_acc:.2f}%"
        )

        # Save best model
        if val_acc > best_val_accuracy:
            best_val_accuracy = val_acc
            torch.save(model.state_dict(), MODEL_SAVE)
            print(f"  ✓ Best model saved (val_acc={val_acc:.2f}%)")
            patience_counter = 0
        else:
            patience_counter += 1

        # Early stopping
        if patience_counter >= early_stop_patience:
            print(f"\n  Early stopping at epoch {epoch} — no improvement for {early_stop_patience} epochs")
            break

    # Final summary
    print("-" * 55)
    print(f"\n[4/4] Training Complete")
    print(f"  Best Validation Accuracy : {best_val_accuracy:.2f}%")
    print(f"  Model saved to           : {MODEL_SAVE}")

    if best_val_accuracy >= 85:
        print("  Model quality            : GOOD — ready for inference")
    elif best_val_accuracy >= 70:
        print("  Model quality            : ACCEPTABLE — consider more epochs")
    else:
        print("  Model quality            : POOR — check dataset and settings")

    print(f"\n  Next step : run stage3_inference.py")
