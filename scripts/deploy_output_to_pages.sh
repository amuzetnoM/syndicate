#!/usr/bin/env bash
set -euo pipefail

# Deploy contents of 'output/' to the gh-pages branch under 'outputs/<date>/'.
# Requires: GITHUB_TOKEN (repo write) and git installed.

REPO=${GITHUB_REPOSITORY:-amuzetnoM/syndicate}
BRANCH=gh-pages
DATE=$(date -u +"%Y-%m-%d_%H%MZ")
TEMP_DIR=$(mktemp -d)

echo "Cloning ${REPO}@${BRANCH} into ${TEMP_DIR}"
GIT_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"

git clone --depth 1 --branch ${BRANCH} "${GIT_URL}" "${TEMP_DIR}"
cd "${TEMP_DIR}"

# Prepare output path
mkdir -p "outputs/${DATE}"

# Copy files from main repo output (caller should provide working dir that contains 'output/')
# Typical usage from CI: uses actions/checkout to fetch repo, then runs this script with GITHUB_TOKEN available
rsync -a --delete --exclude '.git' "$GITHUB_WORKSPACE/output/" "outputs/${DATE}/" || true

# Commit & push
git add outputs/${DATE}
if git diff --cached --quiet; then
  echo "No changes to deploy."
else
  git commit -m "deploy: publish output snapshot ${DATE}"
  git push origin ${BRANCH}
fi

# Cleanup
cd -
rm -rf "${TEMP_DIR}"

echo "Deployed output to ${REPO}::${BRANCH}/outputs/${DATE}/"
