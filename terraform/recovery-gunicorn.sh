#!/bin/bash
# ==============================================================================
# RECOVERY SCRIPT: Install missing Gunicorn and dependencies
# ==============================================================================
# Usage: Run this on each EC2 instance to fix the missing gunicorn module error
# Requirement: Must have sudo privileges
# ==============================================================================

set -e  # Exit on any error
set -o pipefail

# Logging
exec 1> >(tee -a /var/log/recovery-gunicorn.log)
exec 2>&1

echo "=========================================="
echo "Starting Gunicorn Recovery Script"
echo "Timestamp: $(date)"
echo "=========================================="

# Step 1: Verify we can access the repository
echo "[1/5] Verifying repository access..."
cd /apps/Arquisoft || {
    echo "ERROR: /apps/Arquisoft directory not found!"
    exit 1
}
echo "✓ Repository found at $(pwd)"

# Step 2: Pull latest requirements.txt from git
echo "[2/5] Pulling latest requirements.txt from git..."
sudo git fetch origin main || {
    echo "ERROR: Failed to fetch from origin"
    exit 1
}
sudo git checkout origin/main -- requirements.txt || {
    echo "ERROR: Failed to checkout requirements.txt"
    exit 1
}
echo "✓ requirements.txt updated"

# Verify gunicorn is in requirements.txt
if grep -q "gunicorn" requirements.txt; then
    echo "✓ Gunicorn found in requirements.txt"
else
    echo "ERROR: Gunicorn not found in requirements.txt"
    exit 1
fi

# Step 3: Upgrade pip
echo "[3/5] Upgrading pip..."
sudo pip3 install --upgrade pip --break-system-packages || {
    echo "ERROR: Failed to upgrade pip"
    exit 1
}
echo "✓ pip upgraded"

# Step 4: Install all dependencies
echo "[4/5] Installing dependencies from requirements.txt..."
sudo pip3 install -r requirements.txt --break-system-packages || {
    echo "ERROR: Failed to install requirements"
    exit 1
}
echo "✓ All dependencies installed"

# Verify gunicorn installation
if python3 -c "import gunicorn" 2>/dev/null; then
    GUNICORN_VERSION=$(python3 -c "import gunicorn; print(gunicorn.__version__)")
    echo "✓ Gunicorn $GUNICORN_VERSION verified"
else
    echo "ERROR: Gunicorn import failed"
    exit 1
fi

# Step 5: Restart gunicorn service
echo "[5/5] Restarting Gunicorn service..."
sudo systemctl restart gunicorn || {
    echo "ERROR: Failed to restart gunicorn service"
    exit 1
}
echo "✓ Gunicorn service restarted"

# Verify service is running
echo ""
echo "=========================================="
echo "Verification"
echo "=========================================="

sleep 2

if sudo systemctl is-active --quiet gunicorn; then
    echo "✓ Gunicorn service is RUNNING"
    sudo systemctl status gunicorn --no-pager
else
    echo "✗ Gunicorn service is NOT running"
    echo "Checking logs..."
    sudo journalctl -u gunicorn -n 20 --no-pager
    exit 1
fi

echo ""
echo "=========================================="
echo "Recovery completed successfully!"
echo "=========================================="
