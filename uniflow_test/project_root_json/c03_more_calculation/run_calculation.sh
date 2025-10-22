#!/bin/bash

# Run the more calculation pipeline
# This script executes the 15/3+2*8 calculation using registry tools

echo "Starting calculation pipeline: 15/3+2*8"
echo "======================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is required but not installed."
    exit 1
fi

# Run the calculation pipeline
python3 calculation_pipeline.py

# Capture exit code
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "======================================"
    echo "Calculation completed successfully!"
else
    echo "======================================"
    echo "Calculation failed with exit code: $exit_code"
    exit $exit_code
fi
