#!/bin/bash

# Exit on error, unset variables are an error
set -eu

# collect arguments

de_init=true

function usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "Options:"
  echo " -h, --help             Display this help message"
  echo " -k, --keep-submodules  Keep documentation repository checked out after build completes"
}

while [ $# -gt 0 ]; do
  case $1 in
  -h | --help)
    usage
    exit 0
    ;;
  -k | --keep-submodules)
    de_init=false
    ;;
  *)
    echo "Invalid option: $1" >&2
    exit 1
    ;;
  esac
  shift
done

# Main program

function echo_and_exit {
  echo "$1"
  exit 1
}


# create/clean build dir
mkdir build &>/dev/null || rm -rf build/*


# early-exit if npx is not available
if ! command -v npx &> /dev/null; then
  echo "npx must be installed!"
  echo "go to https://nodejs.org/en/download"
  exit 1
fi


echo "Initializing git submodules"
git submodule update --init --recursive team1661-site-docs || echo_and_exit "Failed to initialize documentation repository"


echo "Copying source files"
cp -r src/* build/ || echo_and_exit "Failed to copy source files"


echo "Building documentation"
pushd team1661-site-docs >/dev/null || echo_and_exit "Could not find team1661-site-docs"
echo "> Installing Quartz dependencies"
npm ci || echo_and_exit "Failed to install Quartz dependencies"
echo "> Building with Quartz"
npx quartz build || echo_and_exit "Failed to build with Quartz"
echo "> Moving build files"
mv public ../build/docs || echo_and_exit "Failed to move built documentation files"
popd >/dev/null || echo_and_exit "Failed to change directory to project root"

# clean up submodules unless we are told not to
if [ "$de_init" == true ]; then
  echo "Deinitializing git submodules"
  git submodule deinit team1661-site-docs
fi

echo "Done"