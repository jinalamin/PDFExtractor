import PyPDF2
import pdfplumber
import re
import json
from typing import List, Dict, Any
import tempfile
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables from .env file
load_dotenv()

# Initialize AWS Bedrock client
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
    """Extract content and organize by logical sections instead of pages"""
    sections = {
        'dividends': [],
        'transactions': [],
        'positions': [],
        'fees': [],
        'performance': [],
        'account_summary': [],
        'other': []
    }
    
    all_text = ""  # Collect all text for overall summary
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract tables and categorize them
                tables = page.extract_tables()
                
                for i, table in enumerate(tables):
                    if table and table[0]:  # Check if table has headers
                        headers = [str(cell).lower() if cell else '' for cell in table[0]]
                        
                        # Categorize table based on headers
                        if any('dividend' in h or 'distribution' in h for h in headers):
                            sections['dividends'].append(table)
                        elif any(('symbol' in h and 'qty' in h) or 'position' in h for h in headers):
                            sections['positions'].append(table)
                        elif any('trade' in h or 'buy' in h or 'sell' in h or 'transaction' in h for h in headers):
                            sections['transactions'].append(table)
                        elif any('fee' in h or 'charge' in h or 'commission' in h for h in headers):
                            sections['fees'].append(table)
                        else:
                            sections['other'].append(table)
                
                # Extract and categorize text
                text = page.extract_text()
                if text:
                    cleaned_text = clean_extracted_text(text)
                    all_text += cleaned_text + "\n"
                    
                    # Categorize text by content
                    lines = cleaned_text.split('\n')
                    current_section = 'other'
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Identify section based on content
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['dividend', 'distribution', 'reinvestment']):
                            current_section = 'dividends'
                        elif any(keyword in line_lower for keyword in ['trade', 'transaction', 'buy', 'sell', 'purchase']):
                            current_section = 'transactions'
                        elif any(keyword in line_lower for keyword in ['position', 'holding', 'shares', 'quantity', 'portfolio']):
                            current_section = 'positions'
                        elif any(keyword in line_lower for keyword in ['fee', 'charge', 'commission', 'expense']):
                            current_section = 'fees'
                        elif any(keyword in line_lower for keyword in ['gain', 'loss', 'return', 'performance', 'change']):
                            current_section = 'performance'
                        elif any(keyword in line_lower for keyword in ['account summary', 'portfolio value', 'total value', 'balance']):
                            current_section = 'account_summary'
                        
                        sections[current_section].append(line)
    
    except Exception as e:
        print(f"Error extracting tables and sections: {e}")
        return {'error': f"Could not extract structured data: {e}"}
    
    # Add overall text for summary
    sections['overall_text'] = all_text
    
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
        # Construct Llama 3 format prompt with clear instructions
        if system_prompt:
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        else:
            formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        
        # Prepare request body for Llama with increased token limit
        body = {
            "prompt": formatted_prompt,
            "max_gen_len": 400,  # Increased from 300
            "temperature": 0.1,  # Lower temperature for more focused responses
            "top_p": 0.7        # Slightly lower for more focused responses
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
            # Clean up the response
            clean_text = generated_text.strip()
            
            # Remove any leading '>' characters
            while clean_text.startswith('>'):
                clean_text = clean_text[1:].strip()
            
            # Remove any trailing incomplete sentences if text was truncated
            if len(clean_text) > 10:
                # If text doesn't end with proper punctuation and seems truncated
                if not clean_text.endswith(('.', '!', '?', ':')) and len(clean_text) > 500:
                    # Find the last complete sentence
                    last_period = clean_text.rfind('.')
                    last_exclamation = clean_text.rfind('!')
                    last_question = clean_text.rfind('?')
                    
                    last_punct = max(last_period, last_exclamation, last_question)
                    
                    if last_punct > len(clean_text) * 0.7:  # If we have at least 70% of the text
                        clean_text = clean_text[:last_punct + 1]
            
            return clean_text
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
    """Summarize a specific section using AWS Bedrock Llama model"""
    
    # Convert content to string based on type
    if isinstance(content, list):
        if len(content) > 0 and isinstance(content[0], list):  # It's a list of tables
            content_str = ""
            for table in content:
                table_str = '\n'.join(['\t'.join([str(cell) if cell else '' for cell in row]) for row in table])
                content_str += table_str + "\n\n"
        else:  # It's a list of text lines
            content_str = '\n'.join(str(item) for item in content if item)
    else:
        content_str = str(content)
    
    # Clean the content before sending to AI
    content_str = clean_extracted_text(content_str)
    
    # Skip if content is too short or empty
    if len(content_str.strip()) < 20:
        return f"No meaningful {section_name} data found"
    
    # Truncate content if too long (Bedrock has token limits)
    if len(content_str) > 4000:
        content_str = content_str[:4000] + "... (truncated)"
    
    # Context-specific prompts with clearer instructions
    prompts = {
        'overall_summary': """Analyze this complete brokerage statement and provide a comprehensive summary. Include:
1. Total portfolio value and period-over-period change
2. Key account balances 
3. Major transactions or activity
4. Income/dividends received
5. Notable performance highlights
Write in clear, complete sentences without using quotation marks or special formatting:""",
        
        'dividends': """Analyze the dividend and distribution information. Summarize:
1. Total dividends/distributions received
2. Companies that paid dividends
3. Payment dates and amounts
Write in clear, complete sentences:""",
        
        'transactions': """Analyze the trading activity. Summarize:
1. Number of trades executed
2. Most active securities traded
3. Buy vs sell activity
4. Total transaction volume
Write in clear, complete sentences:""",
        
        'positions': """Analyze the portfolio positions. Summarize:
1. Largest holdings by value
2. Asset allocation breakdown
3. Total portfolio value
4. Any significant position changes
Write in clear, complete sentences:""",
        
        'fees': """Analyze all fees and charges. Summarize:
1. Total fees paid during the period
2. Types of fees (management, transaction, etc.)
3. Any changes in fee structure
Write in clear, complete sentences:""",
        
        'performance': """Analyze the performance metrics. Summarize:
1. Investment gains or losses
2. Portfolio returns
3. Performance highlights
4. Year-to-date performance
Write in clear, complete sentences:""",
        
        'account_summary': """Analyze the account overview. Summarize:
1. Account balances by type
2. Key metrics and totals
3. Important account information
Write in clear, complete sentences:""",
        
        'other': """Analyze this additional information from the brokerage statement. Summarize the key points in clear, complete sentences:"""
    }
    
    prompt = prompts.get(section_name, f"Analyze and summarize this {section_name} information from the brokerage statement in clear, complete sentences:")
    full_prompt = f"{prompt}\n\nData to analyze:\n{content_str}"
    
    system_prompt = """You are a professional financial analyst. Provide clear, concise summaries of brokerage statement sections. 

IMPORTANT RULES:
- Write in complete sentences that end with periods
- Do NOT use quotation marks, asterisks, or special formatting
- Do NOT start responses with '>' or other symbols
- Focus on key numbers, amounts, and insights
- Ensure proper spacing around currency amounts
- Keep responses complete and well-structured"""
    
    try:
        # Call Llama via Bedrock
        response_text = call_llama_bedrock(full_prompt, system_prompt)
        
        # Additional cleaning of AI response
        clean_response = clean_ai_response(response_text)
        
        # Remove any remaining formatting artifacts
        clean_response = re.sub(r'^[>\-\*\+\s]*', '', clean_response)  # Remove leading symbols
        clean_response = re.sub(r'\s+', ' ', clean_response)  # Normalize spaces
        clean_response = clean_response.strip()
        
        return clean_response
    
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def process_brokerage_statement(pdf_path, bedrock_client):
    # Extract sections organized by content type
    sections = extract_tables_and_sections(pdf_path)
    
    if 'error' in sections:
        return sections
    
    # Generate overall summary first
    overall_text = sections.get('overall_text', '')
    summaries = {}
    
    if overall_text and len(overall_text.strip()) > 100:
        try:
            overall_summary = summarize_section('overall_summary', overall_text, bedrock_client)
            summaries['overall_summary'] = {
                'summary': overall_summary
            }
        except Exception as e:
            summaries['overall_summary'] = {
                'summary': f"Error generating overall summary: {e}"
            }
    
    # Process each section (excluding overall_text and empty sections)
    section_order = ['dividends', 'transactions', 'positions', 'fees', 'performance', 'account_summary', 'other']
    
    for section_name in section_order:
        content = sections.get(section_name, [])
        
        # Skip empty sections
        if not content:
            continue
            
        # Skip if content is too minimal
        content_str = str(content)
        if len(content_str.strip()) < 50:
            continue
        
        try:
            summary = summarize_section(section_name, content, bedrock_client)
            summaries[section_name] = {
                'summary': summary
            }
        except Exception as e:
            summaries[section_name] = {
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
            # Process the PDF and get summaries using Bedrock Llama
            summaries = process_brokerage_statement(tmp_file_path, client)
            
            # Format the output for display
            if summaries:
                formatted_output = {}
                
                # Format overall summary first
                if 'overall_summary' in summaries:
                    formatted_output['overall_summary'] = {
                        'Section': 'Overall Summary',
                        'Summary': summaries['overall_summary']['summary'],
                        'Priority': 0  # For ordering
                    }
                
                # Format section-wise summaries
                section_titles = {
                    'dividends': 'Dividends & Distributions',
                    'transactions': 'Trading Activity',
                    'positions': 'Portfolio Positions',
                    'fees': 'Fees & Charges',
                    'performance': 'Performance Metrics',
                    'account_summary': 'Account Summary',
                    'other': 'Other Information'
                }
                
                priority = 1
                for section_key, data in summaries.items():
                    if section_key != 'overall_summary':
                        formatted_output[section_key] = {
                            'Section': section_titles.get(section_key, section_key.replace('_', ' ').title()),
                            'Summary': data['summary'],
                            'Priority': priority
                        }
                        priority += 1
                
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
    
    # File statistics (for text files)
    content = uploaded_file.read().decode("utf-8")
    lines = content.splitlines()
    words = re.findall(r'\w+', content)
    allContent = content
    
    stats = {
        'lines': len(lines),
        'words': len(words),
        'characters': len(allContent)
    }
    # Orange theme for stats output
    stats_html = '<div class="file-details-title" style="margin-bottom:0.3rem;">File Statistics:</div>'
    stats_html += '<ul style="padding-left:1.2em; margin:0;">'
    for key, value in stats.items():
        stats_html += f'<li style="margin-bottom:0.1rem;"><span class="file-detail-key">{key.capitalize()}</span>: <span class="file-detail-value">{value}</span></li>'
    stats_html += '</ul>'
    st.markdown(stats_html, unsafe_allow_html=True)
    preview = content[:500] + ('...' if len(content) > 500 else '')
    return preview