import streamlit as st
import pandas as pd
import os
import tempfile
from processor import process_file

def main():
    st.title("Brokerage Statement Summary")
    st.write("Upload a file to process its contents")
    
    # File uploader with expanded file type support
    uploaded_file = st.file_uploader("Choose a file", type=["txt", "pdf"])

    if uploaded_file is not None:
        # Display file details
        file_details = {
            "Filename": uploaded_file.name,
            "File type": uploaded_file.type,
            "File size": f"{uploaded_file.size} bytes"
        }
        
        st.write("### File Details:")
        for key, value in file_details.items():
            st.write(f"- {key}: {value}")
        
        # Process button
        if st.button("Process File"):
            with st.spinner('Processing file...'):
                # Call the processing function from processor.py
                output = process_file(uploaded_file)
                
                # Display the output on the webpage
                st.success("File processed successfully!")
                st.subheader("Processing Output:")
                
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
                        label="Download output as text",
                        data=output,
                        file_name=f"processed_{uploaded_file.name}.txt",
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()