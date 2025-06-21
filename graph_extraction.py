import cv2
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import re

# OPTIONAL: Set tesseract path if needed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def convert_pdf_to_images(pdf_path):
    return convert_from_path(pdf_path, dpi=300, poppler_path=r"C:\Users\rmall\OneDrive - stradit.com\Documents\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin")


def extract_bar_data_with_ocr(image):
# Convert image to OpenCV format
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 180, 255, cv2.THRESH_BINARY_INV)

    # Detect contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bars = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 100 and h > 20 and h < 300: # Heuristic to detect bars only
            bars.append((x, y, w, h))
    # Sort by x-position (left to right)
    bars = sorted(bars, key=lambda b: b[0])
    # OCR on the whole image
    ocr_text = pytesseract.image_to_string(image_cv)
    print("OCR Extracted Text (Sanitized):")
    print(ocr_text)

    # Try to get all percent values from OCR

    percent_values = re.findall(r'(\d{1,3}\.?\d*)\s*%', ocr_text)
    percent_values = [float(p) for p in percent_values if float(p) <= 100]


# Map heights to OCR percentages if counts match

    print("\nDetected Bars (x, height) and estimated % if matched with OCR:")
    for i, (x, y, w, h) in enumerate(bars):
        pct = percent_values[i] if i < len(percent_values) else "?"
        print(f"Bar {i+1}: x={x}, height={h} --> ~ {pct}%")
    return bars


def main():
    # pdf_path = r"C:\Users\rmall\OneDrive - stradit.com\Documents\Downloads\Item Analysis Graph Report.pdf"
    pdf_path = "sample-new-fidelity-acnt-stmt.pdf"
    images = convert_pdf_to_images(pdf_path)
    for i, image in enumerate(images):
        print(f"\n===== Page {i+1} =====")
        extract_bar_data_with_ocr(image)

if __name__ == "__main__":
    main()