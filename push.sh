#!/bin/bash
# ============================================================
# push.sh — One-time setup: create GitHub repo and push
# 5-Day AI Agents: Intensive Vibe Coding Course With Google
# ============================================================
# Prerequisites:
#   - Git installed
#   - GitHub CLI installed: https://cli.github.com/
#     (run `gh auth login` first if not already authenticated)
# ============================================================

set -e

REPO_NAME="5day-ai-agents-vibecoding"

echo "🚀 Step 1: Initialise git repo..."
git init
git checkout -b main

echo "📦 Step 2: Create GitHub repo..."
gh repo create $REPO_NAME --public --description "5-Day AI Agents: Intensive Vibe Coding Course With Google × Kaggle" --source=. --remote=origin

echo "✅ Step 3: Stage and commit on main..."
git add .
git commit -m "init: 5-Day AI Agents Intensive repo structure"

echo "⬆️  Step 4: Push main branch..."
git push -u origin main

echo "🌿 Step 5: Create and push day1 branch..."
git checkout -b day1
git push -u origin day1
git checkout main

echo ""
echo "✅ Done! Repo live at:"
echo "   https://github.com/$(gh api user --jq .login)/$REPO_NAME"
echo ""
echo "Branches: main, day1"
