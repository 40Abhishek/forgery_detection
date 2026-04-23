import cv2
import numpy as np


def noise_inconsistency(image_path):

    # Load image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Image not found")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Smooth image (removes noise)
    smooth = cv2.medianBlur(gray, 5)

    # Extract noise
    noise = cv2.absdiff(gray, smooth)

    # Normalize for visualization
    noise_map = cv2.normalize(
        noise,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    # Compute score (noise variation)
    noise_score = np.std(noise_map) / 255

    # Threshold to detect abnormal regions
    _, thresh = cv2.threshold(noise_map, 30, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    regions = []

    for c in contours:

        x, y, w, h = cv2.boundingRect(c)

        if w * h > 200:
            regions.append((x, y, w, h))

            # draw box
            cv2.rectangle(image, (x,y), (x+w, y+h), (0,255,0), 2)

    # Save outputs
    cv2.imwrite("noise_map.png", noise_map)
    cv2.imwrite("noise_regions.png", image)

    return {
        "noise_score": float(round(noise_score,3)),
        "regions": regions
    }


if __name__ == "__main__":

    result = noise_inconsistency("C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\test_img.jpg")

    print(result)