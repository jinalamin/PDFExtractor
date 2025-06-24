import streamlit as st
import pandas as pd
import os
import tempfile
from processor import process_file

# Set the page configuration
st.set_page_config(
    page_title="Brokerage Statement Summary",  # Tab name
    page_icon="📄",  # Optional: Tab icon
    layout="centered",  # Optional: Layout of the app
    initial_sidebar_state="auto"  # Optional: Sidebar state
)
def main():
    # Add logo at the top center of the page (before the title)
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
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
    
    st.markdown(
        """
        <style>

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
        """,
        unsafe_allow_html=True
    )

    # Main title and subtitle
    st.title("Brokerage Statement Summary")
    st.markdown('<span style="color: #FFA500; font-weight: bold; font-size: 1.1rem;">Upload a file to process its contents</span>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choose a file", type=["txt", "pdf"])

    if uploaded_file is not None:
        st.markdown('<div class="file-details-title">File Details:</div>', unsafe_allow_html=True)
        file_details = {
            "Filename": uploaded_file.name,
            "File type": uploaded_file.type,
            "File size": f"{uploaded_file.size} bytes"
        }
        for key, value in file_details.items():
            st.markdown(f'<li style="margin-bottom:0.1rem;"><span class="file-detail-key">{key.capitalize()}</span>: <span class="file-detail-value">{value}</span></li>', unsafe_allow_html=True)
        st.markdown('</ul>', unsafe_allow_html=True)
        # Process button
        if st.button("Process File"):
            with st.spinner('Processing file...'):
                # Call the processing function from processor.py
                output = process_file(uploaded_file)

                 # Display the output on the webpage
                st.success("File processed successfully!")
                
                # Custom styled subheader for summary, matching the orange theme
                st.markdown('<div style="color: #FF7300; font-size: 1.1rem; font-weight: 700; margin-top: 1.2rem;">Summary of the file details:</div>', unsafe_allow_html=True)
                
                # Handle different output types
                if isinstance(output, pd.DataFrame):
                    st.dataframe(output)
                elif isinstance(output, dict):
                    st.json(output)
                else:
                    st.text_area("", output, height=300)
                    
                # Download button for processed output
                if isinstance(output, str):
                    st.download_button(
                        label="Download output as text",
                        data=output,
                        file_name=f"processed_{uploaded_file.name}.txt",
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()