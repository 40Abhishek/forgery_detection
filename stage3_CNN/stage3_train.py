import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image


# ── Settings ──────────────────────────────────────────────

AU_FOLDER  = "/kaggle/input/casia-20-image-tampering-detection-dataset/CASIA2/Au"
TP_FOLDER  = "/kaggle/input/casia-20-image-tampering-detection-dataset/CASIA2/Tp"
MODEL_PATH = "/content/stage3_model.pth"
IMAGE_SIZE = 128
BATCH_SIZE = 32
EPOCHS     = 75
LR         = 0.001
VAL_SPLIT  = 0.20
DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


# ── Dataset Class ─────────────────────────────────────────

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


# ── Functions ─────────────────────────────────────────────

def load_and_split():
    """Loads image paths, shuffles, splits 80/20."""
    genuine  = [(os.path.join(AU_FOLDER, f), 0) for f in os.listdir(AU_FOLDER)
                if os.path.splitext(f)[1].lower() in EXTENSIONS]
    tampered = [(os.path.join(TP_FOLDER, f), 1) for f in os.listdir(TP_FOLDER)
                if os.path.splitext(f)[1].lower() in EXTENSIONS]
    all_data = genuine + tampered

    print(f"Genuine: {len(genuine)}  Tampered: {len(tampered)}  Total: {len(all_data)}")

    random.shuffle(all_data)
    split = int(len(all_data) * (1 - VAL_SPLIT))
    return all_data[:split], all_data[split:]


def get_transforms():
    """Train gets augmentation, val gets only resize + normalize."""
    train = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10, fill=255),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])
    val = transforms.Compose([
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])
    return train, val


def build_model():
    """4 conv blocks + 3 FC layers."""
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
    ).to(DEVICE)


def train_one_epoch(model, loader, loss_fn, optimizer, epoch):
    """One pass over training data with batch progress."""
    model.train()
    correct = 0
    for batch_num, (images, labels) in enumerate(loader, 1):
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss    = loss_fn(outputs, labels)
        loss.backward()
        optimizer.step()
        correct += ((outputs >= 0.5).float() == labels).sum().item()
        if batch_num % 10 == 0:
            print(f"  Epoch {epoch}/{EPOCHS} — batch {batch_num}/{len(loader)}", end="\r")
    return correct / len(loader.dataset)


def validate(model, loader, loss_fn):
    """One pass over validation data, no gradient updates."""
    model.eval()
    correct, loss_sum = 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs   = model(images)
            loss_sum += loss_fn(outputs, labels).item() * images.size(0)
            correct  += ((outputs >= 0.5).float() == labels).sum().item()
    return correct / len(loader.dataset), loss_sum / len(loader.dataset)


# ── Main ──────────────────────────────────────────────────

if __name__ == "__main__":

    print(f"Device: {DEVICE}\n")

    train_data, val_data           = load_and_split()
    train_transform, val_transform = get_transforms()

    train_loader = DataLoader(ForgeryDataset(train_data, train_transform),
                              batch_size=BATCH_SIZE, shuffle=True)
    val_loader   = DataLoader(ForgeryDataset(val_data, val_transform),
                              batch_size=BATCH_SIZE, shuffle=False)

    model     = build_model()
    loss_fn   = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", patience=3, factor=0.5)  # ADDED: reduces LR by half if val_acc doesn't improve for 3 epochs

    print(f"Parameters : {sum(p.numel() for p in model.parameters()):,}")
    print(f"Training   : {len(train_data)}  Val: {len(val_data)}")
    print(f"\nStarting {EPOCHS} epochs...\n")

    best_val_acc     = 0.0
    no_improve_count = 0

    #added model more training
    model.load_state_dict(torch.load(MODEL_PATH))  # add this before the epoch loop

    for epoch in range(1, EPOCHS + 1):
        train_acc         = train_one_epoch(model, train_loader, loss_fn, optimizer, epoch)
        val_acc, val_loss = validate(model, val_loader, loss_fn)
        scheduler.step(val_acc)                                        # ADDED: step scheduler with val accuracy
        current_lr = optimizer.param_groups[0]["lr"]                   # ADDED: read current LR

        print(f"Epoch {epoch:02d}/{EPOCHS} | Train: {train_acc*100:.1f}% | Val: {val_acc*100:.1f}% | Val Loss: {val_loss:.4f} | LR: {current_lr}")  # CHANGED: added LR to print

        if val_acc > best_val_acc:
            best_val_acc     = val_acc
            no_improve_count = 0
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"  → Best model saved ({val_acc*100:.1f}%)")
        else:
            no_improve_count += 1

        # if no_improve_count >= 5:
        #     print(f"Early stopping at epoch {epoch}")
        #     break

    print(f"\nDone. Best val accuracy: {best_val_acc*100:.1f}%")
    print(f"Model saved: {MODEL_PATH}")