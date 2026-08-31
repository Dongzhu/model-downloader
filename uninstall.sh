# uninstall.sh
#!/usr/bin/env bash
set -e
echo "Removing venv and data..."
rm -rf venv
rm -rf data
echo "Uninstall complete. Models kept in the models/ directory unless you delete them." 
