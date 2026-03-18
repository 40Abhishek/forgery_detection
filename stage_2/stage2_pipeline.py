import cv2
import numpy as np
import tempfile


#Detector 1 — Error Level Analysis

'''
_OUTPUT_
ela_score
ela_heatmap
ela_regions

'''

def detect_ela(image):

    ela_map = ...
    score = ...

    regions = extract_regions(ela_map)

    return {
        "score":score,
        "heatmap":ela_map,
        "regions":regions
    }



#Detector 2 — Noise Inconsistency

'''
_OUTPUT_
noise_score
noise_map
noise_regions

'''


#Detector 3 — Edge Discontinuity

'''
_METHOD_
Canny edges
Morphological comparison
Edge break detection

_OUTPUT_
edge_score
edge_map
edge_regions
'''

#Detector 4 — Copy-Move Detection

'''
_METHOD_
ORB feature detection
feature matching within image
cluster matches

_OUTPUT_
copy_move_score
match_clusters
regions
'''

#Detector 5 — Illumination / Contrast Anomaly

'''
_METHOD_
large Gaussian blur
compare local brightness

_OUTPUT_
illumination_score
illumination_map
illumination_regions
'''


#Suspicious Region Fusion

all_regions = (
    ela_regions +
    noise_regions +
    edge_regions +
    illumination_regions +
    copy_move_regions
)

merged_regions = merge_overlapping_boxes(all_regions)



#Tamper Indicator Vector

tamper_indicators = {

"ela": 0.38,
"noise": 0.44,
"edge": 0.29,
"copy_move": 0.51,
"illumination": 0.33

}


#Final Stage-2 Output Format

{
 "stage":"tamper_evidence_detection",

 "tamper_indicators":{
   "ela":0.41,
   "noise":0.36,
   "edge":0.28,
   "copy_move":0.52,
   "illumination":0.33
 },

 "suspicious_regions":[
   {"x":120,"y":230,"w":90,"h":40},
   {"x":415,"y":505,"w":110,"h":70}
 ],

 "forensic_maps":[
   "ela_map.png",
   "noise_map.png",
   "edge_map.png"
 ]
}














def detect_ela(image, quality=90):

    # Save temporary JPEG
    _, temp_file = tempfile.mkstemp(suffix=".jpg")
    cv2.imwrite(temp_file, image, [cv2.IMWRITE_JPEG_QUALITY, quality])

    recompressed = cv2.imread(temp_file)

    ela = cv2.absdiff(image, recompressed)
    ela_gray = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY)

    ela_norm = cv2.normalize(ela_gray, None, 0, 255, cv2.NORM_MINMAX)

    score = float(np.mean(ela_norm)) / 255

    return ela_norm, score


def detect_noise(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    median = cv2.medianBlur(gray, 5)

    noise = cv2.absdiff(gray, median)

    score = float(np.std(noise)) / 255

    return noise, score


def detect_edges(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 50, 150)

    kernel = np.ones((3,3), np.uint8)

    dilated = cv2.dilate(edges, kernel)

    diff = cv2.absdiff(edges, dilated)

    score = float(np.mean(diff)) / 255

    return diff, score


def detect_illumination(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (51,51), 0)

    illum = cv2.absdiff(gray, blur)

    score = float(np.mean(illum)) / 255

    return illum, score


def detect_copy_move(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(2000)

    kp, des = orb.detectAndCompute(gray, None)

    if des is None:
        return [], 0.0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    matches = bf.match(des, des)

    suspicious = []

    for m in matches:

        if abs(m.queryIdx - m.trainIdx) > 10:

            pt = kp[m.queryIdx].pt
            suspicious.append((int(pt[0]), int(pt[1])))

    score = len(suspicious) / max(len(matches),1)

    return suspicious, score











#___Detectors___

def detect_ela(image, quality=90):

    # Save temporary JPEG
    _, temp_file = tempfile.mkstemp(suffix=".jpg")
    cv2.imwrite(temp_file, image, [cv2.IMWRITE_JPEG_QUALITY, quality])

    recompressed = cv2.imread(temp_file)

    ela = cv2.absdiff(image, recompressed)
    ela_gray = cv2.cvtColor(ela, cv2.COLOR_BGR2GRAY)

    ela_norm = cv2.normalize(ela_gray, None, 0, 255, cv2.NORM_MINMAX)

    score = float(np.mean(ela_norm)) / 255

    return ela_norm, score


def detect_noise(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    median = cv2.medianBlur(gray, 5)

    noise = cv2.absdiff(gray, median)

    score = float(np.std(noise)) / 255

    return noise, score


def detect_edges(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    edges = cv2.Canny(gray, 50, 150)

    kernel = np.ones((3,3), np.uint8)

    dilated = cv2.dilate(edges, kernel)

    diff = cv2.absdiff(edges, dilated)

    score = float(np.mean(diff)) / 255

    return diff, score


def detect_illumination(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (51,51), 0)

    illum = cv2.absdiff(gray, blur)

    score = float(np.mean(illum)) / 255

    return illum, score


def detect_copy_move(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    orb = cv2.ORB_create(2000)

    kp, des = orb.detectAndCompute(gray, None)

    if des is None:
        return [], 0.0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    matches = bf.match(des, des)

    suspicious = []

    for m in matches:

        if abs(m.queryIdx - m.trainIdx) > 10:

            pt = kp[m.queryIdx].pt
            suspicious.append((int(pt[0]), int(pt[1])))

    score = len(suspicious) / max(len(matches),1)

    return suspicious, score










#___Extract___


def extract_regions(heatmap, threshold=40, min_area=300):

    _, mask = cv2.threshold(heatmap, threshold, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []

    for c in contours:

        x,y,w,h = cv2.boundingRect(c)

        if w*h > min_area:

            regions.append({
                "x":int(x),
                "y":int(y),
                "w":int(w),
                "h":int(h)
            })

    return regions