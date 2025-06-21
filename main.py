# import pdfplumber
# from openai import OpenAI
# # from dotenv import load_dotenv
# import os

# # Load environment variables from .env file
# # load_dotenv()

# client = OpenAI()
# # client.api_key = os.getenv("OPENAI_API_KEY")  # Fetch API key from .env file
# client.api_key = "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"

# def extract_from_machine_pdf(pdf_path):
#     extracted_text = ""
#     extracted_tables = []

#     with pdfplumber.open(pdf_path) as pdf:
#         for page in pdf.pages:
#             text = page.extract_text()
#             if text:
#                 extracted_text += text + "\n"
#             tables = page.extract_tables()
#             if tables:
#                 extracted_tables.extend(tables)
#     return extracted_text.strip(), extracted_tables

# def chunk_text(text, chunk_size=1000, overlap=200):
#     chunks = []
#     start = 0
#     while start < len(text):
#         end = min(start + chunk_size, len(text))
#         chunks.append(text[start:end].strip())
#         start += chunk_size - overlap
#     return chunks

# def summarize_chunk(chunk, model="gpt-3.5- turbo", temperature=0.2):
#     prompt = f"Summarize the following section of a brokerage statement in detail:\n\n{chunk}"
#     response = client.chat.completions.create(
#         model=model,
#         messages=[{"role": "user", "content": prompt}],
#         temperature=temperature,
#     )
#     return response.choices[0].message.content.strip()

# def summarize_pdf(pdf_path):
#     print(f"📄 Reading PDF: {pdf_path}")
#     text, tables = extract_from_machine_pdf(pdf_path)

#     chunks = chunk_text(text, chunk_size=1000, overlap=200)

#     print(f"\n✂️ Summarizing {len(chunks)} chunks...\n")
#     chunk_summaries = []
#     for i, chunk in enumerate(chunks):
#         print(f"🔹 Summarizing chunk {i + 1}/{len(chunks)}")
#         summary = summarize_chunk(chunk)
#         print(f"Summary {i + 1}: {summary}\n")
#         chunk_summaries.append(summary)

#     print("🧠 Generating overall summary...")
#     overall_prompt = (
#         "Based on the following summaries of parts of a brokerage statement, provide a concise but detailed overall summary. Make sure not to include any redundant information, and summarize the details of investor's portfolio value, transactions, income, asset allocation, and holdings:\n\n"
#         + "\n\n".join(f"Chunk {i+1} summary: {s}" for i, s in enumerate(chunk_summaries))
#     )
#     overall_response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "user", "content": overall_prompt}],
#         temperature=0.2,
#     )
#     overall_summary = overall_response.choices[0].message.content.strip()
    
#     print("\n✅ Final Summary:\n")
#     print(overall_summary)
#     return overall_summary

# if __name__ == "__main__":
#     # pdf_path = "sample-new-fidelity-acnt-stmt.pdf"
#     pdf_path = "document.pdf"
#     summarize_pdf(pdf_path)

import PyPDF2
import pdfplumber
import re
from typing import List, Dict

def extract_pdf_with_structure(pdf_path):
    sections = {}
    current_section = None
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            
            for line in lines:
                # Identify section headers (customize these patterns)
                if re.search(r'(dividend|income)', line, re.IGNORECASE):
                    current_section = 'dividends'
                elif re.search(r'(trade|transaction|buy|sell)', line, re.IGNORECASE):
                    current_section = 'transactions'
                elif re.search(r'(balance|position|holding)', line, re.IGNORECASE):
                    current_section = 'positions'
                elif re.search(r'(fee|charge|expense)', line, re.IGNORECASE):
                    current_section = 'fees'
                
                # Add content to current section
                if current_section:
                    if current_section not in sections:
                        sections[current_section] = []
                    sections[current_section].append(line)
    
    return sections

