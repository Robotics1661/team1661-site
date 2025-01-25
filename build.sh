#!/bin/bash

if [ -d .venv ]; then
  echo "Virtual environment already exists"
else
  echo "Creating virtual environment"
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "Installing dependencies"
pip install -r development_assets/system_diagrams/requirements.txt

echo "Building system diagrams"
pushd development_assets/system_diagrams >/dev/null || (echo "Failed to change directory to system diagrams"; exit 1)
python3 assembler.py || (echo "Failed to build system diagrams"; exit 1)
popd >/dev/null || (echo "Failed to change directory to project root"; exit 1)

echo "Done"