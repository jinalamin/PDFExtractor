import pdfplumber

def extract_from_machine_pdf(pdf_path):
    extracted_text = ""
    extracted_tables = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
            tables = page.extract_tables()
            if tables:
                extracted_tables.extend(tables)
    return extracted_text.strip(), extracted_tables


def extract_pdf_contents(pdf_path):
    print(f"📄 Reading PDF: {pdf_path}")
    text, tables = extract_from_machine_pdf(pdf_path)

    print("\n--- Extracted Text ---\n")
    print(text)

    print("\n--- Extracted Tables ---")
    for i, table in enumerate(tables):
        print(f"\nTable {i + 1}:")
        for row in table:
            print(row)


if __name__ == "__main__":
    #pdf_path = "sample_statement.pdf"
    pdf_path = "sample-new-fidelity-acnt-stmt.pdf"
    extract_pdf_contents(pdf_path)