def identify_sections_by_patterns(text):
    section_patterns = {
        'account_summary': [
            r'account\s+summary', r'portfolio\s+value', r'total\s+value'
        ],
        'dividends': [
            r'dividend', r'distribution', r'reinvestment'
        ],
        'transactions': [
            r'transaction', r'trade', r'buy', r'sell', r'purchase'
        ],
        'positions': [
            r'position', r'holding', r'shares', r'quantity'
        ],
        'fees': [
            r'fee', r'charge', r'commission', r'expense'
        ],
        'performance': [
            r'gain', r'loss', r'return', r'performance'
        ]
    }
    
    sections = {}
    lines = text.split('\n')
    current_section = 'general'
    
    for line in lines:
        # Check if line matches any section pattern
        for section_name, patterns in section_patterns.items():
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
                current_section = section_name
                break
        
        if current_section not in sections:
            sections[current_section] = []
        sections[current_section].append(line)
    
    return sections

def extract_tables_and_sections(pdf_path):
    sections = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract tables
            tables = page.extract_tables()
            
            for i, table in enumerate(tables):
                # Identify table type based on headers
                if table and table[0]:  # Check if table has headers
                    headers = [str(cell).lower() if cell else '' for cell in table[0]]
                    
                    if any('dividend' in h for h in headers):
                        section_name = 'dividend_table'
                    elif any('symbol' in h and 'qty' in h for h in headers):
                        section_name = 'positions_table'
                    elif any('trade' in h or 'buy' in h or 'sell' in h for h in headers):
                        section_name = 'transactions_table'
                    else:
                        section_name = f'table_{page_num}_{i}'
                    
                    sections[section_name] = table
            
            # Extract remaining text (non-tabular)
            text = page.extract_text()
            if text:
                sections[f'text_page_{page_num}'] = text
    
    return sections

from openai import OpenAI
from typing import Dict, Any

client = OpenAI()
client.api_key = "os.getenv("OPENAI_API_KEY")"

def summarize_section(section_name: str, content: Any, llm_client):
    """Summarize a specific section with context-aware prompts"""
    
    # Convert content to string if it's a table
    if isinstance(content, list) and len(content) > 0:
        if isinstance(content[0], list):  # It's a table
            content_str = '\n'.join(['\t'.join([str(cell) for cell in row]) for row in content])
        else:  # It's a list of lines
            content_str = '\n'.join(content)
    else:
        content_str = str(content)
    
    # Context-specific prompts
    prompts = {
        'dividends': "Summarize this dividend information including total dividends received, companies that paid dividends, and dates:",
        'transactions': "Summarize these transactions including number of trades, most active securities, and net buying/selling activity:",
        'positions': "Summarize the portfolio positions including largest holdings, sector allocation, and total portfolio value:",
        'fees': "Summarize all fees and charges including total costs and types of fees:",
        'performance': "Summarize the performance metrics including gains/losses and returns:"
    }
    
    prompt = prompts.get(section_name, "Summarize this brokerage statement section:")
    
    response = llm_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a financial analyst summarizing brokerage statements. Be concise and focus on key numbers and insights."},
            {"role": "user", "content": f"{prompt}\n\n{content_str}"}
        ],
        max_tokens=300
    )
    
    return response.choices[0].message.content

def process_brokerage_statement(pdf_path, llm_client):
    # Extract sections
    sections = extract_tables_and_sections(pdf_path)
    
    # Clean and filter sections
    meaningful_sections = {}
    for name, content in sections.items():
        if isinstance(content, str) and len(content.strip()) > 50:
            meaningful_sections[name] = content
        elif isinstance(content, list) and len(content) > 1:
            meaningful_sections[name] = content
    
    # Summarize each section
    summaries = {}
    for section_name, content in meaningful_sections.items():
        try:
            summary = summarize_section(section_name, content, llm_client)
            summaries[section_name] = {
                'original_length': len(str(content)),
                'summary': summary
            }
        except Exception as e:
            print(f"Error summarizing {section_name}: {e}")
    
    return summaries

# Usage
summaries = process_brokerage_statement("sample-new-fidelity-acnt-stmt.pdf", client)
for section, data in summaries.items():
    print(f"\n{section.upper()}:")
    print(data['summary'])