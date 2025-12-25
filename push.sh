#!/bin/bash
cd ~/VORTEX-AML
git add -A
git commit -m "${1:-Auto update $(date '+%Y-%m-%d %H:%M')}"
git push origin main
echo "✅ Pushed to GitHub"
