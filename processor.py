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
load_dotenv('/etc/environment')

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

def clean_and_align_text(text):
    """Enhanced text cleaning and alignment function"""
    if not text:
        return text
    
    # Remove any leading/trailing whitespace
    text = text.strip()
    
    # Remove markdown formatting artifacts
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italic
    text = re.sub(r'`(.*?)`', r'\1', text)        # Remove code
    text = re.sub(r'#{1,6}\s*(.*)', r'\1', text)  # Remove headers
    text = re.sub(r'^[>\-\*\+\s]*', '', text, flags=re.MULTILINE)  # Remove leading symbols per line
    
    # Clean up bullet points and list formatting
    text = re.sub(r'^\s*[-\*\+]\s*', '• ', text, flags=re.MULTILINE)  # Standardize bullets
    text = re.sub(r'^\s*\d+\.\s*', lambda m: f"{m.group().strip()} ", text, flags=re.MULTILINE)  # Clean numbered lists
    
    # Fix spacing around currency and numbers
    text = re.sub(r'\$\s*(\d)', r'$\1', text)  # Fix "$" spacing
    text = re.sub(r'(\d)\s*%', r'\1%', text)   # Fix "%" spacing
    text = re.sub(r'(\d),\s*(\d{3})', r'\1,\2', text)  # Fix comma separators
    
    # Normalize whitespace while preserving paragraph breaks
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Clean each line individually
        line = re.sub(r'\s+', ' ', line.strip())
        
        # Skip empty lines but preserve intentional paragraph breaks
        if line or (cleaned_lines and cleaned_lines[-1]):
            cleaned_lines.append(line)
    
    # Join lines back together, preserving paragraph structure
    text = '\n'.join(cleaned_lines)
    
    # Remove excessive line breaks (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Ensure sentences end with proper punctuation
    text = re.sub(r'([a-zA-Z0-9])\s*$', r'\1.', text, flags=re.MULTILINE)
    
    return text.strip()


def format_summary_for_display(summary_text, section_name):
    """Format summary text specifically for clean display"""
    
    # Apply base cleaning
    formatted_text = clean_and_align_text(summary_text)
    
    # Section-specific formatting
    if section_name.lower() in ['dividends', 'transactions', 'positions']:
        # For financial sections, ensure currency amounts are properly formatted
        formatted_text = re.sub(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', r'$\1', formatted_text)
        
        # Standardize percentage formatting
        formatted_text = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1%', formatted_text)
    
    # Split into sentences for better readability
    sentences = re.split(r'(?<=[.!?])\s+', formatted_text)
    
    # Clean each sentence
    clean_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 3:  # Skip very short fragments
            # Ensure proper capitalization
            sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
            clean_sentences.append(sentence)
    
    # Rejoin with consistent spacing
    return ' '.join(clean_sentences)


def clean_ai_response(response_text):
    """Enhanced AI response cleaning with better alignment"""
    if not response_text:
        return response_text
    
    # Remove common AI artifacts
    response_text = re.sub(r'^(Here\'s|Here is|Based on|According to).*?[:\.]?\s*', '', response_text, flags=re.IGNORECASE)
    response_text = re.sub(r'(In summary|To summarize|In conclusion)[:\.]?\s*', '', response_text, flags=re.IGNORECASE)
    
    # Apply standard cleaning
    response_text = clean_and_align_text(response_text)
    
    # Remove any remaining formatting artifacts
    response_text = re.sub(r'^\s*[>\-\*\+]\s*', '', response_text, flags=re.MULTILINE)
    response_text = re.sub(r'\s+([.!?])', r'\1', response_text)  # Fix punctuation spacing
    
    # Ensure proper sentence structure
    response_text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', response_text)
    
    return response_text.strip()


# Updated system prompt for better consistency
SYSTEM_PROMPT_TEMPLATE = """You are a professional financial analyst. Provide clear, well-structured summaries of brokerage statement sections.

FORMATTING REQUIREMENTS:
- Write in complete, properly punctuated sentences
- Use consistent spacing and formatting
- Start each summary with the most important information
- Use specific numbers, dates, and amounts when available
- Do NOT use quotation marks, asterisks, or markdown formatting
- Do NOT start responses with introductory phrases
- Keep responses focused and factual
- Ensure proper spacing around currency amounts (e.g., $1,234.56)

CONTENT FOCUS:
- Highlight key financial metrics and changes
- Include specific dollar amounts and percentages when relevant  
- Mention important dates and time periods
- Provide context for significant changes or activity"""


def call_llama_bedrock(prompt, section_name, model_arn=None):
    """Enhanced Bedrock call with better formatting controls"""
    
    if model_arn is None:
        model_arn = os.getenv("BEDROCK_MODEL_ID")
        if not model_arn:
            return "Error: BEDROCK_MODEL_ID not set in environment variables"
    
    if "llama" not in model_arn.lower():
        return f"Error: Expected Llama model, got {model_arn}"
    
    try:
        # Use the enhanced system prompt
        formatted_prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{SYSTEM_PROMPT_TEMPLATE}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        
        # Optimized parameters for cleaner output
        body = {
            "prompt": formatted_prompt,
            "max_gen_len": 500,      # Increased for complete responses
            "temperature": 0.05,     # Very low for consistency
            "top_p": 0.6,           # Focused responses
        }
        
        response = client.invoke_model(
            modelId=model_arn,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        generated_text = response_body.get('generation', '')
        
        if generated_text:
            # Apply enhanced cleaning
            clean_text = clean_ai_response(generated_text)
            
            # Apply section-specific formatting
            formatted_text = format_summary_for_display(clean_text, section_name)
            
            return formatted_text
        else:
            return "No response generated"
            
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