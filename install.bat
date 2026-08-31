:: install.bat - Windows installer (simplified)
@echo off
python -V >nul 2>&1 || (
  echo Python not found. Please install Python 3.8+ and ensure it's in PATH.
  exit /b 1
)
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
echo Installation complete. To run:
echo call venv\Scripts\activate
echo python run.py --cli
