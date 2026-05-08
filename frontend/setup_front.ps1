Write-Host "====================================="
Write-Host " Policy Scanner Frontend Setup"
Write-Host "====================================="

# -------------------------------------------------
# 1. Move to frontend directory
# -------------------------------------------------
Set-Location -Path "C:\Users\security-dashboard\frontend"

Write-Host ""
Write-Host "📁 Current directory:"
Get-Location

# -------------------------------------------------
# 2. Verify Node.js
# -------------------------------------------------
Write-Host ""
Write-Host "🔍 Verifying Node.js..."

try {
    $nodeVersion = node -v
    Write-Host "✅ Node.js version: $nodeVersion"
}
catch {
    Write-Host "❌ Node.js is not installed"
    exit 1
}

# -------------------------------------------------
# 3. Verify npm
# -------------------------------------------------
Write-Host ""
Write-Host "🔍 Verifying npm..."

try {
    $npmVersion = npm -v
    Write-Host "✅ npm version: $npmVersion"
}
catch {
    Write-Host "❌ npm is not installed"
    exit 1
}

# -------------------------------------------------
# 4. Verify npm registry
# -------------------------------------------------
Write-Host ""
Write-Host "🔍 Checking npm registry..."

npm config get registry

# -------------------------------------------------
# 5. Disable strict SSL (if corporate proxy/JFrog)
# -------------------------------------------------
Write-Host ""
Write-Host "🔧 Setting npm strict-ssl to false..."

npm config set strict-ssl false

# -------------------------------------------------
# 6. Install frontend dependencies
# -------------------------------------------------
Write-Host ""
Write-Host "📦 Installing frontend dependencies..."

npm install
npm install axios

# -------------------------------------------------
# 7. Ollama instructions
# -------------------------------------------------
Write-Host ""
Write-Host "====================================="
Write-Host " IMPORTANT - START OLLAMA SEPARATELY "
Write-Host "====================================="
Write-Host ""
Write-Host "Open NEW PowerShell window and run:"
Write-Host ""
Write-Host '$env:OLLAMA_HOST="0.0.0.0:11434"'
Write-Host "ollama serve"
Write-Host ""
Write-Host "Verify:"
Write-Host "http://192.168.1.172:11434"
Write-Host ""

# -------------------------------------------------
# 8. Start frontend
# -------------------------------------------------
Write-Host "🚀 Starting frontend..."

npm run dev