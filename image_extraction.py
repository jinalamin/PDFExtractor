import fitz 
import pytesseract
from PIL import Image
import io
import os

def extract_images_from_pdf(pdf_path, output_folder):
    doc = fitz.open(pdf_path)
    image_paths = []

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        image_list = page.get_images(full=True)

        for image_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image = Image.open(io.BytesIO(image_bytes))

            img_filename = f"page{page_index+1}_img{image_index+1}.{image_ext}"
            img_path = os.path.join(output_folder, img_filename)
            image.save(img_path)
            image_paths.append(img_path)

    return image_paths

def extract_text_from_images(image_paths):
    extracted_text = ""
    for img_path in image_paths:
        text = pytesseract.image_to_string(Image.open(img_path))
        extracted_text += f"\n--- Text from {img_path} ---\n{text}"
    print(f"Text: {extracted_text}")
    return extracted_text

def main():
    pdf_file = "sample-new-fidelity-acnt-stmt.pdf"
    # pdf_file = "document.pdf"  
    output_dir = "extracted_images"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Extracting images from PDF...")
    images = extract_images_from_pdf(pdf_file, output_dir)

    print("Extracting text from images...")
    final_text = extract_text_from_images(images)

    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(final_text)

if __name__ == "__main__":
    main()