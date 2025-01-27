#!/bin/bash

mkdir build || rm -rf build/*

USE_SVGO=1

function usage {
  echo "Usage: build.sh [flags]"
  echo "Flags:"
  echo "  --no-svgo: Skip SVG optimization"
}

function echo_and_exit {
  echo "$1"
  exit 1
}

# check for flags
for arg in "$@"
do
  if [ "$arg" == "--no-svgo" ]; then
    USE_SVGO=0
  elif [ "$arg" == "-h" ] || [ "$arg" == "--help" ]; then
    usage
    exit 0
  else
    echo "Unknown flag: $arg"
    usage
    exit 1
  fi
done

####################
# Copy over source #
####################
echo "Copying source files"
cp -r src/* build/
# remove the dev-env link
rm build/assets/system_diagrams

########################
# System diagram build #
########################

# todo use netlify cache

if [ -d .venv ]; then
  echo "Virtual environment already exists"
else
  echo "Creating virtual environment"
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "Installing dependencies"
pip install -r development_assets/system_diagrams/requirements.txt

# Try to find or install svgo (a utility that optimizes SVG files)
# skip if --no-svgo flag is present
if [ "$USE_SVGO" -eq 1 ]; then
  echo "Checking for svgo"
  if ! command -v svgo &> /dev/null
  then
    echo "svgo could not be found, checking for npm"
    if ! command -v npm &> /dev/null
    then
      echo "npm could not be found, will not optimize svgs"
      USE_SVGO=0
    else
      echo "npm found, installing svgo"
      USE_SVGO=$( (npm install -g svgo && echo 1) || echo 0 )
      if [ "$USE_SVGO" -eq 0 ]; then
        echo "Failed to install svgo, will not optimize svgs"
      else
        echo "svgo installed"
      fi
    fi
  fi
fi

echo "Building system diagrams"
pushd development_assets/system_diagrams >/dev/null || echo_and_exit "Failed to change directory to system diagrams"
python3 assembler.py || echo_and_exit "Failed to build system diagrams"
if [ "$USE_SVGO" -eq 1 ]; then
  echo "Optimizing SVGs"
  svgo -f output
fi
popd >/dev/null || echo_and_exit "Failed to change directory to project root"

mkdir build/assets/system_diagrams
cp -r development_assets/system_diagrams/output/* build/assets/system_diagrams/

echo "Done"