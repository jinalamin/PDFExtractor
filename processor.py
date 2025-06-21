import PyPDF2
import pdfplumber
import re
from typing import List, Dict, Any
from openai import OpenAI
import tempfile
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
import json

load_dotenv()
# Initialize OpenAI client
# client = OpenAI()
# client.api_key = os.getenv("OPENAI_API_KEY")

def get_bedrock_client():
    """Initialize AWS Bedrock client"""
    try:
        # Get region from environment or use default
        region = os.getenv("AWS_BEDROCK_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        return bedrock_client
    except Exception as e:
        raise ValueError(f"Failed to initialize Bedrock client: {str(e)}")

client = get_bedrock_client()

def clean_extracted_text(text):
    """Clean and improve extracted text from PDF"""
    if not text:
        return text
    
    # Fix common PDF extraction issues
    # Add spaces around numbers and currency symbols
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\$)([A-Za-z])', r'\1 \2', text)
    
    # Fix concatenated words (basic heuristic)
    # Look for lowercase letter followed by uppercase letter
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove any potential HTML/markdown artifacts
    text = re.sub(r'[*_`#]', '', text)
    
    return text.strip()

def extract_pdf_with_structure(pdf_path):
    sections = {}
    current_section = None
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            # Clean the extracted text
            text = clean_extracted_text(text)
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
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

def extract_tables_and_sections(pdf_path):
    sections = {}
    
    try:
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
                    # Clean the text before storing
                    cleaned_text = clean_extracted_text(text)
                    sections[f'text_page_{page_num}'] = cleaned_text
    
    except Exception as e:
        print(f"Error extracting tables and sections: {e}")
        # Fallback to basic text extraction
        sections = {'error': f"Could not extract structured data: {e}"}
    
    return sections

def clean_ai_response(response_text):
    """Clean AI response to remove unwanted formatting"""
    if not response_text:
        return response_text
    
    # Remove any markdown formatting that might cause issues
    response_text = re.sub(r'\*\*(.*?)\*\*', r'\1', response_text)  # Remove bold
    response_text = re.sub(r'\*(.*?)\*', r'\1', response_text)      # Remove italic
    response_text = re.sub(r'`(.*?)`', r'\1', response_text)        # Remove code
    response_text = re.sub(r'#{1,6}\s*(.*)', r'\1', response_text)  # Remove headers
    
    # Ensure proper spacing around numbers and currency
    response_text = re.sub(r'(\$\d+(?:,\d{3})*(?:\.\d{2})?)', r' \1 ', response_text)
    response_text = re.sub(r'\s+', ' ', response_text)
    
    return response_text.strip()

