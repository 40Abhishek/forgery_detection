import cv2
import numpy as np


def edge_discontinuity(image_path):

    # Load image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Image not found")

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect edges
    edges = cv2.Canny(gray, 50, 150)

    # Dilate edges (simulate continuity)
    kernel = np.ones((3,3), np.uint8)
    dilated = cv2.dilate(edges, kernel)

    # Find discontinuities
    discontinuity = cv2.absdiff(edges, dilated)

    # Normalize for visualization
    edge_map = cv2.normalize(
        discontinuity,
        None,
        0,
        255,
        cv2.NORM_MINMAX
    )

    # Compute score
    edge_score = np.mean(edge_map) / 255

    # Threshold to find suspicious regions
    _, thresh = cv2.threshold(edge_map, 25, 255, cv2.THRESH_BINARY)

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
            cv2.rectangle(image, (x,y), (x+w, y+h), (255,0,0), 2)

    # Save outputs
    cv2.imwrite("edge_map.png", edge_map)
    cv2.imwrite("edge_regions.png", image)

    return {
        "edge_score": float(round(edge_score,3)),
        "regions": regions
    }


if __name__ == "__main__":

    result = edge_discontinuity("C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\images\\test_img.jpg")

    print(result)