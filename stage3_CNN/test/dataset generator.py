import cv2
import numpy as np
import os
import random

# ================= CONFIG =================
INPUT_DIR = "dataset/clean"
GEN_DIR = "dataset/generated"
MASK_DIR = "dataset/masks"
PATCH_CLEAN_DIR = "dataset/patches/clean"
PATCH_TAMPER_DIR = "dataset/patches/tampered"

PATCH_SIZE = 128
STRIDE = 64
TAMPERS_PER_IMAGE = 4

# ==========================================

# Create folders
for d in [GEN_DIR, MASK_DIR, PATCH_CLEAN_DIR, PATCH_TAMPER_DIR]:
    os.makedirs(d, exist_ok=True)


def random_region(h, w):
    x1 = random.randint(0, w - 150)
    y1 = random.randint(0, h - 100)
    x2 = x1 + random.randint(50, 150)
    y2 = y1 + random.randint(30, 100)
    return x1, y1, x2, y2


def tamper_image(img):
    h, w, _ = img.shape
    tampered = img.copy()
    mask = np.zeros((h, w), dtype=np.uint8)

    x1, y1, x2, y2 = random_region(h, w)

    method = random.choice(["text", "blur", "copy", "compress"])

    if method == "text":
        cv2.rectangle(tampered, (x1, y1), (x2, y2), (255, 255, 255), -1)
        text = str(random.randint(1000, 9999))
        cv2.putText(tampered, text, (x1 + 5, y2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

    elif method == "blur":
        blurred = cv2.GaussianBlur(tampered, (15, 15), 0)
        tampered[y1:y2, x1:x2] = blurred[y1:y2, x1:x2]

    elif method == "copy":
        patch = tampered[y1:y2, x1:x2].copy()
        nx = random.randint(0, w - (x2 - x1))
        ny = random.randint(0, h - (y2 - y1))
        tampered[ny:ny + (y2 - y1), nx:nx + (x2 - x1)] = patch
        x1, y1, x2, y2 = nx, ny, nx + (x2 - x1), ny + (y2 - y1)

    elif method == "compress":
        temp_path = "temp.jpg"
        cv2.imwrite(temp_path, tampered, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
        low = cv2.imread(temp_path)
        tampered[y1:y2, x1:x2] = low[y1:y2, x1:x2]
        os.remove(temp_path)

    # mark tampered region
    mask[y1:y2, x1:x2] = 255

    return tampered, mask


def extract_patches(img, mask, base_name):
    h, w = mask.shape
    count = 0

    for y in range(0, h - PATCH_SIZE + 1, STRIDE):
        for x in range(0, w - PATCH_SIZE + 1, STRIDE):

            patch = img[y:y + PATCH_SIZE, x:x + PATCH_SIZE]
            patch_mask = mask[y:y + PATCH_SIZE, x:x + PATCH_SIZE]

            tamper_ratio = np.sum(patch_mask > 0) / (PATCH_SIZE * PATCH_SIZE)

            if tamper_ratio > 0.2:
                label = "tampered"
                save_dir = PATCH_TAMPER_DIR
            else:
                label = "clean"
                save_dir = PATCH_CLEAN_DIR

            filename = f"{base_name}_{count}.jpg"
            cv2.imwrite(os.path.join(save_dir, filename), patch)

            count += 1


def process():
    files = os.listdir(INPUT_DIR)

    for file in files:
        path = os.path.join(INPUT_DIR, file)
        img = cv2.imread(path)

        if img is None:
            print(f"Skipping {file}")
            continue

        img = cv2.resize(img, (512, 512))

        base = os.path.splitext(file)[0]

        # CLEAN IMAGE PATCHES
        zero_mask = np.zeros((512, 512), dtype=np.uint8)
        extract_patches(img, zero_mask, base + "_clean")

        # TAMPERED VERSIONS
        for i in range(TAMPERS_PER_IMAGE):
            tampered, mask = tamper_image(img)

            img_name = f"{base}_tampered_{i}.jpg"
            mask_name = f"{base}_mask_{i}.png"

            cv2.imwrite(os.path.join(GEN_DIR, img_name), tampered)
            cv2.imwrite(os.path.join(MASK_DIR, mask_name), mask)

            extract_patches(tampered, mask, base + f"_t{i}")


if __name__ == "__main__":
    process()
    print("✅ Dataset generation complete.")