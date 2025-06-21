import pandas as pd
import io

from main import extract_pdf_contents


def process_file(uploaded_file):
    """
    Process the uploaded file based on its type.
    
    Parameters:
    uploaded_file (UploadedFile): The file uploaded via Streamlit's file_uploader

    Returns:
    Various: Processed content (DataFrame, string, dict, etc.) depending on file type
    """
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    try:
        content= None
        # Process based on file extension
        if file_type == 'txt':
            # Read text file
            content = uploaded_file.read().decode('utf-8')
        elif file_type == 'pdf':
            content = extract_pdf_contents(uploaded_file)
        else:
            return f"Unsupported file type: {file_type}. Please upload a TXT or PDF file."

        lines = content.split('\n')
        words = content.split()
        stats = f"""
File Statistics:
- Lines: {len(lines)}
- Words: {len(words)}
- Characters: {len(content)}

Content Preview:
{content[:500]}{'...' if len(content) > 500 else ''}
            """
        return stats
            
    except Exception as e:
        return f"Error processing file: {str(e)}"