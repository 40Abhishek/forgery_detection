import cv2
import numpy as np


def illumination_anomaly(image_path):

    # Load image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Image not found")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Estimate global illumination
    blur = cv2.GaussianBlur(gray, (51,51), 0)

    # Compute difference
    illum = cv2.absdiff(gray, blur)

    # Normalize for visualization
    illum_map = cv2.normalize(
        illum,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    # Compute score
    illum_score = np.mean(illum_map) / 255

    # Threshold for suspicious regions
    _, thresh = cv2.threshold(illum_map, 30, 255, cv2.THRESH_BINARY)

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

            # draw bounding box
            cv2.rectangle(image, (x,y), (x+w, y+h), (0,255,255), 2)

    # Save outputs
    cv2.imwrite("illumination_map.png", illum_map)
    cv2.imwrite("illumination_regions.png", image)

    return {
        "illumination_score": float(round(illum_score,3)),
        "regions": regions
    }


if __name__ == "__main__":

    result = illumination_anomaly("C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\images\\test_img.jpg")

    print(result)