#!/bin/bash

# Gas Tracker - Cron wrapper script
# This script activates the virtual environment and runs the gas tracker

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR" || exit 1

# Load environment variables
source setup_env.sh

# Activate virtual environment (uv-created venv)
source .venv/bin/activate

# Run the gas tracker
python go.py

# Exit with the same status as the Python script
exit $?
