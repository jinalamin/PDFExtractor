# Brokerage Statement Summary

This project is a Streamlit-based web application that processes uploaded files (TXT or PDF) and provides a summary of their contents. It includes features like file details display, content processing, and output preview.

## Prerequisites

Ensure you have the following installed on your local machine:

- Python 3.8 or higher
- `pip` (Python package manager)

## Setup Instructions

Follow these steps to run the project locally:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:
  ```bash
  venv\Scripts\activate
  ```
- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Run the Application

Start the Streamlit application:

```bash
streamlit run app.py
```

### 5. Access the Application

Open your browser and navigate to:

```
http://localhost:8501
```

## File Upload Support

The application supports the following file types:

- **TXT**: Plain text files
- **PDF**: PDF files (machine-readable)

## Project Structure

- `app.py`: Main Streamlit application file.
- `processor.py`: Contains the logic for processing uploaded files.
- `main.py`: Handles PDF extraction using `pdfplumber`.
- `.gitignore`: Specifies files and folders to ignore in version control.

## Notes

- Ensure that the `pdfplumber` library is installed for PDF processing.
- The `.gitignore` file excludes IDE-specific files (`.idea`) and virtual environments (`*venv*`).

## Troubleshooting

If you encounter issues:

1. Verify that all dependencies are installed.
2. Ensure the virtual environment is activated.
3. Check the console for error messages and debug accordingly.

## Running code on EC2 Server
The EC2 host is already created with public IP address and security group configured to allow all inbound traffic.
We didn't want to connect github repository to the AWS account so the code deployment is done manually.

To deploy the code on EC2 server, follow these steps:
1. Log on to the EC2 instance using SSM.
2. cd `/opt/brokerage-app` : The code lives in `/opt/brokerage-app` directory.
3. It contains an installation.sh file that installs the required packages and sets up the environment. 
4. Whenever you need to update the code, zip the latest code and upload it to the S3 bucket:
   ```bash
   s3://source-code-stradit/brokerage-summary/
   The folder should be named as: PDFExtractor-master.zip <This is important as the code is configured to look for this name>
   ```
5. After uploading the code, run the installation script:
   ```bash
   ./installation.sh
   ```
   This shall pull the latest code from S3 bucket and install the required packages. This script also stops the streamlit app and re-run the app with latest code pulled.
6. If you want to make any changes to installation script, you can do so in the `installation.sh` file. But it has to be done manually, edit the contents of installation.sh and save it.