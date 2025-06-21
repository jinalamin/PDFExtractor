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
