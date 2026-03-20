import cv2
import numpy as np
import os


def error_level_analysis(image_path, quality=90):

    # Load image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Image not found")

    # Temporary recompressed image
    temp_file = "temp_ela.jpg"

    # Recompress image
    cv2.imwrite(temp_file, image, [cv2.IMWRITE_JPEG_QUALITY, quality])

    recompressed = cv2.imread(temp_file)

    # Compute difference
    ela = cv2.absdiff(image, recompressed)

    # Convert to grayscale
    ela_gray = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY)

    # Normalize for visualization
    ela_map = cv2.normalize(
        ela_gray,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    # Tamper score
    ela_score = np.mean(ela_map) / 255

    # Detect suspicious regions
    _, thresh = cv2.threshold(ela_map, 40, 255, cv2.THRESH_BINARY)

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
            cv2.rectangle(image, (x, y), (x+w, y+h), (0,0,255), 2)

    # Save outputs
    cv2.imwrite("ela_map.png", ela_map)
    cv2.imwrite("ela_regions.png", image)

    # Remove temporary file
    os.remove(temp_file)

    return {
        "ela_score": float(round(ela_score,3)),
        "regions": regions
    }


if __name__ == "__main__":

    result = error_level_analysis("C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\test_img.jpg")

    print(result)