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
    st.subheader("📊 Key Takeaways")

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

                # st.text(data['Summary'])
                formatted_summary = data['Summary'].replace('\n', '\n\n')
                st.markdown(f"<div style='text-align: justify; line-height: 1.6; padding: 10px; background-color: #f8f9fa; border-radius: 5px; border-left: 4px solid #dd511d;'>{formatted_summary}</div>", unsafe_allow_html=True)
    else:
        # Single section, display directly
        for section, data in summaries.items():
            st.write(f"### {data['Section']}")
            st.write("**Summary:**")

            # st.text(data['Summary'])
            formatted_summary = data['Summary'].replace('\n', '\n\n')
            st.markdown(f"<div style='text-align: justify; line-height: 1.6; padding: 10px; background-color: #f8f9fa; border-radius: 5px; border-left: 4px solid #dd511d;'>{formatted_summary}</div>", unsafe_allow_html=True)
def main():
    logo_path = os.path.join(os.path.dirname(__file__), "straditLogo.png")
    if os.path.exists(logo_path):
        import base64
        from io import BytesIO
        from PIL import Image as PILImage
        try:
            with open(logo_path, "rb") as image_file:
                img = PILImage.open(image_file)
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                encoded = base64.b64encode(buffered.getvalue()).decode()
            img_mime = "image/png"
        except Exception:
            with open(logo_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
            img_mime = "image/jpeg"
        st.markdown(
            f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 0.15rem;">'
            f'<img src="data:{img_mime};base64,{encoded}" width="150" style="border-radius: 14px; background: transparent;" alt="Logo">'
            '</div>',
            unsafe_allow_html=True
        )
    st.title("📄 Brokerage Statement Summary")
    #st.write("Upload a PDF brokerage statement to get an AI-powered summary of key sections")
    st.markdown('<span style="color: #FF7300; font-weight: bold; font-size: 1.1rem;">Upload a PDF brokerage statement to get an AI-powered summary of key sections</span>', unsafe_allow_html=True)

    # Add some styling
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 16px;
        font-weight: bold;
    }
    /* Apply color only to the selected tab */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #FF7300 !important;
    font-weight: bold;
}   
   
    
    # .st-emotion-cache-bfgnao {
    # font-family: "Source Sans", sans-serif;
    # font-size: 0.875rem;
    # color: #FF7300 !important;
    # }
    
     /* File details */
        .file-details-title {
            color: #FF7300;
            font-size: 1.1rem;
            font-weight: 700;
            margin-top: 1.2rem;
        }
        .file-detail-key {
            color: #FFA500;
            font-weight: 600;
        }
        .file-detail-value {
            color: #181818;
        }
        textarea {
    background-color: #1E1E1E; /* Dark background for dark mode */
    color: #FFFFFF; /* White text for visibility */
    border: 1px solid #FFA500; /* Optional: Add a border for better visibility */
    border-radius: 8px; /* Rounded corners */
    padding: 10px; /* Add some padding */
    font-size: 1rem; /* Adjust font size */
    font-family: "Source Sans", sans-serif; /* Consistent font */
    resize: none; /* Disable resizing if not needed */
}
        /* Buttons */
        .stButton>button, .stDownloadButton>button {
            background: linear-gradient(90deg, #FFA500 0%, #FF7300 100%) !important;
            color: #fff !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 1.08rem !important;
            padding: 0.6rem 2rem !important;
            border: none !important;
            box-shadow: 0 2px 8px rgba(255,140,0,0.10) !important;
            transition: background 0.2s, box-shadow 0.2s !important;
        }
        .stButton>button:hover, .stDownloadButton>button:hover {
            background: linear-gradient(90deg, #FF7300 0%, #FFA500 100%) !important;
            color: #fff !important;
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
        st.markdown('<div class="file-details-title">File Details:</div>', unsafe_allow_html=True)
        file_details = {
            "Filename": uploaded_file.name,
            "File type": uploaded_file.type,
            "File size": f"{uploaded_file.size} bytes"
        }
        for key, value in file_details.items():
            st.markdown(f'<li style="margin-bottom:0.1rem;"><span class="file-detail-key">{key.capitalize()}</span>: <span>{value}</span></li>', unsafe_allow_html=True)
        st.markdown('</ul>', unsafe_allow_html=True)
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
                            # Get overall and section summaries for display
                            overall_summary = None
                            section_summaries = []

                            sorted_output = sorted(output.items(), key=lambda x: x[1].get('Priority', 999))
                            for section_key, data in sorted_output:
                                if section_key == 'overall_summary':
                                    overall_summary = data
                                else:
                                    section_summaries.append((section_key, data))

                            display_pdf_summaries(output)

                            # Add download option for summaries
                            summary_text = ""

                            # Add overall summary first
                            if overall_summary:
                                summary_text += "OVERALL SUMMARY\n"
                                summary_text += "=" * 50 + "\n"
                                summary_text += f"{overall_summary['Summary']}\n\n"

                            # Add section summaries
                            for section_key, data in section_summaries:
                                if "error" not in section_key.lower():
                                    summary_text += f"{data['Section'].upper()}\n"
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