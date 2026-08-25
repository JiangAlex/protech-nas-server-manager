#!/bin/bash
# ProTech NAS — Project Dependencies Setup
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== ProTech NAS — Setting Up Project Dependencies ==="

# Backend
echo "[1/3] Setting up Python backend..."
cd "$PROJECT_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
echo "  Backend OK."

# Frontend
echo "[2/3] Setting up Vue.js frontend..."
cd "$PROJECT_DIR/frontend"
npm install
echo "  Frontend OK."

# Build frontend
echo "[3/3] Building frontend for production..."
npm run build
echo "  Frontend built to dist/."

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start development:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn src.main:app --reload --port 8000"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "For production:"
echo "  Backend:  cd backend && source .venv/bin/activate && uvicorn src.main:app --host 0.0.0.0 --port 8000"
echo "  Frontend: Serve frontend/dist/ with nginx or similar"
