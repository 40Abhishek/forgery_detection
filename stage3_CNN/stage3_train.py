"""
Stage 3 : CNN Forgery Detector — Training
Run on Google Colab (CPU or GPU)

Dataset:
    CASIA2/Au/   real images     → label 0
    CASIA2/Tp/   tampered images → label 1
"""

import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image


# ── Settings ──────────────────────────────────────────────

AU_FOLDER  = "CASIA2/Au"
TP_FOLDER  = "CASIA2/Tp"
MODEL_PATH = "stage3_model.pth"
IMAGE_SIZE = 128
BATCH_SIZE = 32
EPOCHS     = 25
LR         = 0.001
VAL_SPLIT  = 0.20
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


# ── Load Data ─────────────────────────────────────────────

genuine  = [(os.path.join(AU_FOLDER, f), 0) for f in os.listdir(AU_FOLDER)
            if os.path.splitext(f)[1].lower() in EXTENSIONS]
tampered = [(os.path.join(TP_FOLDER, f), 1) for f in os.listdir(TP_FOLDER)
            if os.path.splitext(f)[1].lower() in EXTENSIONS]
all_data = genuine + tampered

print(f"Genuine: {len(genuine)}  Tampered: {len(tampered)}  Total: {len(all_data)}")

random.shuffle(all_data)
split      = int(len(all_data) * (1 - VAL_SPLIT))
train_data = all_data[:split]
val_data   = all_data[split:]

print(f"Train: {len(train_data)}  Val: {len(val_data)}")


# ── Transforms ────────────────────────────────────────────

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(5, fill=255),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
])

val_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
])


# ── Dataset ───────────────────────────────────────────────

class ForgeryDataset(Dataset):

    def __init__(self, samples, transform):
        self.samples   = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        path, label = self.samples[i]
        image = Image.open(path).convert("RGB")
        return self.transform(image), torch.tensor([label], dtype=torch.float32)


train_loader = DataLoader(ForgeryDataset(train_data, train_transform),
                          batch_size=BATCH_SIZE, shuffle=True)
val_loader   = DataLoader(ForgeryDataset(val_data, val_transform),
                          batch_size=BATCH_SIZE, shuffle=False)


# ── Model ─────────────────────────────────────────────────
# 4 conv blocks — each doubles filters and halves image size
# then 2 fully connected layers for binary classification

def conv_block(in_ch, out_ch):
    return nn.Sequential(
        nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
        nn.BatchNorm2d(out_ch),
        nn.ReLU(),
        nn.MaxPool2d(2),
    )

model = nn.Sequential(
    conv_block(3,   32),    # 128 → 64
    conv_block(32,  64),    # 64  → 32
    conv_block(64,  128),   # 32  → 16
    conv_block(128, 256),   # 16  → 8
    nn.Flatten(),
    nn.Linear(256 * 8 * 8, 512),
    nn.ReLU(),
    nn.Dropout(0.5),
    nn.Linear(512, 1),
    nn.Sigmoid(),
).to(DEVICE)

print(f"\nDevice: {DEVICE}")
print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")


# ── Training ──────────────────────────────────────────────

loss_fn   = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=LR)
best_val_acc     = 0.0
no_improve_count = 0

print(f"\nStarting training — {EPOCHS} epochs\n")

for epoch in range(1, EPOCHS + 1):

    # Train
    model.train()
    train_correct = 0
    for batch_num, (images, labels) in enumerate(train_loader, 1):
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss    = loss_fn(outputs, labels)
        loss.backward()
        optimizer.step()
        train_correct += ((outputs >= 0.5).float() == labels).sum().item()

        # Print batch progress every 10 batches
        if batch_num % 10 == 0:
            print(f"  Epoch {epoch}/{EPOCHS} — batch {batch_num}/{len(train_loader)}", end="\r")

    train_acc = train_correct / len(train_loader.dataset)

    # Validate
    model.eval()
    val_correct  = 0
    val_loss_sum = 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs      = model(images)
            val_loss_sum += loss_fn(outputs, labels).item() * images.size(0)
            val_correct  += ((outputs >= 0.5).float() == labels).sum().item()

    val_acc  = val_correct  / len(val_loader.dataset)
    val_loss = val_loss_sum / len(val_loader.dataset)

    print(f"Epoch {epoch:02d}/{EPOCHS} | Train: {train_acc*100:.1f}% | Val: {val_acc*100:.1f}% | Val Loss: {val_loss:.4f}")

    # Save best model
    if val_acc > best_val_acc:
        best_val_acc     = val_acc
        no_improve_count = 0
        torch.save(model.state_dict(), MODEL_PATH)
        print(f"  → Best model saved ({val_acc*100:.1f}%)")
    else:
        no_improve_count += 1

    # Early stop
    if no_improve_count >= 5:
        print(f"Early stopping — no improvement for 5 epochs")
        break

print(f"\nDone. Best val accuracy: {best_val_acc*100:.1f}%")
print(f"Model saved: {MODEL_PATH}")