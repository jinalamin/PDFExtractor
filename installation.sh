#!/bin/bash

cd /opt/brokerage-app
# 1. Pull a zip file from S3 location
echo "Downloading app-source.zip from S3..."
aws s3 cp s3://source-code-stradit/brokerage-summary/PDFExtractor-master.zip app-source.zip

# 2. Install Python if it doesn't exist
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
else
    echo "Python3 is already installed."
fi

# 4. Unzip and overwrite files
unzip -o app-source.zip -d .

cd PDFExtractor-master || { echo "Failed to change directory to PDFExtractor-master"; exit 1; }

# 2.5. Check for venv 'app-env', create if not exists, then activate
if [ ! -d "app-env" ]; then
    echo "Python venv 'app-env' not found. Creating..."
    python3 -m venv app-env
fi
source app-env/bin/activate

# 5. Install requirements again (in case requirements.txt was updated)
pip install -r requirements.txt || true

# 6. Run or restart Streamlit
if pgrep -f "streamlit run app.py" > /dev/null; then
    echo "Restarting Streamlit..."
    pkill -f "streamlit run app.py"
    streamlit run app.py
else
    echo "Starting Streamlit..."
    streamlit run app.py
fi