def call_llama_bedrock(prompt, system_prompt="", model_arn=None):
    """Call AWS Bedrock Llama model with given prompt"""
    
    # Get model ARN from environment or use provided one
    if model_arn is None:
        model_arn = os.getenv("BEDROCK_MODEL_ID")
        if not model_arn:
            return "Error: BEDROCK_MODEL_ID not set in environment variables"
    
    # Validate that it's a Llama model
    if "llama" not in model_arn.lower():
        return f"Error: Expected Llama model, got {model_arn}"
    
    try:
        # Construct Llama 3 format prompt
        if system_prompt:
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        else:
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        
        # Prepare request body for Llama
        body = {
            "prompt": formatted_prompt,
            "max_gen_len": 300,
            "temperature": 0.3,
            "top_p": 0.9
        }
        
        # Call Bedrock
        response = client.invoke_model(
            modelId=model_arn,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract text from Llama response
        generated_text = response_body.get('generation', '')
        
        if generated_text:
            return generated_text.strip()
        else:
            return "No response generated"
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException' and 'inference profile' in str(e):
            return f"Error: Model {model_arn} requires inference profile setup. Please use the correct inference profile ARN from your Bedrock console."
        elif error_code == 'AccessDeniedException':
            return f"Error: Access denied to model {model_arn}. Please check model access permissions in Bedrock console."
        else:
            return f"AWS Bedrock error: {str(e)}"
    except Exception as e:
        return f"Error calling Bedrock: {str(e)}"

    
def summarize_section(section_name: str, content: Any, bedrock_client):
    """Summarize a specific section using AWS Bedrock"""
    
    # Convert content to string if it's a table
    if isinstance(content, list) and len(content) > 0:
        if isinstance(content[0], list):  # It's a table
            content_str = '\n'.join(['\t'.join([str(cell) if cell else '' for cell in row]) for row in content])
        else:  # It's a list of lines
            content_str = '\n'.join(content)
    else:
        content_str = str(content)
    
    # Clean the content before sending to AI
    content_str = clean_extracted_text(content_str)
    
    # Truncate content if too long (Bedrock has token limits)
    if len(content_str) > 3000:
        content_str = content_str[:3000] + "... (truncated)"
    
    # Context-specific prompts
    prompts = {
        'dividends': "Summarize this dividend information including total dividends received, companies that paid dividends, and dates. Use plain text only, no formatting:",
        'dividend_table': "Summarize this dividend table including total dividends received, companies that paid dividends, and dates. Use plain text only, no formatting:",
        'transactions': "Summarize these transactions including number of trades, most active securities, and net buying/selling activity. Use plain text only, no formatting:",
        'transactions_table': "Summarize this transactions table including number of trades, most active securities, and net buying/selling activity. Use plain text only, no formatting:",
        'positions': "Summarize the portfolio positions including largest holdings, sector allocation, and total portfolio value. Use plain text only, no formatting:",
        'positions_table': "Summarize this positions table including largest holdings, sector allocation, and total portfolio value. Use plain text only, no formatting:",
        'fees': "Summarize all fees and charges including total costs and types of fees. Use plain text only, no formatting:",
        'performance': "Summarize the performance metrics including gains/losses and returns. Use plain text only, no formatting:"
    }
    
    prompt = prompts.get(section_name, "Summarize this brokerage statement section. Use plain text only, no formatting:")
    full_prompt = f"{prompt}\n\n{content_str}"
    
    system_prompt = "You are a financial analyst summarizing brokerage statements. Be concise and focus on key numbers and insights. Use plain text only with no markdown, asterisks, or special formatting. Ensure proper spacing around numbers and currency amounts."
    
    try:
        # Call Bedrock instead of OpenAI
        response_text = call_llama_bedrock(full_prompt, system_prompt)
        
        # Clean the AI response
        clean_response = clean_ai_response(response_text)
        return clean_response
    
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# def summarize_section(section_name: str, content: Any, llm_client):
#     """Summarize a specific section with context-aware prompts"""
    
#     # Convert content to string if it's a table
#     if isinstance(content, list) and len(content) > 0:
#         if isinstance(content[0], list):  # It's a table
#             content_str = '\n'.join(['\t'.join([str(cell) if cell else '' for cell in row]) for row in content])
#         else:  # It's a list of lines
#             content_str = '\n'.join(content)
#     else:
#         content_str = str(content)
    
#     # Clean the content before sending to LLM
#     content_str = clean_extracted_text(content_str)
    
#     # Truncate content if too long (OpenAI has token limits)
#     if len(content_str) > 3000:
#         content_str = content_str[:3000] + "... (truncated)"
    
#     # Context-specific prompts
#     prompts = {
#         'dividends': "Summarize this dividend information including total dividends received, companies that paid dividends, and dates. Use plain text only, no formatting:",
#         'dividend_table': "Summarize this dividend table including total dividends received, companies that paid dividends, and dates. Use plain text only, no formatting:",
#         'transactions': "Summarize these transactions including number of trades, most active securities, and net buying/selling activity. Use plain text only, no formatting:",
#         'transactions_table': "Summarize this transactions table including number of trades, most active securities, and net buying/selling activity. Use plain text only, no formatting:",
#         'positions': "Summarize the portfolio positions including largest holdings, sector allocation, and total portfolio value. Use plain text only, no formatting:",
#         'positions_table': "Summarize this positions table including largest holdings, sector allocation, and total portfolio value. Use plain text only, no formatting:",
#         'fees': "Summarize all fees and charges including total costs and types of fees. Use plain text only, no formatting:",
#         'performance': "Summarize the performance metrics including gains/losses and returns. Use plain text only, no formatting:"
#     }
    
#     prompt = prompts.get(section_name, "Summarize this brokerage statement section. Use plain text only, no formatting:")
    
#     try:
#         response = llm_client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are a financial analyst summarizing brokerage statements. Be concise and focus on key numbers and insights. Use plain text only with no markdown, asterisks, or special formatting. Ensure proper spacing around numbers and currency amounts."},
#                 {"role": "user", "content": f"{prompt}\n\n{content_str}"}
#             ],
#             max_tokens=300,
#             temperature=0.3  # Lower temperature for more consistent formatting
#         )
        
#         # Clean the AI response
#         clean_response = clean_ai_response(response.choices[0].message.content)
#         return clean_response
    
#     except Exception as e:
#         return f"Error generating summary: {str(e)}"

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
            summaries[section_name] = {
                'original_length': len(str(content)),
                'summary': f"Error summarizing {section_name}: {e}"
            }
    
    return summaries

def process_file(uploaded_file):
    """
    Main function to process uploaded files
    This function will be called by the Streamlit app
    """
    
    if uploaded_file.type == "application/pdf":
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            # Process the PDF and get summaries
            summaries = process_brokerage_statement(tmp_file_path, client)
            
            # Format the output for display
            if summaries:
                formatted_output = {}
                for section, data in summaries.items():
                    formatted_output[section] = {
                        'Section': section.replace('_', ' ').title(),
                        'Original Length': f"{data['original_length']} characters",
                        'Summary': data['summary']
                    }
                return formatted_output
            else:
                return {"error": "No meaningful sections found in the PDF"}
                
        except Exception as e:
            return {"error": f"Error processing PDF: {str(e)}"}
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
    
    elif uploaded_file.type == "text/plain":
        # Handle text files (existing functionality)
        try:
            content = uploaded_file.read().decode("utf-8")
            return f"Text file content:\n\n{content}"
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    
    else:
        return f"Unsupported file type: {uploaded_file.type}"