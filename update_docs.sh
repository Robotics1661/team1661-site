#!/bin/bash

function echo_and_exit {
  echo "$1"
  exit 1
}

echo "Pulling team1661-site-docs"
git submodule update --init --remote team1661-site-docs || echo_and_exit "Failed to pull documentation repository"

echo "Committing the update"
# use `git status --porcelain` to save current stage
git_status=$(git status --porcelain)
git restore --staged . || echo_and_exit "Failed to unstage changes for a clean commit"
git add team1661-site-docs || echo_and_exit "Failed to stage documentation repository"
git commit -m "Update team1661-site-docs" || echo_and_exit "Failed to commit documentation update"
# re-add changes, but only if they were added before
IFS=$'\n'
for line in $git_status; do
  if [[ $line == "M"* || $line == "A"* ]]; then
    git add "${line:3}" || echo_and_exit "Failed to re-add changes"
  fi
done

echo "Deinitializing team1661-site-docs"
git submodule deinit team1661-site-docs || echo_and_exit "Failed to deinitialize documentation repository"
echo "Done"