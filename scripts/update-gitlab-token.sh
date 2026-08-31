#!/usr/bin/env bash
# Update GitLab PAT across all auth contexts:
#   1. Git credentials (~/.git-credentials)
#   2. Docker registry (local)
#   3. Docker registry (VPS via villar-vps-iac)
#
# Usage: ./update-gitlab-token.sh

set -euo pipefail

read -rp "GitLab username: " USERNAME
read -rsp "GitLab personal access token: " TOKEN
echo

GITLAB_HOST="gitlab.petit.gg"
REGISTRY="glcr.petit.gg"

# 1. Git credentials
echo "Updating git credentials..."
# Remove old entry, add new one
sed -i "\|https://${GITLAB_HOST}|d" ~/.git-credentials 2>/dev/null || true
echo "https://${USERNAME}:${TOKEN}@${GITLAB_HOST}" >> ~/.git-credentials
chmod 600 ~/.git-credentials
echo "  ✓ ~/.git-credentials updated"

# 2. Local Docker registry
echo "Updating local Docker registry login..."
echo "$TOKEN" | docker login "$REGISTRY" -u "$USERNAME" --password-stdin
echo "  ✓ Local docker login updated"

# 3. VPS Docker registry
echo "Updating VPS Docker registry login..."
ssh villar-vps-iac "echo '$TOKEN' | docker login $REGISTRY -u $USERNAME --password-stdin"
echo "  ✓ VPS docker login updated"

echo ""
echo "All done! You can now use:"
echo "  git push"
echo "  just villar-release"
echo "  just villar-prod-deploy"
