# install.sh - unix installer (simplified)
#!/usr/bin/env bash
set -e
ROOT=$(pwd)
python3 -V >/dev/null 2>&1 || { echo "Python3 not found. Please install Python 3.8+"; exit 1; }
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo """Installation complete. To run:
source venv/bin/activate
python run.py --cli
"""
