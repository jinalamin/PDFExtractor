import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")  # Fetch API key from .env file

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

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return chunks

def summarize_chunk(chunk, model="gpt-3.5- turbo", temperature=0.2):
    prompt = f"Summarize the following section of a brokerage statement in detail:\n\n{chunk}"
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()

def summarize_pdf(pdf_path):
    print(f"📄 Reading PDF: {pdf_path}")
    text, tables = extract_from_machine_pdf(pdf_path)

    chunks = chunk_text(text, chunk_size=1000, overlap=200)

    print(f"\n✂️ Summarizing {len(chunks)} chunks...\n")
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"🔹 Summarizing chunk {i + 1}/{len(chunks)}")
        summary = summarize_chunk(chunk)
        print(f"Summary {i + 1}: {summary}\n")
        chunk_summaries.append(summary)

    print("🧠 Generating overall summary...")
    overall_prompt = (
        "Based on the following summaries of parts of a brokerage statement, provide a concise but detailed overall summary. Make sure not to include any redundant information, and summarize the details of investor's portfolio value, transactions, income, asset allocation, and holdings:\n\n"
        + "\n\n".join(f"Chunk {i+1} summary: {s}" for i, s in enumerate(chunk_summaries))
    )
    overall_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": overall_prompt}],
        temperature=0.2,
    )
    overall_summary = overall_response.choices[0].message.content.strip()
    
    print("\n✅ Final Summary:\n")
    print(overall_summary)
    return overall_summary

if __name__ == "__main__":
    # pdf_path = "sample-new-fidelity-acnt-stmt.pdf"
    pdf_path = "document.pdf"
    summarize_pdf(pdf_path)
