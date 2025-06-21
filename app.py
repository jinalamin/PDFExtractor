import streamlit as st
import pandas as pd
import os
import tempfile
import json
from processor import process_file

# Set the page configuration
st.set_page_config(
    page_title="Brokerage Statement Summary",  # Tab name
    page_icon="📄",  # Optional: Tab icon
    layout="centered",  # Optional: Layout of the app
    initial_sidebar_state="auto"  # Optional: Sidebar state
)

def display_pdf_summaries(summaries):
    """Display PDF summaries in a nice format"""
    st.subheader("📊 Brokerage Statement Summary")
    
    if "error" in summaries:
        st.error(summaries["error"])
        return
    
    # Create tabs for better organization
    section_names = list(summaries.keys())
    if len(section_names) > 1:
        tabs = st.tabs([summaries[section]['Section'] for section in section_names])
        
        for i, section in enumerate(section_names):
            with tabs[i]:
                data = summaries[section]
                st.write("**Summary:**")
                # Use st.text() instead of st.write() for plain text display
                st.text(data['Summary'])
    else:
        # Single section, display directly
        for section, data in summaries.items():
            st.write(f"### {data['Section']}")
            st.write(f"**Original Length:** {data['Original Length']}")
            st.write("**Summary:**")
            # Use st.text() instead of st.write() for plain text display
            st.text(data['Summary'])

def main():
    st.title("📄 Brokerage Statement Summary")
    st.write("Upload a PDF brokerage statement to get an AI-powered summary of key sections")
    
    # Add some styling
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # File uploader with expanded file type support
    uploaded_file = st.file_uploader(
        "Choose a file", 
        type=["txt", "pdf"],
        help="Upload a PDF brokerage statement or text file for processing"
    )

    if uploaded_file is not None:
        # Display file details in an expandable section
        with st.expander("📋 File Details", expanded=False):
            file_details = {
                "Filename": uploaded_file.name,
                "File type": uploaded_file.type,
                "File size": f"{uploaded_file.size:,} bytes ({uploaded_file.size/1024:.1f} KB)"
            }
            
            for key, value in file_details.items():
                st.write(f"**{key}:** {value}")
        
        # Process button
        if st.button("🚀 Process File", type="primary"):
            with st.spinner('🔄 Processing file... This may take a moment for PDF files.'):
                try:
                    # Call the processing function from processor.py
                    output = process_file(uploaded_file)
                    
                    # Display the output based on file type
                    if uploaded_file.type == "application/pdf":
                        # PDF processing with summaries
                        if isinstance(output, dict):
                            display_pdf_summaries(output)
                            
                            # Add download option for summaries
                            summary_text = ""
                            for section, data in output.items():
                                if "error" not in section:
                                    summary_text += f"{data['Section']}\n"
                                    summary_text += "=" * len(data['Section']) + "\n"
                                    summary_text += f"{data['Summary']}\n\n"
                            
                            if summary_text:
                                st.download_button(
                                    label="💾 Download Summary as Text",
                                    data=summary_text,
                                    file_name=f"summary_{uploaded_file.name}.txt",
                                    mime="text/plain"
                                )
                        else:
                            st.error("Unexpected output format from PDF processing")
                            
                    else:
                        # Text file processing
                        st.success("✅ File processed successfully!")
                        st.subheader("📄 Processing Output:")
                        
                        # Handle different output types
                        if isinstance(output, pd.DataFrame):
                            st.dataframe(output)
                        elif isinstance(output, dict):
                            st.json(output)
                        else:
                            st.text_area("Text output", output, height=300)
                            
                        # Download button for processed output
                        if isinstance(output, str):
                            st.download_button(
                                label="💾 Download output as text",
                                data=output,
                                file_name=f"processed_{uploaded_file.name}.txt",
                                mime="text/plain"
                            )
                
                except Exception as e:
                    st.error(f"❌ Error processing file: {str(e)}")
                    st.write("Please check that your file is a valid PDF or text file and try again.")

    # Add some helpful information
    with st.expander("ℹ️ How it works", expanded=False):
        st.write("""
        **For PDF Files:**
        - The app extracts different sections from your brokerage statement (dividends, transactions, positions, fees, etc.)
        - Each section is summarized using AI to highlight key information
        - You can view summaries in organized tabs and download them as text
        
        **For Text Files:**
        - The content is displayed as-is for review
        - You can download the processed output
        
        **Supported File Types:** PDF, TXT
        """)

if __name__ == "__main__":
    main()