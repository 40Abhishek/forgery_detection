"""
=============================================================
  DOCUMENT FORGERY DETECTION SYSTEM
  Stage 3 : CNN Tamper Detection  —  TRAINING
  Library : TensorFlow / Keras
=============================================================
  What this script does:
    - Loads the CASIA dataset (genuine + forged images)
    - Fine-tunes a pretrained MobileNetV2 on our data
    - Saves the trained model as stage3_model.keras

  Run this ONCE to train. After this, use stage3_inference.py
  for every document check.

  Expected dataset folder structure:
    casia_dataset/
        genuine/   ← real, untampered document images
        forged/    ← tampered / forged document images

  Usage:
    python stage3_train.py
=============================================================
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2


# ─────────────────────────────────────────────────────────
#  SETTINGS  — change these if needed
# ─────────────────────────────────────────────────────────

DATASET_PATH  = "casia_dataset"   # folder containing Au/ and Tp/ subfolders
MODEL_SAVE    = "stage3_model.keras"
IMAGE_SIZE    = (224, 224)        # MobileNetV2 expects 224×224
BATCH_SIZE    = 32
EPOCHS        = 10
LEARNING_RATE = 0.0001


# ─────────────────────────────────────────────────────────
#  STEP 1 : LOAD DATASET
# ─────────────────────────────────────────────────────────

def load_dataset():
    """
    Walks through the dataset folder and loads all images.

    Labels:
        genuine → 0
        forged  → 1

    Returns:
        images : numpy array of shape (N, 224, 224, 3)
        labels : numpy array of shape (N,)  — 0 or 1
    """

    images = []
    labels = []

    # Au = authentic/genuine → label 0
    # Tp = tampered/forged   → label 1
    categories = {"Au": 0, "Tp": 1}

    for category, label in categories.items():
        folder = os.path.join(DATASET_PATH, category)

        if not os.path.exists(folder):
            raise FileNotFoundError(
                f"Folder not found: {folder}\n"
                f"Make sure your dataset is organized as:\n"
                f"  {DATASET_PATH}/Au/  and  {DATASET_PATH}/Tp/"
            )

        files = os.listdir(folder)
        print(f"  Loading {category}: {len(files)} images...")

        for filename in files:
            # Accept both JPG and PNG — training data can be either format
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            path  = os.path.join(folder, filename)
            image = tf.keras.utils.load_img(path, target_size=IMAGE_SIZE)
            image = tf.keras.utils.img_to_array(image)

            images.append(image)
            labels.append(label)

    images = np.array(images, dtype=np.float32)
    labels = np.array(labels, dtype=np.float32)

    print(f"\n  Total images loaded : {len(images)}")
    print(f"  Genuine             : {int(np.sum(labels == 0))}")
    print(f"  Forged              : {int(np.sum(labels == 1))}")

    return images, labels


# ─────────────────────────────────────────────────────────
#  STEP 2 : PREPROCESS
# ─────────────────────────────────────────────────────────

def preprocess(images, labels):
    """
    - Normalizes pixel values from 0-255 to -1 to +1
      (MobileNetV2 was trained with this scale, so we match it)
    - Shuffles the data randomly
    - Splits into 80% training, 20% validation
    """

    # MobileNetV2 preprocessing: scale pixels to [-1, +1]
    images = tf.keras.applications.mobilenet_v2.preprocess_input(images)

    # Shuffle
    indices = np.random.permutation(len(images))
    images  = images[indices]
    labels  = labels[indices]

    # 80/20 split
    split        = int(0.8 * len(images))
    train_images = images[:split]
    train_labels = labels[:split]
    val_images   = images[split:]
    val_labels   = labels[split:]

    print(f"\n  Training samples   : {len(train_images)}")
    print(f"  Validation samples : {len(val_images)}")

    return train_images, train_labels, val_images, val_labels


# ─────────────────────────────────────────────────────────
#  STEP 3 : BUILD MODEL
# ─────────────────────────────────────────────────────────

def build_model():
    """
    How it works:
        MobileNetV2 is a CNN pretrained on ImageNet (1.2 million images).
        It already knows how to detect textures, edges, patterns — exactly
        what we need for forgery detection.

        We freeze its layers (don't retrain them) and add our own small
        classifier on top that learns to say "genuine" or "forged".

        This is called Transfer Learning — we borrow a powerful model
        and teach it our specific task with much less data and time.

    Architecture:
        MobileNetV2 base (frozen)
              ↓
        GlobalAveragePooling  — squashes spatial features to a vector
              ↓
        Dropout 0.3           — randomly drops neurons to prevent overfitting
              ↓
        Dense 128, ReLU       — our custom learning layer
              ↓
        Dropout 0.2
              ↓
        Dense 1, Sigmoid      — output: 0.0 = genuine, 1.0 = forged
    """

    # Load MobileNetV2 without its top classification layer
    base_model = MobileNetV2(
        input_shape = IMAGE_SIZE + (3,),
        include_top = False,             # remove ImageNet classifier
        weights     = "imagenet"         # keep pretrained weights
    )

    # Freeze all base layers — we don't want to overwrite what it already knows
    base_model.trainable = False

    # Build our classifier on top
    model = models.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dropout(0.3),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.2),
        layers.Dense(1, activation="sigmoid")   # 0 = genuine, 1 = forged
    ])

    model.compile(
        optimizer = tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss      = "binary_crossentropy",  # binary because we have 2 classes
        metrics   = ["accuracy"]
    )

    print("\n  Model built successfully.")
    print(f"  Base model layers : {len(base_model.layers)} (frozen)")
    print(f"  Total parameters  : {model.count_params():,}")

    return model


# ─────────────────────────────────────────────────────────
#  STEP 4 : TRAIN
# ─────────────────────────────────────────────────────────

def train_model(model, train_images, train_labels, val_images, val_labels):
    """
    Trains the model on our dataset.

    Callbacks used:
        EarlyStopping  — stops training if validation accuracy stops improving
                         (prevents wasting time and overfitting)
        ModelCheckpoint — saves the best version of the model during training
                         (not just the final one, which may be slightly worse)
    """

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor  = "val_accuracy",
        patience = 3,              # stop if no improvement for 3 epochs
        restore_best_weights = True
    )

    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        filepath          = MODEL_SAVE,
        monitor           = "val_accuracy",
        save_best_only    = True,
        verbose           = 1
    )

    print(f"\n  Starting training for up to {EPOCHS} epochs...")
    print(f"  (EarlyStopping will halt early if accuracy plateaus)\n")

    history = model.fit(
        train_images, train_labels,
        validation_data = (val_images, val_labels),
        epochs          = EPOCHS,
        batch_size      = BATCH_SIZE,
        callbacks       = [early_stop, checkpoint]
    )

    return history


# ─────────────────────────────────────────────────────────
#  STEP 5 : EVALUATE
# ─────────────────────────────────────────────────────────

def evaluate_model(model, val_images, val_labels):
    """
    Runs the model on validation data and prints final accuracy.
    This tells us how well the model generalises to images it has never seen.
    """

    loss, accuracy = model.evaluate(val_images, val_labels, verbose=0)
    print(f"\n  Validation Accuracy : {accuracy * 100:.2f}%")
    print(f"  Validation Loss     : {loss:.4f}")

    if accuracy >= 0.85:
        print("  Model quality       : GOOD — ready for inference")
    elif accuracy >= 0.70:
        print("  Model quality       : ACCEPTABLE — consider more epochs or data")
    else:
        print("  Model quality       : POOR — check dataset quality and balance")


# ─────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  Stage 3 : CNN Training")
    print("=" * 55)

    # Load and prepare data
    print("\n[1/4] Loading dataset...")
    images, labels = load_dataset()

    print("\n[2/4] Preprocessing...")
    train_images, train_labels, val_images, val_labels = preprocess(images, labels)

    # Build and train model
    print("\n[3/4] Building model...")
    model = build_model()

    print("\n[4/4] Training...")
    train_model(model, train_images, train_labels, val_images, val_labels)

    # Final evaluation
    print("\n" + "=" * 55)
    print("  Training Complete")
    print("=" * 55)
    evaluate_model(model, val_images, val_labels)
    print(f"\n  Model saved to : {MODEL_SAVE}")
    print(f"  Next step      : run stage3_inference.py to use this model")

# Dataset folder structure expected:
#   casia_dataset/
#       Au/    ← original untampered images  (genuine, label 0)
#       Tp/    ← tampered/forged images      (forged,  label 1)
#   Casia2 Ground Truth/ is ignored — not needed for classification