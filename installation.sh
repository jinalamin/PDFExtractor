#!/bin/bash

# 1. Pull a zip file from S3 location
echo "Downloading app-source.zip from S3..."
aws s3 cp s3://source-code-stradit/brokerage-summary/app-source.zip app-source.zip

# 2. Install Python if it doesn't exist
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
else
    echo "Python3 is already installed."
fi

# 3. Install requirements
pip3 install --upgrade pip
pip3 install -r requirements.txt || true  # In case requirements.txt is overwritten in next step

# 4. Unzip and overwrite files
unzip -o app-source.zip -d .

# 5. Install requirements again (in case requirements.txt was updated)
pip3 install -r requirements.txt

# 6. Run or restart Streamlit
if pgrep -f "streamlit run app.py" > /dev/null; then
    echo "Restarting Streamlit..."
    pkill -f "streamlit run app.py"
    nohup streamlit run app.py --server.port=8501 --server.address=0.0.0.0 &
else
    echo "Starting Streamlit..."
    nohup streamlit run app.py --server.port=8501 --server.address=0.0.0.0 &
fi
