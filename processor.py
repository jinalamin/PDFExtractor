import streamlit as st
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

        #preview = content[:500] + ('...' if len(content) > 500 else '')
        preview = content
        allContent = content
        lines = allContent.split('\n')
        words = allContent.split()
        stats = {
            'lines': len(lines),
            'words': len(words),
            'characters': len(allContent)
        }
        st.markdown('<div class="file-details-title">File Statistics:</div>', unsafe_allow_html=True)
        for key, value in stats.items():
            st.markdown(f'<li style="margin-bottom:0.1rem;"><span class="file-detail-key">{key.capitalize()}</span>: <span class="file-detail-value">{value}</span></li>', unsafe_allow_html=True)
        st.markdown('</ul>', unsafe_allow_html=True)

        return preview
            
    except Exception as e:
        return f"Error processing file: {str(e)}"