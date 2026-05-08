#!/bin/bash

set -e  # stop if any command fails

echo "🚀 Starting SecureScan backend setup..."

# -----------------------------
# 1. Go to backend directory
# -----------------------------
cd /home/ansible/security-dashboard/backend

echo "📁 Moved to backend directory"

# -----------------------------
# 2. Check JFrog pip config
# -----------------------------
PIP_CONF="$HOME/.pip/pip.conf"

if [ ! -f "$PIP_CONF" ]; then
    echo "❌ pip.conf not found at $PIP_CONF"
    exit 1
fi

if ! grep -q "index-url" "$PIP_CONF"; then
    echo "❌ JFrog index-url not configured in pip.conf"
    exit 1
fi

echo "✅ pip.conf verified"

# -----------------------------
# 3. Activate virtual env
# -----------------------------
if [ ! -d "venv" ]; then
    echo "❌ venv not found"
    exit 1
fi

source venv/bin/activate

echo "🐍 Virtual environment activated"

# -----------------------------
# 4. Install dependencies
# -----------------------------
echo "📦 Installing dependencies..."

pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, skipping install"
fi

echo "✅ Dependencies checked"

# -----------------------------
# 5. Start backend server
# -----------------------------
echo "🔥 Starting FastAPI server..."

uvicorn main:app --reload --host 0.0.0.0 --port 8000