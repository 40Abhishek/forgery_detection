import cv2
import numpy as np


def copy_move_detection(image_path):

    # Load image
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Image not found")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # ORB feature detector
    orb = cv2.ORB_create(2000)

    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None:
        return {
            "copy_move_score": 0.0,
            "regions": []
        }

    # Match features within same image
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    matches = bf.match(descriptors, descriptors)

    suspicious_matches = []

    for m in matches:

        # Avoid matching same or nearby points
        if abs(m.queryIdx - m.trainIdx) < 10:
            continue

        pt1 = keypoints[m.queryIdx].pt
        pt2 = keypoints[m.trainIdx].pt

        # Only consider matches far apart
        distance = np.linalg.norm(np.array(pt1) - np.array(pt2))

        if distance > 20:
            suspicious_matches.append((pt1, pt2))

            # draw lines between matched regions
            cv2.line(
                image,
                (int(pt1[0]), int(pt1[1])),
                (int(pt2[0]), int(pt2[1])),
                (0,0,255),
                1
            )

    # Compute score
    score = len(suspicious_matches) / max(len(matches), 1)

    # Convert matches to region points
    regions = []

    for (pt1, pt2) in suspicious_matches[:50]:  # limit

        regions.append((int(pt1[0]), int(pt1[1]), 10, 10))
        regions.append((int(pt2[0]), int(pt2[1]), 10, 10))

    # Save output image
    cv2.imwrite("copy_move_matches.png", image)

    return {
        "copy_move_score": float(round(score,3)),
        "regions": regions
    }


if __name__ == "__main__":

    result = copy_move_detection("C:\\Users\\2077a\\OneDrive\\Desktop\\MCA 2024-2026\\SEM 4\\Major\\forgery_detection\\images\\test_img.jpg")

    print(result)