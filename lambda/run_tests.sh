#!/bin/bash
# Script to run Lambda tests in a virtual environment

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -q pytest hypothesis moto boto3

# Run tests
PYTHONPATH=. python -m pytest tests/test_properties.py::TestProperty8RatingPersistenceRoundTrip tests/test_properties.py::TestProperty9RatingUpdate tests/test_properties.py::TestProperty10SessionDataIntegrity tests/test_properties.py::TestProperty11SessionIdUniqueness -v

# Deactivate venv
deactivate
