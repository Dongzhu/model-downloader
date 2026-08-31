:: uninstall.bat
@echo off
rmdir /s /q venv
rmdir /s /q data
echo Uninstall complete. Models kept in models\ directory unless you delete them.
